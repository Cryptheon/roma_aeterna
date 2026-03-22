"""
Sack of Rome scenario — 455 AD, the Vandal siege.

Uses the full Rome map but cameras into the Forum Romanum district
where the fighting is fiercest.  Vandal warbands pour through the streets
looting temples and markets while Roman legionaries and guards try to hold
the line.

Named vandals are placed in and around the Forum Romanum.
Named Roman defenders anchor key positions (Curia, Basilica, Rostra).
A small wave of random vandals and defending citizens fills out the crowds.
"""

import random

from .base import BaseScenario
from ._utils import generate_roman_name, find_spawn_point
from roma_aeterna.config import N_AGENTS, RANDOM_SEED

# ── Forum Romanum bounding box (from generator.py) ───────────────────────────
# world.fill_rect(50, 48, 130, 65, "forum_floor", …)
_FX1, _FY1 = 50, 48    # west/north edge of forum floor
_FX2, _FY2 = 130, 65   # east/south edge of forum floor
_FCX = (_FX1 + _FX2) // 2   # 90
_FCY = (_FY1 + _FY2) // 2   # 56

# Spawn clusters — vandals come from the north and east, defenders hold south/west
_VANDAL_SPAWN = [
    # Warband 1: north of forum, flooding down from the Subura
    (_FCX - 10, _FY1 - 4), (_FCX - 5, _FY1 - 6), (_FCX,     _FY1 - 5),
    (_FCX + 5,  _FY1 - 4), (_FCX + 10, _FY1 - 3),
    # Warband 2: east flank near the Arch of Titus
    (_FX2 + 5, _FCY - 4), (_FX2 + 8, _FCY), (_FX2 + 6, _FCY + 4),
    (_FX2 + 3, _FY2 - 2), (_FX2 + 9, _FY2),
    # Warband 3: already inside the forum (chaos is total)
    (_FCX - 8, _FCY - 2), (_FCX + 3, _FCY + 3), (_FCX - 3, _FCY + 5),
    (_FCX + 12, _FCY - 3), (_FCX - 12, _FCY + 2),
]

_DEFENDER_SPAWN = [
    # Legionaries holding the Rostra / west end
    (_FX1 + 4, _FCY - 2), (_FX1 + 6, _FCY), (_FX1 + 4, _FCY + 2),
    # Guards at the Curia (NW corner of forum)
    (_FX1 + 2, _FY1 + 3), (_FX1 + 5, _FY1 + 2),
    # Guards holding Basilica Julia (south side)
    (_FCX - 5, _FY2 - 2), (_FCX, _FY2 - 1), (_FCX + 5, _FY2 - 2),
    # A small reserve east of centre
    (_FCX + 8, _FCY - 5), (_FCX + 8, _FCY + 5),
]


# ── Named historical figures ──────────────────────────────────────────────────

_VANDAL_NAMES = [
    ("Genseric",         0),   # king — index into _VANDAL_SPAWN
    ("Huneric",          1),   # Genseric's son
    ("Geiseric's Thane", 2),
    ("Radagaisus",       5),   # another warband leader
    ("Alaric the Bold",  8),
]

_DEFENDER_NAMES = [
    ("Petronius Maximus", 0),   # emperor, cornered
    ("Aetius Calvus",     1),   # general
    ("Flavius Rufus",     2),   # tribune
    ("Gaius Lentulus",    3),   # centurion at Curia
    ("Marcus Regulus",    6),   # guard at Basilica
]

_CONTEXT_VANDAL = (
    "It is 455 AD. You are a Vandal warrior who has broken into Rome. "
    "The city is yours to plunder. Loot gold, attack any Roman who resists, "
    "take trophies from their temples. Your king Genseric has ordered: leave no "
    "treasure behind. Attack and loot anything of value."
)
_CONTEXT_DEFENDER = (
    "It is 455 AD. Vandal barbarians have breached the walls and are ransacking "
    "the Forum Romanum. You must defend Roman citizens and push the invaders back. "
    "Attack any Vandal you see. Protect the Curia, the temples, and the people."
)


