"""
Gladiator Arena scenario — The Flavian Amphitheatre c. 80 AD.

A 120×90 map centred on the Colosseum arena.

Layout (not to scale):
  ┌──────────────────────────────────────────────────────────────────────┐
  │  Armory ┐   [Fountain]  N-TUNNEL  [Fountain]   ┌ Medical Tent       │
  │  (west) │   ──────────────────────────────────  │  (east)            │
  │         └── road ──► [Gate of Life]  ◄── road ──┘                   │
  │              ╔══════════════════════════╗                             │
  │              ║  (outer structural wall) ║                             │
  │              ║  ┌────────────────────┐  ║                             │
  │              ║  │   arena seating    │  ║                             │
  │              ║  │  ╔══════════════╗  │  ║                             │
  │              ║  │  ║  sand arena  ║  │  ║   ← Editor's Box           │
  │              ║  │  ║  [Altar]     ║  │  ║                             │
  │              ║  │  ╚══════════════╝  │  ║                             │
  │              ║  └────────────────────┘  ║                             │
  │              ║  (outer structural wall) ║                             │
  │              ╚══════════════════════════╝                             │
  │                   [Gate of Death]                                     │
  │                   S-TUNNEL                                            │
  └──────────────────────────────────────────────────────────────────────┘
"""

import random

from .base import BaseScenario
from ._utils import generate_roman_name, find_spawn_point
from roma_aeterna.config import N_AGENTS, RANDOM_SEED


# ── Scenario-specific spawn configuration ────────────────────────────────────

_ROLE_WEIGHTS = {
    "Gladiator":          40,
    "Plebeian":           30,   # crowd
    "Merchant":           15,   # vendors in the forecourt
    "Guard (Legionary)":  10,   # arena guards
    "Craftsman":           5,   # physicians, armourers
}

_ROLE_SPAWN_ZONES = {
    "Gladiator":          ["sand_arena", "road_paved"],
    "Plebeian":           ["plaza", "road_paved"],
    "Merchant":           ["road_paved"],
    "Guard (Legionary)":  ["road_paved", "plaza"],
    "Craftsman":          ["road_paved"],
}

# ── Map geometry ──────────────────────────────────────────────────────────────

_W = 120   # map width  (tiles)  — 1.5× original 80
_H = 90    # map height (tiles)  — 1.5× original 60
_CX = _W // 2   # arena centre column  (60)
_CY = _H // 2   # arena centre row     (45)

# ── Arena ellipse radii ──────────────────────────────────────────────────────
# 1.5× the original radii (20/16, 17/14, 14/11, 12/9).
_OUTER_RX = 30   # outer structural wall — horizontal radius
_OUTER_RY = 24   # outer structural wall — vertical radius
_SEAT_RX  = 26   # spectator concourse
_SEAT_RY  = 21
_WALL_RX  = 21   # inner podium wall
_WALL_RY  = 17
_SAND_RX  = 18   # sand fighting floor
_SAND_RY  = 14

# ── Forecourt geometry ───────────────────────────────────────────────────────
_FORECOURT_TOP    = 3                    # top edge of forecourt buildings
_FORECOURT_BOTTOM = _CY - _OUTER_RY - 2 # just above the arena outer wall
_FORECOURT_MID_Y  = (_FORECOURT_TOP + _FORECOURT_BOTTOM) // 2


