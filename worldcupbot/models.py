from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

FLAG_BY_CODE = {
    "SUI": "🇨🇭",
    "USA": "🇺🇸",
    "GER": "🇩🇪",
    "JPN": "🇯🇵",
    "FRA": "🇫🇷",
    "ARG": "🇦🇷",
}


def flag_for(code: str, fallback_name: str = "") -> str:
    return FLAG_BY_CODE.get(code, "")


@dataclass
class Team:
    code: str
    name: str

    @property
    def label(self) -> str:
        flag = flag_for(self.code)
        return f"{flag} {self.name}".strip()

    @classmethod
    def from_api(cls, data: dict) -> "Team":
        return cls(
            code=data.get("code") or data.get("id") or "",
            name=data.get("name") or data.get("code") or "Unknown",
        )


@dataclass
class MatchEvent:
    id: str
    type: str  # goal | red_card | half_time | second_half_start | extra_time | penalties | full_time
    minute: str
    team_code: Optional[str] = None
    player: Optional[str] = None
    assist: Optional[str] = None

    @classmethod
    def from_api(cls, data: dict) -> "MatchEvent":
        return cls(
            id=str(data.get("id") or data.get("event_id")),
            type=data.get("type") or data.get("event_type") or "",
            minute=str(data.get("minute") or data.get("clock") or ""),
            team_code=data.get("team_code") or data.get("team"),
            player=data.get("player") or data.get("player_name"),
            assist=data.get("assist") or data.get("assist_name"),
        )

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
        return self.type in ("goal", "own_goal", "penalty_goal")

    @property
    def is_red_card(self) -> bool:
        return self.type in ("red_card", "second_yellow_card")

    @property
    def is_phase_transition(self) -> bool:
        return self.type in (
            "half_time",
            "second_half_start",
            "extra_time_start",
            "penalties_start",
            "full_time",
        )


@dataclass
class Match:
    id: str
    status: str  # scheduled | live | finished
    kickoff_utc: datetime
    venue: str
    round_name: str
    home: Team
    away: Team
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    minute: Optional[str] = None
    events: list[MatchEvent] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: dict) -> "Match":
        kickoff_raw = data.get("kickoff") or data.get("kickoff_utc") or data.get("date")
        kickoff_utc = _parse_utc(kickoff_raw)
        return cls(
            id=str(data.get("id") or data.get("match_id")),
            status=_normalize_status(data.get("status")),
            kickoff_utc=kickoff_utc,
            venue=data.get("venue") or data.get("stadium") or "",
            round_name=data.get("round") or data.get("group") or "",
            home=Team.from_api(data.get("home_team") or data.get("home") or {}),
            away=Team.from_api(data.get("away_team") or data.get("away") or {}),
            home_score=_safe_int((data.get("score") or {}).get("home") if data.get("score") else data.get("home_score")),
            away_score=_safe_int((data.get("score") or {}).get("away") if data.get("score") else data.get("away_score")),
            minute=str(data.get("minute")) if data.get("minute") is not None else None,
            events=[MatchEvent.from_api(e) for e in data.get("events", []) or []],
        )

    @property
    def involves_watched_team(self) -> bool:
        from worldcupbot.config import WATCHED_TEAM_CODES

        return self.home.code in WATCHED_TEAM_CODES or self.away.code in WATCHED_TEAM_CODES

    @property
    def is_live(self) -> bool:
        return self.status == "live"

    @property
    def is_finished(self) -> bool:
        return self.status == "finished"

    @property
    def is_scheduled(self) -> bool:
        return self.status == "scheduled"

    @property
    def score_label(self) -> str:
        if self.home_score is None or self.away_score is None:
            return ""
        return f"{self.home_score}–{self.away_score}"

    def scorers_label(self, team_code: Optional[str] = None) -> str:
        goals = sorted(
            (e for e in self.events if e.is_goal and (team_code is None or e.team_code == team_code)),
            key=lambda e: e.minute_sort_key,
        )
        parts = []
        for g in goals:
            label = f"{g.player} {g.minute}'" if g.player else f"{g.minute}'"
            parts.append(label)
        return ", ".join(parts)


def _parse_utc(raw) -> Optional[datetime]:
    if not raw:
        return None
    if isinstance(raw, datetime):
        return raw.astimezone(timezone.utc)
    text = str(raw)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _normalize_status(raw: Optional[str]) -> str:
    if not raw:
        return "scheduled"
    raw = raw.lower()
    if raw in ("live", "in_play", "in_progress", "1h", "2h", "ht", "et", "pen"):
        return "live"
    if raw in ("finished", "ft", "full_time", "ended"):
        return "finished"
    return "scheduled"


def _safe_int(value) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
