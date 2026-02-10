import uuid
import math
from .memory import Memory
from src.core.logger import SimLogger

class Agent:
    def __init__(self, name, role, x, y):
        self.uid = str(uuid.uuid4())[:8]
        self.name = name
        self.role = role
        self.x = x
        self.y = y
        self.path = []
        self.inventory = []
        
        # Stats
        self.health = 100.0
        self.energy = 100.0
        self.hunger = 0.0
        
        self.action = "IDLE"
        self.waiting_for_llm = False
        self.memory = Memory()

    def update_biological(self, dt, weather_fx):
        drain = 0.5 * dt
        if "energy_drain" in weather_fx: drain *= weather_fx["energy_drain"]
        
        self.energy -= drain
        self.hunger += 0.2 * dt

    def move_towards(self, target_tuple, speed):
        # Physics interpolation
        tx, ty = target_tuple
        dx, dy = tx - self.x, ty - self.y
        dist = math.sqrt(dx*dx + dy*dy)
        
        if dist < speed:
            self.x, self.y = float(tx), float(ty)
            return True # Arrived at node
        
        self.x += (dx/dist) * speed
        self.y += (dy/dist) * speed
        return False

    def get_inspection_data(self):
        return [
            f"Name: {self.name}",
            f"Role: {self.role}",
            f"Health: {int(self.health)} | Hunger: {int(self.hunger)}",
            f"Action: {self.action}",
            f"Inv: {', '.join(self.inventory)}"
        ]
