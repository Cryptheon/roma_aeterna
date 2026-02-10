import threading
from src.core.logger import SimLogger
from src.world.generator import WorldGenerator
from src.engine.loop import SimulationEngine
from src.gui.renderer import Renderer
from src.agent.base import Agent

def main():
    # 1. Init Logging
    logger = SimLogger()
    logger.log_event("SYSTEM", "Initializing Rome: Aeterna...")

    # 2. Generate World
    rome_map = WorldGenerator.generate_rome()
    logger.log_event("WORLD", f"Map Generated: {rome_map.width}x{rome_map.height}")

    # 3. Create Agents
    agents = []
    # Place Marcus in the center (Forum)
    cx, cy = rome_map.width // 2, rome_map.height // 2
    
    marcus = Agent("Marcus Aurelius", "Senator", cx, cy)
    marcus.inventory.append("Stylus")
    agents.append(marcus)

    # Place Plebeians
    for i in range(5):
        agents.append(Agent(f"Plebeian {i+1}", "Plebeian", cx + i + 2, cy + 2))

    # 4. Initialize Simulation Engine
    engine = SimulationEngine(rome_map, agents)

    # 5. Start GUI (Main Thread)
    # The Renderer will tick the engine to keep visuals synced with logic
    renderer = Renderer(engine)
    renderer.run()

if __name__ == "__main__":
    main()
