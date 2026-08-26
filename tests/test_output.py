"""Tests for schedule formatting and mandatory verification."""

import dataclasses
import re

import pytest

from scheduler.models import GAMES_PER_WEEK, WEEKS_IN_SEASON, LeagueInput, Schedule, WeekNumber
from scheduler.output import VerificationError, format_schedule
from scheduler.verifier import verify

LINE_PATTERN = re.compile(r"^\d{2},\d{4},\d{4}$")


def test_format_produces_expected_shape(
    solved_schedule: Schedule, default_league: LeagueInput
) -> None:
    rendered = format_schedule(solved_schedule, default_league)
    lines = rendered.splitlines()
    assert len(lines) == GAMES_PER_WEEK * WEEKS_IN_SEASON
    for line in lines:
        assert LINE_PATTERN.match(line), f"bad line format: {line!r}"


def test_lines_sorted_by_week(solved_schedule: Schedule, default_league: LeagueInput) -> None:
    rendered = format_schedule(solved_schedule, default_league)
    weeks = [int(line.split(",")[0]) for line in rendered.splitlines()]
    assert weeks == sorted(weeks)
    assert weeks[0] == 1
    assert weeks[-1] == WEEKS_IN_SEASON


def test_zero_padding(solved_schedule: Schedule, default_league: LeagueInput) -> None:
    rendered = format_schedule(solved_schedule, default_league)
    first_line = rendered.splitlines()[0]
    week, away, home = first_line.split(",")
    assert len(week) == 2
    assert len(away) == 4
    assert len(home) == 4


def test_invalid_schedule_is_not_formatted(
    solved_schedule: Schedule, default_league: LeagueInput
) -> None:
    game = solved_schedule.games[0]
    mutated = Schedule(
        games=(dataclasses.replace(game, week=WeekNumber(99)), *solved_schedule.games[1:])
    )
    assert verify(mutated, default_league)
    with pytest.raises(VerificationError):
        format_schedule(mutated, default_league)
