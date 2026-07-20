from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_DATA_FILE = "data/signal.json"
DEFAULT_CHECK_INTERVAL_SECONDS = 900
DEFAULT_BINANCE_BASE_URL = "https://api.binance.com"


@dataclass(frozen=True, slots=True)
class Config:
    bot_token: str
    data_file: Path
    check_interval_seconds: int
    binance_base_url: str

    @classmethod
    def from_env(cls) -> Config:
        load_dotenv()

        token = os.getenv("SIGNAL_BOT_TOKEN")
        if not token:
            raise RuntimeError("SIGNAL_BOT_TOKEN is not configured.")

        return cls(
            bot_token=token,
            data_file=Path(os.getenv("SIGNAL_DATA_FILE", DEFAULT_DATA_FILE)),
            check_interval_seconds=_positive_int(
                "SIGNAL_CHECK_INTERVAL_SECONDS", DEFAULT_CHECK_INTERVAL_SECONDS
            ),
            binance_base_url=os.getenv("SIGNAL_BINANCE_BASE_URL", DEFAULT_BINANCE_BASE_URL),
        )


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default

    try:
        value = int(raw)
    except ValueError:
        raise RuntimeError(f"{name} must be an integer, got {raw!r}.") from None

    if value <= 0:
        raise RuntimeError(f"{name} must be positive, got {value}.")

    return value
