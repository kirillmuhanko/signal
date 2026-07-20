from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Self


def utcnow() -> datetime:
    return datetime.now(UTC)


def _parse_time(value: Any) -> datetime | None:
    return datetime.fromisoformat(value) if isinstance(value, str) else None


def _format_time(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


@dataclass(slots=True)
class User:
    chat_id: int
    created_at: datetime = field(default_factory=utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chat_id": self.chat_id,
            "created_at": _format_time(self.created_at),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            chat_id=data["chat_id"],
            created_at=_parse_time(data.get("created_at")) or utcnow(),
        )


@dataclass(slots=True)
class PriceAlert:
    chat_id: int
    symbol: str
    upper_threshold_percent: float
    lower_threshold_percent: float
    baseline_price: float = 0.0
    created_at: datetime = field(default_factory=utcnow)
    id: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "chat_id": self.chat_id,
            "symbol": self.symbol,
            "upper_threshold_percent": self.upper_threshold_percent,
            "lower_threshold_percent": self.lower_threshold_percent,
            "baseline_price": self.baseline_price,
            "created_at": _format_time(self.created_at),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            chat_id=data["chat_id"],
            symbol=data["symbol"],
            upper_threshold_percent=data["upper_threshold_percent"],
            lower_threshold_percent=data["lower_threshold_percent"],
            baseline_price=data.get("baseline_price", 0.0),
            created_at=_parse_time(data.get("created_at")) or utcnow(),
            id=data.get("id", 0),
        )


@dataclass(frozen=True, slots=True)
class AlertTrigger:
    chat_id: int
    symbol: str
    previous_price: float
    current_price: float
    change_percent: float
