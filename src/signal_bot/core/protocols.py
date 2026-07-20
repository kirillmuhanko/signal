from __future__ import annotations

from collections.abc import Collection, Sequence
from typing import Protocol

from signal_bot.core.models import PriceAlert, User


class UserRepository(Protocol):
    async def get_or_add(self, chat_id: int) -> User: ...


class AlertRepository(Protocol):
    async def add(self, alert: PriceAlert) -> bool: ...

    async def get_by_chat(self, chat_id: int) -> Sequence[PriceAlert]: ...

    async def get_tracked(self) -> Sequence[PriceAlert]: ...

    async def update_range(self, alerts: Sequence[PriceAlert]) -> None: ...

    async def remove_by_symbol(self, chat_id: int, symbol: str) -> bool: ...


class PriceFeed(Protocol):
    async def get_prices(self, symbols: Collection[str]) -> dict[str, float]: ...
