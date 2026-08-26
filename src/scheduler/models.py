"""Domain models for the sports league schedule solver."""

from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
from typing import NewType

TeamId = NewType("TeamId", int)
WeekNumber = NewType("WeekNumber", int)


TOTAL_TEAMS = 10
DIVISION_COUNT = 2
DIVISION_SIZE = 5
LOSER_COUNT = 5
WEEKS_IN_SEASON = 13
GAMES_PER_WEEK = TOTAL_TEAMS // 2


class TeamClass(Enum):
    """A team is either a designated 'loser' team or a 'winner' team."""

    LOSER = "loser"
    WINNER = "winner"

    @property
    def required_home_games(self) -> int:
        return 7 if self is TeamClass.LOSER else 6

    @property
    def required_away_games(self) -> int:
        return 6 if self is TeamClass.LOSER else 7


@dataclass(frozen=True, slots=True)
class Game:
    """A single game: the away team visits the home team in a given week."""

    week: WeekNumber
    away: TeamId
    home: TeamId


@dataclass(frozen=True, slots=True)
class LeagueInput:
    """Validated league structure: two divisions plus the set of loser teams."""

    divisions: tuple[frozenset[TeamId], frozenset[TeamId]]
    losers: frozenset[TeamId]
    featured: tuple[TeamId, TeamId] | None = None

    @property
    def teams(self) -> frozenset[TeamId]:
        return self.divisions[0] | self.divisions[1]

    @property
    def winners(self) -> frozenset[TeamId]:
        return self.teams - self.losers

    def team_class(self, team: TeamId) -> TeamClass:
        if team not in self.teams:
            msg = f"unknown team {team}"
            raise KeyError(msg)
        return TeamClass.LOSER if team in self.losers else TeamClass.WINNER

    def division_index(self, team: TeamId) -> int:
        for index, division in enumerate(self.divisions):
            if team in division:
                return index
        msg = f"unknown team {team}"
        raise KeyError(msg)

    def are_division_rivals(self, first: TeamId, second: TeamId) -> bool:
        return self.division_index(first) == self.division_index(second)

    def opponent_pairs(self) -> Iterator[tuple[TeamId, TeamId]]:
        """All unordered pairs of distinct teams."""
        ordered = sorted(self.teams)
        for index, first in enumerate(ordered):
            for second in ordered[index + 1 :]:
                yield (first, second)


@dataclass(frozen=True, slots=True)
class Schedule:
    """A complete solved schedule."""

    games: tuple[Game, ...]
