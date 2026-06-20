from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

FLAG_BY_NAME = {
    "Switzerland": "🇨🇭",
    "USA": "🇺🇸",
    "United States": "🇺🇸",
    "Germany": "🇩🇪",
    "Japan": "🇯🇵",
    "France": "🇫🇷",
    "Argentina": "🇦🇷",
}

# football-data.org v4 match status codes
_LIVE_STATUSES = {"IN_PLAY", "PAUSED"}
_FINISHED_STATUSES = {"FINISHED", "AWARDED"}


def flag_for(name: str) -> str:
    return FLAG_BY_NAME.get(name, "")


@dataclass
class Team:
    id: int
    name: str

    @property
    def label(self) -> str:
        flag = flag_for(self.name)
        return f"{flag} {self.name}".strip()

    @classmethod
    def from_api(cls, data: dict) -> "Team":
        return cls(id=data.get("id"), name=data.get("name") or data.get("shortName") or "Unknown")


@dataclass
class Match:
    id: int
    status: str
    kickoff_utc: Optional[datetime]
    venue: str
    round_name: str
    home: Team
    away: Team
    home_score: Optional[int] = None
    away_score: Optional[int] = None

    @classmethod
    def from_api(cls, data: dict) -> "Match":
        kickoff_raw = data.get("utcDate")
        kickoff_utc = (
            datetime.fromisoformat(kickoff_raw.replace("Z", "+00:00")) if kickoff_raw else None
        )

        score = data.get("score") or {}
        full_time = score.get("fullTime") or {}

        stage = (data.get("stage") or "").replace("_", " ").title()
        group = data.get("group")
        round_name = f"{stage} · {group}" if group else stage

        return cls(
            id=data.get("id"),
            status=data.get("status") or "SCHEDULED",
            kickoff_utc=kickoff_utc,
            venue=data.get("venue") or "",
            round_name=round_name,
            home=Team.from_api(data.get("homeTeam") or {}),
            away=Team.from_api(data.get("awayTeam") or {}),
            home_score=full_time.get("home"),
            away_score=full_time.get("away"),
        )

    @property
    def involves_watched_team(self) -> bool:
        from worldcupbot.config import WATCHED_TEAM_NAMES

        return self.home.name in WATCHED_TEAM_NAMES or self.away.name in WATCHED_TEAM_NAMES

    @property
    def is_live(self) -> bool:
        return self.status in _LIVE_STATUSES

    @property
    def is_finished(self) -> bool:
        return self.status in _FINISHED_STATUSES

    @property
    def is_scheduled(self) -> bool:
        return not self.is_live and not self.is_finished

    @property
    def score_label(self) -> str:
        if self.home_score is None or self.away_score is None:
            return ""
        return f"{self.home_score}–{self.away_score}"
