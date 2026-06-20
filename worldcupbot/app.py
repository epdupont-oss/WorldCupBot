from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application, ApplicationBuilder

from worldcupbot.api import WorldCupAPIClient
from worldcupbot.config import TELEGRAM_BOT_TOKEN
from worldcupbot.core import WorldCupBot
from worldcupbot.handlers import register_handlers
from worldcupbot.mistral import MistralEnricher

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def build_application() -> Application:
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    api = WorldCupAPIClient()
    mistral = MistralEnricher()
    scheduler = AsyncIOScheduler()
    bot_core = WorldCupBot(bot=application.bot, api=api, scheduler=scheduler, mistral=mistral)

    register_handlers(application, bot_core)

    async def on_startup(app: Application) -> None:
        scheduler.start()
        bot_core.reschedule_daily_refresh()
        await bot_core.refresh_schedule()

    async def on_shutdown(app: Application) -> None:
        if scheduler.running:
            scheduler.shutdown(wait=False)
        await api.aclose()
        await mistral.aclose()

    application.post_init = on_startup
    application.post_shutdown = on_shutdown

    return application
