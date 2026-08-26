"""Week shuffling and week-1 featured-game placement."""

from __future__ import annotations

import dataclasses
import random

from scheduler.models import WEEKS_IN_SEASON, Game, LeagueInput, Schedule, WeekNumber


class FeaturedGameError(RuntimeError):
    """Raised when the featured teams could not be placed in week 1."""


def shuffle_weeks(
    schedule: Schedule,
    league: LeagueInput,
    rng: random.Random | None = None,
) -> Schedule:
    """Randomly permute which games happen in which week.

    Every rule in this league is either week-independent (matchups, home/away
    totals) or applied after shuffling (the featured week-1 game), so a week
    permutation of a valid schedule is always valid.
    """
    del league
    randomizer = rng if rng is not None else random.Random()
    weeks = list(range(1, WEEKS_IN_SEASON + 1))
    shuffled = weeks[:]
    randomizer.shuffle(shuffled)
    week_map = dict(zip(weeks, shuffled, strict=True))
    return _relabel_weeks(schedule, week_map)


def move_featured_to_week_one(schedule: Schedule, league: LeagueInput) -> Schedule:
    """Ensure the featured pair meets in week 1 by swapping whole weeks.

    Finds the first week in which the featured teams play each other and swaps
    that week's entire slate with week 1. If they already meet in week 1, the
    schedule is returned unchanged.
    """
    if league.featured is None:
        return schedule
    first, second = league.featured
    meeting_weeks = {
        game.week for game in schedule.games if {game.home, game.away} == {first, second}
    }
    if not meeting_weeks:
        msg = f"featured teams {first:04d} and {second:04d} never play each other"
        raise FeaturedGameError(msg)

    source_week = min(meeting_weeks)
    if source_week == WeekNumber(1):
        return schedule

    week_map: dict[int, int] = {}
    for week in range(1, WEEKS_IN_SEASON + 1):
        week_map[week] = week
    week_map[1] = source_week
    week_map[source_week] = 1
    relabeled = _relabel_weeks(schedule, week_map)
    _assert_featured_in_week_one(relabeled, league)
    return relabeled


def _assert_featured_in_week_one(schedule: Schedule, league: LeagueInput) -> None:
    if league.featured is None:
        return
    first, second = league.featured
    plays_week_one = any(
        game.week == WeekNumber(1) and {game.home, game.away} == {first, second}
        for game in schedule.games
    )
    if not plays_week_one:
        msg = f"featured teams {first:04d} and {second:04d} are not scheduled in week 1"
        raise FeaturedGameError(msg)


def _relabel_weeks(schedule: Schedule, week_map: dict[int, int]) -> Schedule:
    games: list[Game] = [
        dataclasses.replace(game, week=WeekNumber(week_map[game.week])) for game in schedule.games
    ]
    return Schedule(games=tuple(games))
