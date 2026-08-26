"""Strict validation of raw league input into a typed LeagueInput."""

import json
import re

from scheduler.models import (
    DIVISION_COUNT,
    DIVISION_SIZE,
    LOSER_COUNT,
    TOTAL_TEAMS,
    LeagueInput,
    TeamId,
)

MAX_TEAM_ID = 9999


class ValidationError(ValueError):
    """Raised when the raw league input violates structural rules."""


def parse_league_input(data: object) -> LeagueInput:
    """Validate an already-parsed JSON document and build a LeagueInput.

    Team ids may be plain integers or zero-padded 4-digit strings ('0006'),
    matching the output format. Both forms may be mixed freely.
    """
    document = _require_dict(data, "input")
    divisions = _parse_divisions(document)
    losers = _parse_losers(document, divisions)
    featured = _parse_featured(document, divisions)
    return LeagueInput(divisions=divisions, losers=losers, featured=featured)


def parse_league_input_json(raw: str) -> LeagueInput:
    """Parse a JSON string and validate it."""
    try:
        data: object = json.loads(raw)
    except json.JSONDecodeError as exc:
        msg = f"input is not valid JSON: {exc}"
        if _LOOKS_LIKE_UNQUOTED_PADDED_ID.search(raw):
            msg += (
                " (note: ids padded with leading zeros must be quoted "
                'strings, e.g. "0006", because JSON forbids 0-prefixed numbers)'
            )
        raise ValidationError(msg) from exc
    return parse_league_input(data)


_LOOKS_LIKE_UNQUOTED_PADDED_ID = re.compile(r"""[\[,\s]0\d""")


def _require_dict(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        msg = f"{label} must be a JSON object"
        raise ValidationError(msg)
    for key in value:
        if not isinstance(key, str):
            msg = f"{label} must only have string keys"
            raise ValidationError(msg)
    return value


def _require_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{label} must be an integer"
        raise ValidationError(msg)
    return value


def _parse_divisions(
    document: dict[str, object],
) -> tuple[frozenset[TeamId], frozenset[TeamId]]:
    if "divisions" not in document:
        msg = "input is missing required key 'divisions'"
        raise ValidationError(msg)
    raw_divisions = document["divisions"]
    if not isinstance(raw_divisions, list) or len(raw_divisions) != DIVISION_COUNT:
        msg = "'divisions' must be a list of exactly 2 divisions"
        raise ValidationError(msg)

    divisions: list[frozenset[TeamId]] = []
    seen: set[TeamId] = set()
    for index, raw_division in enumerate(raw_divisions):
        label = f"divisions[{index}]"
        division = _require_dict_values(raw_division, label)
        teams: set[TeamId] = set()
        for position, entry in enumerate(division):
            team_id = _validate_team_id(entry, f"{label}[{position}]")
            if team_id in seen:
                msg = f"team {team_id:04d} appears more than once across divisions"
                raise ValidationError(msg)
            if team_id in teams:
                msg = f"team {team_id:04d} is duplicated within {label}"
                raise ValidationError(msg)
            teams.add(team_id)
        seen |= teams
        divisions.append(frozenset(teams))

    if len(seen) != TOTAL_TEAMS:
        msg = f"expected exactly {TOTAL_TEAMS} distinct teams, got {len(seen)}"
        raise ValidationError(msg)

    first, second = divisions
    return (first, second)


def _require_dict_values(value: object, label: str) -> list[object]:
    if not isinstance(value, list) or len(value) != DIVISION_SIZE:
        msg = f"{label} must be a list of exactly {DIVISION_SIZE} team ids"
        raise ValidationError(msg)
    return value


def _validate_team_id(entry: object, label: str) -> TeamId:
    value = _parse_team_number(entry, label)
    if not 1 <= value <= MAX_TEAM_ID:
        msg = f"{label} must be between 1 and {MAX_TEAM_ID} (4-digit id)"
        raise ValidationError(msg)
    return TeamId(value)


def _parse_team_number(entry: object, label: str) -> int:
    """Accept plain integers and zero-padded digit strings like '0006'."""
    if isinstance(entry, bool):
        msg = f"{label} must be an integer or a 4-digit string"
        raise ValidationError(msg)
    if isinstance(entry, str):
        if not entry.isdigit() or len(entry) > len(str(MAX_TEAM_ID)):
            msg = f"{label} must be an integer or a 4-digit string"
            raise ValidationError(msg)
        return int(entry)
    return _require_int(entry, label)


def _parse_losers(
    document: dict[str, object],
    divisions: tuple[frozenset[TeamId], frozenset[TeamId]],
) -> frozenset[TeamId]:
    if "losers" not in document:
        msg = "input is missing required key 'losers'"
        raise ValidationError(msg)
    raw_losers = document["losers"]
    if not isinstance(raw_losers, list) or len(raw_losers) != LOSER_COUNT:
        msg = f"'losers' must be a list of exactly {LOSER_COUNT} team ids"
        raise ValidationError(msg)

    all_teams = divisions[0] | divisions[1]
    losers: set[TeamId] = set()
    for index, entry in enumerate(raw_losers):
        team_id = _validate_team_id(entry, f"losers[{index}]")
        if team_id not in all_teams:
            msg = f"losers[{index}] refers to unknown team {team_id:04d}"
            raise ValidationError(msg)
        if team_id in losers:
            msg = f"team {team_id:04d} is duplicated in 'losers'"
            raise ValidationError(msg)
        losers.add(team_id)
    return frozenset(losers)


def _parse_featured(
    document: dict[str, object],
    divisions: tuple[frozenset[TeamId], frozenset[TeamId]],
) -> tuple[TeamId, TeamId] | None:
    if "featured" not in document or document["featured"] is None:
        return None
    raw_featured = document["featured"]
    if not isinstance(raw_featured, list) or len(raw_featured) != 2:
        msg = "'featured' must be a list of exactly 2 team ids"
        raise ValidationError(msg)

    all_teams = divisions[0] | divisions[1]
    featured: list[TeamId] = []
    for index, entry in enumerate(raw_featured):
        team_id = _validate_team_id(entry, f"featured[{index}]")
        if team_id not in all_teams:
            msg = f"featured[{index}] refers to unknown team {team_id:04d}"
            raise ValidationError(msg)
        featured.append(team_id)

    first, second = featured
    if first == second:
        msg = "'featured' must contain two distinct teams"
        raise ValidationError(msg)
    return (first, second)
