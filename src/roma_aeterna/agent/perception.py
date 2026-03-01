"""
PerceptionSystem — Builds natural-language descriptions of what an agent sees.

Extracted from Agent in base.py so that base.py stays focused on
state and lifecycle. All scan/describe methods live here.
"""

import math
from typing import Any, List, Optional

from roma_aeterna.config import PERCEPTION_RADIUS, INTERACTION_RADIUS
from .constants import DIRECTION_DELTAS


class PerceptionSystem:
    """Handles all perception and environment scanning for one agent."""

    def __init__(self, agent: Any) -> None:
        self._agent = agent

    # ================================================================
    # PUBLIC — called by Agent.perceive()
    # ================================================================

    def perceive(self, world: Any, agents: List[Any],
                 radius: Optional[int] = None,
                 include_environment: bool = True) -> str:
        """Build a natural-language description of what the agent sees."""
        agent = self._agent
        radius = radius or PERCEPTION_RADIUS
        radius_mod = int(agent.status_effects.get_additive("perception_radius"))
        effective_radius = max(2, radius + radius_mod)

        sections: List[str] = []

        tile_desc = self._describe_current_tile(world)
        if tile_desc:
            sections.append(f"YOU ARE STANDING ON: {tile_desc}")

        buildings = self._scan_buildings(world, effective_radius)
        if buildings:
            sections.append("STRUCTURES NEARBY:\n" + "\n".join(buildings))

        ground_items = self._scan_ground_items(world, effective_radius)
        if ground_items:
            sections.append("ITEMS ON THE GROUND:\n" + "\n".join(ground_items))

        nearby_agents = self._scan_agents(agents, effective_radius)
        if nearby_agents:
            sections.append("PEOPLE NEARBY:\n" + "\n".join(nearby_agents))

        # Full environment prose is throttled; anomalies (smoke/rubble) always shown
        if include_environment:
            env_full = self._describe_environment_full(world)
            env_anomalies = self._describe_environment_anomalies(world)
            env_combined = " ".join(filter(None, [env_full, env_anomalies]))
        else:
            env_combined = self._describe_environment_anomalies(world)
        if env_combined:
            sections.append("ENVIRONMENT:\n" + env_combined)

        directions = self._scan_directions(world)
        if directions:
            sections.append("PASSABLE DIRECTIONS: " + ", ".join(directions))

        if not sections:
            return "You see nothing remarkable around you. The area is quiet."

        return "\n\n".join(sections)

    # ================================================================
    # SCANNING HELPERS
    # ================================================================

    def _scan_buildings(self, world: Any, radius: int) -> List[str]:
        agent = self._agent
        results: List[str] = []
        seen_names: set = set()

        min_x = max(0, int(agent.x) - radius)
        max_x = min(world.width, int(agent.x) + radius)
        min_y = max(0, int(agent.y) - radius)
        max_y = min(world.height, int(agent.y) + radius)

        for ty in range(min_y, max_y):
            for tx in range(min_x, max_x):
                tile = world.get_tile(tx, ty)
                if not tile or not tile.building:
                    continue

                bld = tile.building
                if bld.name in seen_names:
                    continue
                seen_names.add(bld.name)

                dist = math.sqrt((tx - agent.x) ** 2 + (ty - agent.y) ** 2)
                direction = self._get_direction(tx, ty)

                modifiers: List[str] = []
                for comp in bld.components.values():
                    if getattr(comp, "is_burning", False):
                        intensity = getattr(comp, "fire_intensity", 0)
                        if intensity > 10:
                            modifiers.append("ENGULFED IN FLAMES!")
                        else:
                            modifiers.append("ON FIRE!")

                from roma_aeterna.world.components import Structural, Interactable
                struct = bld.get_component(Structural)
                if struct and struct.hp < struct.max_hp * 0.3:
                    modifiers.append("badly damaged, looks about to collapse")
                elif struct and struct.hp < struct.max_hp * 0.5:
                    modifiers.append("damaged")

                interact = bld.get_component(Interactable)
                if interact:
                    modifiers.append(f"[{interact.interaction_type}]")

                mod_str = f" ({', '.join(modifiers)})" if modifiers else ""
                results.append(
                    f"- {bld.name}{mod_str}: {dist:.0f}m to the {direction}"
                )
                agent.memory.learn_location(bld.name, (tx, ty))

        return results

    def _scan_ground_items(self, world: Any, radius: int) -> List[str]:
        agent = self._agent
        results: List[str] = []
        min_x = max(0, int(agent.x) - radius)
        max_x = min(world.width, int(agent.x) + radius)
        min_y = max(0, int(agent.y) - radius)
        max_y = min(world.height, int(agent.y) + radius)

        for ty in range(min_y, max_y):
            for tx in range(min_x, max_x):
                tile = world.get_tile(tx, ty)
                if not tile:
                    continue
                for item in getattr(tile, "ground_items", []):
                    dist = math.sqrt((tx - agent.x) ** 2 + (ty - agent.y) ** 2)
                    direction = self._get_direction(tx, ty)
                    results.append(f"- {item.name}: {dist:.0f}m to the {direction}")
        return results

    def _scan_agents(self, agents: List[Any], radius: int) -> List[str]:
        agent = self._agent
        _ACTIVITY_LABELS = {
            "idle": "standing idle",
            "move": "walking",
            "talk": "speaking to someone",
            "rest": "resting",
            "sleep": "sleeping",
            "work": "working",
            "buy": "buying something",
            "interact": "busy with something",
            "craft": "crafting",
            "trade": "trading",
            "inspect": "examining something",
            "reflect": "lost in thought",
            "goto": "heading somewhere",
            "consume": "eating or drinking",
            "pick_up": "picking something up",
            "drop": "dropping something",
        }
        results: List[str] = []
        for other in agents:
            if other.uid == agent.uid or not other.is_alive:
                continue
            dist = math.sqrt((other.x - agent.x) ** 2 + (other.y - agent.y) ** 2)
            if dist > radius:
                continue

            direction = self._get_direction(other.x, other.y)
            rel = agent.memory.relationships.get(other.name)

            # Trust level description
            if rel and rel.familiarity > 10:
                if rel.trust > 50:
                    known = " (trusted ally)"
                elif rel.trust > 20:
                    known = " (friendly)"
                elif rel.trust < -50:
                    known = " (hostile)"
                elif rel.trust < -20:
                    known = " (distrusted)"
                else:
                    known = " (acquaintance)"
            else:
                known = ""

            # Human-readable activity
            activity = _ACTIVITY_LABELS.get(other.action.lower(), other.action.lower())

            # Speech — always shown if within earshot
            speech = ""
            if other.last_speech and dist < INTERACTION_RADIUS * 2:
                speech = f', saying: "{other.last_speech}"'

            # Visible distress
            distress_parts = []
            if other.health < 30:
                distress_parts.append("looks badly injured")
            elif other.status_effects.has_effect("Burned"):
                distress_parts.append("appears burned")
            if other.drives["hunger"] > 70:
                distress_parts.append("looks hungry")
            if other.drives["thirst"] > 70:
                distress_parts.append("looks parched")
            distress = (", " + ", ".join(distress_parts)) if distress_parts else ""

            results.append(
                f"- {other.name}, a {other.role}, {dist:.0f}m to the {direction}, "
                f"{activity}{distress}{known}{speech}"
            )
        return results

    # ================================================================
    # ENVIRONMENT DESCRIPTION
    # ================================================================

    def _describe_environment_full(self, world: Any) -> str:
        """Return weather and time-of-day prose (throttled by build_prompt)."""
        parts: List[str] = []
        weather = getattr(world, "_current_weather_desc", None)
        if weather:
            parts.append(weather)
        time_of_day = getattr(world, "_current_time_desc", None)
        if time_of_day:
            parts.append(time_of_day)
        return " ".join(parts) if parts else ""

    def _describe_environment_anomalies(self, world: Any) -> str:
        """Return hazard anomalies (smoke, rubble) — always shown regardless of throttle."""
        agent = self._agent
        parts: List[str] = []
        tile = world.get_tile(int(agent.x), int(agent.y))
        if tile:
            effects = getattr(tile, "effects", [])
            if "smoke" in effects:
                parts.append("⚠ Thick smoke fills the air here, stinging your eyes.")
            if "rubble" in effects:
                parts.append("⚠ The ground is covered in rubble from a collapsed building.")
        return " ".join(parts) if parts else ""

    def _describe_environment(self, world: Any) -> str:
        """Combined full + anomalies (kept for any direct callers outside build_prompt)."""
        parts = [
            self._describe_environment_full(world),
            self._describe_environment_anomalies(world),
        ]
        return " ".join(p for p in parts if p)

    def _describe_current_tile(self, world: Any) -> str:
        agent = self._agent
        tile = world.get_tile(int(agent.x), int(agent.y))
        if not tile:
            return "unknown terrain"

        terrain_names = {
            "road": "a paved Roman road",
            "grass": "a grassy patch",
            "dirt": "bare earth",
            "sand": "sandy ground",
            "water": "shallow water",
            "marble_floor": "polished marble flooring",
            "plaza": "an open plaza",
            "forest": "dense woodland",
            "mountain": "rocky rubble",
        }
        desc = terrain_names.get(tile.terrain_type, tile.terrain_type)
        if tile.building:
            desc += f" (inside/near {tile.building.name})"
        return desc

    def _scan_directions(self, world: Any) -> List[str]:
        agent = self._agent
        passable: List[str] = []
        for direction, (dx, dy) in DIRECTION_DELTAS.items():
            nx, ny = int(agent.x) + dx, int(agent.y) + dy
            tile = world.get_tile(nx, ny)
            if tile and tile.is_walkable:
                passable.append(direction)
        return passable

    def _get_direction(self, tx: float, ty: float) -> str:
        agent = self._agent
        dx, dy = tx - agent.x, ty - agent.y
        if dx == 0 and dy == 0:
            return "here"
        angle = math.degrees(math.atan2(dy, dx))
        if angle < 0:
            angle += 360
        dirs = ["east", "southeast", "south", "southwest",
                "west", "northwest", "north", "northeast"]
        idx = int((angle + 22.5) // 45) % 8
        return dirs[idx]