class GladiatorArenaScenario(BaseScenario):
    name = "Gladiator Arena"
    description = "The Flavian Amphitheatre c. 80 AD — The Grand Games of Titus"
    title_lines = [
        "ROME: AETERNA — Flavian Amphitheatre",
        "c. 80 AD, The Grand Games of Emperor Titus",
    ]

    # ------------------------------------------------------------------ #
    # World generation                                                     #
    # ------------------------------------------------------------------ #

    def generate_world(self):
        from ..map import GameMap
        from ..objects import WorldObject, create_prefab
        from ..components import (
            Structural, Footprint, Elevation, Decoration,
            Interactable, WaterFeature, Liquid, Flammable,
        )

        random.seed(RANDOM_SEED)
        world = GameMap(_W, _H)

        self._paint_base(world)
        self._build_arena_layers(world)
        self._carve_tunnels(world)
        self._build_forecourt(world)
        self._place_objects(world, WorldObject, create_prefab,
                            Structural, Footprint, Elevation, Decoration,
                            Interactable, WaterFeature, Liquid, Flammable)

        # Camera focus: arena floor centre
        world.camera_start = (_CX, _CY)
        return world

    # ── Phase 1: base terrain ─────────────────────────────────────────────

    @staticmethod
    def _paint_base(world):
        for y in range(_H):
            for x in range(_W):
                t = "dirt" if random.random() < 0.6 else "grass"
                world.set_tile(x, y, t, zone="open")

    # ── Phase 2: arena structure (painted outside-in) ─────────────────────

    @staticmethod
    def _build_arena_layers(world):
        world.fill_ellipse(_CX, _CY, _OUTER_RX, _OUTER_RY, "wall",       zone="arena_structure")
        world.fill_ellipse(_CX, _CY, _SEAT_RX,  _SEAT_RY,  "plaza",      zone="arena_seating")
        world.fill_ellipse(_CX, _CY, _WALL_RX,  _WALL_RY,  "wall",       zone="arena_wall")
        world.fill_ellipse(_CX, _CY, _SAND_RX,  _SAND_RY,  "sand_arena", zone="arena_floor")

    # ── Phase 3: north/south entrance tunnels ─────────────────────────────

    @staticmethod
    def _carve_tunnels(world):
        # North tunnel: top of map → arena floor
        world.draw_road(_CX, 0, _CX, _CY - _SAND_RY,
                        width=5, terrain_type="road_paved", zone="arena_tunnel")
        # South tunnel: arena floor → bottom of map
        world.draw_road(_CX, _CY + _SAND_RY, _CX, _H - 1,
                        width=5, terrain_type="road_paved", zone="arena_tunnel")

    # ── Phase 4: north forecourt (armory, medical tent) ───────────────────

    @staticmethod
    def _build_forecourt(world):
        _bld_w = 15   # building width
        _bld_h = _FORECOURT_BOTTOM - _FORECOURT_TOP

        # Armory wing — west of the north tunnel entrance
        _arm_x1 = 6
        _arm_x2 = _arm_x1 + _bld_w
        world.fill_rect(_arm_x1, _FORECOURT_TOP, _arm_x2, _FORECOURT_BOTTOM,
                        "building_floor", zone="armory")
        world.draw_road(_arm_x2, _FORECOURT_MID_Y, _CX - 3, _FORECOURT_MID_Y,
                        width=2, terrain_type="road_paved", zone="service_road")

        # Medical wing — east of the north tunnel entrance
        _med_x2 = _W - 6
        _med_x1 = _med_x2 - _bld_w
        world.fill_rect(_med_x1, _FORECOURT_TOP, _med_x2, _FORECOURT_BOTTOM,
                        "building_floor", zone="medical")
        world.draw_road(_CX + 3, _FORECOURT_MID_Y, _med_x1, _FORECOURT_MID_Y,
                        width=2, terrain_type="road_paved", zone="service_road")

    # ── Phase 5: world objects ────────────────────────────────────────────

    @staticmethod
    def _place_objects(world, WorldObject, create_prefab,
                       Structural, Footprint, Elevation, Decoration,
                       Interactable, WaterFeature, Liquid, Flammable):

        # ── Colosseum outer shell (visual landmark — tiles already painted) ──
        # Build manually instead of create_prefab so the footprint matches
        # the scaled arena ellipse (diameter = 2× outer radii).
        _colo_w = _OUTER_RX * 2
        _colo_h = _OUTER_RY * 2
        colosseum = WorldObject("Colosseum", _CX - _OUTER_RX, _CY - _OUTER_RY)
        colosseum.obj_type = "monument"
        colosseum.add_component(Structural(hp=5000, max_hp=5000, material="concrete"))
        colosseum.add_component(Footprint(width=_colo_w, height=_colo_h))
        colosseum.add_component(Elevation(height=4.5, shadow_length=3.5))
        colosseum.add_component(Decoration(sprite_key="colosseum", layer=2))
        colosseum.add_component(Interactable(interaction_type="spectate", capacity=50))
        world.register_landmark("Colosseum", colosseum)

        # ── Armory ── (west forecourt building)
        _arm_cx = 14
        armory = WorldObject("Armory", _arm_cx - 5, _FORECOURT_MID_Y - 4)
        armory.add_component(Structural(hp=800, max_hp=800, material="stone"))
        armory.add_component(Footprint(width=10, height=9))
        armory.add_component(Decoration(sprite_key="ludus", layer=2))
        armory.add_component(Interactable(interaction_type="trade", capacity=10))
        world.register_landmark("Armory", armory)

        # ── Medical Tent ── (east forecourt building)
        _med_cx = _W - 14
        medic = WorldObject("Medical Tent", _med_cx - 5, _FORECOURT_MID_Y - 4)
        medic.add_component(Structural(hp=150, max_hp=150, material="wood"))
        medic.add_component(Footprint(width=10, height=9))
        medic.add_component(Decoration(sprite_key="domus", layer=1))
        medic.add_component(Interactable(interaction_type="rest", capacity=5))
        medic.add_component(Flammable(fuel=40.0, burn_rate=0.8))
        world.register_landmark("Medical Tent", medic)

        # ── Gate of Life (north — gladiators enter) ──
        gate_n = WorldObject("Gate of Life", _CX - 3, _CY - _WALL_RY - 2)
        gate_n.obj_type = "monument"
        gate_n.add_component(Structural(hp=1000, max_hp=1000, material="stone"))
        gate_n.add_component(Footprint(width=6, height=3))
        gate_n.add_component(Decoration(sprite_key="arch", layer=2))
        gate_n.add_component(Interactable(interaction_type="inspect", capacity=20))
        world.register_landmark("Gate of Life", gate_n)

        # ── Gate of Death (south — corpses removed) ──
        gate_s = WorldObject("Gate of Death", _CX - 3, _CY + _WALL_RY)
        gate_s.obj_type = "monument"
        gate_s.add_component(Structural(hp=1000, max_hp=1000, material="stone"))
        gate_s.add_component(Footprint(width=6, height=3))
        gate_s.add_component(Decoration(sprite_key="arch", layer=2))
        gate_s.add_component(Interactable(interaction_type="inspect", capacity=20))
        world.register_landmark("Gate of Death", gate_s)

        # ── Altar of Victory (arena floor, south of centre) ──
        altar = WorldObject("Altar of Victory", _CX - 2, _CY + 8)
        altar.obj_type = "monument"
        altar.add_component(Structural(hp=500, max_hp=500, material="marble"))
        altar.add_component(Footprint(width=4, height=4))
        altar.add_component(Decoration(sprite_key="statue", layer=2))
        altar.add_component(Interactable(interaction_type="pray", capacity=5))
        world.register_landmark("Altar of Victory", altar)

        # ── Editor's Box (elevated north seating — imperial loge) ──
        editor = WorldObject("Editor's Box", _CX - 4, _CY - _SEAT_RY - 2)
        editor.obj_type = "monument"
        editor.add_component(Structural(hp=300, max_hp=300, material="marble"))
        editor.add_component(Footprint(width=8, height=4))
        editor.add_component(Decoration(sprite_key="rostra", layer=2))
        editor.add_component(Elevation(height=1.5, shadow_length=1.0))
        editor.add_component(Interactable(interaction_type="inspect", capacity=10))
        world.register_landmark("Editor's Box", editor)

        # ── Fountains (north forecourt, either side of tunnel) ──
        for fx, fy in [(_CX - 18, _FORECOURT_MID_Y - 1),
                        (_CX + 18, _FORECOURT_MID_Y - 1)]:
            fountain = create_prefab("Fountain", fx, fy)
            world.add_object(fountain)

        # ── Torches (arena perimeter — always burning, decorative) ──
        for tx, ty in [
            (_CX - _WALL_RX + 4, _CY - _WALL_RY + 8),
            (_CX + _WALL_RX - 4, _CY - _WALL_RY + 8),
            (_CX - _WALL_RX + 4, _CY + _WALL_RY - 8),
            (_CX + _WALL_RX - 4, _CY + _WALL_RY - 8),
            (_CX - _WALL_RX - 2, _CY),
            (_CX + _WALL_RX + 2, _CY),
            (_CX, _CY - _WALL_RY - 2),
            (_CX, _CY + _WALL_RY + 2),
        ]:
            world.add_object(create_prefab("Torch", tx, ty))

        # ── Water trough on the arena floor (gladiators can drink without leaving) ──
        trough = create_prefab("Fountain", _CX - 8, _CY - 6)
        trough.name = "Water Trough"
        world.add_object(trough)
        world.register_landmark("Water Trough", trough)

        # ── Decorative columns flanking the north tunnel entrance ──
        for cx in (_CX - 5, _CX + 5):
            world.add_object(create_prefab("Column", cx, _CY - _SAND_RY - 2))

    # ------------------------------------------------------------------ #
    # Agent and animal creation                                            #
    # ------------------------------------------------------------------ #

    def create_agents(self, world) -> list:
        from roma_aeterna.agent.base import Agent

        # Named characters with arena-appropriate positions
        named = [
            # Gladiators — spread across the sand floor
            Agent("Spartacus",  "Gladiator", _CX - 5,  _CY - 4),
            Agent("Crixus",     "Gladiator", _CX + 5,  _CY - 4),
            Agent("Flamma",     "Gladiator", _CX - 10, _CY + 4),
            Agent("Vercinix",   "Gladiator", _CX + 10, _CY + 4),
            Agent("Tetraites",  "Gladiator", _CX,      _CY - 8),
            # Support staff in the forecourt
            Agent("Batiatus",   "Merchant",  14,        _FORECOURT_MID_Y),
            Agent("Galen",      "Craftsman", _W - 14,   _FORECOURT_MID_Y),
        ]

        # Teach all agents about the water trough so they drink on-site
        trough_pos = (_CX - 8, _CY - 6)
        for a in named:
            a.memory.learn_location("Water Trough", trough_pos)

        agents = list(named)
        used_names = {a.name for a in agents}
        used_positions = {(int(a.x), int(a.y)) for a in agents}

        n_random = max(0, N_AGENTS - len(named))
        if n_random > 0:
            roles = list(_ROLE_WEIGHTS.keys())
            weights = list(_ROLE_WEIGHTS.values())
            for _ in range(n_random):
                role = random.choices(roles, weights=weights, k=1)[0]
                is_female = random.random() < 0.35
                name = generate_roman_name(is_female, used_names)
                x, y = find_spawn_point(world, role, used_positions, _ROLE_SPAWN_ZONES)
                agents.append(Agent(name, role, x, y))

        # Arena guards — 6 soldiers: tunnel entrances + east/west flanks
        agents.extend(self._create_arena_guards())
        return agents

    @staticmethod
    def _create_arena_guards():
        from roma_aeterna.agent.base import Agent
        guard_data = [
            # Guards deployed inside the sand floor to engage animals
            ("Gaius Carbo",    _CX - 8,  _CY - 8),   # north-west sand
            ("Lucius Capito",  _CX + 8,  _CY - 8),   # north-east sand
            ("Marcus Fuscus",  _CX - 8,  _CY + 8),   # south-west sand
            ("Publius Scaeva", _CX + 8,  _CY + 8),   # south-east sand
            ("Titus Labienus", _CX - 14, _CY),        # west sand edge
            ("Quintus Balbus", _CX + 14, _CY),        # east sand edge
        ]
        return [Agent(name, "Guard (Legionary)", x, y) for name, x, y in guard_data]

    def create_animals(self, world) -> list:
        from roma_aeterna.agent.animal import Animal
        animals = []
        # Eight wolves spread across the sand floor
        wolf_positions = [
            (_CX - 6,  _CY + 10),   # south-west
            (_CX + 6,  _CY + 10),   # south-east
            (_CX - 12, _CY - 2),    # west mid
            (_CX + 12, _CY - 2),    # east mid
            (_CX - 4,  _CY - 10),   # north-west
            (_CX + 4,  _CY - 10),   # north-east
        ]
        for i, (x, y) in enumerate(wolf_positions):
            wolf = Animal("wolf", x, y, f"Arena Wolf {i + 1}")
            # Constrain wolves to the sand floor so they don't wander out the tunnels
            wolf.home_x = float(_CX)
            wolf.home_y = float(_CY)
            wolf.home_radius = float(_SAND_RX)
            animals.append(wolf)
        # Boar — centre of the arena floor; keep it on the sand too
        boar = Animal("boar", _CX, _CY + 8, "Arena Boar 1")
        boar.home_x = float(_CX)
        boar.home_y = float(_CY)
        boar.home_radius = float(_SAND_RX)
        animals.append(boar)
        # Raven — perched above the arena; free to fly
        animals.append(Animal("raven", _CX, 3, "Raven"))
        return animals