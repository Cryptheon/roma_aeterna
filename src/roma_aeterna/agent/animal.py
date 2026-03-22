"""
Animal — Lightweight autopilot-only agents for Rome: Aeterna.

Animals are NOT full Agent subclasses. They share the same list as
human agents in `engine.agents` but bypass the LIF/LLM pipeline
entirely. Each species has a simple tick() method that handles all
behaviour.

Animals are ephemeral: not saved/loaded across sessions.
"""

import random
import math
import uuid
from typing import Any, List, Optional

from .status_effects import StatusEffectManager
from roma_aeterna.config import (
    WOLF_PACK_RADIUS, WOLF_ATTACK_RANGE, WOLF_NIGHT_AGGRO_RADIUS,
    WOLF_DAY_AGGRO_RADIUS,
    WOLF_DAMAGE, DOG_DAMAGE, BOAR_AGGRO_RADIUS, BOAR_DAMAGE,
    MOVEMENT_TICKS_PER_TILE,
)

# speed_interval = ticks between each move step.
# Scaled relative to MOVEMENT_TICKS_PER_TILE so animal speed is always
# proportional to human walking speed regardless of TPS tuning.
_M = MOVEMENT_TICKS_PER_TILE
ANIMAL_STATS = {
    "wolf":  {"health": 60.0, "speed_interval": _M * 2},    # deliberate — acts every ~1s at TPS=30
    "dog":   {"health": 40.0, "speed_interval": _M + 6},    # slightly slower than human road pace
    "boar":  {"health": 80.0, "speed_interval": _M + 10},   # heavy, slow
    "raven": {"health": 20.0, "speed_interval": _M - 4},    # quick, light
}


def _dist(a: Any, b: Any) -> float:
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)


def _dist_xy(ax: float, ay: float, bx: float, by: float) -> float:
    return math.sqrt((ax - bx) ** 2 + (ay - by) ** 2)


