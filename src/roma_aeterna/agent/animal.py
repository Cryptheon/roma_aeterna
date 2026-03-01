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
    WOLF_DAMAGE, DOG_DAMAGE, BOAR_AGGRO_RADIUS, BOAR_DAMAGE,
)


ANIMAL_STATS = {
    "wolf":  {"health": 60.0, "speed_interval": 3},
    "dog":   {"health": 40.0, "speed_interval": 4},
    "boar":  {"health": 80.0, "speed_interval": 5},
    "raven": {"health": 20.0, "speed_interval": 6},
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

    # ================================================================
    # ENGINE INTERFACE
    # ================================================================

    def take_damage(self, amount: float) -> None:
        """Apply direct damage; die if HP reaches zero."""
        self.health = max(0.0, self.health - amount)
        if self.health <= 0.0 and self.is_alive:
            self.is_alive = False
            self.action = "DEAD"
            self.death_tick = int(self.current_time)

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
                self._move_away_from(nearest.x, nearest.y, world)
                self.action = "FLEEING"
            return

        # Daytime: mostly rest, occasional wander
        if not is_night:
            if random.random() < 0.75:
                self.action = "RESTING"
                return
            self._wander(world)
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
                self._move_toward(cx, cy, world)
                self.action = "MOVING"
                return

        # Hunt: find nearest living human
        humans = [a for a in agents
                  if not getattr(a, "is_animal", False) and a.is_alive]
        if not humans:
            self._wander(world)
            return

        target = min(humans, key=lambda a: _dist(self, a))
        d = _dist(self, target)

        if d <= WOLF_ATTACK_RANGE:
            target.take_damage(WOLF_DAMAGE)
            self.action = "ATTACKING"
        elif d <= WOLF_NIGHT_AGGRO_RADIUS:
            self._move_toward(target.x, target.y, world)
            self.action = "HUNTING"
        else:
            self._wander(world)

    def _dog_tick(self, world: Any, agents: List[Any], is_night: bool) -> None:
        # Flee nearby wolves
        wolves = [
            a for a in agents
            if isinstance(a, Animal) and a.animal_type == "wolf" and a.is_alive
        ]
        nearby_wolf = next((w for w in wolves if _dist(self, w) < 6.0), None)
        if nearby_wolf:
            self._move_away_from(nearby_wolf.x, nearby_wolf.y, world)
            self.action = "FLEEING"
            return

        # Passive: mostly rest, occasional wander
        if random.random() < 0.6:
            self.action = "RESTING"
        else:
            self._wander(world)

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
            else:
                self._move_toward(target.x, target.y, world)
                self.action = "CHARGING"
        else:
            if random.random() < 0.5:
                self.action = "RESTING"
            else:
                self._wander(world)

    def _raven_tick(self, world: Any, agents: List[Any], is_night: bool) -> None:
        self._wander(world)
        self.action = "FLYING"

    # ================================================================
    # MOVEMENT HELPERS
    # ================================================================

    def _move_toward(self, tx: float, ty: float, world: Any) -> None:
        dx, dy = tx - self.x, ty - self.y
        step_x = (1 if dx > 0 else -1) if abs(dx) > 0.5 else 0
        step_y = (1 if dy > 0 else -1) if abs(dy) > 0.5 else 0
        nx, ny = self.x + step_x, self.y + step_y
        tile = world.get_tile(int(nx), int(ny))
        if tile and tile.is_walkable:
            self.x, self.y = nx, ny

    def _move_away_from(self, tx: float, ty: float, world: Any) -> None:
        # Reflect direction through self
        self._move_toward(self.x * 2 - tx, self.y * 2 - ty, world)

    def _wander(self, world: Any) -> None:
        dx, dy = random.choice([
            (-1, 0), (1, 0), (0, -1), (0, 1),
            (-1, -1), (1, -1), (-1, 1), (1, 1),
        ])
        nx, ny = self.x + dx, self.y + dy
        tile = world.get_tile(int(nx), int(ny))
        if tile and tile.is_walkable:
            self.x, self.y = nx, ny
        self.action = "WANDERING"
