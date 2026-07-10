"""Mapping a knockout finish to a ranking result key.

Result keys are the strings a federation configures points against, e.g.
``winner``, ``runner_up``, ``semi_final``. They are derived from how far a
player advanced in an event's bracket.
"""

from __future__ import annotations

# Canonical result keys, best finish first. Federations configure points per key.
RESULT_KEYS: list[str] = [
    "winner",
    "runner_up",
    "semi_final",
    "quarter_final",
    "round_16",
    "round_32",
    "round_64",
    "round_128",
]

# A loss in a round that had N matches maps to this result key.
_LOSS_KEY_BY_ROUND_MATCHES: dict[int, str] = {
    1: "runner_up",
    2: "semi_final",
    4: "quarter_final",
    8: "round_16",
    16: "round_32",
    32: "round_64",
    64: "round_128",
}


def loss_result_key(matches_in_round: int) -> str:
    """Result key for a player eliminated in a round that had ``matches_in_round`` matches."""
    return _LOSS_KEY_BY_ROUND_MATCHES.get(matches_in_round, f"round_{matches_in_round * 2}")


def compute_event_results(matches: list) -> dict:
    """Map ``player_id -> result_key`` for every player in a completed event.

    ``matches`` is the full bracket (all rounds). Each player's finish is the
    furthest round they appear in: winning the final ⇒ ``winner``; otherwise the
    loss key for the round in which they were eliminated. Byes/walkovers are
    handled naturally since we only look at the furthest appearance.
    """
    counts_by_round: dict[int, int] = {}
    for m in matches:
        counts_by_round[m.round] = counts_by_round.get(m.round, 0) + 1

    furthest: dict = {}  # player_id -> match (their furthest appearance)
    for m in matches:
        for pid in (m.player1_id, m.player2_id):
            if pid is None:
                continue
            if pid not in furthest or m.round > furthest[pid].round:
                furthest[pid] = m

    results: dict = {}
    for pid, m in furthest.items():
        if m.winner_id == pid and m.next_match_id is None:
            results[pid] = "winner"
        else:
            results[pid] = loss_result_key(counts_by_round[m.round])
    return results
