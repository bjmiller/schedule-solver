"""CP-SAT based schedule solver."""

from ortools.sat.python import cp_model

from scheduler.models import (
    GAMES_PER_WEEK,
    WEEKS_IN_SEASON,
    Game,
    LeagueInput,
    Schedule,
    TeamId,
    WeekNumber,
)

MAX_SOLVE_TIME_SECONDS = 300.0


class SolverError(RuntimeError):
    """Raised when no feasible schedule could be found."""


def solve(league: LeagueInput) -> Schedule:
    """Build and solve the CP-SAT model, returning a verified-feasible Schedule."""
    model = cp_model.CpModel()
    teams = sorted(league.teams)
    weeks = range(WEEKS_IN_SEASON)

    # x[(home, away, w)] is true iff `home` hosts `away` in week w (0-based).
    x: dict[tuple[TeamId, TeamId, int], cp_model.IntVar] = {}
    for home in teams:
        for away in teams:
            if home == away:
                continue
            for week in weeks:
                x[(home, away, week)] = model.new_bool_var(
                    f"x_h{home:04d}_a{away:04d}_w{week + 1:02d}"
                )

    _add_weekly_constraints(model, x, league, teams, weeks)
    _add_pair_constraints(model, x, league)
    _add_home_count_constraints(model, x, league, teams, weeks)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = MAX_SOLVE_TIME_SECONDS
    status = solver.solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        status_name = solver.status_name(status)
        msg = f"no feasible schedule exists (solver status: {status_name})"
        raise SolverError(msg)

    return _extract_schedule(solver, x)


def _add_weekly_constraints(
    model: cp_model.CpModel,
    x: dict[tuple[TeamId, TeamId, int], cp_model.IntVar],
    league: LeagueInput,
    teams: list[TeamId],
    weeks: range,
) -> None:
    """Each team plays exactly one game per week; exactly GAMES_PER_WEEK per week."""
    del league  # kept for signature symmetry; weekly rules are league-independent
    for team in teams:
        for week in weeks:
            plays = [x[(team, other, week)] for other in teams if other != team] + [
                x[(other, team, week)] for other in teams if other != team
            ]
            model.add_exactly_one(plays)
    for week in weeks:
        games_in_week = [x[(home, away, week)] for home in teams for away in teams if home != away]
        model.add(sum(games_in_week) == GAMES_PER_WEEK)


def _add_pair_constraints(
    model: cp_model.CpModel,
    x: dict[tuple[TeamId, TeamId, int], cp_model.IntVar],
    league: LeagueInput,
) -> None:
    """Division rivals meet twice (once each way); others meet once."""
    weeks = range(WEEKS_IN_SEASON)
    for first, second in league.opponent_pairs():
        pair_games = [x[(first, second, week)] + x[(second, first, week)] for week in weeks]
        if league.are_division_rivals(first, second):
            first_hosts = [x[(first, second, week)] for week in weeks]
            second_hosts = [x[(second, first, week)] for week in weeks]
            model.add(sum(pair_games) == 2)
            model.add(sum(first_hosts) == 1)
            model.add(sum(second_hosts) == 1)
        else:
            model.add(sum(pair_games) == 1)


def _add_home_count_constraints(
    model: cp_model.CpModel,
    x: dict[tuple[TeamId, TeamId, int], cp_model.IntVar],
    league: LeagueInput,
    teams: list[TeamId],
    weeks: range,
) -> None:
    """Loser teams host 7 / visit 6; winner teams host 6 / visit 7."""
    for team in teams:
        team_class = league.team_class(team)
        home_games = [x[(team, other, week)] for other in teams if other != team for week in weeks]
        away_games = [x[(other, team, week)] for other in teams if other != team for week in weeks]
        model.add(sum(home_games) == team_class.required_home_games)
        model.add(sum(away_games) == team_class.required_away_games)


def _extract_schedule(
    solver: cp_model.CpSolver,
    x: dict[tuple[TeamId, TeamId, int], cp_model.IntVar],
) -> Schedule:
    games: list[Game] = []
    for (home, away, week), variable in sorted(x.items()):
        if solver.value(variable):
            games.append(Game(week=WeekNumber(week + 1), away=away, home=home))
    return Schedule(games=tuple(games))
