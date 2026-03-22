"""
Shared utilities for scenario agent spawning.

Both RomeScenario and GladiatorArenaScenario use these helpers to find
walkable spawn tiles and generate Roman names for random citizens.
"""

import random

# ── Roman name pools ─────────────────────────────────────────────────────────

MALE_PRAENOMINA = [
    "Gaius", "Lucius", "Marcus", "Publius", "Quintus", "Titus",
    "Aulus", "Decimus", "Gnaeus", "Spurius", "Manius", "Servius",
    "Appius", "Numerius", "Vibius", "Sextus", "Kaeso", "Postumus",
]

FEMALE_PRAENOMINA = [
    "Julia", "Claudia", "Cornelia", "Livia", "Valeria", "Aurelia",
    "Flavia", "Caecilia", "Aemilia", "Sulpicia", "Pompeia", "Tullia",
    "Antonia", "Domitia", "Fabia", "Lucretia", "Sempronia", "Terentia",
]

NOMINA = [
    "Cornelius", "Julius", "Claudius", "Valerius", "Fabius",
    "Aemilius", "Sempronius", "Licinius", "Cassius", "Sulpicius",
    "Servilius", "Tullius", "Octavius", "Horatius", "Petronius",
    "Flavius", "Domitius", "Antonius", "Calpurnius", "Marcius",
    "Pompeius", "Junius", "Manlius", "Postumius", "Volumnius",
    "Aquilius", "Atilius", "Rutilius", "Papirius", "Furius",
]

COGNOMINA = [
    "Rufus", "Niger", "Crassus", "Longus", "Maximus", "Magnus",
    "Brutus", "Scaevola", "Pulcher", "Naso", "Cursor", "Corvus",
    "Laenas", "Balbus", "Priscus", "Severus", "Calvus", "Gallus",
    "Flaccus", "Lepidus", "Piso", "Scipio", "Cato", "Gracchus",
    "Sulla", "Nerva", "Firmus", "Macer", "Paullus", "Regulus",
]


def generate_roman_name(is_female: bool, used_names: set) -> str:
    """Generate a unique Roman name not already in *used_names*."""
    for _ in range(50):
        if is_female:
            name = f"{random.choice(FEMALE_PRAENOMINA)} {random.choice(COGNOMINA)}"
        else:
            praenomen = random.choice(MALE_PRAENOMINA)
            nomen = random.choice(NOMINA)
            if random.random() < 0.5:
                name = f"{praenomen} {nomen} {random.choice(COGNOMINA)}"
            else:
                name = f"{praenomen} {nomen}"
        if name not in used_names:
            used_names.add(name)
            return name
    # Fallback: numbered name (never collides)
    name = f"{random.choice(MALE_PRAENOMINA)} {random.randint(1, 999)}"
    used_names.add(name)
    return name


def find_spawn_point(world, role: str, used_positions: set,
                     role_spawn_zones: dict) -> tuple:
    """Return (x, y) for a new agent.

    Tries terrain types preferred by the role first; falls back to any
    walkable unoccupied tile.  Uses *world.width/height* so it works for
    any map size.
    """
    preferred = role_spawn_zones.get(role, ["dirt", "road_cobble"])

    for _ in range(100):
        x = random.randint(5, world.width - 5)
        y = random.randint(5, world.height - 5)
        if (x, y) in used_positions:
            continue
        tile = world.get_tile(x, y)
        if tile and tile.is_walkable and tile.terrain_type in preferred:
            used_positions.add((x, y))
            return (x, y)

    for _ in range(200):
        x = random.randint(5, world.width - 5)
        y = random.randint(5, world.height - 5)
        if (x, y) in used_positions:
            continue
        tile = world.get_tile(x, y)
        if tile and tile.is_walkable and tile.building is None:
            used_positions.add((x, y))
            return (x, y)

    return (random.randint(20, world.width - 20), random.randint(20, world.height - 20))
