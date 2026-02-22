from .components import (
    Flammable, Structural, Footprint, Elevation,
    Decoration, Interactable, WaterFeature, Liquid
)

class WorldObject:
    def __init__(self, name, x, y, obj_type="building"):
        self.name = name
        self.x = x
        self.y = y
        self.obj_type = obj_type
        self.components = {}

    def add_component(self, component):
        self.components[type(component)] = component
        return self

    def get_component(self, component_type):
        return self.components.get(component_type)

    def has_component(self, component_type):
        return component_type in self.components


# ============================================================
# Building Prefabs — Roman Architecture (historically placed)
# ============================================================

def create_prefab(type_name, x, y, **kwargs):
    obj = WorldObject(type_name, x, y)

    # ===== MONUMENTAL =====
    
    if type_name == "Colosseum":
        obj.obj_type = "monument"
        obj.add_component(Structural(hp=5000, max_hp=5000, material="concrete"))
        obj.add_component(Footprint(width=24, height=20))
        obj.add_component(Elevation(height=4.5, shadow_length=3.5))
        obj.add_component(Decoration(sprite_key="colosseum", layer=2))
        obj.add_component(Interactable(interaction_type="spectate", capacity=50))

    elif type_name == "TempleOfSaturn":
        obj.obj_type = "monument"
        obj.add_component(Structural(hp=2000, max_hp=2000, material="marble"))
        obj.add_component(Footprint(width=6, height=10))
        obj.add_component(Elevation(height=3.0, shadow_length=2.5))
        obj.add_component(Decoration(sprite_key="temple_large", layer=2))
        obj.add_component(Interactable(interaction_type="pray", capacity=20))

    elif type_name == "TempleOfVesta":
        obj.obj_type = "monument"
        obj.add_component(Structural(hp=1500, max_hp=1500, material="marble"))
        obj.add_component(Footprint(width=4, height=4))
        obj.add_component(Elevation(height=2.0, shadow_length=1.5))
        obj.add_component(Decoration(sprite_key="temple_round", layer=2))
        obj.add_component(Interactable(interaction_type="pray", capacity=6))

    elif type_name == "TempleOfAntoninus":
        obj.obj_type = "monument"
        obj.add_component(Structural(hp=1800, max_hp=1800, material="marble"))
        obj.add_component(Footprint(width=5, height=7))
        obj.add_component(Elevation(height=2.5, shadow_length=2.0))
        obj.add_component(Decoration(sprite_key="temple_medium", layer=2))
        obj.add_component(Interactable(interaction_type="pray", capacity=15))

    elif type_name == "TempleOfCastor":
        obj.obj_type = "monument"
        obj.add_component(Structural(hp=1200, max_hp=1200, material="marble"))
        obj.add_component(Footprint(width=4, height=8))
        obj.add_component(Elevation(height=3.0, shadow_length=2.0))
        obj.add_component(Decoration(sprite_key="temple_podium", layer=2))
        obj.add_component(Interactable(interaction_type="pray", capacity=10))

    elif type_name == "TempleOfDivusJulius":
        obj.obj_type = "monument"
        obj.add_component(Structural(hp=1500, max_hp=1500, material="marble"))
        obj.add_component(Footprint(width=5, height=7))
        obj.add_component(Elevation(height=2.0, shadow_length=1.5))
        obj.add_component(Decoration(sprite_key="temple_medium", layer=2))
        obj.add_component(Interactable(interaction_type="pray", capacity=12))

    elif type_name == "TempleOfConcord":
        obj.obj_type = "monument"
        obj.add_component(Structural(hp=1600, max_hp=1600, material="marble"))
        obj.add_component(Footprint(width=8, height=5))
        obj.add_component(Elevation(height=2.5, shadow_length=2.0))
        obj.add_component(Decoration(sprite_key="temple_medium", layer=2))
        obj.add_component(Interactable(interaction_type="pray", capacity=15))

    elif type_name == "TempleOfVenusRoma":
        obj.obj_type = "monument"
        obj.add_component(Structural(hp=3000, max_hp=3000, material="marble"))
        obj.add_component(Footprint(width=8, height=14))
        obj.add_component(Elevation(height=3.5, shadow_length=3.0))
        obj.add_component(Decoration(sprite_key="temple_venus_roma", layer=2))
        obj.add_component(Interactable(interaction_type="pray", capacity=30))

    elif type_name == "TempleOfVictoria":
        obj.obj_type = "monument"
        obj.add_component(Structural(hp=1000, max_hp=1000, material="marble"))
        obj.add_component(Footprint(width=4, height=6))
        obj.add_component(Elevation(height=2.0, shadow_length=1.5))
        obj.add_component(Decoration(sprite_key="temple_medium", layer=2))
        obj.add_component(Interactable(interaction_type="pray", capacity=10))

    elif type_name == "TempleOfMagnaMater":
        obj.obj_type = "monument"
        obj.add_component(Structural(hp=1200, max_hp=1200, material="marble"))
        obj.add_component(Footprint(width=5, height=7))
        obj.add_component(Elevation(height=2.5, shadow_length=2.0))
        obj.add_component(Decoration(sprite_key="temple_medium", layer=2))
        obj.add_component(Interactable(interaction_type="pray", capacity=12))

    elif type_name == "TempleOfJovisOM":
        obj.obj_type = "monument"
        obj.add_component(Structural(hp=3500, max_hp=3500, material="marble"))
        obj.add_component(Footprint(width=10, height=12))
        obj.add_component(Elevation(height=4.0, shadow_length=3.0))
        obj.add_component(Decoration(sprite_key="temple_large", layer=2))
        obj.add_component(Interactable(interaction_type="pray", capacity=30))

    elif type_name == "BasilicaJulia":
        obj.obj_type = "monument"
        obj.add_component(Structural(hp=3000, max_hp=3000, material="marble"))
        obj.add_component(Footprint(width=16, height=6))
        obj.add_component(Elevation(height=2.5, shadow_length=2.0))
        obj.add_component(Decoration(sprite_key="basilica", layer=2))
        obj.add_component(Interactable(interaction_type="trade", capacity=30))

    elif type_name == "BasilicaAemilia":
        obj.obj_type = "monument"
        obj.add_component(Structural(hp=2500, max_hp=2500, material="marble"))
        obj.add_component(Footprint(width=14, height=5))
        obj.add_component(Elevation(height=2.0, shadow_length=1.8))
        obj.add_component(Decoration(sprite_key="basilica_aemilia", layer=2))
        obj.add_component(Interactable(interaction_type="trade", capacity=25))

    elif type_name == "Rostra":
        obj.obj_type = "monument"
        obj.add_component(Structural(hp=1000, max_hp=1000, material="marble"))
        obj.add_component(Footprint(width=5, height=3))
        obj.add_component(Elevation(height=1.5, shadow_length=1.0))
        obj.add_component(Decoration(sprite_key="rostra", layer=2))
        obj.add_component(Interactable(interaction_type="speak", capacity=1))

    elif type_name == "CuriaJulia":
        obj.obj_type = "monument"
        obj.add_component(Structural(hp=2000, max_hp=2000, material="brick"))
        obj.add_component(Footprint(width=4, height=5))
        obj.add_component(Elevation(height=3.0, shadow_length=2.0))
        obj.add_component(Decoration(sprite_key="curia", layer=2))
        obj.add_component(Interactable(interaction_type="deliberate", capacity=10))

    elif type_name == "Tabularium":
        obj.obj_type = "monument"
        obj.add_component(Structural(hp=3000, max_hp=3000, material="concrete"))
        obj.add_component(Footprint(width=12, height=4))
        obj.add_component(Elevation(height=3.5, shadow_length=2.5))
        obj.add_component(Decoration(sprite_key="tabularium", layer=2))

    elif type_name == "Regia":
        obj.obj_type = "monument"
        obj.add_component(Structural(hp=800, max_hp=800, material="stone"))
        obj.add_component(Footprint(width=3, height=3))
        obj.add_component(Elevation(height=1.5, shadow_length=1.0))
        obj.add_component(Decoration(sprite_key="regia", layer=2))

    elif type_name == "ArchOfTitus":
        obj.obj_type = "monument"
        obj.add_component(Structural(hp=2000, max_hp=2000, material="marble"))
        obj.add_component(Footprint(width=3, height=2))
        obj.add_component(Elevation(height=3.0, shadow_length=2.0))
        obj.add_component(Decoration(sprite_key="triumphal_arch", layer=2))

    elif type_name == "ArchOfSeptimiusSeverus":
        obj.obj_type = "monument"
        obj.add_component(Structural(hp=2500, max_hp=2500, material="marble"))
        obj.add_component(Footprint(width=5, height=3))
        obj.add_component(Elevation(height=3.5, shadow_length=2.5))
        obj.add_component(Decoration(sprite_key="arch_large", layer=2))

    elif type_name == "ArchOfConstantine":
        obj.obj_type = "monument"
        obj.add_component(Structural(hp=2500, max_hp=2500, material="marble"))
        obj.add_component(Footprint(width=5, height=3))
        obj.add_component(Elevation(height=3.5, shadow_length=2.5))
        obj.add_component(Decoration(sprite_key="arch_large", layer=2))

    elif type_name == "MetaSudans":
        obj.obj_type = "monument"
        obj.add_component(Structural(hp=500, max_hp=500, material="stone"))
        obj.add_component(Footprint(width=3, height=3))
        obj.add_component(Decoration(sprite_key="fountain_large", layer=1,
                                     animation="fountain"))
        obj.add_component(WaterFeature(flow_rate=2.0, splash_radius=2.0))
        obj.add_component(Liquid(amount=500))

    elif type_name == "Colossus":
        obj.obj_type = "monument"
        obj.add_component(Structural(hp=1000, max_hp=1000, material="bronze"))
        obj.add_component(Footprint(width=2, height=2))
        obj.add_component(Elevation(height=5.0, shadow_length=4.0))
        obj.add_component(Decoration(sprite_key="statue_equestrian", layer=2))

    # ===== IMPERIAL FORA =====

    elif type_name == "ForumOfAugustus":
        obj.obj_type = "monument"
        obj.add_component(Structural(hp=3000, max_hp=3000, material="marble"))
        obj.add_component(Footprint(width=8, height=10))
        obj.add_component(Elevation(height=2.0, shadow_length=1.5))
        obj.add_component(Decoration(sprite_key="forum_imperiale", layer=2))
        obj.add_component(Interactable(interaction_type="inspect", capacity=20))

    elif type_name == "ForumOfNerva":
        obj.obj_type = "monument"
        obj.add_component(Structural(hp=2000, max_hp=2000, material="marble"))
        obj.add_component(Footprint(width=4, height=10))
        obj.add_component(Elevation(height=1.5, shadow_length=1.0))
        obj.add_component(Decoration(sprite_key="forum_imperiale", layer=2))

    elif type_name == "ForumOfVespasian":
        obj.obj_type = "monument"
        obj.add_component(Structural(hp=2500, max_hp=2500, material="marble"))
        obj.add_component(Footprint(width=8, height=8))
        obj.add_component(Elevation(height=1.5, shadow_length=1.0))
        obj.add_component(Decoration(sprite_key="forum_imperiale", layer=2))

    elif type_name == "ForumOfTrajan":
        obj.obj_type = "monument"
        obj.add_component(Structural(hp=4000, max_hp=4000, material="marble"))
        obj.add_component(Footprint(width=10, height=12))
        obj.add_component(Elevation(height=2.0, shadow_length=1.5))
        obj.add_component(Decoration(sprite_key="forum_imperiale", layer=2))
        obj.add_component(Interactable(interaction_type="inspect", capacity=25))

    elif type_name == "MarketsOfTrajan":
        obj.obj_type = "building"
        obj.add_component(Structural(hp=2000, max_hp=2000, material="brick"))
        obj.add_component(Footprint(width=10, height=8))
        obj.add_component(Elevation(height=3.0, shadow_length=2.0))
        obj.add_component(Decoration(sprite_key="markets_trajan", layer=2))
        obj.add_component(Interactable(interaction_type="trade", capacity=30))

    elif type_name == "ColumnaTraiani":
        obj.obj_type = "monument"
        obj.add_component(Structural(hp=2000, max_hp=2000, material="marble"))
        obj.add_component(Footprint(width=1, height=1))
        obj.add_component(Elevation(height=5.0, shadow_length=3.0))
        obj.add_component(Decoration(sprite_key="column", layer=2))

    # ===== PALATINE HILL =====
    
    elif type_name == "DomusTiberiana":
        obj.obj_type = "monument"
        obj.add_component(Structural(hp=3500, max_hp=3500, material="marble"))
        obj.add_component(Footprint(width=14, height=10))
        obj.add_component(Elevation(height=3.5, shadow_length=3.0))
        obj.add_component(Decoration(sprite_key="palace", layer=2))
        obj.add_component(Interactable(interaction_type="audience", capacity=10))

    elif type_name == "DomusAugustana":
        obj.obj_type = "monument"
        obj.add_component(Structural(hp=4000, max_hp=4000, material="marble"))
        obj.add_component(Footprint(width=18, height=16))
        obj.add_component(Elevation(height=4.0, shadow_length=3.5))
        obj.add_component(Decoration(sprite_key="domus_augustana", layer=2))
        obj.add_component(Interactable(interaction_type="audience", capacity=15))

    elif type_name == "Stadium":
        obj.obj_type = "monument"
        obj.add_component(Structural(hp=2000, max_hp=2000, material="concrete"))
        obj.add_component(Footprint(width=5, height=18))
        obj.add_component(Elevation(height=1.5, shadow_length=1.0))
        obj.add_component(Decoration(sprite_key="stadium", layer=2))

    # ===== CIRCUS MAXIMUS =====
    
    elif type_name == "CircusMaximus":
        obj.obj_type = "monument"
        obj.add_component(Structural(hp=5000, max_hp=5000, material="concrete"))
        obj.add_component(Footprint(width=40, height=8))
        obj.add_component(Elevation(height=2.0, shadow_length=1.5))
        obj.add_component(Decoration(sprite_key="circus_maximus", layer=2))
        obj.add_component(Interactable(interaction_type="spectate", capacity=100))

    # ===== CIVIC =====
    
    elif type_name == "LudusMagnus":
        obj.obj_type = "building"
        obj.add_component(Structural(hp=1500, max_hp=1500, material="concrete"))
        obj.add_component(Footprint(width=10, height=10))
        obj.add_component(Elevation(height=1.5, shadow_length=1.0))
        obj.add_component(Decoration(sprite_key="ludus", layer=2))
        obj.add_component(Interactable(interaction_type="train", capacity=20))

    elif type_name == "TheatreOfMarcellus":
        obj.obj_type = "monument"
        obj.add_component(Structural(hp=3000, max_hp=3000, material="concrete"))
        obj.add_component(Footprint(width=10, height=6))
        obj.add_component(Elevation(height=3.0, shadow_length=2.0))
        obj.add_component(Decoration(sprite_key="theatre", layer=2))
        obj.add_component(Interactable(interaction_type="spectate", capacity=15))

    elif type_name == "Market":
        obj.obj_type = "building"
        obj.add_component(Structural(hp=200, max_hp=200, material="wood"))
        obj.add_component(Flammable(fuel=150, burn_rate=3.0))
        obj.add_component(Footprint(width=3, height=2))
        obj.add_component(Elevation(height=1.0))
        obj.add_component(Decoration(sprite_key="market_stall", layer=1))
        obj.add_component(Interactable(interaction_type="trade", capacity=5))

    elif type_name == "Taberna":
        obj.obj_type = "building"
        obj.add_component(Structural(hp=150, max_hp=150, material="brick"))
        obj.add_component(Flammable(fuel=100, burn_rate=2.0))
        obj.add_component(Footprint(width=2, height=2))
        obj.add_component(Elevation(height=1.0))
        obj.add_component(Decoration(sprite_key="taberna", layer=1))
        obj.add_component(Interactable(interaction_type="trade", capacity=3))

    elif type_name == "Bathhouse":
        obj.obj_type = "building"
        obj.add_component(Structural(hp=800, max_hp=800, material="stone"))
        obj.add_component(Footprint(width=6, height=5))
        obj.add_component(Elevation(height=1.5))
        obj.add_component(Decoration(sprite_key="bathhouse", layer=2))
        obj.add_component(WaterFeature(flow_rate=1.5))
        obj.add_component(Interactable(interaction_type="rest", capacity=15))

    elif type_name == "Porticus":
        obj.obj_type = "building"
        obj.add_component(Structural(hp=600, max_hp=600, material="marble"))
        obj.add_component(Footprint(width=8, height=2))
        obj.add_component(Elevation(height=1.0, shadow_length=0.5))
        obj.add_component(Decoration(sprite_key="porticus", layer=1))

    # ===== RESIDENTIAL =====
    
    elif type_name == "Domus":
        obj.obj_type = "building"
        obj.add_component(Structural(hp=400, max_hp=400, material="brick"))
        obj.add_component(Flammable(fuel=100, burn_rate=1.0))
        obj.add_component(Footprint(width=4, height=3))
        obj.add_component(Elevation(height=1.5))
        obj.add_component(Decoration(sprite_key="domus", layer=1))

    elif type_name == "DomusLiviae":
        obj.obj_type = "building"
        obj.add_component(Structural(hp=500, max_hp=500, material="marble"))
        obj.add_component(Footprint(width=5, height=4))
        obj.add_component(Elevation(height=1.5))
        obj.add_component(Decoration(sprite_key="domus", layer=1))

    elif type_name == "Insula":
        obj.obj_type = "building"
        stories = kwargs.get("stories", 4)
        obj.add_component(Structural(hp=150, max_hp=150, material="wood"))
        obj.add_component(Flammable(fuel=300, burn_rate=5.0))
        obj.add_component(Footprint(width=3, height=3))
        obj.add_component(Elevation(height=float(stories) * 0.5, shadow_length=2.0))
        obj.add_component(Decoration(sprite_key="insula", layer=1))

    elif type_name == "House":
        obj.obj_type = "building"
        obj.add_component(Structural(hp=100, max_hp=100, material="wood"))
        obj.add_component(Flammable(fuel=200, burn_rate=2.0))
        obj.add_component(Footprint(width=2, height=2))
        obj.add_component(Elevation(height=1.0))
        obj.add_component(Decoration(sprite_key="house_simple", layer=1))

    # ===== INFRASTRUCTURE =====
    
    elif type_name == "Fountain":
        obj.obj_type = "infrastructure"
        obj.add_component(Structural(hp=200, max_hp=200, material="stone"))
        obj.add_component(Footprint(width=1, height=1))
        obj.add_component(Decoration(sprite_key="fountain", layer=1,
                                     animation="fountain"))
        obj.add_component(WaterFeature(flow_rate=1.0, splash_radius=1.0))
        obj.add_component(Interactable(interaction_type="drink", capacity=3))

    elif type_name == "Column":
        obj.obj_type = "decoration"
        obj.add_component(Structural(hp=500, max_hp=500, material="marble"))
        obj.add_component(Elevation(height=2.0))
        obj.add_component(Decoration(sprite_key="column", layer=1))

    elif type_name == "Statue":
        obj.obj_type = "decoration"
        obj.add_component(Structural(hp=300, max_hp=300, material="marble"))
        obj.add_component(Elevation(height=1.5))
        obj.add_component(Decoration(sprite_key="statue", layer=1))

    elif type_name == "StatueEquestrian":
        obj.obj_type = "decoration"
        obj.add_component(Structural(hp=400, max_hp=400, material="bronze"))
        obj.add_component(Footprint(width=2, height=2))
        obj.add_component(Elevation(height=2.5, shadow_length=1.5))
        obj.add_component(Decoration(sprite_key="statue_equestrian", layer=1))

    elif type_name == "Obelisk":
        obj.obj_type = "decoration"
        obj.add_component(Structural(hp=800, max_hp=800, material="granite"))
        obj.add_component(Footprint(width=1, height=2))
        obj.add_component(Elevation(height=3.0, shadow_length=2.0))
        obj.add_component(Decoration(sprite_key="obelisk", layer=2))

    elif type_name == "Cloaca":
        obj.obj_type = "infrastructure"
        obj.add_component(Structural(hp=1000, max_hp=1000, material="stone"))
        obj.add_component(Decoration(sprite_key="cloaca", layer=0))

    # ===== VEGETATION =====
    
    elif type_name == "Cypress":
        obj.obj_type = "vegetation"
        obj.add_component(Flammable(fuel=80, burn_rate=4.0))
        obj.add_component(Elevation(height=2.0, shadow_length=1.5))
        obj.add_component(Decoration(sprite_key="cypress", layer=1))

    elif type_name == "OliveTree":
        obj.obj_type = "vegetation"
        obj.add_component(Flammable(fuel=60, burn_rate=3.0))
        obj.add_component(Elevation(height=1.5, shadow_length=1.5))
        obj.add_component(Decoration(sprite_key="olive_tree", layer=1))

    elif type_name == "PineTree":
        obj.obj_type = "vegetation"
        obj.add_component(Flammable(fuel=70, burn_rate=3.5))
        obj.add_component(Elevation(height=2.5, shadow_length=2.0))
        obj.add_component(Decoration(sprite_key="pine_tree", layer=1))

    elif type_name == "Shrub":
        obj.obj_type = "vegetation"
        obj.add_component(Flammable(fuel=20, burn_rate=8.0))
        obj.add_component(Decoration(sprite_key="shrub", layer=0))

    elif type_name == "FlowerBed":
        obj.obj_type = "vegetation"
        obj.add_component(Decoration(sprite_key="flowers", layer=0))

    # ===== MISC =====
    
    elif type_name == "Torch":
        obj.obj_type = "decoration"
        obj.add_component(Decoration(sprite_key="torch", layer=1,
                                     animation="torch"))
        obj.add_component(Flammable(fuel=500, burn_rate=0.1,
                                    is_burning=True, fire_intensity=3.0))

    elif type_name == "Aqueduct":
        obj.obj_type = "infrastructure"
        obj.add_component(Structural(hp=2000, max_hp=2000, material="concrete"))
        obj.add_component(Elevation(height=3.0, shadow_length=2.5))
        obj.add_component(Decoration(sprite_key="aqueduct", layer=2))
        obj.add_component(WaterFeature(flow_rate=5.0))

    return obj