class Animal:
    """Lightweight autopilot-only agent. Sits in engine.agents alongside humans."""

    is_animal = True

    def __init__(self, animal_type: str, x: float, y: float, name: str = "") -> None:
        uid = str(uuid.uuid4())[:8]
        self.uid: str = uid
        self.animal_type: str = animal_type
        self.name: str = name or f"{animal_type.capitalize()} #{uid[:4]}"
        self.role: str = animal_type        # renderer reads .role

        self.x: float = float(x)
        self.y: float = float(y)

        stats = ANIMAL_STATS[animal_type]
        self.health: float = stats["health"]
        self.max_health: float = stats["health"]

        self.is_alive: bool = True
        self.death_tick: int = -1

        self.action: str = "WANDERING"
        self.current_time: float = 0.0
        self.sim_tick: int = 0      # Set by engine outer loop each tick
        self.last_speech: str = ""

        # LLM / autopilot shims — keep engine code happy
        self.waiting_for_llm: bool = False
        self.brain = None
        self.drives: dict = {}
        self.inventory: list = []
        self.personality_seed: dict = {}

        # Status effects — fire/chaos still work on animals
        self.status_effects = StatusEffectManager()

        self._tick_counter: int = 0
        self._move_interval: int = stats["speed_interval"]

        # Optional home-range constraint (set by scenarios to keep animals in bounds)
        self.home_x: Optional[float] = None
        self.home_y: Optional[float] = None
        self.home_radius: Optional[float] = None

        self.last_hit_tick: int = -999

    # ================================================================
    # ENGINE INTERFACE
    # ================================================================

    def take_damage(self, amount: float) -> None:
        """Apply direct damage; die if HP reaches zero."""
        self.health = max(0.0, self.health - amount)
        self.last_hit_tick = self.sim_tick
        if self.health <= 0.0 and self.is_alive:
            self.is_alive = False
            self.action = "DEAD"
            self.death_tick = self.sim_tick

    def receive_speech(self, *args, **kwargs) -> None:
        """Animals ignore speech."""

    def update_biological(self, *args, **kwargs) -> bool:
        """No LIF neuron — always returns False (never fires)."""
        return False

    # ================================================================
    # TICK
    # ================================================================

    def tick(self, world: Any, agents: List[Any],
             tick_count: int, time_of_day: str) -> None:
        """Called by engine loop once per tick instead of LIF/LLM path."""
        self.current_time = float(tick_count)
        self._tick_counter += 1
        if self._tick_counter < self._move_interval:
            return
        self._tick_counter = 0

        is_night = time_of_day in ("night", "dusk", "dawn", "evening")

        dispatch = {
            "wolf":  self._wolf_tick,
            "dog":   self._dog_tick,
            "boar":  self._boar_tick,
            "raven": self._raven_tick,
        }
        dispatch[self.animal_type](world, agents, is_night)

    # ================================================================
    # SPECIES BEHAVIOURS
    # ================================================================

    def _wolf_tick(self, world: Any, agents: List[Any], is_night: bool) -> None:
        # Flee if badly wounded
        if self.health < 15.0:
            humans = [a for a in agents
                      if not getattr(a, "is_animal", False) and a.is_alive]
            if humans:
                nearest = min(humans, key=lambda a: _dist(self, a))
                self._move_away_from(nearest.x, nearest.y, world, agents)
                self.action = "FLEEING"
            return

        # Daytime: mostly rest — but will snap if something walks too close
        if not is_night:
            humans = [a for a in agents
                      if not getattr(a, "is_animal", False) and a.is_alive]
            if humans:
                nearest = min(humans, key=lambda a: _dist(self, a))
                d = _dist(self, nearest)
                if d <= WOLF_ATTACK_RANGE:
                    nearest.take_damage(WOLF_DAMAGE)
                    self.action = "ATTACKING"
                    self._notify_victim(
                        nearest,
                        f"A wolf snapped at you! You took {WOLF_DAMAGE:.0f} damage."
                        + (" You are dying." if nearest.health < 20 else ""),
                    )
                    return
                if d <= WOLF_DAY_AGGRO_RADIUS:
                    self._move_toward(nearest.x, nearest.y, world, agents)
                    self.action = "STALKING"
                    return
            if random.random() < 0.75:
                self.action = "RESTING"
                return
            self._wander(world, agents)
            return

        # Nighttime: pack cohesion first
        other_wolves = [
            a for a in agents
            if isinstance(a, Animal) and a.animal_type == "wolf"
            and a.uid != self.uid and a.is_alive
        ]
        pack_nearby = [w for w in other_wolves if _dist(self, w) < WOLF_PACK_RADIUS]
        if pack_nearby:
            cx = sum(w.x for w in pack_nearby) / len(pack_nearby)
            cy = sum(w.y for w in pack_nearby) / len(pack_nearby)
            if _dist_xy(self.x, self.y, cx, cy) > 3.0:
                self._move_toward(cx, cy, world, agents)
                self.action = "MOVING"
                return

        # Hunt: find nearest living human
        humans = [a for a in agents
                  if not getattr(a, "is_animal", False) and a.is_alive]
        if not humans:
            self._wander(world, agents)
            return

        target = min(humans, key=lambda a: _dist(self, a))
        d = _dist(self, target)

        if d <= WOLF_ATTACK_RANGE:
            target.take_damage(WOLF_DAMAGE)
            self.action = "ATTACKING"
            self._notify_victim(
                target,
                f"A wolf lunged at you and bit into you! You took {WOLF_DAMAGE:.0f} damage."
                + (" You are dying." if target.health < 20 else ""),
            )
        elif d <= WOLF_NIGHT_AGGRO_RADIUS:
            self._move_toward(target.x, target.y, world, agents)
            self.action = "HUNTING"
        else:
            self._wander(world, agents)

    def _dog_tick(self, world: Any, agents: List[Any], is_night: bool) -> None:
        # Flee nearby wolves
        wolves = [
            a for a in agents
            if isinstance(a, Animal) and a.animal_type == "wolf" and a.is_alive
        ]
        nearby_wolf = next((w for w in wolves if _dist(self, w) < 6.0), None)
        if nearby_wolf:
            self._move_away_from(nearby_wolf.x, nearby_wolf.y, world, agents)
            self.action = "FLEEING"
            return

        # Passive: mostly rest, occasional wander
        if random.random() < 0.6:
            self.action = "RESTING"
        else:
            self._wander(world, agents)

    def _boar_tick(self, world: Any, agents: List[Any], is_night: bool) -> None:
        humans = [a for a in agents
                  if not getattr(a, "is_animal", False) and a.is_alive]
        target = next(
            (h for h in humans if _dist(self, h) <= BOAR_AGGRO_RADIUS), None
        )
        if target:
            d = _dist(self, target)
            if d <= 1.2:
                target.take_damage(BOAR_DAMAGE)
                self.action = "ATTACKING"
                self._notify_victim(
                    target,
                    f"A wild boar charged and gored you! You took {BOAR_DAMAGE:.0f} damage."
                    + (" You are dying." if target.health < 20 else ""),
                )
            else:
                self._move_toward(target.x, target.y, world, agents)
                self.action = "CHARGING"
        else:
            if random.random() < 0.5:
                self.action = "RESTING"
            else:
                self._wander(world, agents)

    def _raven_tick(self, world: Any, agents: List[Any], is_night: bool) -> None:
        self._wander(world, agents)
        self.action = "FLYING"

    # ================================================================
    # ATTACK HELPERS
    # ================================================================

    def _notify_victim(self, target: Any, message: str) -> None:
        """Write an attack event into the victim's memory and spike their LIF.

        Importance 6.0 ensures it rises to long-term memory immediately and
        dominates the next LLM prompt. The LIF spike forces the brain to fire
        so the agent reacts this tick rather than waiting for the next cycle.
        """
        tick = getattr(target, "sim_tick", 0)
        if hasattr(target, "memory"):
            target.memory.add_event(
                message,
                tick=tick,
                importance=6.0,
                memory_type="observation",
                tags=["danger", "violence", "attacked"],
            )
        if hasattr(target, "brain") and target.brain is not None:
            target.brain.potential += 15.0  # guaranteed LIF fire regardless of role threshold

    # ================================================================
    # MOVEMENT HELPERS
    # ================================================================

    def _move_toward(self, tx: float, ty: float, world: Any,
                     agents: Optional[List[Any]] = None) -> None:
        dx, dy = tx - self.x, ty - self.y
        step_x = (1 if dx > 0 else -1) if abs(dx) > 0.5 else 0
        step_y = (1 if dy > 0 else -1) if abs(dy) > 0.5 else 0
        nx, ny = self.x + step_x, self.y + step_y
        tile = world.get_tile(int(nx), int(ny))
        if tile and tile.is_walkable:
            if agents and any(
                a is not self and getattr(a, "is_alive", True)
                and int(a.x) == int(nx) and int(a.y) == int(ny)
                for a in agents
            ):
                return  # tile occupied — don't stack
            self.x, self.y = nx, ny

    def _move_away_from(self, tx: float, ty: float, world: Any,
                        agents: Optional[List[Any]] = None) -> None:
        self._move_toward(self.x * 2 - tx, self.y * 2 - ty, world, agents)

    def _wander(self, world: Any, agents: Optional[List[Any]] = None) -> None:
        # If outside home range, step back toward home instead of wandering freely
        if (self.home_x is not None and self.home_radius is not None
                and _dist_xy(self.x, self.y, self.home_x, self.home_y) > self.home_radius):
            self._move_toward(self.home_x, self.home_y, world, agents)
            self.action = "WANDERING"
            return
        dx, dy = random.choice([
            (-1, 0), (1, 0), (0, -1), (0, 1),
            (-1, -1), (1, -1), (-1, 1), (1, 1),
        ])
        nx, ny = self.x + dx, self.y + dy
        tile = world.get_tile(int(nx), int(ny))
        if tile and tile.is_walkable:
            if agents and any(
                a is not self and getattr(a, "is_alive", True)
                and int(a.x) == int(nx) and int(a.y) == int(ny)
                for a in agents
            ):
                pass  # tile occupied — stay put this tick
            else:
                self.x, self.y = nx, ny
        self.action = "WANDERING"
