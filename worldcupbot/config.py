import os


def _env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default) if default is not None else os.environ[name]
    return value.strip()


TELEGRAM_BOT_TOKEN = _env("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = _env("TELEGRAM_CHAT_ID")
WC_API_KEY = _env("WC_API_KEY")
DEFAULT_DISPLAY_TZ = _env("DISPLAY_TZ", "Europe/Zurich")

# API-Football (api-sports.io). Direct subscription uses this base URL and the
# x-apisports-key header; if going through RapidAPI instead, set
# WC_API_BASE_URL=https://api-football-v1.p.rapidapi.com/v3 and adjust api.py's
# auth header to x-rapidapi-key / x-rapidapi-host.
WC_API_BASE_URL = _env("WC_API_BASE_URL", "https://v3.football.api-sports.io")
WC_LEAGUE_ID = int(_env("WC_LEAGUE_ID", "1"))  # World Cup
WC_SEASON = int(_env("WC_SEASON", "2026"))

WATCHED_TEAM_NAMES = {
    name.strip()
    for name in _env("WATCHED_TEAMS", "Switzerland,USA").split(",")
    if name.strip()
}

LIVE_POLL_INTERVAL_MINUTES = 5
PRE_MATCH_ALERT_MINUTES_BEFORE = 2
MORNING_DIGEST_HOUR = 8
EVENING_RECAP_OFFSET_MINUTES_AFTER_KICKOFF = 120 + 30
