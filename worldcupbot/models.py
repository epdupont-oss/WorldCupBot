from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

FLAG_BY_NAME = {
    "Switzerland": "🇨🇭",
    "USA": "🇺🇸",
    "Germany": "🇩🇪",
    "Japan": "🇯🇵",
    "France": "🇫🇷",
    "Argentina": "🇦🇷",
}

# api-football fixture.status.short codes
_LIVE_STATUSES = {"1H", "HT", "2H", "ET", "BT", "P", "INT"}
_FINISHED_STATUSES = {"FT", "AET", "PEN", "CANC", "ABD", "AWD", "WO"}


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
        return cls(id=data.get("id"), name=data.get("name") or "Unknown")


@dataclass
class MatchEvent:
    id: str
    type: str  # goal | red_card | half_time | second_half_start | extra_time_start | penalties_start
    minute: str
    team_id: Optional[int] = None
    player: Optional[str] = None
    assist: Optional[str] = None

    @classmethod
    def from_api_goal_or_card(cls, data: dict) -> Optional["MatchEvent"]:
        api_type = data.get("type")
        detail = data.get("detail") or ""
        if api_type == "Goal":
            event_type = "goal"
        elif api_type == "Card" and detail in ("Red Card", "Second Yellow card"):
            event_type = "red_card"
        else:
            return None

        time = data.get("time") or {}
        elapsed = time.get("elapsed")
        extra = time.get("extra")
        minute = f"{elapsed}+{extra}" if extra else str(elapsed)

        team = data.get("team") or {}
        player = data.get("player") or {}
        assist = data.get("assist") or {}

        event_id = f"{event_type}:{minute}:{team.get('id')}:{player.get('name')}:{detail}"
        return cls(
            id=event_id,
            type=event_type,
            minute=minute,
            team_id=team.get("id"),
            player=player.get("name"),
            assist=assist.get("name"),
        )

    @classmethod
    def phase_transition(cls, status_short: str) -> Optional["MatchEvent"]:
        mapping = {
            "HT": "half_time",
            "2H": "second_half_start",
            "ET": "extra_time_start",
            "P": "penalties_start",
        }
        event_type = mapping.get(status_short)
        if event_type is None:
            return None
        return cls(id=f"status:{status_short}", type=event_type, minute="")

    @property
    def minute_sort_key(self) -> tuple[int, int]:
        base, _, extra = self.minute.partition("+")
        try:
            base_val = int(base)
        except ValueError:
            base_val = 0
        try:
            extra_val = int(extra) if extra else 0
        except ValueError:
            extra_val = 0
        return (base_val, extra_val)

    @property
    def is_goal(self) -> bool:
        return self.type == "goal"

    @property
    def is_red_card(self) -> bool:
        return self.type == "red_card"

    @property
    def is_phase_transition(self) -> bool:
        return self.type in ("half_time", "second_half_start", "extra_time_start", "penalties_start")


@dataclass
class Match:
    id: int
    status_short: str
    kickoff_utc: Optional[datetime]
    venue: str
    round_name: str
    home: Team
    away: Team
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    minute: Optional[str] = None
    events: list[MatchEvent] = field(default_factory=list)

    @classmethod
    def from_api(cls, fixture: dict, events: Optional[list[dict]] = None) -> "Match":
        f = fixture.get("fixture", {})
        league = fixture.get("league", {})
        teams = fixture.get("teams", {})
        goals = fixture.get("goals", {})
        status = f.get("status", {})

        kickoff_raw = f.get("date")
        kickoff_utc = datetime.fromisoformat(kickoff_raw) if kickoff_raw else None

        elapsed = status.get("elapsed")
        minute = str(elapsed) if elapsed is not None else None

        parsed_events = [
            e
            for raw in (events or [])
            if (e := MatchEvent.from_api_goal_or_card(raw)) is not None
        ]

        return cls(
            id=f.get("id"),
            status_short=status.get("short") or "NS",
            kickoff_utc=kickoff_utc,
            venue=(f.get("venue") or {}).get("name") or "",
            round_name=league.get("round") or "",
            home=Team.from_api(teams.get("home") or {}),
            away=Team.from_api(teams.get("away") or {}),
            home_score=goals.get("home"),
            away_score=goals.get("away"),
            minute=minute,
            events=parsed_events,
        )

    @property
    def involves_watched_team(self) -> bool:
        from worldcupbot.config import WATCHED_TEAM_NAMES

        return self.home.name in WATCHED_TEAM_NAMES or self.away.name in WATCHED_TEAM_NAMES

    @property
    def is_live(self) -> bool:
        return self.status_short in _LIVE_STATUSES

    @property
    def is_finished(self) -> bool:
        return self.status_short in _FINISHED_STATUSES

    @property
    def is_scheduled(self) -> bool:
        return not self.is_live and not self.is_finished

    @property
    def score_label(self) -> str:
        if self.home_score is None or self.away_score is None:
            return ""
        return f"{self.home_score}–{self.away_score}"

    def scorers_label(self, team_id: Optional[int] = None) -> str:
        goals = sorted(
            (e for e in self.events if e.is_goal and (team_id is None or e.team_id == team_id)),
            key=lambda e: e.minute_sort_key,
        )
        parts = []
        for g in goals:
            label = f"{g.player} {g.minute}'" if g.player else f"{g.minute}'"
            parts.append(label)
        return ", ".join(parts)
