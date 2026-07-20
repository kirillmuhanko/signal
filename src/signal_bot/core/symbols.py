from __future__ import annotations

DEFAULT_THRESHOLDS = (15.0, -15.0)
MAJOR_THRESHOLDS = (10.0, -10.0)

MAJOR_SYMBOLS = ("BTCUSDT", "ETHUSDT")
QUOTE_ASSETS = ("USDT", "USDC", "FDUSD", "BUSD", "BTC", "ETH", "BNB")


def is_valid(value: str) -> bool:
    return 1 <= len(value) <= 20 and value.isalnum()


def normalize(value: str) -> str:
    symbol = value.strip().upper()
    has_quote = any(len(symbol) > len(quote) and symbol.endswith(quote) for quote in QUOTE_ASSETS)

    return symbol if has_quote else symbol + "USDT"


def thresholds_for(symbol: str) -> tuple[float, float]:
    return MAJOR_THRESHOLDS if symbol in MAJOR_SYMBOLS else DEFAULT_THRESHOLDS


def display(symbol: str) -> str:
    return symbol[:-4] if symbol.upper().endswith("USDT") else symbol
