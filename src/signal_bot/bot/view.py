from __future__ import annotations

import math
from collections.abc import Sequence

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from signal_bot.core.models import AlertTrigger, PriceAlert
from signal_bot.core.symbols import (
    DEFAULT_THRESHOLDS,
    MAJOR_SYMBOLS,
    MAJOR_THRESHOLDS,
    display,
)

ADD_BUTTON = "➕ Add coin"
LIST_BUTTON = "📋 My coins"

MAJOR_NAMES = " and ".join(display(symbol) for symbol in MAJOR_SYMBOLS)
DEFAULT_MOVE = f"±{DEFAULT_THRESHOLDS[0]:g}%"
MAJOR_MOVE = f"±{MAJOR_THRESHOLDS[0]:g}%"

EMPTY_LIST_TEXT = "Nothing here yet! Tap *➕ Add coin* and I'll start watching 👀"
FALLBACK_TEXT = (
    "Not sure what that means 🤔\n\n"
    "Tap a button below, or try `/add BTC`. Send `/help` for the full rundown."
)
ADD_MENU_TEXT = (
    f"Pick one and I'll watch it for you — I'll ping you on a {MAJOR_MOVE} move.\n\n"
    f"Something else in mind? Send `/add SYMBOL`, like `/add SOL` ({DEFAULT_MOVE})."
)


def welcome_text(interval_seconds: int) -> str:
    return (
        "Hey! 👋 I'm *Signal* — I keep an eye on your coins and ping you "
        "when the price makes a real move.\n\n"
        "You pick a coin and how big a swing matters to you. I check the price every "
        f"{format_interval(interval_seconds)} and message you the moment it gets there — "
        "up or down.\n\n"
        "Ready? Tap *➕ Add coin* below."
    )


def help_text(interval_seconds: int) -> str:
    return (
        "*Signal — price alerts* 📈\n\n"
        "*How it works*\n"
        f"I check your coins every {format_interval(interval_seconds)}. When one moves past "
        "your threshold, I ping you and start counting again from that new price — so a long "
        "run gets you several heads-ups, not just one.\n\n"
        "*What you can do*\n"
        f"`/add BTC` — watch a coin ({DEFAULT_MOVE}, or {MAJOR_MOVE} for {MAJOR_NAMES})\n"
        "`/add BTC 5` — pick your own size: I'll ping you at ±5%\n"
        "`/list` — see your coins, tap ❌ to drop one\n"
        "`/remove BTC` — stop watching\n\n"
        "Want a different threshold? Just remove the coin and add it again 🙂"
    )


def tracking_text(symbol: str, upper_percent: float, lower_percent: float) -> str:
    return (
        f"Got it — now watching *{display(symbol)}* 📈\n"
        f"I'll ping you as soon as it moves {format_thresholds(upper_percent, lower_percent)} "
        "from where it is now.\n\n"
        "Tap *📋 My coins* anytime to manage your list."
    )


def list_text(alerts: Sequence[PriceAlert]) -> str:
    lines = (
        f"• *{display(alert.symbol)}*  "
        f"`{format_thresholds(alert.upper_threshold_percent, alert.lower_threshold_percent)}`"
        for alert in alerts
    )

    return "*Your coins* 📋\nI'll ping you when one of these moves:\n\n" + "\n".join(lines)


def alert_text(triggers: Sequence[AlertTrigger]) -> str:
    lines = (
        f"{'🟢' if trigger.change_percent > 0 else '🔴'} *{display(trigger.symbol)}*  "
        f"`{trigger.change_percent:+.2f}%`\n"
        f"`{format_price(trigger.previous_price)}` → `{format_price(trigger.current_price)}`"
        for trigger in triggers
    )

    return "\n\n".join(lines) + "\n\n_I'll start counting again from here._"


def format_thresholds(upper_percent: float, lower_percent: float) -> str:
    if upper_percent == abs(lower_percent):
        return f"±{upper_percent:g}%"

    return f"+{upper_percent:g}% / −{abs(lower_percent):g}%"


def format_interval(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds} sec"

    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min"

    hours = minutes / 60
    return f"{hours:g} h"


def format_price(value: float) -> str:
    if value >= 1000:
        return f"${value:,.0f}"

    if value >= 1:
        return f"${value:,.2f}"

    if value <= 0:
        return "$0"

    decimals = min(10, max(4, 2 - math.floor(math.log10(value))))
    return f"${value:.{decimals}f}"


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(ADD_BUTTON), KeyboardButton(LIST_BUTTON)]],
        resize_keyboard=True,
    )


def add_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(display(symbol), callback_data=f"add:{symbol}")
                for symbol in MAJOR_SYMBOLS
            ]
        ]
    )


def remove_keyboard(alerts: Sequence[PriceAlert]) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(f"❌ {display(alert.symbol)}", callback_data=f"rm:{alert.symbol}")
        for alert in alerts
    ]

    return InlineKeyboardMarkup(_chunk(buttons, 2))


def _chunk(buttons: list[InlineKeyboardButton], size: int) -> list[list[InlineKeyboardButton]]:
    return [buttons[index : index + size] for index in range(0, len(buttons), size)]
