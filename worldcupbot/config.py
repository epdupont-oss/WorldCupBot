import os


def _env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default) if default is not None else os.environ[name]
    return value.strip()


TELEGRAM_BOT_TOKEN = _env("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = _env("TELEGRAM_CHAT_ID")
WC_API_KEY = _env("WC_API_KEY")
DEFAULT_DISPLAY_TZ = _env("DISPLAY_TZ", "Europe/Zurich")

# football-data.org. Free tier includes the World Cup competition (code "WC")
# with match scores/standings, but not goal-scorer or card-level event data.
WC_API_BASE_URL = _env("WC_API_BASE_URL", "https://api.football-data.org/v4")
WC_COMPETITION_CODE = _env("WC_COMPETITION_CODE", "WC")
WC_SEASON = int(_env("WC_SEASON", "2026"))

# Optional: enriches goal alerts with a web-search-grounded scorer lookup via
# Mistral's Agents API. Leave MISTRAL_API_KEY unset to disable (alerts stay generic).
MISTRAL_API_KEY = _env("MISTRAL_API_KEY", "")
MISTRAL_MODEL = _env("MISTRAL_MODEL", "mistral-small-latest")

WATCHED_TEAM_NAMES = {
    name.strip()
    for name in _env("WATCHED_TEAMS", "Switzerland,USA").split(",")
    if name.strip()
}

LIVE_POLL_INTERVAL_MINUTES = 5
PRE_MATCH_ALERT_MINUTES_BEFORE = 2
MORNING_DIGEST_HOUR = 8
EVENING_RECAP_OFFSET_MINUTES_AFTER_KICKOFF = 120 + 30
