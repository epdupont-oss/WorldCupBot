from __future__ import annotations

import logging

import httpx

from worldcupbot.config import MISTRAL_API_KEY, MISTRAL_MODEL

logger = logging.getLogger(__name__)

_MISTRAL_BASE_URL = "https://api.mistral.ai/v1"


class MistralEnricher:
    """Optional web-search-grounded lookup to enrich generic goal alerts with a
    scorer name, since football-data.org's free tier doesn't expose that.

    Disabled (returns None for every lookup) unless MISTRAL_API_KEY is set.
    Failures (timeouts, errors, no answer found) are swallowed and logged —
    enrichment is a nice-to-have, never a reason to block or delay an alert.
    """

    def __init__(self) -> None:
        self.enabled = bool(MISTRAL_API_KEY)
        self._client = httpx.AsyncClient(
            base_url=_MISTRAL_BASE_URL,
            headers={"Authorization": f"Bearer {MISTRAL_API_KEY}"},
            timeout=20.0,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def lookup_goal_scorer(self, scoring_team_name: str, score_label: str) -> str | None:
        if not self.enabled:
            return None

        question = (
            f"A goal was just scored by {scoring_team_name} in a World Cup 2026 match "
            f"(score now {score_label}). Search the web for the most recent news and tell me "
            f"who scored the goal. Reply with just the player's name and the minute if known, "
            f"or reply exactly 'UNKNOWN' if you cannot find a confident, recent answer."
        )
        try:
            resp = await self._client.post(
                "/conversations",
                json={
                    "model": MISTRAL_MODEL,
                    "instructions": "You are a terse sports-news assistant. Answer in one short line.",
                    "tools": [{"type": "web_search"}],
                    "inputs": question,
                },
            )
            resp.raise_for_status()
            payload = resp.json()
        except Exception:
            logger.exception("Mistral scorer lookup failed")
            return None

        answer = self._extract_text(payload)
        if not answer or "UNKNOWN" in answer.upper():
            return None
        return answer

    @staticmethod
    def _extract_text(payload: dict) -> str | None:
        for entry in payload.get("outputs", []):
            if entry.get("type") != "message.output":
                continue
            content = entry.get("content")
            if isinstance(content, str):
                return content.strip()
            if isinstance(content, list):
                texts = [c.get("text", "") for c in content if isinstance(c, dict)]
                joined = " ".join(t for t in texts if t).strip()
                if joined:
                    return joined
        return None
