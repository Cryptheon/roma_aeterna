import random
import noise
import math
from .map import GameMap, Tile
from .objects import create_prefab
from ..config import GRID_WIDTH, GRID_HEIGHT, RANDOM_SEED

class WorldGenerator:
    @staticmethod
    def generate_rome() -> GameMap:
        world = GameMap(GRID_WIDTH, GRID_HEIGHT)
        
        # 1. Terrain (Noise)
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                scale = 0.05
                elev = noise.pnoise2(x*scale, y*scale, base=RANDOM_SEED, octaves=4)
                
                t_type = "grass"
                cost = 2.0
                walkable = True
                
                if elev < -0.3:
                    t_type = "water"
                    cost = 999.0
                    walkable = False
                elif elev > 0.4:
                    t_type = "mountain"
                    cost = 8.0
                    walkable = False
                elif elev > 0.15:
                    t_type = "forest"
                    cost = 4.0

                world.tiles[y][x] = Tile(x, y, t_type, cost, walkable, effects=[])

        # 2. Roads (Random Walkers from Center)
        cx, cy = GRID_WIDTH // 2, GRID_HEIGHT // 2
        for _ in range(6):
            WorldGenerator._carve_road(world, cx, cy, random.randint(0, 360), 60)

        # 3. Buildings
        for _ in range(50):
            rx, ry = random.randint(5, GRID_WIDTH-5), random.randint(5, GRID_HEIGHT-5)
            tile = world.get_tile(rx, ry)
            # Place buildings on grass near roads
            if tile and tile.terrain_type == "grass":
                neighbors = WorldGenerator._get_neighbors(world, rx, ry)
                if any(n.terrain_type == "road" for n in neighbors):
                    b_type = random.choice(["Insula", "Temple", "Insula"])
                    obj = create_prefab(b_type, rx, ry)
                    world.add_object(obj)
                    tile.movement_cost = 5.0 # Walkable but inside building is slow? Or block it
        
        return world

    @staticmethod
    def _carve_road(world, sx, sy, angle, length):
        rad = math.radians(angle)
        dx, dy = math.cos(rad), math.sin(rad)
        cx, cy = float(sx), float(sy)
        
        for _ in range(length):
            ix, iy = int(cx), int(cy)
            t = world.get_tile(ix, iy)
            if t and t.terrain_type not in ["water", "mountain"]:
                t.terrain_type = "road"
                t.movement_cost = 1.0
            cx += dx + random.uniform(-0.2, 0.2)
            cy += dy + random.uniform(-0.2, 0.2)

    @staticmethod
    def _get_neighbors(world, x, y):
        res = []
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                if dx == 0 and dy == 0: continue
                t = world.get_tile(x+dx, y+dy)
                if t: res.append(t)
        return res
