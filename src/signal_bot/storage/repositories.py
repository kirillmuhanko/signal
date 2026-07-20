from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from signal_bot.core.models import PriceAlert, User
from signal_bot.core.protocols import AlertRepository, UserRepository
from signal_bot.storage.database import JsonDatabase


class JsonUserRepository(UserRepository):
    def __init__(self, database: JsonDatabase) -> None:
        self._database = database

    async def get_or_add(self, chat_id: int) -> User:
        async with self._database.write() as snapshot:
            for user in snapshot.users:
                if user.chat_id == chat_id:
                    return user

            user = User(chat_id=chat_id)
            snapshot.users.append(user)
            return user


class JsonAlertRepository(AlertRepository):
    def __init__(self, database: JsonDatabase) -> None:
        self._database = database

    async def add(self, alert: PriceAlert) -> bool:
        async with self._database.write() as snapshot:
            duplicate = any(
                existing.chat_id == alert.chat_id and existing.symbol == alert.symbol
                for existing in snapshot.alerts
            )
            if duplicate:
                return False

            alert.id = snapshot.next_alert_id()
            snapshot.alerts.append(alert)
            return True

    async def get_by_chat(self, chat_id: int) -> Sequence[PriceAlert]:
        async with self._database.read() as snapshot:
            matching = [alert for alert in snapshot.alerts if alert.chat_id == chat_id]
            return sorted(matching, key=lambda alert: alert.symbol)

    async def get_tracked(self) -> Sequence[PriceAlert]:
        async with self._database.read() as snapshot:
            return [replace(alert) for alert in snapshot.alerts]

    async def update_range(self, alerts: Sequence[PriceAlert]) -> None:
        if not alerts:
            return

        updated = {alert.id: alert for alert in alerts}

        async with self._database.write() as snapshot:
            snapshot.alerts = [updated.get(alert.id, alert) for alert in snapshot.alerts]

    async def remove_by_symbol(self, chat_id: int, symbol: str) -> bool:
        async with self._database.write() as snapshot:
            remaining = [
                alert
                for alert in snapshot.alerts
                if not (alert.chat_id == chat_id and alert.symbol == symbol)
            ]
            removed = len(remaining) != len(snapshot.alerts)
            snapshot.alerts = remaining
            return removed
