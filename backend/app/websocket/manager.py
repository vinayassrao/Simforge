"""WebSocket connections grouped by episode, with thread-safe publishing."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, episode_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[episode_id].add(websocket)

    def disconnect(self, episode_id: str, websocket: WebSocket) -> None:
        self._connections[episode_id].discard(websocket)
        if not self._connections[episode_id]:
            del self._connections[episode_id]

    def publish(self, episode_id: str | None, message: dict[str, Any]) -> None:
        """Queue a message for one episode's clients, or for everyone if ``episode_id`` is None.

        Safe to call from any thread, including the simulation output pump.
        """
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        asyncio.run_coroutine_threadsafe(self._broadcast(episode_id, message), loop)

    async def _broadcast(self, episode_id: str | None, message: dict[str, Any]) -> None:
        if episode_id is None:
            targets = [socket for sockets in self._connections.values() for socket in sockets]
        else:
            targets = list(self._connections.get(episode_id, ()))
        for websocket in targets:
            try:
                await websocket.send_json(message)
            except Exception:
                logger.debug("Dropping a closed WebSocket connection")
                for sockets in self._connections.values():
                    sockets.discard(websocket)
