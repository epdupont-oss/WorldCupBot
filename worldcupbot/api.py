from __future__ import annotations

import logging
from datetime import date
from typing import Optional

import httpx

from worldcupbot.config import WC_API_BASE_URL, WC_API_KEY, WC_COMPETITION_CODE, WC_SEASON
from worldcupbot.models import Match

logger = logging.getLogger(__name__)


class WorldCupAPIClient:
    """Async wrapper around the football-data.org v4 REST API, scoped to the
    World Cup competition. https://docs.football-data.org/general/v4/
    """

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=WC_API_BASE_URL,
            headers={"X-Auth-Token": WC_API_KEY},
            timeout=15.0,
        )
        self._team_id_cache: dict[str, int] = {}

    async def aclose(self) -> None:
        await self._client.aclose()

    @staticmethod
    def _log_api_errors(payload: dict) -> None:
        message = payload.get("message")
        if message:
            logger.warning("football-data.org returned an error: %s", message)

    async def get_matches_for_date(self, day: date) -> list[Match]:
        resp = await self._client.get(
            f"/competitions/{WC_COMPETITION_CODE}/matches",
            params={"dateFrom": day.isoformat(), "dateTo": day.isoformat(), "season": WC_SEASON},
        )
        resp.raise_for_status()
        payload = resp.json()
        self._log_api_errors(payload)
        matches = payload.get("matches", [])
        return [Match.from_api(item) for item in matches]

    async def get_match(self, fixture_id: int) -> Match:
        resp = await self._client.get(f"/matches/{fixture_id}")
        resp.raise_for_status()
        payload = resp.json()
        self._log_api_errors(payload)
        return Match.from_api(payload)

    async def get_team_id(self, team_name: str) -> Optional[int]:
        if team_name in self._team_id_cache:
            return self._team_id_cache[team_name]
        resp = await self._client.get(
            f"/competitions/{WC_COMPETITION_CODE}/teams", params={"season": WC_SEASON}
        )
        resp.raise_for_status()
        payload = resp.json()
        self._log_api_errors(payload)
        teams = payload.get("teams", [])
        match = next(
            (
                t
                for t in teams
                if team_name in (t.get("name"), t.get("shortName"), t.get("tla"))
            ),
            None,
        )
        if match is None:
            return None
        team_id = match["id"]
        self._team_id_cache[team_name] = team_id
        return team_id

    async def get_next_fixture(self, team_name: str) -> Optional[Match]:
        team_id = await self.get_team_id(team_name)
        if team_id is None:
            return None
        resp = await self._client.get(
            f"/teams/{team_id}/matches",
            params={"status": "SCHEDULED", "competitions": WC_COMPETITION_CODE, "limit": 1},
        )
        resp.raise_for_status()
        payload = resp.json()
        self._log_api_errors(payload)
        matches = payload.get("matches", [])
        if not matches:
            return None
        return Match.from_api(matches[0])
