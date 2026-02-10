from .components import Flammable, Structural

class WorldObject:
    def __init__(self, name, x, y, char='?'):
        self.name = name
        self.x = x
        self.y = y
        self.components = {}

    def add_component(self, component):
        self.components[type(component)] = component
        return self

    def get_component(self, component_type):
        return self.components.get(component_type)

def create_prefab(type_name, x, y):
    obj = WorldObject(type_name, x, y)
    
    if type_name == "House":
        # Standard NPC House
        obj.add_component(Structural(hp=100, material="wood"))
        obj.add_component(Flammable(fuel=200, burn_rate=2.0))
        
    elif type_name == "Bathhouse":
        # The "PokeCenter" of Rome
        obj.add_component(Structural(hp=500, material="stone"))
        
    elif type_name == "Market":
        # The "PokeMart"
        obj.add_component(Structural(hp=300, material="wood"))
        
    elif type_name == "Temple":
        # The "Gym"
        obj.add_component(Structural(hp=1000, material="stone"))
        
    elif type_name == "TallGrass":
        obj.add_component(Flammable(fuel=20, burn_rate=10.0))
        
    return obj