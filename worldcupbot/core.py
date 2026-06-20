from __future__ import annotations

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from telegram import Bot

from worldcupbot.api import WorldCupAPIClient
from worldcupbot.config import (
    EVENING_RECAP_OFFSET_MINUTES_AFTER_KICKOFF,
    LIVE_POLL_INTERVAL_MINUTES,
    MORNING_DIGEST_HOUR,
    PRE_MATCH_ALERT_MINUTES_BEFORE,
    TELEGRAM_CHAT_ID,
    WATCHED_TEAM_CODES,
)
from worldcupbot.formatting import (
    format_evening_recap,
    format_full_time,
    format_goal,
    format_morning_digest,
    format_phase_transition,
    format_pre_match,
    format_red_card,
    next_fixture_label,
)
from worldcupbot.models import Match
from worldcupbot.state import STATE

logger = logging.getLogger(__name__)

JOB_MORNING_DIGEST = "morning_digest"
JOB_EVENING_RECAP = "evening_recap"
JOB_PRE_MATCH_ALERT = "pre_match_alert"
JOB_LIVE_POLL = "live_poll"
JOB_DAILY_REFRESH = "daily_refresh"

DAY_JOB_IDS = (JOB_MORNING_DIGEST, JOB_EVENING_RECAP, JOB_PRE_MATCH_ALERT, JOB_LIVE_POLL)


def _first_watched_team_code(match: Match) -> str | None:
    if match.home.code in WATCHED_TEAM_CODES:
        return match.home.code
    if match.away.code in WATCHED_TEAM_CODES:
        return match.away.code
    return None


