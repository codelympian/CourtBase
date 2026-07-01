"""Age and age-category helpers (derived, never stored)."""

from __future__ import annotations

from datetime import date

# Junior age brackets (upper-exclusive), highest priority first.
_JUNIOR_BRACKETS = [
    (11, "U11"),
    (13, "U13"),
    (15, "U15"),
    (17, "U17"),
    (19, "U19"),
]


def calculate_age(dob: date | None, on: date | None = None) -> int | None:
    if dob is None:
        return None
    ref = on or date.today()
    return ref.year - dob.year - ((ref.month, ref.day) < (dob.month, dob.day))


def age_category(dob: date | None, on: date | None = None) -> str | None:
    """Return the junior bracket (U11..U19) or 'Senior'."""
    age = calculate_age(dob, on)
    if age is None:
        return None
    for upper, label in _JUNIOR_BRACKETS:
        if age < upper:
            return label
    return "Senior"
