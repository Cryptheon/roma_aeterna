"""
Autopilot — Finite State Automaton for routine agent decisions.

This is the "System 1" fast brain. It handles predictable, well-defined
situations without needing an LLM call:
  - SURVIVAL: Flee fire, drink when parched, eat when starving
  - NAVIGATION: Follow a multi-step path to a known destination
  - ROUTINE: Rest when exhausted, seek shelter at night
  - SOCIAL: Basic greetings when lonely and someone is nearby

Returns a decision dict (same format as LLM output) or None if the
situation is too complex/novel and needs the LLM's "System 2" reasoning.

The LLM can always override the autopilot by setting agent.autopilot_override.
The autopilot also steps aside when:
  - The agent encounters something it hasn't seen before
  - There's a conversation to respond to
  - Multiple conflicting needs are at similar urgency
  - The agent has been on autopilot too long (novelty-seeking)
"""

import math
import random
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from roma_aeterna.config import (
    MAX_AUTOPILOT_TICKS,
    CRITICAL_THIRST_THRESHOLD, CRITICAL_HUNGER_THRESHOLD,
    CRITICAL_ENERGY_THRESHOLD, ROUTINE_ENERGY_THRESHOLD,
    ROUTINE_SOCIAL_THRESHOLD, HEALTH_CRITICAL_THRESHOLD,
    NEARBY_AGENT_RADIUS, LEGIONARY_GROUP_RADIUS,
    ATTACK_PROXIMITY_RADIUS,
)
from .pathfinding import Pathfinder


class AutopilotState(Enum):
    """Current autopilot behavior mode."""
    IDLE = "idle"
    NAVIGATING = "navigating"       # Following a path
    FLEEING = "fleeing"             # Running from danger
    SEEKING_RESOURCE = "seeking"    # Going to a known resource
    WORKING = "working"            # Performing role duties
    SOCIALIZING = "socializing"    # In a conversation
    RESTING = "resting"            # Recovering energy


