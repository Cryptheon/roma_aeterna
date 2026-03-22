"""
Gladiator Fight scenario — Vandal Barbarians vs Roman Legionaries in the arena.

Reuses the Colosseum map from GladiatorArenaScenario verbatim.
Two sides face off on the sand floor:
  - West half: Vandal warriors (dark leather)
  - East half: Roman Legionaries (red)

Named combatants are placed symmetrically. Genseric leads the Vandals;
Titus Pullo leads the Romans. Support staff (physician, editor) sit in the
forecourt as in the base arena scenario.
"""

import random

from .base import BaseScenario
from .arena import GladiatorArenaScenario, _CX, _CY, _SAND_RX, _SAND_RY, _FORECOURT_MID_Y, _W
from roma_aeterna.config import RANDOM_SEED

# ── Named combatants ─────────────────────────────────────────────────────────

_VANDAL_FIGHTERS = [
    # (name, dx, dy from arena centre)
    ("Genseric",        -10,  0),   # chieftain — centre-west
    ("Huneric",          -7, -6),   # north-west flank
    ("Thrasamund",      -13,  4),   # deep west
    ("Godomar",          -5,  8),   # south-west
    ("Ragnachar",       -15, -2),   # far west edge
    ("Hilderic",         -8,  5),   # mid-west cluster
    ("Alaric",          -12, -5),   # north-west edge
    ("Radagaisus",       -3,  9),   # south centre-west
]

_ROMAN_FIGHTERS = [
    # (name, dx, dy from arena centre)
    ("Titus Pullo",      10,  0),   # centurion — centre-east
    ("Lucius Vorenus",    7, -6),   # north-east flank
    ("Gaius Crastinus",  13,  4),   # deep east
    ("Marcus Petreius",   5,  8),   # south-east
    ("Sextus Baculus",   15, -2),   # far east edge
    ("Aulus Hirtius",     8,  5),   # mid-east cluster
    ("Publius Sulla",    12, -5),   # north-east edge
    ("Quintus Galba",     3,  9),   # south centre-east
]

_CONTEXT_VANDAL = (
    "You are a Vandal warrior fighting in the Roman Colosseum. "
    "The Romans on the east side of the arena are your enemies. "
    "Fight them, attack them, prove your strength. "
    "Your chieftain Genseric leads you. Glory comes through combat."
)

_CONTEXT_ROMAN = (
    "You are a Roman Legionary fighting in the Colosseum arena. "
    "Vandal barbarians on the west side are your enemy. "
    "Hold the line, attack the Vandals, defend Rome's honour. "
    "Centurion Titus Pullo commands your side."
)


class GladiatorFightScenario(GladiatorArenaScenario):
    """Vandals vs Legionaries — inherits the arena map wholesale."""

    name = "gladiator_fight"
    description = "Colosseum arena: Vandal barbarians vs Roman legionaries."
    title_lines = [
        "GLADIATOR FIGHT",
        "Vandals vs Legionaries — Colosseum Arena",
        "Ave Caesar — morituri te salutant",
    ]

    # generate_world() is inherited unchanged from GladiatorArenaScenario

    def create_agents(self, world) -> list:
        from roma_aeterna.agent.base import Agent

        agents = []

        # ── Vandal side (west half of sand) ───────────────────────────────────
        for name, dx, dy in _VANDAL_FIGHTERS:
            a = Agent(name, "Vandal", _CX + dx, _CY + dy)
            a.memory.add_event(_CONTEXT_VANDAL, tick=0, importance=6.0,
                               memory_type="observation", tags=["context", "war"])
            agents.append(a)

        # ── Roman side (east half of sand) ────────────────────────────────────
        for name, dx, dy in _ROMAN_FIGHTERS:
            a = Agent(name, "Legionary", _CX + dx, _CY + dy)
            a.memory.add_event(_CONTEXT_ROMAN, tick=0, importance=6.0,
                               memory_type="observation", tags=["context", "war"])
            agents.append(a)

        # ── Support staff in the forecourt ────────────────────────────────────
        from roma_aeterna.agent.base import Agent as _A
        agents.append(_A("Batiatus",  "Merchant",  14,        _FORECOURT_MID_Y))
        agents.append(_A("Galen",     "Craftsman", _W - 14,   _FORECOURT_MID_Y))

        # Teach everyone about the water trough (same position as base arena)
        trough_pos = (_CX - 8, _CY - 6)
        for a in agents:
            a.memory.learn_location("Water Trough", trough_pos)

        return agents

    def create_animals(self, world) -> list:
        from roma_aeterna.agent.animal import Animal

        animals = []

        # Wolves released onto the sand floor — constrained to the arena
        wolf_positions = [
            (_CX,      _CY),       # dead centre
            (_CX - 4,  _CY - 7),   # north-west
            (_CX + 4,  _CY - 7),   # north-east
            (_CX - 4,  _CY + 7),   # south-west
            (_CX + 4,  _CY + 7),   # south-east
            (_CX - 12, _CY),       # far west (Vandal side)
            (_CX + 12, _CY),       # far east (Roman side)
        ]
        for i, (x, y) in enumerate(wolf_positions):
            wolf = Animal("wolf", x, y, f"Arena Wolf {i + 1}")
            wolf.home_x = float(_CX)
            wolf.home_y = float(_CY)
            wolf.home_radius = float(_SAND_RX)
            animals.append(wolf)

        # Ravens circling above
        animals.append(Animal("raven", _CX - 2, 3, "Raven"))
        animals.append(Animal("raven", _CX + 2, 3, "Raven"))

        return animals