class SackOfRomeScenario(BaseScenario):
    name = "sack_of_rome"
    description = "455 AD — Vandal warbands loot the Forum Romanum while Roman defenders fight back."
    title_lines = [
        "THE SACK OF ROME",
        "455 AD — The Vandal Storm",
        "Forum Romanum — defend or plunder",
    ]

    def generate_world(self):
        from ..generator import WorldGenerator
        world = WorldGenerator.generate_rome()
        # Keep camera focused on the Forum Romanum
        world.camera_start = (_FCX, _FCY)
        return world

    def create_agents(self, world) -> list:
        from roma_aeterna.agent.base import Agent
        from roma_aeterna.world.items import ITEM_DB

        agents = []
        used_names: set = set()
        used_positions: set = set()

        # ── Named vandal leaders ──────────────────────────────────────────────
        for name, spawn_idx in _VANDAL_NAMES:
            x, y = _VANDAL_SPAWN[spawn_idx]
            a = Agent(name, "Vandal", x, y)
            a.memory.add_event(_CONTEXT_VANDAL, tick=0, importance=6.0,
                               memory_type="observation", tags=["context", "war"])
            agents.append(a)
            used_names.add(name)
            used_positions.add((int(x), int(y)))

        # ── Named Roman defenders ─────────────────────────────────────────────
        for name, spawn_idx in _DEFENDER_NAMES:
            x, y = _DEFENDER_SPAWN[spawn_idx]
            a = Agent(name, "Legionary", x, y)
            a.memory.add_event(_CONTEXT_DEFENDER, tick=0, importance=6.0,
                               memory_type="observation", tags=["context", "war"])
            agents.append(a)
            used_names.add(name)
            used_positions.add((int(x), int(y)))

        # ── Random vandal warriors (fill remaining _VANDAL_SPAWN slots) ───────
        rng = random.Random(RANDOM_SEED)
        named_vandal_indices = {idx for _, idx in _VANDAL_NAMES}
        for idx, (x, y) in enumerate(_VANDAL_SPAWN):
            if idx in named_vandal_indices:
                continue
            if (int(x), int(y)) in used_positions:
                continue
            vname = f"Vandal {rng.randint(100, 999)}"
            a = Agent(vname, "Vandal", x, y)
            a.memory.add_event(_CONTEXT_VANDAL, tick=0, importance=6.0,
                               memory_type="observation", tags=["context", "war"])
            agents.append(a)
            used_names.add(vname)
            used_positions.add((int(x), int(y)))

        # ── Random Roman defenders ────────────────────────────────────────────
        named_def_indices = {idx for _, idx in _DEFENDER_NAMES}
        for idx, (x, y) in enumerate(_DEFENDER_SPAWN):
            if idx in named_def_indices:
                continue
            if (int(x), int(y)) in used_positions:
                continue
            dname = generate_roman_name(False, used_names)
            role = rng.choice(["Legionary", "Guard (Legionary)"])
            a = Agent(dname, role, x, y)
            a.memory.add_event(_CONTEXT_DEFENDER, tick=0, importance=6.0,
                               memory_type="observation", tags=["context", "war"])
            agents.append(a)
            used_names.add(dname)
            used_positions.add((int(x), int(y)))

        # ── Extra random agents from config N_AGENTS top-up ──────────────────
        _SACK_ROLE_WEIGHTS = {
            "Vandal":            55,
            "Legionary":         25,
            "Guard (Legionary)": 20,
        }
        _SACK_SPAWN_ZONES = {
            "Vandal":            ["forum_floor", "via_sacra", "road_paved"],
            "Legionary":         ["forum_floor", "via_sacra"],
            "Guard (Legionary)": ["forum_floor", "road_paved"],
        }
        n_extra = max(0, N_AGENTS - len(agents))
        roles = list(_SACK_ROLE_WEIGHTS.keys())
        weights = list(_SACK_ROLE_WEIGHTS.values())
        for _ in range(n_extra):
            role = rng.choices(roles, weights=weights, k=1)[0]
            name = (f"Vandal {rng.randint(100,999)}" if role == "Vandal"
                    else generate_roman_name(False, used_names))
            x, y = find_spawn_point(world, role, used_positions, _SACK_SPAWN_ZONES)
            a = Agent(name, role, x, y)
            ctx = _CONTEXT_VANDAL if role == "Vandal" else _CONTEXT_DEFENDER
            a.memory.add_event(ctx, tick=0, importance=6.0,
                               memory_type="observation", tags=["context", "war"])
            agents.append(a)
            used_names.add(name)

        return agents

    def create_animals(self, world) -> list:
        # A few ravens circling above the carnage — no wolves or boars
        from roma_aeterna.agent.animal import Animal
        return [
            Animal("raven", _FCX - 5, _FY1 - 8, "Raven"),
            Animal("raven", _FCX + 5, _FY1 - 8, "Raven"),
        ]
