from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from zoneinfo import ZoneInfo

from worldcupbot.config import DEFAULT_DISPLAY_TZ


@dataclass
class BotState:
    tz_name: str = DEFAULT_DISPLAY_TZ
    live_match_id: int | None = None
    live_match_status: str | None = None
    live_home_score: int | None = None
    live_away_score: int | None = None
    morning_digest_sent_for: date | None = None
    evening_recap_sent_for: date | None = None
    pre_match_alert_sent_for_match: int | None = None

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.tz_name)


STATE = BotState()
