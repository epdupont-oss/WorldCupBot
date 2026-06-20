# WorldCupBot

Telegram bot tracking the 2026 World Cup, with extra attention to Switzerland and USA
matches. Built with `python-telegram-bot` (async), `APScheduler`, and `httpx`. Designed
to run as a single long-lived worker process (e.g. on Railway).

## Configuration

All configuration is via environment variables:

| Variable | Required | Default | Description |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | yes | — | Bot token from `@BotFather` |
| `TELEGRAM_CHAT_ID` | yes | — | Chat/channel id to post updates to |
| `WC_API_KEY` | yes | — | API key for API-Football (api-sports.io) |
| `DISPLAY_TZ` | no | `Europe/Zurich` | IANA timezone all displayed times and schedules are anchored to |
| `WC_API_BASE_URL` | no | `https://v3.football.api-sports.io` | Override for the API base URL |
| `WC_LEAGUE_ID` | no | `1` | API-Football league id for the World Cup |
| `WC_SEASON` | no | `2026` | Season year passed to API-Football |
| `WATCHED_TEAMS` | no | `Switzerland,USA` | Comma-separated team names (as returned by API-Football) to track closely |

Copy `.env.example` to `.env` and fill in values for local development.

## Running locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export $(cat .env | xargs)   # or use a process manager / direnv
python main.py
```

## Deploying on Railway

This repo includes a `Procfile` (`worker: python main.py`). Set the environment
variables above in the Railway project settings; no other setup is required.

## Operating modes

The bot determines its mode once per day (00:05 in the active display timezone)
and whenever `/timezone` changes the active timezone:

- **LIVE** — a Switzerland or USA match is currently in progress. Polls the match
  endpoint every 5 minutes, diffs the event timeline against already-seen events,
  and posts goals, red cards, and phase transitions. Posts a full-time recap and
  exits live mode when the match finishes.
- **WATCHFUL** — a Switzerland or USA match is scheduled later today. Schedules a
  single pre-match alert 2 minutes before kickoff. No polling.
- **IDLE** — no Switzerland or USA match today. Sends a morning digest at 08:00
  local time and an evening recap 30 minutes after the last match of the day is
  estimated to finish (kickoff + 120 minutes).

## Commands

- `/update` — fetch today's matches in one call and report status/score/scorers
  immediately. No scheduling side effects.
- `/timezone <tz>` — switch the active display timezone (e.g. `America/New_York`).
  Cancels and reschedules all pending jobs against the new timezone; jobs that
  already fired today are not replayed.
- `/timezone` — show the current timezone and local time.

## API-Football integration notes

The original data source (wc2026api.com) is no longer available. The bot now uses
[API-Football](https://www.api-football.com/) (api-sports.io), scoped to the World
Cup league/season:

- `GET /fixtures?date=YYYY-MM-DD&league=1&season=2026` — matches for a given date
- `GET /fixtures?id={id}` + `GET /fixtures/events?fixture={id}` — a single match's
  current score/status plus its full goal/card timeline
- `GET /teams?name={name}&season=2026` — resolve a team name to its numeric id
  (cached in-memory per process)
- `GET /fixtures?team={id}&next=1&league=1&season=2026` — a team's next fixture
- Auth via the `x-apisports-key` header

API-Football doesn't expose explicit "half-time"/"full-time" events — match phase
is read from `fixture.status.short` (`1H`, `HT`, `2H`, `ET`, `P`, `FT`, ...) and
transitions are detected by diffing against the last-seen status in `core.py`.
Goal/card events also lack a stable id, so `MatchEvent` builds a synthetic one from
the event's minute, team, player, and detail to dedupe across polls.

Sign up for a key at api-football.com (or via RapidAPI) — the free tier is rate
limited (historically 100 requests/day), which is enough for this bot's polling
pattern (5-minute polling only while a watched team is actually live) but leaves
little headroom for heavy manual `/update` use; upgrade if needed.

If the live API differs from what's coded here, `worldcupbot/api.py` and
`worldcupbot/models.py` are the only places that need to change — the rest of the
bot operates on the `Match`/`MatchEvent` dataclasses.
