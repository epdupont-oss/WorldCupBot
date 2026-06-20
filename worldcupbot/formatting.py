from __future__ import annotations

from typing import Optional
from zoneinfo import ZoneInfo

from worldcupbot.config import WATCHED_TEAM_CODES
from worldcupbot.models import Match, MatchEvent


def local_time(match: Match, tz: ZoneInfo) -> str:
    if match.kickoff_utc is None:
        return ""
    return match.kickoff_utc.astimezone(tz).strftime("%H:%M")


def local_date_label(match: Match, tz: ZoneInfo) -> str:
    if match.kickoff_utc is None:
        return ""
    return match.kickoff_utc.astimezone(tz).strftime("%b %d")


def next_fixture_label(team_code: str, fixture: Optional[Match], tz: ZoneInfo) -> str:
    if fixture is None:
        return f"📅 Next {team_code}: TBD"
    opponent = fixture.away if fixture.home.code == team_code else fixture.home
    team = fixture.home if fixture.home.code == team_code else fixture.away
    return f"📅 Next: {team.name} vs {opponent.name} · {local_date_label(fixture, tz)} · {local_time(fixture, tz)}"


def format_pre_match(match: Match, tz: ZoneInfo) -> str:
    return (
        f"⏱ Kickoff in 2 minutes!\n"
        f"{match.home.label} vs {match.away.label}\n"
        f"📍 {match.venue} · {match.round_name} · {local_time(match, tz)}"
    )


def format_goal(match: Match, event: MatchEvent) -> str:
    line = f"⚽ GOAL — {match.home.name} {match.score_label} {match.away.name}\n👤 {event.player} {event.minute}'"
    if event.assist:
        line += f" ({event.assist} assist)"
    return line


def format_red_card(match: Match, event: MatchEvent) -> str:
    return f"🟥 Red card — {event.player} {event.minute}'\n{match.home.name} {match.score_label} {match.away.name}"


def format_phase_transition(match: Match, event: MatchEvent) -> str:
    labels = {
        "half_time": "🔔 Half-time",
        "second_half_start": "▶️ Second half underway",
        "extra_time_start": "⏳ Extra time",
        "penalties_start": "🥅 Penalties",
    }
    header = labels.get(event.type, event.type)
    scorers = match.scorers_label()
    body = f"{header}: {match.home.name} {match.score_label} {match.away.name}"
    if scorers:
        body += f"\n⚽ {scorers}"
    return body


def format_full_time(match: Match, next_fixture_lines: list[str]) -> str:
    home_scorers = match.scorers_label(match.home.code)
    away_scorers = match.scorers_label(match.away.code)
    lines = [f"✅ Full-time: {match.home.name} {match.score_label} {match.away.name}"]
    if home_scorers:
        lines.append(f"⚽ {home_scorers}")
    if away_scorers:
        lines.append(f"⚽ {away_scorers} ({match.away.name})")
    lines.extend(next_fixture_lines)
    return "\n".join(lines)


def format_update_line(match: Match, tz: ZoneInfo) -> str:
    if match.is_live:
        status = f"🔴 live {match.minute}'" if match.minute else "🔴 live"
    elif match.is_finished:
        status = "✅ finished"
    else:
        status = "⏳ upcoming"

    line = f"{match.home.label} vs {match.away.label} · {status}"
    if match.is_live or match.is_finished:
        line += f" · {match.score_label}"
    else:
        line += f" · {local_time(match, tz)}"

    scorers = match.scorers_label()
    if scorers and (match.is_live or match.is_finished):
        line += f"\n   ⚽ {scorers}"
    return line


def format_update_message(matches: list[Match], tz: ZoneInfo) -> str:
    watched = [m for m in matches if m.involves_watched_team]
    others = [m for m in matches if not m.involves_watched_team]
    lines = []
    for m in watched:
        lines.append(format_update_line(m, tz))
    for m in others:
        lines.append(format_update_line(m, tz))
    if not lines:
        return "No matches today."
    return "\n".join(lines)


def format_morning_digest(
    matches: list[Match],
    next_fixture: Optional[Match],
    watched_team_code: Optional[str],
    tz: ZoneInfo,
) -> str:
    lines = ["☕ Good morning! Today's matches:"]
    has_watched = any(m.involves_watched_team for m in matches)
    for m in matches:
        venue_part = f" · {m.venue}" if m.venue else ""
        lines.append(f"{m.home.label} vs {m.away.label} · {local_time(m, tz)}{venue_part}")
    if not has_watched:
        lines.append("(No Switzerland or USA today)")
    if watched_team_code:
        lines.append(next_fixture_label(watched_team_code, next_fixture, tz))
    return "\n".join(lines)


def format_evening_recap(
    matches: list[Match],
    next_fixture: Optional[Match],
    watched_team_code: Optional[str],
    tz: ZoneInfo,
) -> str:
    lines = ["🌙 Today's results:"]
    for m in matches:
        scorers = m.scorers_label()
        line = f"{m.home.label} {m.score_label} {m.away.label}"
        if scorers:
            line += f" · {scorers}"
        lines.append(line)
    if watched_team_code:
        lines.append(next_fixture_label(watched_team_code, next_fixture, tz))
    return "\n".join(lines)
