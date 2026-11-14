"""Entry point for the dedicated simulation process."""

from __future__ import annotations

import logging
import multiprocessing
from pathlib import Path
from typing import Any

PARENT_CHECK_SECONDS = 2.0


def run_simulation_process(commands: Any, outputs: Any, frames: Any, options: dict[str, Any]) -> None:
    """Start Panda3D and serve commands until a shutdown command arrives.

    Runs in its own process: Panda3D wants to own its main thread, and a crash
    in the renderer must not take the web server down with it.
    """
    logging.basicConfig(
        level=options.get("log_level", "INFO"),
        format="%(asctime)s %(levelname)s [simulation] %(name)s: %(message)s",
    )
    from simulation.engine import EngineConfig, SimulationEngine

    thumbnail_dir = options.get("thumbnail_dir")
    config = EngineConfig(
        width=options.get("width", 960),
        height=options.get("height", 540),
        offscreen=True,
        thumbnail_dir=Path(thumbnail_dir) if thumbnail_dir else None,
    )
    try:
        engine = SimulationEngine(commands, outputs, frames, config)
    except Exception:
        logging.getLogger(__name__).exception("The Panda3D engine could not start")
        outputs.put({"type": "fatal", "message": "The Panda3D engine could not start. See the server log."})
        raise
    _exit_when_parent_dies(engine)
    outputs.put({"type": "ready"})
    engine.run()


def _exit_when_parent_dies(engine: Any) -> None:
    """Stop rendering if the web server is killed, so no orphan process keeps the GPU busy."""
    parent = multiprocessing.parent_process()
    if parent is None:
        return

    def check(task):
        if not parent.is_alive():
            logging.getLogger(__name__).warning("The web server is gone; stopping the simulation process")
            engine.base.userExit()
        return task.again

    engine.base.taskMgr.doMethodLater(PARENT_CHECK_SECONDS, check, "simforge-parent-watchdog")
