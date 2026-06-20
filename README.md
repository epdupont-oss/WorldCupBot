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
| `WC_API_KEY` | yes | — | API key for wc2026api.com |
| `DISPLAY_TZ` | no | `Europe/Zurich` | IANA timezone all displayed times and schedules are anchored to |
| `WC_API_BASE_URL` | no | `https://wc2026api.com/api/v1` | Override for the API base URL |

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

## wc2026api.com integration notes

`worldcupbot/api.py` and `worldcupbot/models.py` encode the assumed wc2026api.com
contract:

- `GET /matches?date=YYYY-MM-DD` — list of matches for a given date
- `GET /matches/{id}` — single match with full event timeline
- `GET /teams/{code}/fixtures?upcoming=true` — a team's next fixture
- Auth via `X-API-Key` header

`Match.from_api` / `MatchEvent.from_api` are tolerant of a couple of common field
name variants (e.g. `kickoff` vs `kickoff_utc`, `team_code` vs `team`). If the live
API differs, these two files are the only places that need to change — the rest of
the bot operates on the `Match`/`MatchEvent` dataclasses.
