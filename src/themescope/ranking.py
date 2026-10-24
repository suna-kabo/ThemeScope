"""Shared deterministic average-rank calculation for current and prior runs."""

from __future__ import annotations

from collections.abc import Mapping
from math import isfinite
from typing import Any


def average_ranks(scores: Mapping[str, Any]) -> dict[str, float | None]:
    """Return descending average ranks; missing scores do not change valid ranks."""
    ranked = sorted(
        ((key, score) for key, score in scores.items()
        if isinstance(score, (int, float)) and not isinstance(score, bool) and isfinite(float(score))),
        key=lambda item: (-float(item[1]), str(item[0])),
    )
    result: dict[str, float | None] = {key: None for key in scores}
    start = 0
    while start < len(ranked):
        end = start + 1
        while end < len(ranked) and ranked[end][1] == ranked[start][1]:
            end += 1
        average = (start + 1 + end) / 2
        for key, _ in ranked[start:end]:
            result[key] = average
        start = end
    return result
