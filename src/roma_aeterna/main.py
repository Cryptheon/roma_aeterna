import threading
from .core.logger import SimLogger
from .world.generator import WorldGenerator
from .engine.loop import SimulationEngine
from .gui.renderer import Renderer
from .agent.base import Agent
from .config import GRID_WIDTH, GRID_HEIGHT

def main():
    logger = SimLogger()
    logger.log_event("SYSTEM", "Initializing Rome: Aeterna v2.0...")

    # 1. Generate The Geometric City
    rome_map = WorldGenerator.generate_rome()
    logger.log_event("WORLD", f"City Built: {rome_map.width}x{rome_map.height}")

    # 2. Create Diverse Population
    agents = []
    cx, cy = GRID_WIDTH // 2, GRID_HEIGHT // 2
    
    # Senators in the Forum (Purple Squares)
    agents.append(Agent("Marcus Aurelius", "Senator", cx, cy))
    agents.append(Agent("Cicero", "Senator", cx+1, cy-1))

    # Legionaries guarding the Colosseum (Red Squares)
    col_x = cx + 25
    agents.append(Agent("Titus", "Legionary", col_x-5, cy))
    agents.append(Agent("Maximus", "Legionary", col_x+5, cy))

    # Merchants in the Market/Forum (Gold Squares)
    agents.append(Agent("Hermes", "Merchant", cx-5, cy+2))

    # Plebeians in the Subura (Grey Squares)
    for i in range(10):
        # Scatter them in the NE quadrant (Subura)
        px = cx + 5 + (i * 2)
        py = 10 + i
        agents.append(Agent(f"Plebeian {i+1}", "Plebeian", px, py))

    # 3. Initialize Engine
    engine = SimulationEngine(rome_map, agents)

    # 4. Start Render
    renderer = Renderer(engine)
    renderer.run()

if __name__ == "__main__":
    main()