class Autopilot:
    """Fast decision-maker for routine agent behavior."""

    def __init__(self) -> None:
        self.state: AutopilotState = AutopilotState.IDLE
        self.path: List[Tuple[int, int]] = []       # Multi-step navigation
        self.destination_name: Optional[str] = None  # Where we're going
        self.ticks_on_autopilot: int = 0
        self.override: bool = False                  # LLM requested manual control
        self._consecutive_path_blocks: int = 0       # Consecutive blocked MOVE steps

    def set_path(self, path: List[Tuple[int, int]], destination: str = "") -> None:
        """Set a multi-step path for the agent to follow."""
        self.path = list(path)
        self.destination_name = destination
        self.state = AutopilotState.NAVIGATING
        self._consecutive_path_blocks = 0

    def clear_path(self) -> None:
        """Cancel current navigation."""
        self.path = []
        self.destination_name = None
        if self.state == AutopilotState.NAVIGATING:
            self.state = AutopilotState.IDLE

    def request_override(self) -> None:
        """LLM requests control — autopilot steps aside next tick."""
        self.override = True

    def decide(self, agent: Any, agents: List[Any],
               world: Any) -> Optional[Dict]:
        """Try to make a routine decision.

        Returns a decision dict or None if the LLM should handle this.
        """
        # --- Override check ---
        if self.override:
            self.override = False
            self.ticks_on_autopilot = 0
            return None

        # --- Novelty timeout: force LLM thinking periodically ---
        self.ticks_on_autopilot += 1
        if self.ticks_on_autopilot >= MAX_AUTOPILOT_TICKS:
            self.ticks_on_autopilot = 0
            return None  # Let the LLM re-evaluate

        # --- Priority 1: SURVIVAL (always handled by autopilot) ---
        survival = self._check_survival(agent, world, agents)
        if survival:
            return survival

        # --- Priority 2: Follow existing path ---
        if self.path:
            nav = self._follow_path(agent, world)
            if nav:
                return nav

        # --- Priority 3: Critical needs ---
        need = self._check_critical_needs(agent, agents, world)
        if need:
            return need

        # If a critical biological need exists but the autopilot couldn't
        # resolve it (no item in inventory, no known route), defer to the
        # LLM rather than falling through to routine behaviour like REST.
        if agent.drives["thirst"] > CRITICAL_THIRST_THRESHOLD or agent.drives["hunger"] > CRITICAL_HUNGER_THRESHOLD:
            self.ticks_on_autopilot = 0
            return None

        # --- Priority 4: Simple routine behavior ---
        routine = self._check_routine(agent, agents, world)
        if routine:
            return routine

        # --- No routine decision possible: defer to LLM ---
        self.ticks_on_autopilot = 0
        return None

    # ================================================================
    # SURVIVAL — Hardcoded reflexes
    # ================================================================

    def _check_survival(self, agent: Any, world: Any, agents: List[Any] = None) -> Optional[Dict]:
        """Immediate survival reflexes. Always override everything."""

        # Legionaries engage attacking wolves on sight
        if "Legionary" in agent.role and agents is not None:
            attack = self._check_legionary_combat(agent, agents)
            if attack:
                return attack

        # Flee fire/smoke
        if (agent.status_effects.has_effect("Burned") or
                agent.status_effects.has_effect("Smoke Inhalation")):
            self.clear_path()
            self.state = AutopilotState.FLEEING
            direction = self._find_safe_direction(agent, world)
            return {
                "thought": "Fire! I must get away!",
                "action": "MOVE",
                "direction": direction,
                "_autopilot": True,
            }

        # Health critical + have medicine
        if agent.health < HEALTH_CRITICAL_THRESHOLD:
            for item in agent.inventory:
                if getattr(item, "item_type", None) == "medicine":
                    return {
                        "thought": "I'm dying... must use this medicine.",
                        "action": "CONSUME",
                        "target": item.name,
                        "_autopilot": True,
                    }

        return None

    def _find_safe_direction(self, agent: Any, world: Any) -> str:
        """Find direction away from danger (fire, smoke)."""
        return Pathfinder.find_safe_direction(agent, world)

    # ================================================================
    # NAVIGATION — Multi-step path following
    # ================================================================

    def _follow_path(self, agent: Any, world: Any) -> Optional[Dict]:
        """Follow the current path one step at a time."""
        if not self.path:
            return None

        if agent.movement_cooldown > 0:
            return {
                "thought": f"Walking toward {self.destination_name or 'my destination'}...",
                "action": "IDLE",
                "_autopilot": True,
            }

        target = self.path[0]
        tx, ty = target

        # Check if we've arrived at this waypoint
        if int(agent.x) == tx and int(agent.y) == ty:
            self.path.pop(0)
            if not self.path:
                dest = self.destination_name or "destination"
                self.state = AutopilotState.IDLE
                self.ticks_on_autopilot = 0
                # Give the LLM context about where we ended up
                agent.memory.add_event(
                    f"You have arrived near {dest}.",
                    tick=int(agent.current_time), importance=1.5,
                    memory_type="event",
                )
                return None  # Arrived — let LLM decide what to do here
            target = self.path[0]
            tx, ty = target

        # Compute direction to next waypoint
        direction = self._direction_to(agent.x, agent.y, tx, ty)

        # Check if path is still valid (world may have changed since path was set)
        tile = world.get_tile(tx, ty)
        if not tile or not tile.is_walkable:
            dest = self.destination_name or "destination"
            self.clear_path()
            agent.memory.add_event(
                f"The path to {dest} is blocked. Need to find another route.",
                tick=int(agent.current_time), importance=1.5,
                memory_type="event", tags=["blocked"],
            )
            return None  # Path blocked — LLM re-evaluates

        return {
            "thought": f"Heading to {self.destination_name or 'my destination'}.",
            "action": "MOVE",
            "direction": direction,
            "_autopilot": True,
        }

    # ================================================================
    # CRITICAL NEEDS — Consume from inventory
    # ================================================================

    def _check_critical_needs(self, agent: Any, agents: List[Any],
                              world: Any) -> Optional[Dict]:
        """Handle critical biological needs with inventory items."""

        # Desperate thirst: drink from inventory
        if agent.drives["thirst"] > CRITICAL_THIRST_THRESHOLD:
            for item in agent.inventory:
                if getattr(item, "item_type", None) == "drink":
                    return {
                        "thought": f"So thirsty... I'll drink my {item.name}.",
                        "action": "CONSUME",
                        "target": item.name,
                        "_autopilot": True,
                    }
            # No drink in inventory — navigate to nearest known water source.
            # Use partial matching (get_location_for_need) so any fountain name works.
            if not self.path:
                loc = agent.memory.get_location_for_need("thirst")
                if loc:
                    name, pos = loc
                    self._set_path_toward(agent, pos, name, world)
                    if self.path:
                        return self._follow_path(agent, world)

        # Desperate hunger: eat from inventory
        if agent.drives["hunger"] > CRITICAL_HUNGER_THRESHOLD:
            for item in agent.inventory:
                if getattr(item, "item_type", None) == "food":
                    spoiled = getattr(item, "is_spoiled", lambda: False)
                    # Check preference — avoid foods they've had bad experiences with
                    pref = agent.memory.preferences.get(item.name, 0.0)
                    if not spoiled() and pref > -0.5:
                        return {
                            "thought": f"I need to eat. The {item.name} will do.",
                            "action": "CONSUME",
                            "target": item.name,
                            "_autopilot": True,
                        }
            # No food in inventory — navigate to nearest known food source.
            if not self.path:
                loc = agent.memory.get_location_for_need("hunger")
                if loc:
                    name, pos = loc
                    self._set_path_toward(agent, pos, name, world)
                    if self.path:
                        return self._follow_path(agent, world)

        # Desperate exhaustion: rest — but only if no critical survival need
        # is also active (thirst/hunger take priority at their own thresholds).
        if (agent.drives["energy"] > CRITICAL_ENERGY_THRESHOLD
                and agent.drives["thirst"] <= CRITICAL_THIRST_THRESHOLD
                and agent.drives["hunger"] <= CRITICAL_HUNGER_THRESHOLD):
            return {
                "thought": "I can barely stand... must rest.",
                "action": "REST",
                "_autopilot": True,
            }

        return None

    # ================================================================
    # ROUTINE — Low-priority habitual behavior
    # ================================================================

    def _check_routine(self, agent: Any, agents: List[Any],
                       world: Any) -> Optional[Dict]:
        """Handle routine, non-urgent behavior."""

        # Legionary formation cohesion — drift toward squad before anything else
        if "Legionary" in agent.role:
            form = self._check_legionary_formation(agent, agents, world)
            if form:
                return form

        # Lonely + someone nearby → but this is nuanced, let LLM handle
        # unless it's a very simple case
        if agent.drives["social"] > ROUTINE_SOCIAL_THRESHOLD:
            nearby = self._find_nearby_agents(agent, agents)
            if nearby:
                # If we know them well, autopilot can handle a greeting
                for other in nearby:
                    rel = agent.memory.relationships.get(other.name)
                    if rel and rel.familiarity > 20 and rel.trust > 10:
                        greetings = [
                            f"Salve, {other.name}!",
                            f"Ave, {other.name}. Good to see you.",
                            f"How goes it, {other.name}?",
                        ]
                        return {
                            "thought": f"Ah, {other.name}! I should say hello.",
                            "action": "TALK",
                            "target": other.name,
                            "speech": random.choice(greetings),
                            "_autopilot": True,
                        }
                # Stranger nearby + very lonely → defer to LLM for first meeting
                return None

        # Tired: rest (moderate, not critical)
        if agent.drives["energy"] > ROUTINE_ENERGY_THRESHOLD and self.state == AutopilotState.IDLE:
            return {
                "thought": "I should take a moment to catch my breath.",
                "action": "REST",
                "_autopilot": True,
            }

        return None

    def _check_legionary_combat(self, agent: Any, agents: List[Any]) -> Optional[Dict]:
        """Attack any wolf that is hunting or attacking within weapon range."""
        for other in agents:
            if not getattr(other, "is_animal", False):
                continue
            if other.animal_type != "wolf" or not other.is_alive:
                continue
            if other.action not in ("HUNTING", "ATTACKING"):
                continue
            dist = math.sqrt((other.x - agent.x) ** 2 + (other.y - agent.y) ** 2)
            if dist <= ATTACK_PROXIMITY_RADIUS:
                return {
                    "thought": f"A wolf threatens us! Engage!",
                    "action": "ATTACK",
                    "target": other.name,
                    "_autopilot": True,
                }
        return None

    def _check_legionary_formation(self, agent: Any, agents: List[Any],
                                   world: Any) -> Optional[Dict]:
        """Move toward the nearest fellow Legionary if the formation is spread out."""
        soldiers = [
            a for a in agents
            if a.uid != agent.uid and a.is_alive
            and "Legionary" in getattr(a, "role", "")
            and not getattr(a, "is_animal", False)
        ]
        if not soldiers:
            return None
        nearest = min(
            soldiers,
            key=lambda a: math.sqrt((a.x - agent.x) ** 2 + (a.y - agent.y) ** 2),
        )
        d = math.sqrt((nearest.x - agent.x) ** 2 + (nearest.y - agent.y) ** 2)
        if d > LEGIONARY_GROUP_RADIUS and not self.path:
            self._set_path_toward(
                agent, (int(nearest.x), int(nearest.y)), nearest.name, world
            )
        if self.path:
            return self._follow_path(agent, world)
        return None

    # ================================================================
    # HELPERS
    # ================================================================

    def _set_path_toward(self, agent: Any, target: Tuple[int, int],
                         name: str, world: Any) -> None:
        """Find an obstacle-avoiding path toward target using A*."""
        path = Pathfinder.find_path(
            (int(agent.x), int(agent.y)), target, world
        )
        if path:
            self.set_path(path, name)

    def _find_nearby_agents(self, agent: Any,
                            agents: List[Any]) -> List[Any]:
        """Find living agents within interaction range."""
        nearby = []
        for other in agents:
            if other.uid == agent.uid or not other.is_alive:
                continue
            dist = math.sqrt(
                (other.x - agent.x) ** 2 + (other.y - agent.y) ** 2
            )
            if dist < NEARBY_AGENT_RADIUS:
                nearby.append(other)
        return nearby

    @staticmethod
    def _direction_to(ax: float, ay: float, tx: int, ty: int) -> str:
        """Compute direction from (ax,ay) to (tx,ty)."""
        return Pathfinder.direction_to(ax, ay, tx, ty)

    # ================================================================
    # SERIALIZATION (for persistence)
    # ================================================================

    def serialize(self) -> Dict:
        """Serialize autopilot state for saving."""
        return {
            "state": self.state.value,
            "path": self.path,
            "destination_name": self.destination_name,
            "ticks_on_autopilot": self.ticks_on_autopilot,
        }

    def restore(self, data: Dict) -> None:
        """Restore autopilot state from save data."""
        self.state = AutopilotState(data.get("state", "idle"))
        self.path = [tuple(p) for p in data.get("path", [])]
        self.destination_name = data.get("destination_name")
        self.ticks_on_autopilot = data.get("ticks_on_autopilot", 0)
