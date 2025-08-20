"""Self-model with basic state and decision helpers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Goal:
    name: str
    priority: int = 0


@dataclass
class SelfModel:
    energy: float = 1.0
    confidence: float = 0.5
    goals: List[Goal] = None

    def __post_init__(self) -> None:
        if self.goals is None:
            self.goals = []

    def adjust(self, d_energy: float = 0.0, d_conf: float = 0.0) -> None:
        self.energy = max(0.0, min(1.0, self.energy + d_energy))
        self.confidence = max(0.0, min(1.0, self.confidence + d_conf))

    def add_goal(self, name: str, priority: int = 0) -> None:
        self.goals.append(Goal(name=name, priority=priority))
        self.goals.sort(key=lambda g: g.priority, reverse=True)

    def suggest_focus(self, curiosity_score: float, novelty_score: float) -> str:
        """Suggest focus area: 'research' vs 'memory' vs 'commands'.

        Heuristic based on energy/confidence and affect inputs.
        """
        if self.energy < 0.3:
            return "memory"  # lighter tasks
        if curiosity_score > 0.6 or novelty_score > 0.6:
            return "research"
        if self.confidence < 0.4:
            return "memory"
        return "commands"
