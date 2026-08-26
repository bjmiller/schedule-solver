"""Tests for week shuffling and featured-game placement."""

from __future__ import annotations

import random
from collections import defaultdict
from typing import cast

import pytest
from conftest import make_league

from scheduler.models import (
    WEEKS_IN_SEASON,
    Game,
    LeagueInput,
    Schedule,
    TeamId,
    WeekNumber,
)
from scheduler.shuffle import (
    FeaturedGameError,
    move_featured_to_week_one,
    shuffle_weeks,
)
from scheduler.solver import solve
from scheduler.verifier import verify


def games_by_week(schedule: Schedule) -> dict[int, set[tuple[int, int]]]:
    by_week: dict[int, set[tuple[int, int]]] = defaultdict(set)
    for game in schedule.games:
        by_week[game.week].add((game.away, game.home))
    return dict(by_week)


def featured_league() -> LeagueInput:
    return make_league(featured=(3, 7))


def test_shuffled_schedule_is_valid(solved_schedule: Schedule, default_league: LeagueInput) -> None:
    shuffled = shuffle_weeks(solved_schedule, default_league, rng=random.Random(42))
    assert verify(shuffled, default_league) == []
    assert len(shuffled.games) == len(solved_schedule.games)


def test_shuffle_preserves_matchups_and_weekly_slates(
    solved_schedule: Schedule, default_league: LeagueInput
) -> None:
    shuffled = shuffle_weeks(solved_schedule, default_league, rng=random.Random(7))
    original_pairs = {(g.home, g.away) for g in solved_schedule.games}
    shuffled_pairs = {(g.home, g.away) for g in shuffled.games}
    assert original_pairs == shuffled_pairs

    original_slates = sorted(sorted(slate) for slate in games_by_week(solved_schedule).values())
    shuffled_slates = sorted(sorted(slate) for slate in games_by_week(shuffled).values())
    assert original_slates == shuffled_slates


def test_shuffle_is_reproducible_with_seed(
    solved_schedule: Schedule, default_league: LeagueInput
) -> None:
    first = shuffle_weeks(solved_schedule, default_league, rng=random.Random(1))
    second = shuffle_weeks(solved_schedule, default_league, rng=random.Random(1))
    assert first == second


def test_featured_moved_to_week_one() -> None:
    league = featured_league()
    first, second = cast(tuple[TeamId, TeamId], league.featured)
    schedule = move_featured_to_week_one(solve(league), league)
    week_one_pairs = [{game.home, game.away} for game in schedule.games if game.week == 1]
    assert {first, second} in week_one_pairs
    assert verify(schedule, league) == []


def test_featured_already_in_week_one_is_unchanged() -> None:
    league = featured_league()
    placed = move_featured_to_week_one(solve(league), league)
    again = move_featured_to_week_one(placed, league)
    assert placed == again


def test_swap_keeps_five_games_per_week() -> None:
    league = featured_league()
    schedule = move_featured_to_week_one(solve(league), league)
    by_week = games_by_week(schedule)
    assert all(len(by_week[week]) == 5 for week in range(1, WEEKS_IN_SEASON + 1))


def test_no_featured_returns_same_object(
    solved_schedule: Schedule, default_league: LeagueInput
) -> None:
    assert move_featured_to_week_one(solved_schedule, default_league) is solved_schedule


def test_missing_featured_game_raises() -> None:
    league = featured_league()
    first, second = cast(tuple[TeamId, TeamId], league.featured)
    schedule = solve(league)
    target = next(game for game in schedule.games if {game.home, game.away} == {first, second})
    donor = next(
        game
        for game in schedule.games
        if game != target and {game.home, game.away}.isdisjoint({first, second})
    )
    mutated = tuple(
        Game(week=target.week, away=donor.away, home=donor.home) if game == target else game
        for game in schedule.games
    )
    with pytest.raises(FeaturedGameError, match="never play each other"):
        move_featured_to_week_one(Schedule(games=mutated), league)


def test_week_number_relables_cleanly() -> None:
    game = Game(week=WeekNumber(3), away=TeamId(1), home=TeamId(2))
    relabeled = Game(week=WeekNumber(9), away=game.away, home=game.home)
    assert relabeled.week == 9
