"""Tests for the independent schedule verifier."""

import dataclasses

import pytest

from scheduler.models import Game, LeagueInput, Schedule, TeamId, WeekNumber
from scheduler.verifier import verify


def test_valid_schedule_passes(solved_schedule: Schedule, default_league: LeagueInput) -> None:
    assert verify(solved_schedule, default_league) == []


def test_missing_game_detected(solved_schedule: Schedule, default_league: LeagueInput) -> None:
    broken = Schedule(games=solved_schedule.games[1:])
    problems = verify(broken, default_league)
    assert problems


def test_repeated_pair_with_same_orientation_detected(
    solved_schedule: Schedule, default_league: LeagueInput
) -> None:
    first_game = solved_schedule.games[0]
    other_game = next(game for game in solved_schedule.games if game.week != first_game.week)
    cloned = dataclasses.replace(other_game, away=first_game.away, home=first_game.home)
    mutated = [cloned if game == other_game else game for game in solved_schedule.games]
    problems = verify(Schedule(games=tuple(mutated)), default_league)
    assert any("meet" in problem or "do not host" in problem for problem in problems)


def test_same_team_plays_itself_detected(default_league: LeagueInput) -> None:
    games = [Game(week=WeekNumber(week), away=TeamId(1), home=TeamId(2)) for week in range(1, 14)]
    games[0] = Game(week=WeekNumber(1), away=TeamId(1), home=TeamId(1))
    problems = verify(Schedule(games=tuple(games)), default_league)
    assert any("plays itself" in problem for problem in problems)


def test_wrong_home_totals_detected(solved_schedule: Schedule, default_league: LeagueInput) -> None:
    game = solved_schedule.games[0]
    flipped = dataclasses.replace(game, away=game.home, home=game.away)
    others = [g for g in solved_schedule.games if g != game]
    problems = verify(Schedule(games=tuple([flipped, *others])), default_league)
    assert any("home games" in problem for problem in problems)


@pytest.mark.parametrize("bad_week", [-1, 0, 14, 99])
def test_out_of_range_weeks_detected(
    solved_schedule: Schedule,
    default_league: LeagueInput,
    bad_week: int,
) -> None:
    game = solved_schedule.games[0]
    mutated = [dataclasses.replace(game, week=WeekNumber(bad_week)), *solved_schedule.games[1:]]
    problems = verify(Schedule(games=tuple(mutated)), default_league)
    assert any("weeks must be exactly" in problem for problem in problems)


def test_team_playing_twice_in_a_week_detected(
    solved_schedule: Schedule, default_league: LeagueInput
) -> None:
    first_game = solved_schedule.games[0]
    other_game = next(
        game
        for game in solved_schedule.games
        if {game.home, game.away}.isdisjoint({first_game.home, first_game.away})
    )
    moved = dataclasses.replace(other_game, week=first_game.week)
    mutated = [moved if game == other_game else game for game in solved_schedule.games]
    problems = verify(Schedule(games=tuple(mutated)), default_league)
    assert any("games, expected exactly 1" in problem for problem in problems)
