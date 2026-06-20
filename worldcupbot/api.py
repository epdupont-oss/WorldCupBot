from __future__ import annotations

from datetime import date
from typing import Optional

import httpx

from worldcupbot.config import WC_API_BASE_URL, WC_API_KEY
from worldcupbot.models import Match


class WorldCupAPIClient:
    """Thin async wrapper around the wc2026api.com REST API.

    Endpoint paths/shapes are based on the documented wc2026api.com contract;
    adjust ENDPOINT constants below if the live API differs.
    """

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=WC_API_BASE_URL,
            headers={"X-API-Key": WC_API_KEY},
            timeout=15.0,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get_matches_for_date(self, day: date) -> list[Match]:
        resp = await self._client.get("/matches", params={"date": day.isoformat()})
        resp.raise_for_status()
        payload = resp.json()
        items = payload.get("matches", payload) if isinstance(payload, dict) else payload
        return [Match.from_api(item) for item in items]

    async def get_match(self, match_id: str) -> Match:
        resp = await self._client.get(f"/matches/{match_id}")
        resp.raise_for_status()
        payload = resp.json()
        data = payload.get("match", payload) if isinstance(payload, dict) else payload
        return Match.from_api(data)

    async def get_next_fixture(self, team_code: str) -> Optional[Match]:
        resp = await self._client.get(f"/teams/{team_code}/fixtures", params={"upcoming": "true", "limit": 1})
        resp.raise_for_status()
        payload = resp.json()
        items = payload.get("fixtures", payload) if isinstance(payload, dict) else payload
        if not items:
            return None
        return Match.from_api(items[0])
