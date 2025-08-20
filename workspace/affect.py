"""Affect signals: curiosity, novelty, mastery (bounded 0..1)."""
from __future__ import annotations

def _bounded(x: float) -> float:
    return max(0.0, min(1.0, x))


def curiosity(observed_uncertainty: float, opportunity: float = 0.5) -> float:
    # higher when uncertainty or opportunity is high
    return _bounded(0.6 * observed_uncertainty + 0.4 * opportunity)


def novelty(new_items_ratio: float) -> float:
    # fraction of new items seen recently
    return _bounded(new_items_ratio)


def mastery(success_rate: float) -> float:
    # how well tasks are accomplished recently
    return _bounded(success_rate)
