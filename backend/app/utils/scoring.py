"""Badminton scoring rules (BWF rally-point scoring to 21, cap at 30)."""

from __future__ import annotations


def validate_game(a: int, b: int) -> None:
    """Raise ``ValueError`` if ``(a, b)`` is not a valid completed game score."""
    if a < 0 or b < 0:
        raise ValueError("Scores cannot be negative")
    winner, loser = max(a, b), min(a, b)
    if winner == loser:
        raise ValueError(f"A game cannot end in a tie ({a}-{b})")
    valid = (
        (winner == 21 and loser <= 19)
        or (22 <= winner <= 29 and loser == winner - 2)
        or (winner == 30 and loser == 29)
    )
    if not valid:
        raise ValueError(f"'{a}-{b}' is not a valid badminton game score")


def game_winner(a: int, b: int) -> int:
    """Return 1 if player1 won the game, else 2. Assumes an already-valid score."""
    return 1 if a > b else 2


def match_winner(games: list[list[int]]) -> int:
    """Determine the match winner (1 or 2) from a best-of-3 game score list.

    Validates every game, that games stop as soon as one side reaches 2 wins,
    and that at least 2 (and at most 3) games are present.
    """
    if not (2 <= len(games) <= 3):
        raise ValueError("A match requires 2 or 3 completed games")

    wins = {1: 0, 2: 0}
    for i, game in enumerate(games):
        if len(game) != 2:
            raise ValueError("Each game must be `[player1_points, player2_points]`")
        a, b = game
        validate_game(a, b)
        wins[game_winner(a, b)] += 1
        if wins[1] == 2 or wins[2] == 2:
            if i != len(games) - 1:
                raise ValueError("Extra games were submitted after the match was already decided")

    if wins[1] != 2 and wins[2] != 2:
        raise ValueError("The submitted games do not produce a match winner (best of 3)")
    return 1 if wins[1] == 2 else 2
