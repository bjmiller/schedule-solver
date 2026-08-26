# schedule-solver

Solves fixture scheduling for a two-division sports league. Given the division assignments and the list of "loser" teams, it produces a full season schedule that satisfies every league rule.

The solver uses Google OR-Tools' CP-SAT constraint solver. Before it prints anything, an independent verifier checks the finished schedule against all rules, so a broken schedule never reaches stdout.

## Rules enforced

- 13 weeks, one game per team per week, 5 games per week.
- Division rivals play each other twice: once at home, once away.
- Teams in the other division play each other once.
- Loser teams finish with 7 home and 6 away games.
- Winner teams finish with 6 home and 7 away games.

## Requirements

- [uv](https://docs.astral.sh/uv/) for dependency and environment management. No system Python is needed; uv downloads a suitable interpreter automatically.
- Python 3.14 or newer, standard (GIL-enabled) build. The free-threaded (`python3.14t`) build does not work here because ortools publishes no free-threaded wheels. Since uv 0.9, free-threaded 3.14+ interpreters on your PATH are eligible by default, so this repo pins `3.14+gil` in `.python-version` to force the standard build regardless of what is installed. If you change the pin, keep the `+gil` suffix.
- No other system dependencies.

## Input

The league is described as JSON with two keys:

```json
{
  "divisions": [[1, 2, 3, 4, 5], [6, 7, 8, 9, 10]],
  "losers": [1, 2, 3, 4, 5],
  "featured": [3, 7]
}
```

`featured` is optional: two teams that must play each other in week 1. When it is present and the schedule is shuffled (the default), the solver finds the first week where the two teams meet and swaps that entire week's slate with week 1. If they already meet in week 1, nothing changes. `--static` output ignores the featured requirement.

Both divisions must hold exactly 5 distinct teams, for 10 teams total. Team ids are integers from 1 to 9999, rendered zero-padded to four digits in output. Exactly 5 loser teams must be listed, and they must belong to the league.

Team ids may also be written as zero-padded strings, matching the output format, and both forms can be mixed:

```json
{
  "divisions": [["0001", "0002", "0003", "0004", "0005"], ["0006", "0007", "0008", "0009", "0010"]],
  "losers": ["0001", "0002", "0003", "0004", "0005"]
}
```

The quotes are required. JSON forbids numbers with leading zeros, so `[[0001, ...]]` is rejected as malformed input before validation even starts. The error message points this out.

The input is validated strictly. Bad input exits with code 2 and a message explaining what was wrong.

## Usage

Pass the JSON inline:

```sh
uv run scheduler --input-json '{"divisions":[[1,2,3,4,5],[6,7,8,9,10]],"losers":[1,2,3,4,5]}'
```

Or from a file:

```sh
uv run scheduler --input-file league.json
```

Add `-o` to also write the result to a file (stdout always prints too):

```sh
uv run scheduler --input-file league.json -o season.txt
```

By default the solver's raw schedule gets its weeks randomly shuffled before output. Shuffling is safe here: every league rule is either week-independent (matchups, home/away counts) or re-applied after shuffling (the featured week-1 game), and the full verifier still runs on whatever is about to be printed. Pass `--static` to skip the shuffle and emit the solver's schedule exactly as solved, which is useful for verifying the raw solver output.

```sh
uv run scheduler --input-file league.json --static
```

Output is one line per game, sorted by week:

```
01,0006,0002
```

Each line is `week,away team,home team`. Weeks are zero-padded to two digits.

Exit codes: 0 on success, 2 for invalid input, 3 if no feasible schedule exists, 4 if the solved schedule failed verification. Code 4 should never happen; it means there is a bug in the solver, and the verifier's findings are printed to stderr.

## Tests

```sh
uv run pytest
```

The suite covers strict validation of every invalid-input class, rule-by-rule verifier checks (each rule violated in isolation must be detected), solves for several division and loser configurations, and runs the CLI end to end via subprocess. A full run takes a few seconds.

## Static checks

```sh
uv run ruff check .
uv run ruff format --check .
uv run ty check .
```

The codebase avoids `Any` entirely and typechecks cleanly under `ty`.
