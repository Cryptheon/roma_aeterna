import random
from src.world.components import Flammable, Structural

class ChaosEngine:
    def __init__(self, world):
        self.world = world

    def tick(self, weather):
        # Chaos ticks occasionally
        for obj in self.world.objects:
            self._handle_fire(obj, weather)
            self._handle_structure(obj, weather)

    def _handle_fire(self, obj, weather):
        flam = obj.get_component(Flammable)
        if flam and flam.is_burning:
            flam.fuel -= flam.burn_rate
            
            # Damage Structure
            struct = obj.get_component(Structural)
            if struct: struct.hp -= 2.0
            
            # Spread
            if random.random() < 0.1 * weather.wind_speed:
                self._spread_fire(obj)
            
            if flam.fuel <= 0:
                flam.is_burning = False # Burnt out

    def _spread_fire(self, source):
        # Find neighbors
        # Simplified: Just grab random nearby object
        pass

    def _handle_structure(self, obj, weather):
        struct = obj.get_component(Structural)
        if struct and struct.hp <= 0:
            # Collapse logic would remove building and add rubble here
            pass
