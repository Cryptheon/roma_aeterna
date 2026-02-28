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


class AutopilotState(Enum):
    """Current autopilot behavior mode."""
    IDLE = "idle"
    NAVIGATING = "navigating"       # Following a path
    FLEEING = "fleeing"             # Running from danger
    SEEKING_RESOURCE = "seeking"    # Going to a known resource
    WORKING = "working"            # Performing role duties
    SOCIALIZING = "socializing"    # In a conversation
    RESTING = "resting"            # Recovering energy


# How many ticks the autopilot can run before forcing an LLM call
# (prevents agents from being mindless robots)
MAX_AUTOPILOT_TICKS = 30


class Autopilot:
    """Fast decision-maker for routine agent behavior."""

    def __init__(self) -> None:
        self.state: AutopilotState = AutopilotState.IDLE
        self.path: List[Tuple[int, int]] = []       # Multi-step navigation
        self.destination_name: Optional[str] = None  # Where we're going
        self.ticks_on_autopilot: int = 0
        self.override: bool = False                  # LLM requested manual control

    def set_path(self, path: List[Tuple[int, int]], destination: str = "") -> None:
        """Set a multi-step path for the agent to follow."""
        self.path = list(path)
        self.destination_name = destination
        self.state = AutopilotState.NAVIGATING

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
        survival = self._check_survival(agent, world)
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

    def _check_survival(self, agent: Any, world: Any) -> Optional[Dict]:
        """Immediate survival reflexes. Always override everything."""

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
        if agent.health < 25:
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
        from roma_aeterna.agent.base import DIRECTION_DELTAS

        best_dir = "north"
        best_score = -999.0

        for direction, (dx, dy) in DIRECTION_DELTAS.items():
            nx, ny = int(agent.x) + dx, int(agent.y) + dy
            tile = world.get_tile(nx, ny)
            if not tile or not tile.is_walkable:
                continue

            score = 0.0
            # Prefer tiles without smoke
            if "smoke" not in getattr(tile, "effects", []):
                score += 5.0
            # Prefer tiles without fire
            if not tile.building or not any(
                getattr(c, "is_burning", False)
                for c in getattr(tile.building, "components", {}).values()
            ):
                score += 10.0
            # Prefer roads (faster escape)
            if tile.terrain_type == "road":
                score += 2.0
            # Small randomness to prevent oscillation
            score += random.random()

            if score > best_score:
                best_score = score
                best_dir = direction

        return best_dir

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
                self.state = AutopilotState.IDLE
                self.ticks_on_autopilot = 0
                return None  # Arrived — let LLM decide what to do here
            target = self.path[0]
            tx, ty = target

        # Compute direction to next waypoint
        direction = self._direction_to(agent.x, agent.y, tx, ty)

        # Check if path is still valid
        tile = world.get_tile(tx, ty)
        if not tile or not tile.is_walkable:
            self.clear_path()
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
        if agent.drives["thirst"] > 70:
            for item in agent.inventory:
                if getattr(item, "item_type", None) == "drink":
                    return {
                        "thought": f"So thirsty... I'll drink my {item.name}.",
                        "action": "CONSUME",
                        "target": item.name,
                        "_autopilot": True,
                    }
            # No drink in inventory — navigate to known fountain
            fountain = agent.memory.known_locations.get("Fountain")
            if fountain and not self.path:
                self._set_path_toward(agent, fountain, "Fountain", world)
                if self.path:
                    return self._follow_path(agent, world)

        # Desperate hunger: eat from inventory
        if agent.drives["hunger"] > 70:
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

        # Desperate exhaustion: rest
        if agent.drives["energy"] > 85:
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

        # Lonely + someone nearby → but this is nuanced, let LLM handle
        # unless it's a very simple case
        if agent.drives["social"] > 60:
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
        if agent.drives["energy"] > 65 and self.state == AutopilotState.IDLE:
            return {
                "thought": "I should take a moment to catch my breath.",
                "action": "REST",
                "_autopilot": True,
            }

        return None

    # ================================================================
    # HELPERS
    # ================================================================

    def _set_path_toward(self, agent: Any, target: Tuple[int, int],
                         name: str, world: Any) -> None:
        """Generate a simple straight-line path toward a target.

        This is a basic A*-lite: just walk toward the target,
        preferring road tiles. For proper pathfinding, the engine's
        Pathfinder should be used instead.
        """
        path: List[Tuple[int, int]] = []
        cx, cy = int(agent.x), int(agent.y)
        tx, ty = target

        # Simple greedy walk (max 20 steps to prevent infinite loops)
        for _ in range(20):
            if cx == tx and cy == ty:
                break

            best = None
            best_dist = 999.0

            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = cx + dx, cy + dy
                    tile = world.get_tile(nx, ny)
                    if not tile or not tile.is_walkable:
                        continue
                    dist = math.sqrt((nx - tx) ** 2 + (ny - ty) ** 2)
                    # Prefer roads
                    if tile.terrain_type == "road":
                        dist *= 0.7
                    if dist < best_dist:
                        best_dist = dist
                        best = (nx, ny)

            if best:
                path.append(best)
                cx, cy = best
            else:
                break

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
            if dist < 5.0:
                nearby.append(other)
        return nearby

    @staticmethod
    def _direction_to(ax: float, ay: float, tx: int, ty: int) -> str:
        """Compute direction from (ax,ay) to (tx,ty)."""
        dx, dy = tx - ax, ty - ay
        if dx == 0 and dy == 0:
            return "north"
        angle = math.degrees(math.atan2(dy, dx))
        if angle < 0:
            angle += 360
        dirs = ["east", "southeast", "south", "southwest",
                "west", "northwest", "north", "northeast"]
        idx = int((angle + 22.5) // 45) % 8
        return dirs[idx]

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
