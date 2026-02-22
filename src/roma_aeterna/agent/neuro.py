"""
Neuro-Cognitive Model — Leaky Integrate-and-Fire neuron model
that governs when an agent decides to "think" (trigger LLM inference).

Enhanced with potential_history for live monitoring.
"""

from collections import deque
from dataclasses import dataclass
from typing import Optional

@dataclass
class LIFParameters:
    """Tunable parameters for the LIF decision neuron."""
    decay_rate: float = 0.1
    threshold: float = 100.0
    resting_potential: float = 0.0
    refractory_period: float = 5.0


class LeakyIntegrateAndFire:
    """Simulates urgency accumulation. Fires when threshold is reached."""

    def __init__(self, params: Optional["LIFParameters"] = None) -> None:
        self.params = params or LIFParameters()
        self.potential: float = self.params.resting_potential
        self.last_spike_time: float = -999.0
        self.is_refractory: bool = False

        # --- History for LIF monitor ---
        self.potential_history: deque = deque(maxlen=120)  # Last 120 samples
        self.fire_history: deque = deque(maxlen=120)       # True/False per sample
        self.input_history: deque = deque(maxlen=120)      # Urgency input per sample

    def update(self, dt: float, input_current: float, current_time: float) -> bool:
        """Integrate input current, apply leak, check threshold.

        Returns True if the neuron fired (agent should act).
        """
        # Refractory period — mental cooldown after acting
        if current_time - self.last_spike_time < self.params.refractory_period:
            self.potential = self.params.resting_potential
            self.is_refractory = True
            self._record(input_current, False)
            return False
        self.is_refractory = False

        # Leaky integration: dV/dt = -V*decay + I
        leak = self.params.decay_rate * self.potential
        delta_v = (input_current - leak) * dt
        self.potential = max(0.0, self.potential + delta_v)

        # Threshold check
        if self.potential >= self.params.threshold:
            self._fire(current_time)
            self._record(input_current, True)
            return True

        self._record(input_current, False)
        return False

    def _record(self, input_current: float, fired: bool) -> None:
        """Record a sample for the LIF monitor."""
        self.potential_history.append(self.potential)
        self.fire_history.append(fired)
        self.input_history.append(input_current)

    def _fire(self, time: float) -> None:
        """Reset potential after firing."""
        self.potential = self.params.resting_potential
        self.last_spike_time = time

    def force_fire(self, time: float) -> None:
        """Externally force a spike (e.g., for critical events)."""
        self._fire(time)