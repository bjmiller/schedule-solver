"""Command-line entry point for the schedule solver."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from scheduler.models import LeagueInput, Schedule
from scheduler.output import VerificationError, format_schedule
from scheduler.shuffle import FeaturedGameError, move_featured_to_week_one, shuffle_weeks
from scheduler.solver import SolverError
from scheduler.solver import solve as solve_schedule
from scheduler.validation import ValidationError, parse_league_input_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scheduler",
        description="Solve a sports league schedule and print it as WW,AWAY,HOME lines.",
    )
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--input-json",
        help="league definition as an inline JSON document",
    )
    input_group.add_argument(
        "--input-file",
        type=Path,
        help="path to a JSON file containing the league definition",
    )
    parser.add_argument(
        "--static",
        action="store_true",
        help="skip week shuffling and emit the solver's schedule as-is",
    )
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=None,
        help="optional path to also write the schedule to",
    )
    return parser


def load_league(args: argparse.Namespace) -> LeagueInput:
    if args.input_json is not None:
        return parse_league_input_json(args.input_json)
    raw = args.input_file.read_text(encoding="utf-8")
    return parse_league_input_json(raw)


def run(argv: Sequence[str] | None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        league = load_league(args)
    except ValidationError as exc:
        print(f"error: invalid input: {exc}", file=sys.stderr)
        return 2

    try:
        schedule: Schedule = solve_schedule(league)
        if not args.static:
            schedule = move_featured_to_week_one(shuffle_weeks(schedule, league), league)
        rendered = format_schedule(schedule, league)
    except SolverError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3
    except (VerificationError, FeaturedGameError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 4

    if args.out is not None:
        args.out.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


def main() -> None:
    sys.exit(run(None))


if __name__ == "__main__":
    main()
