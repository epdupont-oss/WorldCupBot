from __future__ import annotations

import logging
from datetime import date
from typing import Optional

import httpx

from worldcupbot.config import WC_API_BASE_URL, WC_API_KEY, WC_LEAGUE_ID, WC_SEASON
from worldcupbot.models import Match

logger = logging.getLogger(__name__)


class WorldCupAPIClient:
    """Async wrapper around the API-Football (api-sports.io) REST API, scoped to
    the World Cup league/season. https://www.api-football.com/documentation-v3
    """

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=WC_API_BASE_URL,
            headers={"x-apisports-key": WC_API_KEY},
            timeout=15.0,
        )
        self._team_id_cache: dict[str, int] = {}

    async def aclose(self) -> None:
        await self._client.aclose()

    @staticmethod
    def _log_api_errors(payload: dict) -> None:
        # API-Football returns HTTP 200 even when the request was rejected (e.g.
        # plan restrictions, bad params); the rejection reason is in "errors".
        errors = payload.get("errors")
        if errors:
            logger.warning("API-Football returned errors: %s", errors)

    async def get_matches_for_date(self, day: date) -> list[Match]:
        resp = await self._client.get(
            "/fixtures",
            params={
                "date": day.isoformat(),
                "league": WC_LEAGUE_ID,
                "season": WC_SEASON,
                "timezone": "UTC",
            },
        )
        resp.raise_for_status()
        payload = resp.json()
        self._log_api_errors(payload)
        fixtures = payload.get("response", [])
        return [Match.from_api(item) for item in fixtures]

    async def get_match(self, fixture_id: int) -> Match:
        fixture_resp = await self._client.get("/fixtures", params={"id": fixture_id})
        fixture_resp.raise_for_status()
        fixture_payload = fixture_resp.json()
        self._log_api_errors(fixture_payload)
        fixtures = fixture_payload.get("response", [])
        if not fixtures:
            raise ValueError(f"Fixture {fixture_id} not found")

        events_resp = await self._client.get("/fixtures/events", params={"fixture": fixture_id})
        events_resp.raise_for_status()
        events_payload = events_resp.json()
        self._log_api_errors(events_payload)
        events = events_payload.get("response", [])

        return Match.from_api(fixtures[0], events)

    async def get_team_id(self, team_name: str) -> Optional[int]:
        if team_name in self._team_id_cache:
            return self._team_id_cache[team_name]
        resp = await self._client.get("/teams", params={"name": team_name, "season": WC_SEASON})
        resp.raise_for_status()
        payload = resp.json()
        self._log_api_errors(payload)
        results = payload.get("response", [])
        if not results:
            return None
        team_id = results[0]["team"]["id"]
        self._team_id_cache[team_name] = team_id
        return team_id

    async def get_next_fixture(self, team_name: str) -> Optional[Match]:
        team_id = await self.get_team_id(team_name)
        if team_id is None:
            return None
        resp = await self._client.get(
            "/fixtures",
            params={
                "team": team_id,
                "next": 1,
                "league": WC_LEAGUE_ID,
                "season": WC_SEASON,
            },
        )
        resp.raise_for_status()
        payload = resp.json()
        self._log_api_errors(payload)
        fixtures = payload.get("response", [])
        if not fixtures:
            return None
        return Match.from_api(fixtures[0])
