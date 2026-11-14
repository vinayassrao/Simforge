"""Read-only reference data: agents, the action schema and the built-in documentation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from app.api.deps import AppSettings
from app.api.errors import error_response
from app.evaluation import SCORING_RULES
from app.schemas import ErrorResponse
from simulation.actions import ACTION_DESCRIPTIONS
from simulation.agent import ALLOWED_TRANSITIONS
from simulation.controller import SPEEDS
from simulation.observation import Observation
from simulation.types import Action, AgentState

router = APIRouter(tags=["Reference"])

AGENTS: list[dict[str, Any]] = [
    {
        "id": "manual",
        "name": "Manual control",
        "kind": "Human operator",
        "description": "Drive the robot yourself with the on-screen control pad or the keyboard.",
        "how_it_acts": "Each button press is sent to the actions endpoint as one action.",
    },
    {
        "id": "astar",
        "name": "Built-in A* agent",
        "kind": "Autonomous baseline",
        "description": (
            "Plans the shortest action sequence with A* search over position and heading, "
            "and re-plans whenever a moving obstacle blocks the route."
        ),
        "how_it_acts": "Runs inside the simulation process and issues the same actions as any other agent.",
    },
    {
        "id": "external",
        "name": "External Python agent",
        "kind": "Your own code",
        "description": "Any program that can make HTTP requests: read the observation, post an action, repeat.",
        "how_it_acts": "Calls the REST API from its own process. No API key is needed.",
    },
]
DOC_GROUPS = {
    "workflows": "Workflows",
    "debugging": "Debugging",
    "architecture": "Architecture",
    "api": "API",
}
SLUG_PATTERN = re.compile(r"^[a-z0-9_\-]+$")


@router.get("/agents/", summary="Agent types, the action schema and the state machine")
def read_agents(settings: AppSettings):
    return {
        "agents": AGENTS,
        "actions": [{"name": action.value, **ACTION_DESCRIPTIONS[action]} for action in Action],
        "states": [
            {"name": state.value, "next": sorted(target.value for target in ALLOWED_TRANSITIONS[state])}
            for state in AgentState
        ],
        "speeds": list(SPEEDS),
        "scoring": SCORING_RULES,
        "observation_schema": Observation.model_json_schema(),
        "examples": {
            path.name: path.read_text(encoding="utf-8")
            for path in sorted((settings.examples_dir / "agents").glob("*.py"))
        },
    }


def _title(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("_", " ").title()


def _documents(settings) -> list[dict[str, str]]:
    documents = []
    for folder, group in DOC_GROUPS.items():
        for path in sorted((settings.docs_dir / folder).glob("*.md")):
            documents.append(
                {"slug": f"{folder}-{path.stem}", "title": _title(path), "group": group, "path": str(path)}
            )
    for path in sorted((settings.examples_dir / "task_definitions").glob("*.md")):
        documents.append(
            {
                "slug": f"tasks-{path.stem}",
                "title": _title(path),
                "group": "Task specifications",
                "path": str(path),
            }
        )
    return documents


@router.get("/documents/", summary="The built-in guides, workflows and task specifications")
def list_documents(settings: AppSettings):
    return [{key: doc[key] for key in ("slug", "title", "group")} for doc in _documents(settings)]


@router.get("/documents/{slug}/", responses={404: {"model": ErrorResponse}}, summary="One guide as Markdown")
def read_document(slug: str, settings: AppSettings):
    if SLUG_PATTERN.match(slug):
        for document in _documents(settings):
            if document["slug"] == slug:
                content = Path(document["path"]).read_text(encoding="utf-8")
                return {
                    "slug": slug,
                    "title": document["title"],
                    "group": document["group"],
                    "content": content,
                }
    return error_response(404, "document_not_found", f"No document named '{slug}'.")
