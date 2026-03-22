"""
Rome: Aeterna — Entry Point

Starts the simulation engine, loads any existing save, and runs the
renderer loop. On exit (ESC or window close), saves the game state.

The active scenario is selected via SCENARIO in config.py.
"""

import sys
import threading
from collections import Counter

from roma_aeterna.tools.agent_diagnostics import AgentDiagnostics
from roma_aeterna.tools.agent_logger import AgentLogger

from roma_aeterna.world.scenarios import get_scenario
from roma_aeterna.engine.loop import SimulationEngine
from roma_aeterna.gui.renderer import Renderer
from roma_aeterna.core.persistence import has_save, delete_save
from roma_aeterna.config import SCENARIO


def main():
    scenario = get_scenario(SCENARIO)

    print("=" * 50)
    for line in scenario.title_lines:
        print(f"  {line}")
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
    print(f"Generating world (scenario: {SCENARIO})...")

    world = scenario.generate_world()

    print(f"  Map: {world.width}x{world.height} tiles")
    print(f"  Objects: {len(world.objects)}")
    print(f"  Landmarks: {list(world.landmarks.keys())}")

    human_agents = scenario.create_agents(world)
    animals = scenario.create_animals(world)

    print(f"  Citizens: {len(human_agents)}")
    role_counts = Counter(
        a.role for a in human_agents
        if not getattr(a, "is_animal", False)
    )
    for role, count in sorted(role_counts.items(), key=lambda x: -x[1]):
        print(f"    {role}: {count}")

    animal_counts = Counter(getattr(a, "animal_type", "unknown") for a in animals)
    animal_summary = ", ".join(f"{c} {t}s" for t, c in sorted(animal_counts.items()))
    print(f"  Animals: {len(animals)}" + (f" ({animal_summary})" if animal_summary else ""))

    print()
    print("Starting simulation...")
    print("Controls: WASD=Pan, Scroll=Zoom, Right-click=Inspect, ESC=Quit")
    print("Diagnostics: printing to terminal every 10 seconds")
    print()

    engine = SimulationEngine(world, human_agents + animals)
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
