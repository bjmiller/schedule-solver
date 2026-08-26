"""Shared fixtures: the default league and a solved schedule for it."""

from collections.abc import Iterator

import pytest

from scheduler.models import LeagueInput, Schedule, TeamId
from scheduler.solver import solve


def make_league(
    divisions: tuple[list[int], list[int]] = ([1, 2, 3, 4, 5], [6, 7, 8, 9, 10]),
    losers: list[int] | None = None,
    featured: tuple[int, int] | None = None,
) -> LeagueInput:
    if losers is None:
        losers = divisions[0]
    featured_pair = None
    if featured is not None:
        featured_pair = (TeamId(featured[0]), TeamId(featured[1]))
    return LeagueInput(
        divisions=(
            frozenset(TeamId(team) for team in divisions[0]),
            frozenset(TeamId(team) for team in divisions[1]),
        ),
        losers=frozenset(TeamId(team) for team in losers),
        featured=featured_pair,
    )


@pytest.fixture(scope="session")
def default_league() -> LeagueInput:
    return make_league()


@pytest.fixture(scope="session")
def solved_schedule(default_league: LeagueInput) -> Iterator[Schedule]:
    yield solve(default_league)
