from __future__ import annotations

from workspace.bus import Bus
from workspace.self_model import SelfModel
from workspace import affect


def test_bus_broadcast_priority_order() -> None:
    bus = Bus()
    received: list[int] = []

    def sub(x):
        received.append(x)

    bus.subscribe(sub)
    # higher priority number means lower priority in PriorityQueue (0 first)
    bus.publish(5, 5)
    bus.publish(1, 1)
    bus.publish(3, 3)
    count = bus.broadcast()
    assert count == 3
    assert received == [1, 3, 5]


def test_self_model_focus_with_affect() -> None:
    sm = SelfModel(energy=1.0, confidence=0.5)
    c = affect.curiosity(observed_uncertainty=0.9)
    n = affect.novelty(0.8)
    focus = sm.suggest_focus(c, n)
    assert focus == "research"

    sm.adjust(d_energy=-0.8)
    focus2 = sm.suggest_focus(curiosity_score=0.1, novelty_score=0.1)
    assert focus2 == "memory"

    sm2 = SelfModel(energy=0.9, confidence=0.9)
    f3 = sm2.suggest_focus(curiosity_score=0.1, novelty_score=0.1)
    assert f3 == "commands"
