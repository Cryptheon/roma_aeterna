"""
Chaos Engine — Handles fire propagation, structural collapse,
weather effects on the physical world, and environmental hazards.

Split into two phases:
  - tick_environment(): Fire spread, burn fuel, collapse structures, water levels.
    Can run every N ticks as optimization.
  - tick_agents(): Apply status effects from weather/fire/smoke to agents.
    Must run EVERY tick so agents feel environmental changes immediately.
"""

import random
import math
from typing import Any, List

from roma_aeterna.world.components import Flammable, Structural, Liquid, WaterFeature
from roma_aeterna.config import FIRE_SPREAD_BASE_CHANCE, RAIN_FIRE_SUPPRESSION


class ChaosEngine:
    """Simulates environmental physics: fire, collapse, weather damage."""

    def __init__(self, world: Any) -> None:
        self.world = world

    # ================================================================
    # LEGACY ENTRY POINT (calls both phases)
    # ================================================================

    def tick(self, weather: Any, agents: List[Any]) -> None:
        """Run one full physics + agent tick (backward compatible)."""
        self.tick_environment(weather)
        self.tick_agents(agents, weather)

    # ================================================================
    # PHASE 1: ENVIRONMENT (fire, collapse, water — can run less often)
    # ================================================================

    def tick_environment(self, weather: Any) -> None:
        """Process fire burning/spreading, structural collapse, water levels."""
        objects = list(self.world.objects)
        weather_effects = weather.get_effects()

        for obj in objects:
            self._handle_fire(obj, weather, weather_effects)
            self._handle_structure(obj, weather_effects)
            self._handle_water(obj, weather)

        # Decay smoke from tiles gradually
        self._decay_smoke()

    # ================================================================
    # PHASE 2: AGENTS (status effects — must run every tick)
    # ================================================================

    def tick_agents(self, agents: List[Any], weather: Any) -> None:
        """Apply environmental status effects to agents based on conditions."""
        weather_effects = weather.get_effects()

        from roma_aeterna.agent.status_effects import create_effect

        for agent in agents:
            if not agent.is_alive:
                continue

            tile = self.world.get_tile(int(agent.x), int(agent.y))

            # --- Rain → Wet (unless sheltered) ---
            if weather_effects.get("wet"):
                is_sheltered = (
                    tile and tile.building
                    and getattr(tile.building, "obj_type", None) == "building"
                )
                if not is_sheltered and not agent.status_effects.has_effect("Wet"):
                    wet = create_effect("wet")
                    if wet:
                        agent.status_effects.add(wet)

            # --- Heatwave → Heatstroke risk (scales with thirst) ---
            if weather_effects.get("heatwave"):
                thirst_ratio = agent.drives["thirst"] / 100.0
                heatstroke_chance = 0.005 + (thirst_ratio ** 2) * 0.03
                if random.random() < heatstroke_chance:
                    if not agent.status_effects.has_effect("Heatstroke"):
                        heatstroke = create_effect("heatstroke")
                        if heatstroke:
                            agent.status_effects.add(heatstroke)

            # --- Fire proximity → Burns / Smoke Inhalation ---
            # (skips decorative fires like torches)
            fire_exposure = self._check_fire_proximity(agent)

            if fire_exposure > 5.0:
                if not agent.status_effects.has_effect("Burned"):
                    burned = create_effect("burned")
                    if burned:
                        agent.status_effects.add(burned)
                agent.health -= min(5.0, fire_exposure * 0.5)
            elif fire_exposure > 2.0:
                if not agent.status_effects.has_effect("Smoke Inhalation"):
                    smoke = create_effect("smoke_inhalation")
                    if smoke:
                        agent.status_effects.add(smoke)

            # --- Smoke on current tile → mild discomfort ---
            if tile and "smoke" in getattr(tile, "effects", []):
                agent.drives["comfort"] = min(
                    100.0, agent.drives["comfort"] + 1.5
                )

            # --- Night + outdoors → Chilled (if not already) ---
            if weather_effects.get("danger", 0) > 1.0:
                is_sheltered = (
                    tile and tile.building
                    and getattr(tile.building, "obj_type", None) == "building"
                )
                if (not is_sheltered
                        and weather.temperature < 15.0
                        and not agent.status_effects.has_effect("Chilled")):
                    chilled = create_effect("chilled")
                    if chilled:
                        agent.status_effects.add(chilled)

    # ================================================================
    # FIRE PHYSICS
    # ================================================================

    def _handle_fire(self, obj: Any, weather: Any, effects: dict) -> None:
        """Process fire burning and spreading."""
        flam = obj.get_component(Flammable)
        if not flam or not flam.is_burning:
            return

        # SKIP decorative fires (torches) — they glow but don't spread
        if getattr(flam, "is_decorative", False):
            return

        # Rain suppresses fire
        if effects.get("wet"):
            flam.fire_intensity *= 0.9
            if flam.fire_intensity < 1.0 and random.random() < RAIN_FIRE_SUPPRESSION:
                flam.is_burning = False
                flam.fire_intensity = 0.0
                return

        # Burn fuel
        wind_mult = 1.0 + (weather.wind_speed * 0.15)
        flam.fuel -= flam.burn_rate * wind_mult
        flam.fire_intensity = min(20.0, flam.fire_intensity + 0.5)

        # Damage structure
        struct = obj.get_component(Structural)
        if struct:
            fire_damage = 2.0 * wind_mult * (1.0 - struct.weather_resistance * 0.3)
            struct.hp -= fire_damage

        # Smoke reduces nearby visibility
        self._emit_smoke(obj, flam.smoke_output)

        # Spread fire to neighbors
        spread_chance = FIRE_SPREAD_BASE_CHANCE + (0.03 * weather.wind_speed)
        fire_spread_mult = effects.get("fire_spread", 1.0)
        spread_chance *= fire_spread_mult

        if random.random() < spread_chance:
            self._spread_fire(obj, weather)

        # Extinguish when fuel depleted
        if flam.fuel <= 0:
            flam.is_burning = False
            flam.fire_intensity = 0.0

    def _spread_fire(self, source: Any, weather: Any) -> None:
        """Spread fire to adjacent flammable objects, biased by wind."""
        wind_dx, wind_dy = {
            "north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0),
            "northeast": (1, -1), "northwest": (-1, -1),
            "southeast": (1, 1), "southwest": (-1, 1),
        }.get(weather.wind_direction, (0, 0))

        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue

                wind_bonus = 0.0
                if dx == wind_dx or dy == wind_dy:
                    wind_bonus = 0.1

                nx, ny = source.x + dx, source.y + dy
                tile = self.world.get_tile(nx, ny)
                if not tile or not tile.building:
                    continue

                target_flam = tile.building.get_component(Flammable)
                if target_flam and not target_flam.is_burning:
                    # Don't ignite decorative objects (torches etc.)
                    if getattr(target_flam, "is_decorative", False):
                        continue
                    if random.random() < 0.3 + wind_bonus:
                        target_flam.is_burning = True
                        target_flam.fire_intensity = 5.0

    def _emit_smoke(self, obj: Any, amount: float) -> None:
        """Mark nearby tiles as smoky."""
        if amount <= 0:
            return
        smoke_radius = max(1, int(amount / 2))
        for dy in range(-smoke_radius, smoke_radius + 1):
            for dx in range(-smoke_radius, smoke_radius + 1):
                tile = self.world.get_tile(obj.x + dx, obj.y + dy)
                if tile:
                    effects = getattr(tile, "effects", [])
                    if "smoke" not in effects:
                        effects.append("smoke")
                    if not hasattr(tile, "_smoke_age"):
                        tile._smoke_age = 0
                    tile._smoke_age = 0

    def _decay_smoke(self) -> None:
        """Gradually clear smoke from tiles that aren't being refreshed.
        
        OPTIMIZATION: Only check tiles that actually have smoke tracked,
        instead of iterating the entire 30,000-tile map.
        """
        # We still need to scan, but we can skip tiles without effects
        for y in range(self.world.height):
            for x in range(self.world.width):
                tile = self.world.get_tile(x, y)
                if not tile:
                    continue
                effects = getattr(tile, "effects", [])
                if "smoke" not in effects:
                    continue
                age = getattr(tile, "_smoke_age", 0)
                tile._smoke_age = age + 1
                if tile._smoke_age > 10:
                    effects.remove("smoke")
                    tile._smoke_age = 0

    # ================================================================
    # STRUCTURAL COLLAPSE
    # ================================================================

    def _handle_structure(self, obj: Any, effects: dict) -> None:
        """Check for structural collapse."""
        struct = obj.get_component(Structural)
        if not struct or struct.hp > 0:
            return

        tile = self.world.get_tile(obj.x, obj.y)
        if tile:
            tile.building = None
            tile.terrain_type = "mountain"
            tile.movement_cost = 8.0
            if "rubble" not in getattr(tile, "effects", []):
                tile.effects.append("rubble")

        if obj in self.world.objects:
            self.world.objects.remove(obj)

    # ================================================================
    # WATER FEATURES
    # ================================================================

    def _handle_water(self, obj: Any, weather: Any) -> None:
        """Refill water features in rain, evaporate in heat."""
        liquid = obj.get_component(Liquid)
        if not liquid:
            return

        if weather.current.value in ("Rain", "Storm"):
            liquid.amount = min(liquid.max_amount, liquid.amount + 2.0)
        elif weather.current.value == "Heatwave":
            liquid.amount = max(0, liquid.amount - liquid.evaporation_rate * 3)
        else:
            liquid.amount = max(0, liquid.amount - liquid.evaporation_rate)

    # ================================================================
    # FIRE PROXIMITY CHECK
    # ================================================================

    def _check_fire_proximity(self, agent: Any) -> float:
        """Calculate fire exposure score for an agent.

        Uses inverse-distance weighting so nearby fire is felt strongly.
        SKIPS decorative fires (torches) — they provide light, not danger.
        """
        score = 0.0
        ax, ay = int(agent.x), int(agent.y)

        for dy in range(-3, 4):
            for dx in range(-3, 4):
                tile = self.world.get_tile(ax + dx, ay + dy)
                if not tile or not tile.building:
                    continue
                flam = tile.building.get_component(Flammable)
                if flam and flam.is_burning:
                    # Skip decorative fires (torches)
                    if getattr(flam, "is_decorative", False):
                        continue
                    dist = math.sqrt(dx * dx + dy * dy) + 0.1
                    score += flam.fire_intensity / dist

        return score