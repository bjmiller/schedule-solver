"""Independent verification of a Schedule against all league rules.

This module deliberately shares no logic with the solver so that a solver bug
cannot mask itself.
"""

from collections import defaultdict

from scheduler.models import (
    GAMES_PER_WEEK,
    WEEKS_IN_SEASON,
    Game,
    LeagueInput,
    Schedule,
    TeamId,
)


def verify(schedule: Schedule, league: LeagueInput) -> list[str]:
    """Return a list of human-readable constraint violations; empty means valid."""
    errors: list[str] = []
    errors.extend(_check_shape(schedule))
    errors.extend(_check_weekly_uniqueness(schedule, league))
    errors.extend(_check_matchups(schedule, league))
    errors.extend(_check_home_away_totals(schedule, league))
    return sorted(errors)


def _check_shape(schedule: Schedule) -> list[str]:
    errors: list[str] = []
    weeks = {game.week for game in schedule.games}
    expected_weeks = set(range(1, WEEKS_IN_SEASON + 1))
    if weeks != expected_weeks:
        missing = expected_weeks - weeks
        extra = weeks - expected_weeks
        errors.append(
            f"weeks must be exactly 1..{WEEKS_IN_SEASON}; "
            f"missing={sorted(missing)} extra={sorted(extra)}"
        )

    by_week: dict[int, int] = defaultdict(int)
    for game in schedule.games:
        by_week[game.week] += 1
    for week in sorted(expected_weeks):
        count = by_week.get(week, 0)
        if count != GAMES_PER_WEEK:
            errors.append(f"week {week:02d} has {count} games, expected {GAMES_PER_WEEK}")
    return errors


def _check_weekly_uniqueness(schedule: Schedule, league: LeagueInput) -> list[str]:
    errors: list[str] = []
    played: dict[tuple[TeamId, int], list[TeamId]] = defaultdict(list)
    for game in schedule.games:
        if game.home == game.away:
            errors.append(f"week {game.week:02d}: team plays itself ({game.home:04d})")
            continue
        if game.home not in league.teams or game.away not in league.teams:
            errors.append(
                f"week {game.week:02d}: unknown team in game {game.away:04d}@{game.home:04d}"
            )
            continue
        played[(game.away, game.week)].append(game.home)
        played[(game.home, game.week)].append(game.away)

    for (team, week), opponents in sorted(played.items()):
        if len(opponents) != 1:
            errors.append(
                f"week {week:02d}: team {team:04d} plays {len(opponents)} games, expected exactly 1"
            )
    return errors


def _check_matchups(schedule: Schedule, league: LeagueInput) -> list[str]:
    errors: list[str] = []
    meetings: dict[frozenset[TeamId], list[Game]] = defaultdict(list)
    for game in schedule.games:
        meetings[frozenset((game.home, game.away))].append(game)

    for first, second in league.opponent_pairs():
        pair = frozenset((first, second))
        games = meetings.get(pair, [])
        rivals = league.are_division_rivals(first, second)
        expected_meetings = 2 if rivals else 1
        if len(games) != expected_meetings:
            errors.append(
                f"teams {first:04d} and {second:04d} meet {len(games)} times, "
                f"expected {expected_meetings}"
            )
            continue
        if rivals:
            homes = {game.home for game in games}
            if homes != {first, second}:
                errors.append(
                    f"division rivals {first:04d} and {second:04d} do not host exactly once each"
                )
    return errors


def _check_home_away_totals(schedule: Schedule, league: LeagueInput) -> list[str]:
    errors: list[str] = []
    home_counts: dict[TeamId, int] = defaultdict(int)
    away_counts: dict[TeamId, int] = defaultdict(int)
    for game in schedule.games:
        home_counts[game.home] += 1
        away_counts[game.away] += 1

    for team in sorted(league.teams):
        team_class = league.team_class(team)
        home_count = home_counts.get(team, 0)
        away_count = away_counts.get(team, 0)
        if home_count != team_class.required_home_games:
            errors.append(
                f"team {team:04d} ({team_class.value}) has {home_count} home games, "
                f"expected {team_class.required_home_games}"
            )
        if away_count != team_class.required_away_games:
            errors.append(
                f"team {team:04d} ({team_class.value}) has {away_count} away games, "
                f"expected {team_class.required_away_games}"
            )
    return errors
