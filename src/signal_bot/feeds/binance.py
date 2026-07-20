from __future__ import annotations

import logging
from collections.abc import Collection

import httpx

from signal_bot.core.protocols import PriceFeed

logger = logging.getLogger(__name__)

TICKER_PATH = "/api/v3/ticker/price"


class BinancePriceFeed(PriceFeed):
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def get_prices(self, symbols: Collection[str]) -> dict[str, float]:
        if not symbols:
            return {}

        try:
            response = await self._client.get(TICKER_PATH)
            response.raise_for_status()
            tickers = response.json()
        except (httpx.HTTPError, ValueError):
            logger.exception("Failed to fetch prices from Binance.")
            return {}

        if not isinstance(tickers, list):
            logger.error("Unexpected ticker payload from Binance.")
            return {}

        requested = {symbol.upper() for symbol in symbols}
        prices: dict[str, float] = {}

        for ticker in tickers:
            if not isinstance(ticker, dict):
                continue

            symbol = str(ticker.get("symbol", "")).upper()
            if symbol not in requested:
                continue

            try:
                price = float(ticker["price"])
            except (KeyError, TypeError, ValueError):
                continue

            if price > 0:
                prices[symbol] = price

        return prices
