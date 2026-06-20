import os

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
WC_API_KEY = os.environ["WC_API_KEY"]
DEFAULT_DISPLAY_TZ = os.environ.get("DISPLAY_TZ", "Europe/Zurich")

# API-Football (api-sports.io). Direct subscription uses this base URL and the
# x-apisports-key header; if going through RapidAPI instead, set
# WC_API_BASE_URL=https://api-football-v1.p.rapidapi.com/v3 and adjust api.py's
# auth header to x-rapidapi-key / x-rapidapi-host.
WC_API_BASE_URL = os.environ.get("WC_API_BASE_URL", "https://v3.football.api-sports.io")
WC_LEAGUE_ID = int(os.environ.get("WC_LEAGUE_ID", "1"))  # World Cup
WC_SEASON = int(os.environ.get("WC_SEASON", "2026"))

WATCHED_TEAM_NAMES = {
    name.strip()
    for name in os.environ.get("WATCHED_TEAMS", "Switzerland,USA").split(",")
    if name.strip()
}

LIVE_POLL_INTERVAL_MINUTES = 5
PRE_MATCH_ALERT_MINUTES_BEFORE = 2
MORNING_DIGEST_HOUR = 8
EVENING_RECAP_OFFSET_MINUTES_AFTER_KICKOFF = 120 + 30
