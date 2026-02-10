from dataclasses import dataclass
from typing import Optional, List

@dataclass
class Tile:
    x: int
    y: int
    terrain_type: str  # grass, road, water, forest, mountain
    movement_cost: float
    is_walkable: bool
    building: Optional[object] = None
    effects: List[str] = None  # ['fire', 'rubble']

class GameMap:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.tiles = [[None for _ in range(width)] for _ in range(height)]
        self.objects = []  # List of WorldObjects

    def get_tile(self, x, y) -> Optional[Tile]:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return None

    def add_object(self, obj):
        self.objects.append(obj)
        t = self.get_tile(obj.x, obj.y)
        if t: t.building = obj
