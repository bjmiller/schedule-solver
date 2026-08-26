"""Tests for strict input validation."""

import copy
import json
from typing import Final

import pytest

from scheduler.validation import ValidationError, parse_league_input, parse_league_input_json

VALID: Final[dict[str, object]] = {
    "divisions": [[1, 2, 3, 4, 5], [6, 7, 8, 9, 10]],
    "losers": [1, 2, 3, 4, 5],
}


def test_valid_input_parses() -> None:
    league = parse_league_input(VALID)
    assert len(league.teams) == 10
    assert len(league.divisions) == 2
    assert league.losers == frozenset({1, 2, 3, 4, 5})


@pytest.mark.parametrize(
    ("mutation", "message_fragment"),
    [
        ({"divisions": [[1, 2, 3, 4], [5, 6, 7, 8, 9]]}, "exactly 5 team ids"),
        ({"divisions": [[1, 2, 3, 4, 5, 6], [7, 8, 9, 10, 11]]}, "exactly 5 team ids"),
        ({"divisions": [[1, 2, 3, 4, 5]]}, "exactly 2 divisions"),
        ({"divisions": [[1, 2, 3, 4, 5], [6, 7, 8, 9, 10], [11]]}, "exactly 2 divisions"),
        ({"divisions": [[1, 2, 3, 4, 5], [1, 6, 7, 8, 9]]}, "more than once across divisions"),
        ({"divisions": [[1, 1, 2, 3, 4], [5, 6, 7, 8, 9]]}, "duplicated within"),
        ({"divisions": [["a", 2, 3, 4, 5], [6, 7, 8, 9, 10]]}, "must be an integer"),
        ({"divisions": [[0, 2, 3, 4, 5], [6, 7, 8, 9, 10]]}, "between 1 and 9999"),
        ({"divisions": [[10000, 2, 3, 4, 5], [6, 7, 8, 9, 10]]}, "between 1 and 9999"),
        ({"losers": [1, 2, 3, 4]}, "exactly 5 team ids"),
        ({"losers": [1, 2, 3, 4, 5, 6]}, "exactly 5 team ids"),
        ({"losers": [1, 1, 2, 3, 4]}, "duplicated in 'losers'"),
        ({"losers": [1, 2, 3, 4, 99]}, "unknown team"),
    ],
)
def test_invalid_mutations_rejected(mutation: dict[str, object], message_fragment: str) -> None:
    data: dict[str, object] = {**copy.deepcopy(VALID), **mutation}
    with pytest.raises(ValidationError, match=message_fragment):
        parse_league_input(data)


@pytest.mark.parametrize(
    ("data", "message_fragment"),
    [
        ({}, "missing required key 'divisions'"),
        ({"losers": [1, 2, 3, 4, 5]}, "missing required key 'divisions'"),
        ({"divisions": [[1, 2, 3, 4, 5], [6, 7, 8, 9, 10]]}, "missing required key 'losers'"),
        ([1, 2, 3], "must be a JSON object"),
    ],
)
def test_invalid_documents_rejected(data: object, message_fragment: str) -> None:
    with pytest.raises(ValidationError, match=message_fragment):
        parse_league_input(data)


def test_bool_is_not_an_integer() -> None:
    data = {"divisions": [[True, 2, 3, 4, 5], [6, 7, 8, 9, 10]], "losers": [1, 2, 3, 4, 5]}
    with pytest.raises(ValidationError, match="must be an integer"):
        parse_league_input(data)


PADDED: Final[dict[str, object]] = {
    "divisions": [
        ["0001", "0002", "0003", "0004", "0005"],
        ["0006", "0007", "0008", "0009", "0010"],
    ],
    "losers": ["0001", "0002", "0003", "0004", "0005"],
}


def test_padded_string_ids_parse() -> None:
    league = parse_league_input(PADDED)
    assert league.teams == frozenset(range(1, 11))
    assert league.losers == frozenset({1, 2, 3, 4, 5})


def test_mixed_int_and_padded_ids_parse() -> None:
    data = {
        "divisions": [["0001", 2, "0003", 4, "0005"], [6, "0007", 8, "0009", 10]],
        "losers": ["0005", 7, "0009", 2, 4],
    }
    league = parse_league_input(data)
    assert len(league.teams) == 10
    assert league.losers == frozenset({2, 4, 5, 7, 9})


def test_duplicate_detected_across_id_formats() -> None:
    data = {
        "divisions": [["0001", 2, 3, 4, 5], [1, "0007", 8, 9, 10]],
        "losers": [1, 2, 3, 4, 5],
    }
    with pytest.raises(ValidationError, match="more than once across divisions"):
        parse_league_input(data)


@pytest.mark.parametrize(
    ("bad_entry", "message_fragment"),
    [
        ("12a4", "integer or a 4-digit string"),
        ("12.5", "integer or a 4-digit string"),
        ("-004", "integer or a 4-digit string"),
        ("00001", "4-digit string"),
        ("", "integer or a 4-digit string"),
        (" 12", "integer or a 4-digit string"),
        ("10000", "4-digit string"),
    ],
)
def test_invalid_string_ids_rejected(bad_entry: str, message_fragment: str) -> None:
    data = {
        "divisions": [[bad_entry, 2, 3, 4, 5], [6, 7, 8, 9, 10]],
        "losers": [1, 2, 3, 4, 5],
    }
    with pytest.raises(ValidationError, match=message_fragment):
        parse_league_input(data)


def test_padded_unknown_loser_reports_padded_team() -> None:
    data = {**copy.deepcopy(PADDED), "losers": ["0001", "0002", "0003", "0004", "0099"]}
    with pytest.raises(ValidationError, match="unknown team 0099"):
        parse_league_input(data)


def test_json_string_parsing() -> None:
    league = parse_league_input_json(json.dumps(VALID))
    assert len(league.teams) == 10


def test_malformed_json_string() -> None:
    with pytest.raises(ValidationError, match="not valid JSON"):
        parse_league_input_json("{not json")


def test_unquoted_padded_id_error_includes_hint() -> None:
    raw = '{"divisions":[[0001,2,3,4,5],[6,7,8,9,10]],"losers":[1,2,3,4,5]}'
    with pytest.raises(ValidationError, match="must be quoted"):
        parse_league_input_json(raw)


def test_plain_zero_still_rejected_without_hint() -> None:
    raw = '{"divisions":[[0,2,3,4,5],[6,7,8,9,10]],"losers":[1,2,3,4,5]}'
    with pytest.raises(ValidationError, match=r"between 1 and 9999"):
        parse_league_input_json(raw)


def test_non_object_json_string() -> None:
    with pytest.raises(ValidationError, match="must be a JSON object"):
        parse_league_input_json("[1, 2]")
