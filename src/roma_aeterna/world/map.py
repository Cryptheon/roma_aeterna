from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class Tile:
    x: int
    y: int
    terrain_type: str
    movement_cost: float
    is_walkable: bool
    building: Optional[object] = None
    effects: List[str] = field(default_factory=list)
    elevation: float = 0.0
    moisture: float = 0.0
    zone: str = "open"
    ground_decoration: str = None

# Terrain type definitions with default costs
TERRAIN_TYPES = {
    # Roads & Paved
    "via_sacra":       {"cost": 0.8, "walkable": True},
    "road_paved":      {"cost": 1.0, "walkable": True},
    "road_cobble":     {"cost": 1.2, "walkable": True},
    "forum_floor":     {"cost": 1.0, "walkable": True},
    "plaza":           {"cost": 1.0, "walkable": True},
    "steps":           {"cost": 1.5, "walkable": True},
    
    # Ground
    "dirt":            {"cost": 1.5, "walkable": True},
    "grass":           {"cost": 2.0, "walkable": True},
    "grass_dry":       {"cost": 2.0, "walkable": True},
    "garden":          {"cost": 2.5, "walkable": True},
    "sand_arena":      {"cost": 1.5, "walkable": True},
    "circus_sand":     {"cost": 1.5, "walkable": True},
    
    # Terrain
    "hill":            {"cost": 3.0, "walkable": True},
    "hill_steep":      {"cost": 5.0, "walkable": True},
    "cliff":           {"cost": 999, "walkable": False},
    
    # Water
    "water":           {"cost": 999, "walkable": False},
    "water_shallow":   {"cost": 8.0, "walkable": True},
    "aqueduct_channel":{"cost": 999, "walkable": False},
    
    # Structure footprints
    "building_floor":  {"cost": 999, "walkable": False},
    "wall":            {"cost": 999, "walkable": False},
}


class GameMap:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.tiles = [[None for _ in range(width)] for _ in range(height)]
        self.objects = []
        self.landmarks = {}
        self.zones = {}

    def get_tile(self, x, y) -> Optional[Tile]:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return None

    def set_tile(self, x, y, terrain_type, **kwargs):
        if not (0 <= x < self.width and 0 <= y < self.height):
            return None
            
        defaults = TERRAIN_TYPES.get(terrain_type, {"cost": 2.0, "walkable": True})
        
        tile = Tile(
            x=x, y=y,
            terrain_type=terrain_type,
            movement_cost=kwargs.get("cost", defaults["cost"]),
            is_walkable=kwargs.get("walkable", defaults["walkable"]),
            elevation=kwargs.get("elevation", 0.0),
            moisture=kwargs.get("moisture", 0.0),
            zone=kwargs.get("zone", "open"),
            ground_decoration=kwargs.get("decoration", None),
        )
        self.tiles[y][x] = tile
        return tile

    def add_object(self, obj):
        self.objects.append(obj)
        t = self.get_tile(obj.x, obj.y)
        if t:
            t.building = obj

    def register_landmark(self, name, obj):
        self.landmarks[name] = obj
        self.add_object(obj)

    def fill_rect(self, x1, y1, x2, y2, terrain_type, **kwargs):
        for y in range(max(0, y1), min(self.height, y2)):
            for x in range(max(0, x1), min(self.width, x2)):
                self.set_tile(x, y, terrain_type, **kwargs)

    def fill_ellipse(self, cx, cy, rx, ry, terrain_type, **kwargs):
        for y in range(max(0, cy - ry), min(self.height, cy + ry + 1)):
            for x in range(max(0, cx - rx), min(self.width, cx + rx + 1)):
                dx = (x - cx) / max(rx, 1)
                dy = (y - cy) / max(ry, 1)
                if dx * dx + dy * dy <= 1.0:
                    self.set_tile(x, y, terrain_type, **kwargs)

    def draw_road(self, x1, y1, x2, y2, width=2, terrain_type="road_paved", **kwargs):
        dx = x2 - x1
        dy = y2 - y1
        steps = max(abs(dx), abs(dy), 1)
        
        for i in range(steps + 1):
            t = i / steps
            cx = int(x1 + dx * t)
            cy = int(y1 + dy * t)
            
            hw = width // 2
            for oy in range(-hw, hw + 1):
                for ox in range(-hw, hw + 1):
                    self.set_tile(cx + ox, cy + oy, terrain_type, **kwargs)
