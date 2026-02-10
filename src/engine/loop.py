import threading
import time
from .weather import WeatherSystem
from .chaos import ChaosEngine
from .navigation import Pathfinder
from src.llm.worker import LLMWorker

class SimulationEngine:
    def __init__(self, world, agents):
        self.world = world
        self.agents = agents
        self.weather = WeatherSystem()
        self.chaos = ChaosEngine(world)
        self.llm_worker = LLMWorker(self)
        self.lock = threading.Lock()
        
        # Start LLM thread
        self.llm_worker.start()

    def update(self, dt):
        with self.lock:
            # Environment
            self.weather.update()
            if random.random() < 0.05: # Optimization
                self.chaos.tick(self.weather)

            # Agents
            for agent in self.agents:
                self._update_agent(agent, dt)

    def _update_agent(self, agent, dt):
        # Biological Decay
        weather_fx = self.weather.get_effects()
        agent.update_biological(dt, weather_fx)

        # Movement
        if agent.path:
            # Move to next tile
            target = agent.path[0]
            if agent.move_towards(target, dt * 2.0): # speed
                agent.path.pop(0)
        else:
            # Decision Trigger
            if not agent.waiting_for_llm and agent.action == "IDLE":
                if random.random() < 0.01: # Don't spam LLM
                    self.llm_worker.queue_request(agent)

    def get_path(self, start, end):
        return Pathfinder.find_path(self.world, start, end)
