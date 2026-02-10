import threading
import time
import math  
import random
from .weather import WeatherSystem
from .chaos import ChaosEngine
from .navigation import Pathfinder
from roma_aeterna.llm.worker import LLMWorker

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
        # 1. Perception & Environment
        weather_fx = self.weather.get_effects()
        
        # specific check: scan for "Acute Threats" (like Fire) near the agent
        # This feeds the "Input Current" of the agent's LIF brain.
        threat_score = self._count_threats(agent, radius=5)

        # 2. Update Biology & Neuro-Cognitive Model
        # Returns True ONLY if the agent's 'Urgency' crossed the threshold (The "Spike")
        did_fire = agent.update_biological(dt, weather_fx, visible_threats=threat_score)

        # 3. Handle Physics / Movement
        if agent.path:
            target = agent.path[0]
            # move_towards returns True if arrived at the target node
            if agent.move_towards(target, dt * 2.0): 
                agent.path.pop(0)
                if not agent.path:
                    agent.action = "IDLE"

        # 4. Decision Trigger (The "Action Potential")
        # If the brain fired (did_fire), we MUST act.
        # We allow interruption of movement if the urgency was high enough to fire.
        if did_fire:
            if not agent.waiting_for_llm:
                agent.waiting_for_llm = True
                self.llm_worker.queue_request(agent)

    def _count_threats(self, agent, radius=5):
        """
        Scans the local grid for danger (e.g., Burning Buildings).
        Returns a float score used to spike the agent's Urgency.
        """
        score = 0.0
        
        # Optimization: Bounds check
        min_x = max(0, int(agent.x - radius))
        max_x = min(self.world.width, int(agent.x + radius))
        min_y = max(0, int(agent.y - radius))
        max_y = min(self.world.height, int(agent.y + radius))

        for y in range(min_y, max_y):
            for x in range(min_x, max_x):
                tile = self.world.get_tile(x, y)
                if not tile or not tile.building: continue
                
                # Check for "Flammable" component that is burning
                # Note: We access the component dictionary directly for speed
                # Assuming 'Flammable' class type is the key, or we iterate values.
                # In your setup, keys are Types. We can iterate values for duck-typing.
                for comp in tile.building.components.values():
                    if getattr(comp, "is_burning", False):
                        # Inverse square law: Closer fire = MUCH higher threat
                        dist = math.sqrt((x - agent.x)**2 + (y - agent.y)**2)
                        weight = 10.0 / (dist + 0.1) 
                        score += weight
        
        return score

    def get_path(self, start, end):
        return Pathfinder.find_path(self.world, start, end)