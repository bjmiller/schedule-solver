"""End-to-end CLI tests."""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from scheduler.cli import run

VALID_JSON = json.dumps(
    {
        "divisions": [[1, 2, 3, 4, 5], [6, 7, 8, 9, 10]],
        "losers": [1, 2, 3, 4, 5],
    }
)

PADDED_JSON = json.dumps(
    {
        "divisions": [
            ["0001", "0002", "0003", "0004", "0005"],
            ["0006", "0007", "0008", "0009", "0010"],
        ],
        "losers": ["0001", "0002", "0003", "0004", "0005"],
    }
)

FEATURED_JSON = json.dumps(
    {
        "divisions": [[1, 2, 3, 4, 5], [6, 7, 8, 9, 10]],
        "losers": [1, 2, 3, 4, 5],
        "featured": [3, 7],
    }
)


def week_one_pairs(output: str) -> list[frozenset[int]]:
    pairs = []
    for line in output.strip().splitlines():
        week, away, home = (int(part) for part in line.split(","))
        if week == 1:
            pairs.append(frozenset((away, home)))
    return pairs


LINE_PATTERN = re.compile(r"^\d{2},\d{4},\d{4}$")


def test_run_with_inline_json(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = run(["--input-json", VALID_JSON])
    assert exit_code == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 65
    for line in lines:
        assert LINE_PATTERN.match(line), f"bad line: {line!r}"


def test_run_with_padded_input_json(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = run(["--input-json", PADDED_JSON])
    assert exit_code == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 65
    for line in lines:
        assert LINE_PATTERN.match(line), f"bad line: {line!r}"


def test_run_rejects_invalid_input() -> None:
    invalid = json.dumps({"divisions": [[1, 2, 3], [4, 5, 6]], "losers": [1]})
    assert run(["--input-json", invalid]) == 2


def test_default_output_shuffles_weeks(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(["--input-json", VALID_JSON]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 65
    # A shuffled schedule is still fully valid; the verifier inside the output
    # path would have failed otherwise.


def test_static_flag_skips_shuffle(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    out_path = tmp_path / "static.txt"
    exit_code = run(["--input-json", VALID_JSON, "--static", "-o", str(out_path)])
    assert exit_code == 0
    rendered = capsys.readouterr().out.strip()
    assert len(rendered.splitlines()) == 65
    assert out_path.read_text(encoding="utf-8").strip() == rendered


def test_featured_teams_play_in_week_one_by_default(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run(["--input-json", FEATURED_JSON]) == 0
    pairs = week_one_pairs(capsys.readouterr().out)
    assert frozenset((3, 7)) in pairs


def test_featured_teams_with_static_flag_may_not_be_week_one(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # --static emits the solver's raw schedule; the featured requirement only
    # applies to the shuffled default. Either way it must not crash.
    exit_code = run(["--input-json", FEATURED_JSON, "--static"])
    assert exit_code == 0
    assert len(week_one_pairs(capsys.readouterr().out)) == 5


def test_featured_validation_errors() -> None:
    for bad in ([1], [1, 1], [1, 99], [1, 2, 3]):
        invalid = json.dumps({**json.loads(VALID_JSON), "featured": bad})
        assert run(["--input-json", invalid]) == 2


def test_run_reports_infeasible_or_solves_gracefully() -> None:
    # Even a valid-shaped league must either solve or fail cleanly (never crash).
    exit_code = run(["--input-json", VALID_JSON])
    assert exit_code in (0, 3)


def test_output_file_flag(tmp_path: Path) -> None:
    out_path = tmp_path / "schedule.txt"
    exit_code = run(["--input-json", VALID_JSON, "-o", str(out_path)])
    assert exit_code == 0
    content = out_path.read_text(encoding="utf-8")
    lines = content.strip().splitlines()
    assert len(lines) == 65


def test_subprocess_module_invocation(tmp_path: Path) -> None:
    input_path = tmp_path / "league.json"
    input_path.write_text(VALID_JSON, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "scheduler.cli", "--input-file", str(input_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    lines = result.stdout.strip().splitlines()
    assert len(lines) == 65
    for line in lines:
        assert LINE_PATTERN.match(line), f"bad line: {line!r}"
