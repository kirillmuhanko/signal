from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Sequence

from telegram import CallbackQuery, Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from signal_bot.bot import view
from signal_bot.core.models import AlertTrigger, PriceAlert
from signal_bot.core.monitor import ThresholdPriceMonitor
from signal_bot.core.protocols import AlertRepository, UserRepository
from signal_bot.core.symbols import display, is_valid, normalize, thresholds_for

logger = logging.getLogger(__name__)


class BotHandlers:
    def __init__(
        self,
        users: UserRepository,
        alerts: AlertRepository,
        monitor: ThresholdPriceMonitor,
        interval_seconds: int,
    ) -> None:
        self._users = users
        self._alerts = alerts
        self._monitor = monitor
        self._interval_seconds = interval_seconds

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.effective_message
        if message is None:
            return

        await message.reply_text(
            view.welcome_text(self._interval_seconds),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=view.main_keyboard(),
        )

    async def show_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.effective_message
        if message is None:
            return

        await message.reply_text(
            view.help_text(self._interval_seconds),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=view.main_keyboard(),
        )

    async def add(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.effective_message
        if message is None:
            return

        arguments = context.args or []

        if not arguments:
            await message.reply_text(
                "Which coin? Send something like `/add BTC` 🙂",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=view.main_keyboard(),
            )
            return

        if not is_valid(arguments[0]):
            await message.reply_text(
                "Hmm, that doesn't look like a symbol 🤔 Try `/add BTC`",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        symbol = normalize(arguments[0])
        thresholds = thresholds_for(symbol)

        if len(arguments) > 1:
            parsed = _parse_thresholds(arguments[1:])
            if parsed is None:
                await message.reply_text(
                    "I need a positive number for the move size, like `/add BTC 5`",
                    parse_mode=ParseMode.MARKDOWN,
                )
                return

            thresholds = parsed

        upper_percent, lower_percent = thresholds
        await self._users.get_or_add(message.chat_id)

        if not await self._try_add(message.chat_id, symbol, upper_percent, lower_percent):
            await message.reply_text(
                f"*{display(symbol)}* is already on your list 👍",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        await message.reply_text(
            view.tracking_text(symbol, upper_percent, lower_percent),
            parse_mode=ParseMode.MARKDOWN,
        )

    async def remove(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.effective_message
        if message is None:
            return

        arguments = context.args or []

        if not arguments:
            await message.reply_text(
                "Which coin should I drop? Send something like `/remove BTC`",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        if not is_valid(arguments[0]):
            await message.reply_text(
                "Hmm, that doesn't look like a symbol 🤔 Try `/remove BTC`",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        symbol = normalize(arguments[0])
        await self._users.get_or_add(message.chat_id)
        removed = await self._alerts.remove_by_symbol(message.chat_id, symbol)

        await message.reply_text(
            f"Dropped *{display(symbol)}* 🗑"
            if removed
            else f"*{display(symbol)}* isn't on your list 🤷",
            parse_mode=ParseMode.MARKDOWN,
        )

    async def show_add_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.effective_message
        if message is None:
            return

        await self._users.get_or_add(message.chat_id)
        await message.reply_text(
            view.ADD_MENU_TEXT,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=view.add_menu_keyboard(),
        )

    async def show_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.effective_message
        if message is None:
            return

        await self._users.get_or_add(message.chat_id)
        alerts = await self._alerts.get_by_chat(message.chat_id)

        if not alerts:
            await message.reply_text(
                view.EMPTY_LIST_TEXT,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=view.main_keyboard(),
            )
            return

        await message.reply_text(
            view.list_text(alerts),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=view.remove_keyboard(alerts),
        )

    async def fallback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.effective_message
        if message is None:
            return

        await message.reply_text(
            view.FALLBACK_TEXT,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=view.main_keyboard(),
        )

    async def callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if query is None or query.message is None:
            return

        action, _, symbol = (query.data or "").partition(":")
        chat_id = query.message.chat.id
        await self._users.get_or_add(chat_id)

        if action == "add":
            symbol = normalize(symbol)
            upper_percent, lower_percent = thresholds_for(symbol)
            added = await self._try_add(chat_id, symbol, upper_percent, lower_percent)
            await query.answer(
                f"Now watching {display(symbol)} 👀"
                if added
                else f"{display(symbol)} is already on your list"
            )
            return

        if action == "rm":
            await self._alerts.remove_by_symbol(chat_id, symbol)
            await query.answer(f"Dropped {display(symbol)}")
            await self._refresh_list(query, chat_id)
            return

        await query.answer()

    async def check_prices(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        triggers = await self._monitor.evaluate()
        if not triggers:
            logger.info("No price alerts triggered.")
            return

        by_chat: defaultdict[int, list[AlertTrigger]] = defaultdict(list)
        for trigger in triggers:
            by_chat[trigger.chat_id].append(trigger)

        for chat_id, chat_triggers in by_chat.items():
            try:
                await context.bot.send_message(
                    chat_id,
                    view.alert_text(chat_triggers),
                    parse_mode=ParseMode.MARKDOWN,
                )
            except TelegramError:
                logger.exception("Failed to send price alerts to chat %d.", chat_id)

        logger.info("Sent %d price alerts.", len(triggers))

    async def _refresh_list(self, query: CallbackQuery, chat_id: int) -> None:
        alerts = await self._alerts.get_by_chat(chat_id)

        if not alerts:
            await query.edit_message_text(view.EMPTY_LIST_TEXT, parse_mode=ParseMode.MARKDOWN)
            return

        await query.edit_message_text(
            view.list_text(alerts),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=view.remove_keyboard(alerts),
        )

    async def _try_add(
        self,
        chat_id: int,
        symbol: str,
        upper_percent: float,
        lower_percent: float,
    ) -> bool:
        return await self._alerts.add(
            PriceAlert(
                chat_id=chat_id,
                symbol=symbol,
                upper_threshold_percent=upper_percent,
                lower_threshold_percent=lower_percent,
            )
        )


def _parse_thresholds(arguments: Sequence[str]) -> tuple[float, float] | None:
    try:
        values = [abs(float(argument)) for argument in arguments[:2]]
    except ValueError:
        return None

    if not values or not all(values):
        return None

    upper = values[0]
    lower = values[1] if len(values) > 1 else upper

    return upper, -lower
