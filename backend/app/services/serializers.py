"""Convert database records and scenario definitions into API dictionaries."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.models import EpisodeRecord, EventRecord
from simulation.scenarios.base import ScenarioDefinition
from simulation.types import AgentMode, ZoneKind


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()


def episode_to_dict(record: EpisodeRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "scenario_id": record.scenario_id,
        "scenario_name": record.scenario_name,
        "agent_mode": record.agent_mode,
        "seed": record.seed,
        "status": record.status,
        "created_at": iso(record.created_at),
        "started_at": iso(record.started_at),
        "finished_at": iso(record.finished_at),
        "steps": record.steps,
        "progress": record.progress,
        "collisions": record.collisions,
        "invalid_actions": record.invalid_actions,
        "elapsed_seconds": record.elapsed_seconds,
        "score": record.score,
        "success": record.success,
        "failure_reason": record.failure_reason,
    }


def event_to_dict(record: EventRecord) -> dict[str, Any]:
    return {
        "seq": record.seq,
        "episode_id": record.episode_id,
        "step": record.step,
        "type": record.type,
        "category": record.category,
        "description": record.description,
        "entity_id": record.entity_id,
        "data": record.data,
        "timestamp": record.timestamp,
    }


def scenario_to_dict(scenario: ScenarioDefinition, detailed: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": scenario.id,
        "name": scenario.name,
        "summary": scenario.summary,
        "description": scenario.description,
        "instructions": scenario.instructions,
        "difficulty": scenario.difficulty,
        "task_type": scenario.task_type,
        "complexity": scenario.complexity,
        "estimated_minutes": scenario.estimated_minutes,
        "objectives": len(scenario.packages),
        "moving_obstacles": len(scenario.patrols),
        "static_obstacles": len(scenario.static_obstacles),
        "grid": {"width": scenario.width, "height": scenario.height},
        "max_steps": scenario.max_steps,
        "default_seed": scenario.default_seed,
        "available_agents": [mode.value for mode in AgentMode],
        "thumbnail_url": f"/api/v1/scenarios/{scenario.id}/thumbnail/",
    }
    if not detailed:
        return payload
    payload.update(
        {
            "max_collisions": scenario.max_collisions,
            "time_limit_s": scenario.time_limit_s,
            "completion_conditions": list(scenario.completion_conditions),
            "failure_conditions": list(scenario.failure_conditions),
            "evaluation_criteria": [
                {"label": label, "points": points, "description": description}
                for label, points, description in scenario.evaluation_criteria
            ],
            "packages": [
                {
                    "id": spec.id,
                    "name": spec.name,
                    "category": spec.category,
                    "color": spec.color,
                    "weight_kg": spec.weight_kg,
                    "destination_zone_id": spec.destination_zone_id,
                    "destination_zone_name": scenario.zone(spec.destination_zone_id).name,
                }
                for spec in scenario.packages
            ],
            "layout": {
                "start": list(scenario.start_cell),
                "start_orientation": scenario.start_orientation.value,
                "shelves": sorted(scenario.shelves),
                "static_obstacles": sorted(scenario.static_obstacles),
                "checkpoints": list(scenario.checkpoints),
                "patrols": [
                    {
                        "id": patrol.id,
                        "name": patrol.name,
                        "start": list(patrol.start),
                        "end": list(patrol.end),
                    }
                    for patrol in scenario.patrols
                ],
                "zones": [
                    {
                        "id": zone.id,
                        "name": zone.name,
                        "kind": zone.kind.value,
                        "color": zone.color,
                        "cells": sorted(zone.cells),
                    }
                    for zone in scenario.zones
                    if zone.cells or zone.kind is not ZoneKind.RESTRICTED
                ],
            },
        }
    )
    return payload
