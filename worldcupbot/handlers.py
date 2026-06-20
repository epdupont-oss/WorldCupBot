from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from worldcupbot.core import WorldCupBot
from worldcupbot.formatting import format_update_message
from worldcupbot.state import STATE

logger = logging.getLogger(__name__)


def register_handlers(application, bot_core: WorldCupBot) -> None:
    async def cmd_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        tz = STATE.tz
        today_local = datetime.now(tz).date()
        try:
            matches = await bot_core.api.get_matches_for_date(today_local)
        except Exception:
            logger.exception("Failed to fetch matches for /update")
            await update.message.reply_text("Couldn't fetch today's matches right now.")
            return
        await update.message.reply_text(format_update_message(matches, tz))

    async def cmd_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not context.args:
            now = datetime.now(STATE.tz)
            await update.message.reply_text(
                f"🕐 Current timezone: {STATE.tz_name} (currently {now.strftime('%H:%M')})"
            )
            return

        tz_name = context.args[0]
        try:
            new_tz = ZoneInfo(tz_name)
        except ZoneInfoNotFoundError:
            await update.message.reply_text(f"⚠️ Unknown timezone: {tz_name}")
            return

        STATE.tz_name = tz_name
        bot_core.reschedule_daily_refresh()
        await bot_core.refresh_schedule()

        now = datetime.now(new_tz)
        await update.message.reply_text(
            f"🕐 Timezone set to {tz_name} (currently {now.strftime('%H:%M')})"
        )

    application.add_handler(CommandHandler("update", cmd_update))
    application.add_handler(CommandHandler("timezone", cmd_timezone))
