from __future__ import annotations

from datetime import date
from typing import Optional

import httpx

from worldcupbot.config import WC_API_BASE_URL, WC_API_KEY, WC_LEAGUE_ID, WC_SEASON
from worldcupbot.models import Match


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
        fixtures = resp.json().get("response", [])
        return [Match.from_api(item) for item in fixtures]

    async def get_match(self, fixture_id: int) -> Match:
        fixture_resp = await self._client.get("/fixtures", params={"id": fixture_id})
        fixture_resp.raise_for_status()
        fixtures = fixture_resp.json().get("response", [])
        if not fixtures:
            raise ValueError(f"Fixture {fixture_id} not found")

        events_resp = await self._client.get("/fixtures/events", params={"fixture": fixture_id})
        events_resp.raise_for_status()
        events = events_resp.json().get("response", [])

        return Match.from_api(fixtures[0], events)

    async def get_team_id(self, team_name: str) -> Optional[int]:
        if team_name in self._team_id_cache:
            return self._team_id_cache[team_name]
        resp = await self._client.get("/teams", params={"name": team_name, "season": WC_SEASON})
        resp.raise_for_status()
        results = resp.json().get("response", [])
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
        fixtures = resp.json().get("response", [])
        if not fixtures:
            return None
        return Match.from_api(fixtures[0])