class WorldCupBot:
    def __init__(self, bot: Bot, api: WorldCupAPIClient, scheduler: AsyncIOScheduler) -> None:
        self.bot = bot
        self.api = api
        self.scheduler = scheduler

    async def send(self, text: str) -> None:
        await self.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text)

    def _cancel_day_jobs(self) -> None:
        for job_id in DAY_JOB_IDS:
            job = self.scheduler.get_job(job_id)
            if job is not None:
                job.remove()

    def reschedule_daily_refresh(self) -> None:
        self.scheduler.add_job(
            self._job_daily_refresh,
            trigger=CronTrigger(hour=0, minute=5, timezone=STATE.tz),
            id=JOB_DAILY_REFRESH,
            replace_existing=True,
        )

    async def refresh_schedule(self) -> None:
        """Determine today's mode (LIVE / WATCHFUL / IDLE) and (re)schedule jobs accordingly.

        Already-fired one-off jobs for today are tracked in STATE and are not re-sent,
        per the requirement that a timezone change must not replay past notifications.
        """
        self._cancel_day_jobs()
        tz = STATE.tz
        today_local = datetime.now(tz).date()

        try:
            matches = await self.api.get_matches_for_date(today_local)
        except Exception:
            logger.exception("Failed to fetch matches while refreshing schedule")
            return

        watched_matches = [m for m in matches if m.involves_watched_team]
        live_watched = next((m for m in watched_matches if m.is_live), None)

        if live_watched is not None:
            STATE.live_match_id = live_watched.id
            STATE.seen_event_ids = {e.id for e in live_watched.events}
            self._start_live_poll()
            return

        STATE.live_match_id = None

        upcoming_watched = next(
            (m for m in sorted(watched_matches, key=lambda m: m.kickoff_utc) if m.is_scheduled),
            None,
        )
        if upcoming_watched is not None:
            self._schedule_pre_match_alert(upcoming_watched, tz)
            return

        # IDLE: no SUI/USA match today (upcoming or live). Schedule morning digest + evening recap.
        if matches:
            last_kickoff_local = max(m.kickoff_utc for m in matches).astimezone(tz)
            recap_at = last_kickoff_local + timedelta(minutes=EVENING_RECAP_OFFSET_MINUTES_AFTER_KICKOFF)
        else:
            recap_at = None

        morning_at = datetime.combine(today_local, datetime.min.time(), tzinfo=tz).replace(hour=MORNING_DIGEST_HOUR)

        if STATE.morning_digest_sent_for != today_local and morning_at > datetime.now(tz):
            self.scheduler.add_job(
                self._job_morning_digest,
                trigger=DateTrigger(run_date=morning_at),
                id=JOB_MORNING_DIGEST,
                replace_existing=True,
            )

        if recap_at is not None and STATE.evening_recap_sent_for != today_local and recap_at > datetime.now(tz):
            self.scheduler.add_job(
                self._job_evening_recap,
                trigger=DateTrigger(run_date=recap_at),
                id=JOB_EVENING_RECAP,
                replace_existing=True,
            )

    def _schedule_pre_match_alert(self, match: Match, tz: ZoneInfo) -> None:
        alert_at = match.kickoff_utc.astimezone(tz) - timedelta(minutes=PRE_MATCH_ALERT_MINUTES_BEFORE)
        if STATE.pre_match_alert_sent_for_match == match.id or alert_at <= datetime.now(tz):
            return
        self.scheduler.add_job(
            self._job_pre_match_alert,
            trigger=DateTrigger(run_date=alert_at),
            id=JOB_PRE_MATCH_ALERT,
            replace_existing=True,
            kwargs={"match_id": match.id},
        )

    def _start_live_poll(self) -> None:
        self.scheduler.add_job(
            self._job_live_poll,
            trigger="interval",
            minutes=LIVE_POLL_INTERVAL_MINUTES,
            id=JOB_LIVE_POLL,
            replace_existing=True,
            next_run_time=datetime.now(STATE.tz),
        )

    async def _job_daily_refresh(self) -> None:
        await self.refresh_schedule()

    async def _job_morning_digest(self) -> None:
        tz = STATE.tz
        today_local = datetime.now(tz).date()
        try:
            matches = await self.api.get_matches_for_date(today_local)
        except Exception:
            logger.exception("Failed to fetch matches for morning digest")
            return
        watched_code = next(
            (code for m in matches for code in (m.home.code, m.away.code) if code in WATCHED_TEAM_CODES),
            None,
        )
        next_fixture = None
        team_code = watched_code or next(iter(WATCHED_TEAM_CODES))
        try:
            next_fixture = await self.api.get_next_fixture(team_code)
        except Exception:
            logger.exception("Failed to fetch next fixture for morning digest")
        await self.send(format_morning_digest(matches, next_fixture, team_code, tz))
        STATE.morning_digest_sent_for = today_local

    async def _job_evening_recap(self) -> None:
        tz = STATE.tz
        today_local = datetime.now(tz).date()
        try:
            matches = await self.api.get_matches_for_date(today_local)
        except Exception:
            logger.exception("Failed to fetch matches for evening recap")
            return
        team_code = next(iter(WATCHED_TEAM_CODES))
        next_fixture = None
        try:
            next_fixture = await self.api.get_next_fixture(team_code)
        except Exception:
            logger.exception("Failed to fetch next fixture for evening recap")
        await self.send(format_evening_recap(matches, next_fixture, team_code, tz))
        STATE.evening_recap_sent_for = today_local

    async def _job_pre_match_alert(self, match_id: str) -> None:
        tz = STATE.tz
        try:
            match = await self.api.get_match(match_id)
        except Exception:
            logger.exception("Failed to fetch match for pre-match alert")
            return
        await self.send(format_pre_match(match, tz))
        STATE.pre_match_alert_sent_for_match = match_id

    async def _job_live_poll(self) -> None:
        if STATE.live_match_id is None:
            return
        try:
            match = await self.api.get_match(STATE.live_match_id)
        except Exception:
            logger.exception("Failed to poll live match")
            return

        new_events = [e for e in match.events if e.id not in STATE.seen_event_ids]
        for event in sorted(new_events, key=lambda e: e.minute_sort_key):
            STATE.seen_event_ids.add(event.id)
            if event.is_goal:
                await self.send(format_goal(match, event))
            elif event.is_red_card:
                await self.send(format_red_card(match, event))
            elif event.is_phase_transition and event.type != "full_time":
                await self.send(format_phase_transition(match, event))

        if match.is_finished:
            await self._finish_live_match(match)

    async def _finish_live_match(self, match: Match) -> None:
        job = self.scheduler.get_job(JOB_LIVE_POLL)
        if job is not None:
            job.remove()
        STATE.live_match_id = None

        team_code = _first_watched_team_code(match) or next(iter(WATCHED_TEAM_CODES))
        next_fixture = None
        try:
            next_fixture = await self.api.get_next_fixture(team_code)
        except Exception:
            logger.exception("Failed to fetch next fixture for full-time recap")
        next_line = next_fixture_label(team_code, next_fixture, STATE.tz)
        await self.send(format_full_time(match, [next_line]))

        await self.refresh_schedule()
