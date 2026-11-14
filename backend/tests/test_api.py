import csv
import io

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.gateway import InlineGateway
from simulation.observation import Observation

API = "/api/v1"


def create(client, scenario="basic-delivery", mode="manual", seed=None) -> dict:
    body = {"scenario_id": scenario, "agent_mode": mode}
    if seed is not None:
        body["seed"] = seed
    response = client.post(f"{API}/episodes/", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def act(client, episode_id: str, action: str) -> dict:
    response = client.post(f"{API}/episodes/{episode_id}/actions/", json={"action": action})
    assert response.status_code == 200, response.text
    return response.json()


def run_to_end(client, episode_id: str) -> None:
    """Step the built-in agent until the episode finishes."""
    client.post(f"{API}/episodes/{episode_id}/start/")
    for _ in range(400):
        if client.post(f"{API}/episodes/{episode_id}/step/").json()["done"]:
            return
    pytest.fail("the episode did not finish")


def error_code(response) -> str:
    body = response.json()
    assert set(body) == {"error"} and set(body["error"]) == {"code", "message", "details"}
    return body["error"]["code"]


class TestReferenceEndpoints:
    def test_health_reports_the_simulation_backend(self, client):
        body = client.get(f"{API}/health/").json()

        assert body["status"] == "ok"
        assert body["simulation"] == "inline" and body["rendering"] is False
        assert body["active_episode_id"] is None

    def test_scenarios_are_listed_with_their_task_information(self, client):
        scenarios = client.get(f"{API}/scenarios/").json()

        assert [scenario["id"] for scenario in scenarios] == [
            "basic-delivery",
            "obstacle-navigation",
            "multi-step-delivery",
        ]
        assert [scenario["moving_obstacles"] for scenario in scenarios] == [0, 3, 1]
        assert scenarios[2]["objectives"] == 2

    def test_scenario_detail_includes_layout_and_scoring(self, client):
        detail = client.get(f"{API}/scenarios/obstacle-navigation/").json()

        assert sum(item["points"] for item in detail["evaluation_criteria"]) == 100
        assert detail["layout"]["start"] == [0, 0]
        assert len(detail["layout"]["patrols"]) == 3
        assert {zone["kind"] for zone in detail["layout"]["zones"]} == {
            "loading",
            "collection",
            "delivery",
            "restricted",
        }

    def test_unknown_scenario_and_missing_thumbnail_return_404(self, client):
        assert error_code(client.get(f"{API}/scenarios/nope/")) == "unknown_scenario"
        thumbnail = client.get(f"{API}/scenarios/basic-delivery/thumbnail/")
        assert thumbnail.status_code == 404 and error_code(thumbnail) == "thumbnail_unavailable"

    def test_agent_catalogue_describes_actions_states_and_examples(self, client):
        catalogue = client.get(f"{API}/agents/").json()

        assert [agent["id"] for agent in catalogue["agents"]] == ["manual", "astar", "external"]
        assert len(catalogue["actions"]) == 7
        assert all(action["precondition"] and action["failure"] for action in catalogue["actions"])
        assert {"baseline_agent.py", "custom_agent_template.py"} <= set(catalogue["examples"])
        assert "available_actions" in catalogue["observation_schema"]["properties"]

    def test_documents_are_listed_and_readable(self, client):
        documents = client.get(f"{API}/documents/").json()
        workflows = [doc for doc in documents if doc["group"] == "Workflows"]

        assert len(workflows) == 12
        assert sum(1 for doc in documents if doc["group"] == "Task specifications") >= 5
        body = client.get(f"{API}/documents/{workflows[0]['slug']}/").json()
        assert body["content"].startswith("# ")
        assert error_code(client.get(f"{API}/documents/does-not-exist/")) == "document_not_found"

    def test_rendering_endpoints_explain_that_rendering_is_off(self, client):
        assert error_code(client.get(f"{API}/simulation/stream/")) == "rendering_unavailable"
        assert error_code(client.get(f"{API}/simulation/frame/")) == "rendering_unavailable"
        assert client.post(f"{API}/simulation/view/", json={"grid": True}).json()["grid"] is True

    def test_unknown_api_path_returns_a_json_404(self, client):
        response = client.get(f"{API}/nothing-here/")

        assert response.status_code == 404 and error_code(response) == "not_found"

    def test_openapi_schema_documents_the_agent_endpoints(self, client):
        paths = client.get("/api/openapi.json").json()["paths"]

        assert "post" in paths[f"{API}/episodes/{{episode_id}}/actions/"]
        assert "get" in paths[f"{API}/episodes/{{episode_id}}/observation/"]
        assert client.get("/api/docs").status_code == 200


class TestEpisodeLifecycle:
    def test_create_episode_loads_it_into_the_simulation(self, client):
        episode = create(client, seed=42)

        assert episode["id"].startswith("ep-") and episode["status"] == "created"
        assert episode["seed"] == 42 and episode["is_active"] is True
        assert client.get(f"{API}/health/").json()["active_episode_id"] == episode["id"]
        assert client.get(f"{API}/episodes/{episode['id']}/state/").json()["observation"]["step"] == 0

    def test_create_rejects_bad_requests(self, client):
        unknown = client.post(f"{API}/episodes/", json={"scenario_id": "nope"})
        assert unknown.status_code == 404 and error_code(unknown) == "unknown_scenario"

        invalid = client.post(f"{API}/episodes/", json={"scenario_id": "basic-delivery", "agent_mode": "robot"})
        assert invalid.status_code == 422 and error_code(invalid) == "validation_error"
        assert invalid.json()["error"]["details"][0]["field"] == "agent_mode"

        negative = client.post(f"{API}/episodes/", json={"scenario_id": "basic-delivery", "seed": -1})
        assert negative.status_code == 422

    def test_controls_move_the_episode_through_its_states(self, client):
        episode_id = create(client)["id"]
        url = f"{API}/episodes/{episode_id}"

        assert client.post(f"{url}/start/").json()["status"] == "running"
        assert client.post(f"{url}/pause/").json()["status"] == "paused"
        assert client.get(f"{url}/").json()["status"] == "paused"
        assert client.post(f"{url}/resume/").json()["status"] == "running"

        conflict = client.post(f"{url}/start/")
        assert conflict.status_code == 409 and error_code(conflict) == "invalid_state"

    def test_reset_clears_progress_events_and_evaluation(self, client):
        episode_id = create(client, mode="astar")["id"]
        run_to_end(client, episode_id)
        assert client.get(f"{API}/episodes/{episode_id}/evaluation/").status_code == 200

        state = client.post(f"{API}/episodes/{episode_id}/reset/").json()

        assert state["status"] == "created" and state["metrics"]["steps"] == 0
        episode = client.get(f"{API}/episodes/{episode_id}/").json()
        assert episode["score"] is None and episode["trajectory"] == []
        assert client.get(f"{API}/episodes/{episode_id}/evaluation/").status_code == 409
        events = client.get(f"{API}/episodes/{episode_id}/events/").json()
        assert [event["type"] for event in events] == ["AGENT_SPAWNED", "SIMULATION_RESET"]

    def test_speed_can_be_changed_and_is_validated(self, client):
        episode_id = create(client, mode="astar")["id"]

        assert client.post(f"{API}/episodes/{episode_id}/speed/", json={"speed": 2}).json() == {"speed": 2.0}
        invalid = client.post(f"{API}/episodes/{episode_id}/speed/", json={"speed": 3})
        assert invalid.status_code == 422 and error_code(invalid) == "invalid_speed"

    def test_new_episode_aborts_the_unfinished_one(self, client):
        first = create(client)["id"]
        client.post(f"{API}/episodes/{first}/start/")

        second = create(client)["id"]

        old = client.get(f"{API}/episodes/{first}/").json()
        assert old["status"] == "aborted" and old["is_active"] is False
        stale = client.post(f"{API}/episodes/{first}/actions/", json={"action": "WAIT"})
        assert stale.status_code == 409 and error_code(stale) == "episode_not_active"
        assert error_code(client.get(f"{API}/episodes/{first}/state/")) == "episode_not_active"
        assert client.get(f"{API}/episodes/{second}/").json()["is_active"] is True

    def test_unknown_episode_returns_404_everywhere(self, client):
        for method, path in [
            ("get", ""),
            ("post", "start/"),
            ("get", "observation/"),
            ("get", "events/"),
            ("get", "evaluation/"),
            ("get", "export/"),
        ]:
            response = getattr(client, method)(f"{API}/episodes/ep-missing/{path}")
            assert response.status_code == 404, path
            assert error_code(response) == "episode_not_found"


class TestAgentInteraction:
    def test_observation_matches_the_published_schema(self, client):
        episode_id = create(client, "obstacle-navigation")["id"]
        client.post(f"{API}/episodes/{episode_id}/start/")

        body = client.get(f"{API}/episodes/{episode_id}/observation/").json()

        observation = Observation.model_validate(body)
        assert observation.episode_id == episode_id
        assert observation.agent.position == (0, 0)
        assert len(observation.obstacles.moving) == 3
        assert "MOVE_FORWARD" in body["available_actions"]

    def test_valid_action_changes_the_state(self, client):
        episode_id = create(client)["id"]
        client.post(f"{API}/episodes/{episode_id}/start/")

        result = act(client, episode_id, "MOVE_FORWARD")

        assert result["success"] is True and result["done"] is False
        assert result["observation"]["agent"]["position"] == [1, 0]
        assert client.get(f"{API}/episodes/{episode_id}/observation/").json()["step"] == 1

    def test_failed_action_explains_why_and_is_counted(self, client):
        episode_id = create(client)["id"]
        client.post(f"{API}/episodes/{episode_id}/start/")

        collision = act(client, episode_id, "MOVE_BACKWARD")
        pickup = act(client, episode_id, "PICK_UP")

        assert collision["success"] is False and collision["error_code"] == "collision"
        assert pickup["error_code"] == "no_object_in_range"
        assert "no package directly in front" in pickup["message"]
        episode = client.get(f"{API}/episodes/{episode_id}/").json()
        assert (episode["collisions"], episode["invalid_actions"], episode["steps"]) == (1, 1, 2)

    def test_actions_are_rejected_when_not_allowed(self, client):
        episode_id = create(client)["id"]
        url = f"{API}/episodes/{episode_id}/actions/"

        not_started = client.post(url, json={"action": "WAIT"})
        assert not_started.status_code == 409 and error_code(not_started) == "invalid_state"

        unknown = client.post(url, json={"action": "FLY"})
        assert unknown.status_code == 422 and error_code(unknown) == "validation_error"

        agent_episode = create(client, mode="astar")["id"]
        client.post(f"{API}/episodes/{agent_episode}/start/")
        refused = client.post(f"{API}/episodes/{agent_episode}/actions/", json={"action": "WAIT"})
        assert refused.status_code == 409 and error_code(refused) == "agent_controlled"

    def test_external_agent_can_complete_a_task_through_the_api(self, client):
        """Drive the robot with a tiny greedy policy that uses only API responses."""
        from agents.astar_agent import AStarAgent

        episode_id = create(client, mode="external")["id"]
        observation = client.post(f"{API}/episodes/{episode_id}/start/").json()["observation"]
        policy = AStarAgent()

        for _ in range(200):
            decision = policy.decide(Observation.model_validate(observation))
            result = act(client, episode_id, decision.action.value)
            observation = result["observation"]
            if result["done"]:
                break

        episode = client.get(f"{API}/episodes/{episode_id}/").json()
        assert episode["status"] == "completed" and episode["agent_mode"] == "external"
        assert client.get(f"{API}/episodes/{episode_id}/evaluation/").json()["success"] is True


class TestEventsAndEvaluation:
    def test_events_are_persisted_in_order_and_can_be_filtered(self, client):
        episode_id = create(client)["id"]
        client.post(f"{API}/episodes/{episode_id}/start/")
        for action in ("MOVE_FORWARD", "MOVE_BACKWARD", "MOVE_BACKWARD", "PICK_UP"):
            act(client, episode_id, action)
        url = f"{API}/episodes/{episode_id}/events/"

        events = client.get(url).json()

        assert [event["seq"] for event in events] == list(range(1, len(events) + 1))
        assert events[0]["type"] == "AGENT_SPAWNED"
        assert {"timestamp", "episode_id", "step", "type", "description", "entity_id", "data"} <= set(events[0])
        collisions = client.get(url, params={"category": "collision"}).json()
        assert [event["type"] for event in collisions] == ["COLLISION"]
        assert [event["type"] for event in client.get(url, params={"category": "error"}).json()] == ["PICKUP_FAILED"]
        assert client.get(url, params={"after_seq": events[-2]["seq"]}).json() == events[-1:]
        assert client.get(url, params={"category": "nonsense"}).status_code == 422

    def test_evaluation_is_unavailable_until_the_episode_ends(self, client):
        episode_id = create(client, mode="astar")["id"]

        pending = client.get(f"{API}/episodes/{episode_id}/evaluation/")

        assert pending.status_code == 409 and error_code(pending) == "not_evaluated"

    def test_completed_run_is_evaluated_and_persisted(self, client):
        episode_id = create(client, mode="astar")["id"]
        run_to_end(client, episode_id)

        report = client.get(f"{API}/episodes/{episode_id}/evaluation/").json()
        episode = client.get(f"{API}/episodes/{episode_id}/").json()

        assert report["success"] is True and report["score"] == 100.0
        assert report["metrics"]["steps"] == report["metrics"]["baseline_steps"] == episode["steps"]
        assert episode["status"] == "completed" and episode["score"] == 100.0
        assert episode["finished_at"] is not None
        assert len(episode["trajectory"]) == episode["steps"] + 1

    def test_failed_run_is_evaluated_with_its_failure_reason(self, client):
        episode_id = create(client)["id"]
        client.post(f"{API}/episodes/{episode_id}/start/")

        for _ in range(8):
            result = act(client, episode_id, "MOVE_BACKWARD")

        assert result["done"] is True
        report = client.get(f"{API}/episodes/{episode_id}/evaluation/").json()
        assert report["success"] is False and report["failure_reason"] == "collision_limit_exceeded"
        assert report["score"] == 5.0  # only the valid-action points remain
        assert len(report["incident_locations"]) == 8
        assert client.get(f"{API}/episodes/{episode_id}/").json()["status"] == "failed"

    def test_evaluations_and_overview_aggregate_stored_runs(self, client):
        assert client.get(f"{API}/evaluations/").json()["summary"]["total_episodes"] == 0
        assert client.get(f"{API}/overview/").json()["average_score"] is None

        winner = create(client, mode="astar")["id"]
        run_to_end(client, winner)
        loser = create(client)["id"]
        client.post(f"{API}/episodes/{loser}/start/")
        for _ in range(8):
            act(client, loser, "MOVE_BACKWARD")

        evaluations = client.get(f"{API}/evaluations/").json()
        overview = client.get(f"{API}/overview/").json()

        assert evaluations["summary"] == {
            "total_episodes": 2,
            "success_rate": 0.5,
            "average_score": 52.5,
            "average_completion_steps": float(evaluations["items"][0]["steps"]),
            "collision_rate": 0.5,
        }
        assert [item["id"] for item in evaluations["items"]] == [winner, loser]
        assert (overview["total_runs"], overview["successful_runs"], overview["average_score"]) == (2, 1, 52.5)
        assert overview["recent_episodes"][0]["id"] == loser
        assert overview["recent_events"][0]["type"] == "TASK_FAILED"

    def test_episode_list_filters(self, client):
        winner = create(client, mode="astar")["id"]
        run_to_end(client, winner)
        other = create(client, "obstacle-navigation")["id"]

        def ids(**params):
            return [episode["id"] for episode in client.get(f"{API}/episodes/", params=params).json()]

        assert ids() == [other, winner]
        assert ids(scenario_id="obstacle-navigation") == [other]
        assert ids(agent_mode="astar") == [winner]
        assert ids(status="completed") == [winner]
        assert ids(min_score=90) == [winner]
        assert ids(limit=1) == [other]

    def test_export_as_json_and_csv(self, client):
        episode_id = create(client, mode="astar")["id"]
        run_to_end(client, episode_id)

        exported = client.get(f"{API}/episodes/{episode_id}/export/")
        as_csv = client.get(f"{API}/episodes/{episode_id}/export/", params={"format": "csv"})

        body = exported.json()
        assert set(body) == {"episode", "evaluation", "events"}
        assert body["evaluation"]["score"] == 100.0
        assert "attachment" in exported.headers["content-disposition"]
        rows = list(csv.DictReader(io.StringIO(as_csv.text)))
        assert len(rows) == len(body["events"])
        assert rows[-1]["type"] == "TASK_COMPLETED"
        assert as_csv.headers["content-type"].startswith("text/csv")


class TestLiveUpdatesAndPersistence:
    def test_websocket_pushes_state_events_and_the_final_evaluation(self, client):
        episode_id = create(client, mode="astar")["id"]

        with client.websocket_connect(f"/ws/episodes/{episode_id}/") as socket:
            hello = socket.receive_json()
            assert hello["type"] == "hello"
            assert hello["episode"]["id"] == episode_id and hello["state"]["status"] == "created"

            client.post(f"{API}/episodes/{episode_id}/start/")
            received = [socket.receive_json(), socket.receive_json()]
            assert [message["type"] for message in received] == ["events", "state"]
            assert received[1]["state"]["status"] == "running"

            run_to_end(client, episode_id)
            finished = None
            for _ in range(2000):
                message = socket.receive_json()
                if message["type"] == "finished":
                    finished = message
                    break
            assert finished is not None and finished["evaluation"]["success"] is True

    def test_websocket_for_unknown_episode_is_closed(self, client):
        from starlette.websockets import WebSocketDisconnect

        with (
            pytest.raises(WebSocketDisconnect) as closed,
            client.websocket_connect("/ws/episodes/ep-missing/") as socket,
        ):
            socket.receive_json()

        assert closed.value.code == 4404

    def test_runs_survive_a_restart_and_open_ones_are_closed(self, client, settings):
        finished = create(client, mode="astar")["id"]
        run_to_end(client, finished)
        unfinished = create(client)["id"]
        client.post(f"{API}/episodes/{unfinished}/start/")

        with TestClient(create_app(settings, InlineGateway())) as restarted:
            episodes = {episode["id"]: episode for episode in restarted.get(f"{API}/episodes/").json()}
            report = restarted.get(f"{API}/episodes/{finished}/evaluation/").json()
            events = restarted.get(f"{API}/episodes/{finished}/events/").json()

        assert episodes[finished]["status"] == "completed" and episodes[finished]["score"] == 100.0
        assert episodes[unfinished]["status"] == "aborted"
        assert report["success"] is True
        assert events[-1]["type"] == "TASK_COMPLETED"


class TestFrontendServing:
    def test_missing_build_is_explained(self, client):
        response = client.get("/")

        assert response.status_code == 404 and error_code(response) == "frontend_not_built"

    def test_built_frontend_is_served_with_client_side_routing(self, settings):
        settings.frontend_dist.mkdir(parents=True)
        (settings.frontend_dist / "index.html").write_text("<!doctype html><title>SIMFORGE</title>", encoding="utf-8")
        (settings.frontend_dist / "favicon.svg").write_text("<svg/>", encoding="utf-8")

        with TestClient(create_app(settings, InlineGateway())) as served:
            assert "SIMFORGE" in served.get("/").text
            assert "SIMFORGE" in served.get("/evaluations/ep-123").text
            assert served.get("/favicon.svg").text == "<svg/>"
            assert served.get("/../secret.txt").status_code in (200, 404)
            assert served.get(f"{API}/health/").json()["status"] == "ok"
