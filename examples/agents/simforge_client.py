"""Minimal SIMFORGE API client for external agents. Standard library only.

Usage::

    client = SimforgeClient("http://127.0.0.1:8000")
    episode_id = client.create_episode("basic-delivery", seed=7)
    observation = client.start(episode_id)
    result = client.act(episode_id, "MOVE_FORWARD")
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

API_PREFIX = "/api/v1"
TIMEOUT_SECONDS = 15


class SimforgeError(RuntimeError):
    """The server rejected a request. ``code`` is the machine-readable reason."""

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(f"{status} {code}: {message}")
        self.status = status
        self.code = code


class SimforgeClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000") -> None:
        self._base = base_url.rstrip("/") + API_PREFIX

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        data = json.dumps(body).encode() if body is not None else (b"" if method == "POST" else None)
        request = urllib.request.Request(
            self._base + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as error:
            payload = json.loads(error.read() or b"{}").get("error", {})
            raise SimforgeError(
                error.code,
                payload.get("code", "http_error"),
                payload.get("message", ""),
            ) from None
        except urllib.error.URLError as error:
            raise SimforgeError(0, "unreachable", f"Cannot reach {self._base}: {error.reason}") from None

    def create_episode(self, scenario_id: str, seed: int | None = None) -> str:
        """Create an episode driven by an external agent and return its id."""
        body: dict[str, Any] = {"scenario_id": scenario_id, "agent_mode": "external"}
        if seed is not None:
            body["seed"] = seed
        return self._request("POST", "/episodes/", body)["id"]

    def start(self, episode_id: str) -> dict[str, Any]:
        """Start the episode and return the first observation."""
        return self._request("POST", f"/episodes/{episode_id}/start/")["observation"]

    def observe(self, episode_id: str) -> dict[str, Any]:
        return self._request("GET", f"/episodes/{episode_id}/observation/")

    def act(self, episode_id: str, action: str) -> dict[str, Any]:
        """Send one action. Returns success, message, done and the new observation."""
        return self._request("POST", f"/episodes/{episode_id}/actions/", {"action": action})

    def evaluation(self, episode_id: str) -> dict[str, Any]:
        return self._request("GET", f"/episodes/{episode_id}/evaluation/")
