"""Start the SIMFORGE server: ``python run.py``."""

from __future__ import annotations

import argparse

import uvicorn

from app.main import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the SIMFORGE API and web interface.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    arguments = parser.parse_args()
    uvicorn.run(create_app(), host=arguments.host, port=arguments.port, timeout_graceful_shutdown=3)


if __name__ == "__main__":
    main()
