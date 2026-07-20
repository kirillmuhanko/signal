from __future__ import annotations

import logging
from typing import Any, TypeAlias

import httpx
from telegram import BotCommand
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from signal_bot.bot import view
from signal_bot.bot.handlers import BotHandlers
from signal_bot.config import Config
from signal_bot.core.monitor import ThresholdPriceMonitor
from signal_bot.feeds.binance import BinancePriceFeed
from signal_bot.storage.database import JsonDatabase
from signal_bot.storage.repositories import JsonAlertRepository, JsonUserRepository

BotApplication: TypeAlias = Application[Any, Any, Any, Any, Any, Any]

HTTP_TIMEOUT_SECONDS = 10.0

COMMANDS = [
    BotCommand("add", "Watch a coin, e.g. /add BTC"),
    BotCommand("list", "See your coins"),
    BotCommand("remove", "Stop watching a coin"),
    BotCommand("help", "How this works"),
]


def build_application(config: Config) -> BotApplication:
    database = JsonDatabase(config.data_file)
    users = JsonUserRepository(database)
    alerts = JsonAlertRepository(database)
    client = httpx.AsyncClient(base_url=config.binance_base_url, timeout=HTTP_TIMEOUT_SECONDS)
    monitor = ThresholdPriceMonitor(alerts, BinancePriceFeed(client))
    handlers = BotHandlers(users, alerts, monitor, config.check_interval_seconds)

    async def on_startup(application: BotApplication) -> None:
        await application.bot.set_my_commands(COMMANDS)

    async def on_shutdown(application: BotApplication) -> None:
        await client.aclose()

    application = (
        ApplicationBuilder()
        .token(config.bot_token)
        .post_init(on_startup)
        .post_shutdown(on_shutdown)
        .build()
    )

    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("help", handlers.show_help))
    application.add_handler(CommandHandler("add", handlers.add))
    application.add_handler(CommandHandler("list", handlers.show_list))
    application.add_handler(CommandHandler("remove", handlers.remove))
    application.add_handler(MessageHandler(filters.Text([view.ADD_BUTTON]), handlers.show_add_menu))
    application.add_handler(MessageHandler(filters.Text([view.LIST_BUTTON]), handlers.show_list))
    application.add_handler(CallbackQueryHandler(handlers.callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.fallback))

    if application.job_queue is None:
        raise RuntimeError("JobQueue is unavailable; install python-telegram-bot[job-queue].")

    application.job_queue.run_repeating(
        handlers.check_prices,
        interval=config.check_interval_seconds,
        first=config.check_interval_seconds,
        name="price-check",
    )

    return application


def run() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    build_application(Config.from_env()).run_polling()
