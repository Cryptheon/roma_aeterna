"""
Rome: Aeterna — Entry Point

Starts the simulation engine, loads any existing save, and runs the
renderer loop. On exit (ESC or window close), saves the game state.
"""

import sys
import random
import threading
from roma_aeterna.tools.agent_diagnostics import AgentDiagnostics
from roma_aeterna.tools.agent_logger import AgentLogger

from roma_aeterna.world.generator import WorldGenerator
from roma_aeterna.agent.base import Agent
from roma_aeterna.engine.loop import SimulationEngine
from roma_aeterna.gui.renderer import Renderer
from roma_aeterna.core.persistence import has_save, delete_save
from roma_aeterna.config import N_AGENTS, GRID_WIDTH, GRID_HEIGHT


# ============================================================
# Roman Name Generator
# ============================================================

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

ROLE_WEIGHTS = {
    "Plebeian":         30,
    "Merchant":         15,
    "Craftsman":        12,
    "Guard (Legionary)": 10,
    "Gladiator":         5,
    "Senator":           4,
    "Patrician":         4,
    "Priest":            3,
}

ROLE_SPAWN_ZONES = {
    "Senator":          ["forum_floor", "via_sacra"],
    "Patrician":        ["palatine", "garden"],
    "Priest":           ["forum_floor"],
    "Gladiator":        ["sand_arena", "circus_sand"],
    "Guard (Legionary)":["via_sacra", "road_paved", "road_cobble"],
    "Merchant":         ["forum_floor", "road_paved", "via_sacra"],
    "Craftsman":        ["road_cobble", "dirt", "building_floor"],
    "Plebeian":         ["dirt", "road_cobble", "grass", "road_paved"],
}


def _generate_roman_name(is_female: bool, used_names: set) -> str:
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
    name = f"{random.choice(MALE_PRAENOMINA)} {random.randint(1, 999)}"
    used_names.add(name)
    return name


def _find_spawn_point(world, role: str, used_positions: set) -> tuple:
    preferred = ROLE_SPAWN_ZONES.get(role, ["dirt", "road_cobble"])

    for _ in range(100):
        x = random.randint(5, GRID_WIDTH - 5)
        y = random.randint(5, GRID_HEIGHT - 5)
        if (x, y) in used_positions:
            continue
        tile = world.get_tile(x, y)
        if tile and tile.is_walkable and tile.terrain_type in preferred:
            used_positions.add((x, y))
            return (x, y)

    for _ in range(200):
        x = random.randint(5, GRID_WIDTH - 5)
        y = random.randint(5, GRID_HEIGHT - 5)
        if (x, y) in used_positions:
            continue
        tile = world.get_tile(x, y)
        if tile and tile.is_walkable and tile.building is None:
            used_positions.add((x, y))
            return (x, y)

    return (random.randint(20, GRID_WIDTH - 20), random.randint(20, GRID_HEIGHT - 20))


def create_agents(world=None):
    """Spawn hand-placed named characters, then fill to N_AGENTS with random citizens."""
    named = [
        Agent("Marcus Aurelius", "Senator", 100, 20),
        Agent("Gaius Petronius", "Merchant", 98, 21),
        # Agent("Lucius Verus", "Senator", 75, 58),
        # Agent("Spartacus", "Gladiator", 148, 96),
        # Agent("Maximus", "Gladiator", 150, 98),
        # Agent("Quintus", "Guard (Legionary)", 140, 90),
        # Agent("Publius", "Plebeian", 65, 35),
        # Agent("Claudia", "Merchant", 78, 40),
        # Agent("Servius", "Craftsman", 85, 32),
        # Agent("Cornelia", "Patrician", 50, 88),
        # Agent("Tiberius", "Guard (Legionary)", 55, 85),
        # Agent("Flavia", "Priest", 135, 30),
        # Agent("Decimus", "Merchant", 145, 42),
    ]

    agents = list(named)
    used_names = {a.name for a in agents}
    used_positions = {(a.x, a.y) for a in agents}

    n_random = max(0, N_AGENTS - len(agents))
    if n_random > 0 and world is not None:
        print(f"  Generating {n_random} random citizens...")
        roles = list(ROLE_WEIGHTS.keys())
        weights = list(ROLE_WEIGHTS.values())
        for _ in range(n_random):
            role = random.choices(roles, weights=weights, k=1)[0]
            is_female = random.random() < 0.35
            name = _generate_roman_name(is_female, used_names)
            x, y = _find_spawn_point(world, role, used_positions)
            agents.append(Agent(name, role, x, y))

    return agents


def main():
    print("=" * 50)
    print("  ROME: AETERNA — Forum Romanum District")
    print("  c. 161 AD, Reign of Marcus Aurelius")
    print("=" * 50)
    print()

    new_game = "--new-game" in sys.argv
    if new_game and has_save():
        print("  --new-game flag detected. Deleting existing save.")
        delete_save()

    if has_save() and not new_game:
        print("  Save file found. Will resume previous session.")
    else:
        print("  Starting new simulation.")

    print()
    print("Generating world...")

    world = WorldGenerator.generate_rome()

    print(f"  Map: {world.width}x{world.height} tiles")
    print(f"  Objects: {len(world.objects)}")
    print(f"  Landmarks: {list(world.landmarks.keys())}")

    agents = create_agents(world)
    print(f"  Citizens: {len(agents)} ({N_AGENTS} configured)")

    from collections import Counter
    role_counts = Counter(a.role for a in agents)
    for role, count in sorted(role_counts.items(), key=lambda x: -x[1]):
        print(f"    {role}: {count}")

    print()
    print("Starting simulation...")
    print("Controls: WASD=Pan, Scroll=Zoom, Right-click=Inspect, ESC=Quit")
    print("Diagnostics: printing to terminal every 10 seconds")
    print()

    engine = SimulationEngine(world, agents)
    renderer = Renderer(engine)

    # Background logger — writes ALL LLM I/O and state to disk
    logger = AgentLogger(engine, path="logs/session.jsonl", snapshot_interval=15.0)
    logger.start()

    # Background diagnostics — prints summary to terminal
    diag = AgentDiagnostics(engine)
    diag_thread = threading.Thread(target=diag.watch, args=(10,), daemon=True)
    diag_thread.start()

    try:
        renderer.run()
    except KeyboardInterrupt:
        print("\n[MAIN] Interrupted.")
    finally:
        logger.stop()
        print(diag.dump_all())
        diag.export_json("session_debug.json")
        engine.shutdown()


if __name__ == "__main__":
    main()
