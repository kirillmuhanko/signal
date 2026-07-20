from __future__ import annotations

import logging
from collections.abc import Sequence

from signal_bot.core.models import AlertTrigger, PriceAlert
from signal_bot.core.protocols import AlertRepository, PriceFeed

logger = logging.getLogger(__name__)


class ThresholdPriceMonitor:
    def __init__(self, alerts: AlertRepository, feed: PriceFeed) -> None:
        self._alerts = alerts
        self._feed = feed

    async def evaluate(self) -> Sequence[AlertTrigger]:
        tracked = await self._alerts.get_tracked()
        if not tracked:
            return []

        symbols = {alert.symbol for alert in tracked}
        prices = await self._feed.get_prices(symbols)

        if not prices:
            logger.warning("No prices returned for %d tracked symbols.", len(symbols))
            return []

        evaluated: list[PriceAlert] = []
        triggers: list[AlertTrigger] = []

        for alert in tracked:
            price = prices.get(alert.symbol)

            if price is None:
                logger.warning("No price available for %s.", alert.symbol)
                continue

            evaluated.append(alert)

            if alert.baseline_price <= 0:
                alert.baseline_price = price
                continue

            change_percent = (price - alert.baseline_price) / alert.baseline_price * 100
            triggered = (
                change_percent >= alert.upper_threshold_percent
                or change_percent <= alert.lower_threshold_percent
            )

            if not triggered:
                continue

            triggers.append(
                AlertTrigger(
                    chat_id=alert.chat_id,
                    symbol=alert.symbol,
                    previous_price=alert.baseline_price,
                    current_price=price,
                    change_percent=change_percent,
                )
            )
            logger.info("Alert for %s: %+.2f%%.", alert.symbol, change_percent)

            alert.baseline_price = price

        await self._alerts.update_range(evaluated)

        return triggers
