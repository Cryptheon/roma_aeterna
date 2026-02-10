from .components import Flammable, Structural

class WorldObject:
    def __init__(self, name, x, y, char='?'):
        self.name = name
        self.x = x
        self.y = y
        self.char = char  # For ASCII debug or easy ID
        self.components = {}

    def add_component(self, component):
        self.components[type(component)] = component
        return self

    def get_component(self, component_type):
        return self.components.get(component_type)

class Building(WorldObject):
    def __init__(self, type_name, x, y):
        super().__init__(type_name, x, y)
        self.width = 1
        self.height = 1

def create_prefab(type_name, x, y):
    obj = WorldObject(type_name, x, y)
    
    if type_name == "Insula":
        obj.add_component(Flammable(fuel=300, burn_rate=2.0))
        obj.add_component(Structural(hp=150, material="wood"))
    elif type_name == "Temple":
        obj.add_component(Structural(hp=1000, material="stone"))
    elif type_name == "Tree":
        obj.add_component(Flammable(fuel=50, burn_rate=5.0))
        obj.add_component(Structural(hp=20, material="wood"))
    
    return obj
