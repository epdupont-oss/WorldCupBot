from __future__ import annotations

import logging

import httpx

from worldcupbot.config import GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)

_GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class GroqEnricher:
    """Optional web-search-grounded lookup to enrich generic goal alerts with a
    scorer name, since football-data.org's free tier doesn't expose that.

    Disabled (returns None for every lookup) unless GROQ_API_KEY is set.
    Failures (timeouts, errors, no answer found) are swallowed and logged —
    enrichment is a nice-to-have, never a reason to block or delay an alert.
    """

    def __init__(self) -> None:
        self.enabled = bool(GROQ_API_KEY)
        self._client = httpx.AsyncClient(
            base_url=_GROQ_BASE_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
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
                "/chat/completions",
                json={
                    "model": GROQ_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a terse sports-news assistant. Answer in one short line.",
                        },
                        {"role": "user", "content": question},
                    ],
                },
            )
            resp.raise_for_status()
            payload = resp.json()
        except Exception:
            logger.exception("Groq scorer lookup failed")
            return None

        answer = self._extract_text(payload)
        if not answer or "UNKNOWN" in answer.upper():
            return None
        return answer

    @staticmethod
    def _extract_text(payload: dict) -> str | None:
        choices = payload.get("choices") or []
        if not choices:
            return None
        content = (choices[0].get("message") or {}).get("content")
        return content.strip() if content else None
