"""Unit tests for badminton scoring rules (app.utils.scoring)."""

from __future__ import annotations

import pytest

from app.utils.scoring import match_winner, validate_game


@pytest.mark.parametrize(
    "a,b",
    [(21, 0), (21, 19), (22, 20), (29, 27), (30, 29)],
)
def test_validate_game_accepts_valid_scores(a, b):
    validate_game(a, b)  # should not raise
    validate_game(b, a)


@pytest.mark.parametrize(
    "a,b",
    [(21, 20), (21, 21), (20, 18), (30, 28), (31, 29), (22, 19), (-1, 21)],
)
def test_validate_game_rejects_invalid_scores(a, b):
    with pytest.raises(ValueError):
        validate_game(a, b)


def test_match_winner_straight_games():
    assert match_winner([[21, 15], [21, 18]]) == 1
    assert match_winner([[15, 21], [10, 21]]) == 2


def test_match_winner_deciding_game():
    assert match_winner([[21, 15], [18, 21], [21, 19]]) == 1
    assert match_winner([[15, 21], [21, 10], [19, 21]]) == 2


def test_match_winner_rejects_incomplete_or_extra_games():
    with pytest.raises(ValueError):
        match_winner([[21, 15]])  # only 1 game, no winner yet
    with pytest.raises(ValueError):
        match_winner([[21, 15], [21, 18], [21, 10]])  # 3rd game unnecessary
    with pytest.raises(ValueError):
        match_winner([[21, 15], [19, 21]])  # 1-1, no decider
