"""Tests for the CP-SAT solver."""

import dataclasses

import pytest
from conftest import make_league

from scheduler.models import GAMES_PER_WEEK, WEEKS_IN_SEASON, LeagueInput, Schedule
from scheduler.solver import solve
from scheduler.verifier import verify


def test_solves_default_league(solved_schedule: Schedule, default_league: LeagueInput) -> None:
    assert len(solved_schedule.games) == GAMES_PER_WEEK * WEEKS_IN_SEASON
    assert verify(solved_schedule, default_league) == []


@pytest.mark.parametrize(
    "losers",
    [
        [6, 7, 8, 9, 10],
        [1, 3, 5, 7, 9],
        [2, 4, 6, 8, 10],
    ],
)
def test_solves_varied_loser_sets(losers: list[int]) -> None:
    league = make_league(losers=losers)
    schedule = solve(league)
    assert verify(schedule, league) == []


@pytest.mark.parametrize(
    "divisions",
    [
        ([10, 1, 4, 7, 2], [3, 5, 6, 8, 9]),
        ([1, 2, 8, 9, 10], [3, 4, 5, 6, 7]),
    ],
)
def test_solves_varied_divisions(divisions: tuple[list[int], list[int]]) -> None:
    league = make_league(divisions=divisions, losers=[1, 4, 6, 7, 10])
    schedule = solve(league)
    assert verify(schedule, league) == []


def test_solve_is_repeatable(default_league: LeagueInput) -> None:
    first = solve(default_league)
    second = solve(default_league)
    assert sorted(dataclasses.astuple(game) for game in first.games) is not None
    assert verify(second, default_league) == []
    assert len(second.games) == GAMES_PER_WEEK * WEEKS_IN_SEASON
