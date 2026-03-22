"""
Rome scenario — the full historical city of Rome c. 161 AD.

Wraps the existing WorldGenerator and preserves all original agent and
animal definitions verbatim, so nothing in the Rome simulation changes.
"""

import random

from .base import BaseScenario
from ._utils import generate_roman_name, find_spawn_point
from roma_aeterna.config import N_AGENTS


_ROLE_WEIGHTS = {
    "Plebeian":          30,
    "Merchant":          15,
    "Craftsman":         12,
    "Guard (Legionary)": 10,
    "Gladiator":          5,
    "Senator":            4,
    "Patrician":          4,
    "Priest":             3,
}

_ROLE_SPAWN_ZONES = {
    "Senator":           ["forum_floor", "via_sacra"],
    "Patrician":         ["palatine", "garden"],
    "Priest":            ["forum_floor"],
    "Gladiator":         ["sand_arena", "circus_sand"],
    "Guard (Legionary)": ["via_sacra", "road_paved", "road_cobble"],
    "Merchant":          ["forum_floor", "road_paved", "via_sacra"],
    "Craftsman":         ["road_cobble", "dirt", "building_floor"],
    "Plebeian":          ["dirt", "road_cobble", "grass", "road_paved"],
}


class RomeScenario(BaseScenario):
    name = "Rome"
    description = "Historical Rome c. 161 AD, the monumental city center"
    title_lines = [
        "ROME: AETERNA — Forum Romanum District",
        "c. 161 AD, Reign of Marcus Aurelius",
    ]

    def generate_world(self):
        from ..generator import WorldGenerator
        return WorldGenerator.generate_rome()

    def create_agents(self, world) -> list:
        from roma_aeterna.agent.base import Agent

        named = [
            Agent("Marcus Aurelius", "Senator", 100, 20),
            Agent("Gaius Petronius", "Merchant", 98, 21),
            Agent("Lucius Verus", "Senator", 100, 19),
            Agent("Spartacus", "Gladiator", 96, 22),
        ]

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

        agents.extend(self._create_legionaries())
        return agents

    @staticmethod
    def _create_legionaries():
        from roma_aeterna.agent.base import Agent
        names = [
            "Titus Pullo", "Lucius Vorenus", "Gaius Crastinus", "Marcus Petreius",
            "Quintus Balbus", "Aulus Hirtius", "Sextus Baculus", "Publius Sulla",
        ]
        soldiers = []
        for i, name in enumerate(names):
            x = 95 + (i % 4) * 2
            y = 48 + (i // 4) * 2
            soldiers.append(Agent(name, "Legionary", x, y))
        return soldiers

    def create_animals(self, world) -> list:
        from roma_aeterna.agent.animal import Animal
        animals = []
        for i, (x, y) in enumerate([(8, 60), (9, 63), (7, 67), (10, 70), (8, 74), (11, 77)]):
            animals.append(Animal("wolf", x, y, f"Wolf {i + 1}"))
        for i, (x, y) in enumerate([(55, 55), (75, 80), (120, 60), (90, 100)]):
            animals.append(Animal("dog", x, y, f"Stray Dog {i + 1}"))
        for i, (x, y) in enumerate([(160, 80), (170, 95)]):
            animals.append(Animal("boar", x, y, f"Wild Boar {i + 1}"))
        for i, (x, y) in enumerate([(100, 30), (130, 50), (80, 70)]):
            animals.append(Animal("raven", x, y, f"Raven {i + 1}"))
        return animals
