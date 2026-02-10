import random
from src.world.components import Flammable, Structural

class ChaosEngine:
    def __init__(self, world):
        self.world = world

    def tick(self, weather):
        # Create a snapshot of objects to avoid modification during iteration issues
        objects = list(self.world.objects)
        
        for obj in objects:
            self._handle_fire(obj, weather)
            self._handle_structure(obj, weather)

    def _handle_fire(self, obj, weather):
        flam = obj.get_component(Flammable)
        if flam and flam.is_burning:
            # Apply burn rate modified by wind
            burn_mult = 1.0 + (weather.wind_speed * 0.2)
            flam.fuel -= flam.burn_rate * burn_mult
            
            # Damage Structure
            struct = obj.get_component(Structural)
            if struct: 
                struct.hp -= 2.0 * burn_mult
            
            # Spread Fire
            # higher wind = higher spread chance
            spread_chance = 0.05 + (0.05 * weather.wind_speed)
            if "fire_spread" in weather.get_effects():
                spread_chance *= 2.0

            if random.random() < spread_chance:
                self._spread_fire(obj)
            
            # Extinguish if fuel out
            if flam.fuel <= 0:
                flam.is_burning = False 

    def _spread_fire(self, source):
        # Get neighbors in the world grid
        # We need to find objects at coordinates (source.x +/- 1, source.y +/- 1)
        # This is an O(N) lookup which is slow. Better to ask the map tile.
        
        tile = self.world.get_tile(source.x, source.y)
        if not tile: return

        # Check adjacent tiles for buildings
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                if dx == 0 and dy == 0: continue
                
                neighbor_tile = self.world.get_tile(source.x + dx, source.y + dy)
                if neighbor_tile and neighbor_tile.building:
                    target = neighbor_tile.building
                    flam = target.get_component(Flammable)
                    # Ignite if flammable and not already burning
                    if flam and not flam.is_burning:
                        flam.is_burning = True
                        flam.fire_intensity = 10.0

    def _handle_structure(self, obj, weather):
        struct = obj.get_component(Structural)
        if struct and struct.hp <= 0:
            # Collapse logic: Transform to rubble
            tile = self.world.get_tile(obj.x, obj.y)
            if tile:
                tile.building = None
                tile.terrain_type = "mountain" # Rough approximation of rubble
                tile.movement_cost = 10.0
                tile.effects.append('rubble')
            
            # Remove object from world list safely
            if obj in self.world.objects:
                self.world.objects.remove(obj)