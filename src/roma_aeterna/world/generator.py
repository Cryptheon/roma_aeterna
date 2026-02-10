import random
from .map import GameMap, Tile
from .objects import create_prefab
from ..config import GRID_WIDTH, GRID_HEIGHT

class WorldGenerator:
    @staticmethod
    def generate_rome() -> GameMap:
        world = GameMap(GRID_WIDTH, GRID_HEIGHT)
        
        # 1. Fill World with "Barrier" (Trees/Mountains)
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                # Default to forest barrier
                world.tiles[y][x] = Tile(x, y, "grass", 1.0, True)

        # 2. Draw "Palatine Town" (Starter Area - Bottom Center)
        WorldGenerator._draw_town(world, 64, 110, 20, 14, "Palatine Town")

        # 3. Draw "Roma Invicta" (Big City - Top Center)
        WorldGenerator._draw_town(world, 64, 30, 40, 30, "Roma City")

        # 4. Draw "Route I" (Connecting them)
        WorldGenerator._draw_route(world, 64, 110, 64, 60)

        return world

    @staticmethod
    def _draw_town(world, cx, cy, w, h, name):
        # Clear land
        for y in range(cy-h//2, cy+h//2):
            for x in range(cx-w//2, cx+w//2):
                t = world.tiles[y][x]
                t.terrain_type = "path" # Town floor
                t.movement_cost = 1.0

        # Place Houses (2x2 grid size for visuals)
        # Top Row
        WorldGenerator._place_building(world, cx-5, cy-4, "House")
        WorldGenerator._place_building(world, cx+5, cy-4, "House")
        
        # Special Buildings
        if name == "Roma City":
            WorldGenerator._place_building(world, cx, cy-8, "Temple") # Gym
            WorldGenerator._place_building(world, cx-8, cy+2, "Market") # Mart
            WorldGenerator._place_building(world, cx+8, cy+2, "Bathhouse") # Center
        else:
            WorldGenerator._place_building(world, cx-6, cy+2, "House") # Lab?

    @staticmethod
    def _draw_route(world, x1, y1, x2, y2):
        # Winding path
        cy = y1
        while cy > y2:
            cy -= 1
            # Path width 3
            for i in range(-2, 3):
                t = world.tiles[cy][x1+i]
                t.terrain_type = "path"
            
            # Add Tall Grass on sides
            if random.random() < 0.3:
                WorldGenerator._place_grass(world, x1-3, cy)
                WorldGenerator._place_grass(world, x1+3, cy)

    @staticmethod
    def _place_building(world, x, y, type_name):
        obj = create_prefab(type_name, x, y)
        world.add_object(obj)
        # Make tile under building unwalkable
        t = world.get_tile(x, y)
        if t: 
            t.movement_cost = 999.0
            t.is_walkable = False

    @staticmethod
    def _place_grass(world, x, y):
        t = world.get_tile(x, y)
        if t:
            t.terrain_type = "tall_grass"
            t.movement_cost = 2.0 # Slows you down!
            # world.add_object(create_prefab("TallGrass", x, y))