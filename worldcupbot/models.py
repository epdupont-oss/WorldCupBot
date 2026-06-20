from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

# ISO 3166-1 alpha-2 codes for national teams, keyed by the name(s) football-data.org
# uses. Covers all 48 World Cup 2026 slots' likely confederations; unmapped names
# (typos, qualifiers not yet seen) fall back to a generic flag rather than nothing.
_ISO2_BY_NAME = {
    "Switzerland": "CH", "USA": "US", "United States": "US", "Germany": "DE",
    "Japan": "JP", "France": "FR", "Argentina": "AR", "Brazil": "BR",
    "Spain": "ES", "Portugal": "PT", "Italy": "IT",
    "Netherlands": "NL", "Belgium": "BE", "Croatia": "HR", "Uruguay": "UY",
    "Mexico": "MX", "Canada": "CA", "Colombia": "CO", "Ecuador": "EC",
    "Morocco": "MA", "Senegal": "SN", "Ghana": "GH", "Nigeria": "NG",
    "Tunisia": "TN", "Algeria": "DZ", "Egypt": "EG", "Cameroon": "CM",
    "Ivory Coast": "CI", "Côte d'Ivoire": "CI", "South Africa": "ZA",
    "South Korea": "KR", "Korea Republic": "KR", "Australia": "AU",
    "Saudi Arabia": "SA", "Iran": "IR", "Qatar": "QA", "Jordan": "JO",
    "Uzbekistan": "UZ", "Sweden": "SE", "Norway": "NO", "Denmark": "DK",
    "Poland": "PL", "Austria": "AT", "Serbia": "RS",
    "Ukraine": "UA", "Turkey": "TR", "Türkiye": "TR",
    "Greece": "GR", "Czech Republic": "CZ", "Slovakia": "SK", "Hungary": "HU",
    "Romania": "RO", "Finland": "FI", "Iceland": "IS", "Ireland": "IE",
    "Republic of Ireland": "IE", "Slovenia": "SI", "Albania": "AL",
    "Costa Rica": "CR", "Panama": "PA", "Honduras": "HN", "Jamaica": "JM",
    "Paraguay": "PY", "Chile": "CL", "Peru": "PE", "Bolivia": "BO",
    "Venezuela": "VE", "New Zealand": "NZ", "China": "CN", "China PR": "CN",
    "India": "IN", "Iraq": "IQ", "United Arab Emirates": "AE", "Bahrain": "BH",
    "Oman": "OM", "Kuwait": "KW", "Cape Verde": "CV", "DR Congo": "CD",
    "Mali": "ML", "Burkina Faso": "BF", "Guinea": "GN", "Gabon": "GA",
    "Curaçao": "CW", "Trinidad and Tobago": "TT", "Suriname": "SR",
    "Haiti": "HT", "Guatemala": "GT",
}

# Home nations don't have ISO 3166-1 alpha-2 codes; their flags are fixed Unicode
# subdivision-flag sequences rather than derivable from two letters.
_FLAG_OVERRIDE_BY_NAME = {
    "England": "🏴",
    "Scotland": "🏴",
    "Wales": "🏴",
}

# football-data.org v4 match status codes
_LIVE_STATUSES = {"IN_PLAY", "PAUSED"}
_FINISHED_STATUSES = {"FINISHED", "AWARDED"}


def _flag_emoji_from_iso2(code: str) -> str:
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in code.upper())


def flag_for(name: str) -> str:
    if name in _FLAG_OVERRIDE_BY_NAME:
        return _FLAG_OVERRIDE_BY_NAME[name]
    code = _ISO2_BY_NAME.get(name)
    if code is None:
        return "🏳️"
    return _flag_emoji_from_iso2(code)


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
