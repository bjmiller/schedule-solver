"""Schedule formatting with mandatory pre-output verification."""

from scheduler.models import Game, LeagueInput, Schedule
from scheduler.verifier import verify


class VerificationError(RuntimeError):
    """Raised when a solved schedule fails verification (a solver bug)."""


def format_schedule(schedule: Schedule, league: LeagueInput) -> str:
    """Verify the schedule, then render it as `WW,AWAY,HOME` lines."""
    problems = verify(schedule, league)
    if problems:
        msg = "internal error: solver produced an invalid schedule:\n" + "\n".join(
            f"  - {problem}" for problem in problems
        )
        raise VerificationError(msg)

    lines = [_format_game(game) for game in sorted(schedule.games, key=_sort_key)]
    return "\n".join(lines)


def _sort_key(game: Game) -> tuple[int, int, int]:
    return (game.week, game.away, game.home)


def _format_game(game: Game) -> str:
    return f"{game.week:02d},{game.away:04d},{game.home:04d}"
