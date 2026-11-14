from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.api.deps import AppSettings
from app.api.errors import error_response
from app.schemas import ErrorResponse, ScenarioDetail, ScenarioOut
from app.services.serializers import scenario_to_dict
from simulation.scenarios import get_scenario, list_scenarios

router = APIRouter(prefix="/scenarios", tags=["Scenarios"])


@router.get("/", response_model=list[ScenarioOut], summary="List the available scenarios")
def read_scenarios():
    return [scenario_to_dict(scenario) for scenario in list_scenarios()]


@router.get(
    "/{scenario_id}/",
    response_model=ScenarioDetail,
    responses={404: {"model": ErrorResponse}},
    summary="Describe one scenario, including its layout and scoring",
)
def read_scenario(scenario_id: str):
    return scenario_to_dict(get_scenario(scenario_id), detailed=True)


@router.get(
    "/{scenario_id}/thumbnail/",
    response_class=FileResponse,
    responses={404: {"model": ErrorResponse}},
    summary="A Panda3D render of the scenario's starting scene",
)
def read_thumbnail(scenario_id: str, settings: AppSettings):
    scenario = get_scenario(scenario_id)
    path = settings.thumbnail_dir / f"{scenario.id}.jpg"
    if not path.exists():
        return error_response(404, "thumbnail_unavailable", "No render is available for this scenario yet.")
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "max-age=300"})
