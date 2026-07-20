from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from signal_bot.core.models import PriceAlert, User

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Snapshot:
    users: list[User] = field(default_factory=list)
    alerts: list[PriceAlert] = field(default_factory=list)
    last_alert_id: int = 0

    def __post_init__(self) -> None:
        self.last_alert_id = max(
            self.last_alert_id, max((alert.id for alert in self.alerts), default=0)
        )

    def next_alert_id(self) -> int:
        self.last_alert_id += 1
        return self.last_alert_id


class JsonDatabase:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = asyncio.Lock()
        self._snapshot: Snapshot | None = None

    @asynccontextmanager
    async def read(self) -> AsyncIterator[Snapshot]:
        async with self._lock:
            yield await self._load()

    @asynccontextmanager
    async def write(self) -> AsyncIterator[Snapshot]:
        async with self._lock:
            snapshot = await self._load()
            try:
                yield snapshot
            finally:
                await asyncio.to_thread(self._persist, snapshot)

    async def _load(self) -> Snapshot:
        if self._snapshot is None:
            self._snapshot = await asyncio.to_thread(self._read_file)

        return self._snapshot

    def _read_file(self) -> Snapshot:
        if not self._path.exists():
            return Snapshot()

        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.exception("Failed to read %s, starting empty.", self._path)
            return Snapshot()

        if not isinstance(payload, dict):
            logger.error("Unexpected content in %s, starting empty.", self._path)
            return Snapshot()

        return Snapshot(
            users=[User.from_dict(item) for item in _rows(payload, "users")],
            alerts=[PriceAlert.from_dict(item) for item in _rows(payload, "alerts")],
            last_alert_id=_counter(payload, "last_alert_id"),
        )

    def _persist(self, snapshot: Snapshot) -> None:
        payload = {
            "last_alert_id": snapshot.last_alert_id,
            "users": [user.to_dict() for user in snapshot.users],
            "alerts": [alert.to_dict() for alert in snapshot.alerts],
        }

        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(self._path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(temporary, self._path)


def _rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    rows = payload.get(key)
    if not isinstance(rows, list):
        return []

    return [row for row in rows if isinstance(row, dict)]


def _counter(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    return value if isinstance(value, int) and value >= 0 else 0
