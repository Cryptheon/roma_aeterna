"""
Rome: Aeterna — Entry Point

Starts the simulation engine, loads any existing save, and runs the
renderer loop. On exit (ESC or window close), saves the game state.
"""

import sys
import threading
from roma_aeterna.tools.agent_diagnostics import AgentDiagnostics

from roma_aeterna.world.generator import WorldGenerator
from roma_aeterna.agent.base import Agent
from roma_aeterna.engine.loop import SimulationEngine
from roma_aeterna.gui.renderer import Renderer
from roma_aeterna.core.persistence import has_save, delete_save


def create_agents():
    """Spawn initial population in historically appropriate locations."""
    agents = [
        # Forum Romanum area
        Agent("Marcus Aurelius", "Senator", 70, 60),
        Agent("Gaius Petronius", "Merchant", 82, 62),
        Agent("Lucius Verus", "Senator", 75, 58),

        # Near the Colosseum
        Agent("Spartacus", "Gladiator", 148, 96),
        Agent("Maximus", "Gladiator", 150, 98),
        Agent("Quintus", "Guard (Legionary)", 140, 90),

        # Subura district
        Agent("Publius", "Plebeian", 65, 35),
        Agent("Claudia", "Merchant", 78, 40),
        Agent("Servius", "Craftsman", 85, 32),

        # Palatine Hill
        Agent("Cornelia", "Patrician", 50, 88),
        Agent("Tiberius", "Guard (Legionary)", 55, 85),

        # Esquiline
        Agent("Flavia", "Priest", 135, 30),
        Agent("Decimus", "Merchant", 145, 42),
    ]
    return agents


def main():
    print("=" * 50)
    print("  ROME: AETERNA — Forum Romanum District")
    print("  c. 161 AD, Reign of Marcus Aurelius")
    print("=" * 50)
    print()

    # Check for --new-game flag
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

    agents = create_agents()
    print(f"  Citizens: {len(agents)}")

    print()
    print("Starting simulation...")
    print("Controls: WASD=Pan, Scroll=Zoom, Hover=Inspect, ESC=Quit")
    print()

    engine = SimulationEngine(world, agents)
    renderer = Renderer(engine)

    # Run diagnostics in a background thread
    diag = AgentDiagnostics(engine)
    diag_thread = threading.Thread(target=diag.watch, args=(10,), daemon=True)
    diag_thread.start()

    try:
        renderer.run()
    except KeyboardInterrupt:
        print("\n[MAIN] Interrupted.")
    finally:
        engine.shutdown()


if __name__ == "__main__":
    main()
