"""
Component System — ECS-style data containers for world objects.

Each component is a pure data holder. Systems (chaos, weather, etc.)
operate on entities that possess specific component combinations.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


# ============================================================
# Physics Components
# ============================================================

@dataclass
class Flammable:
    """Object can catch fire and burn."""
    fuel: float = 100.0
    burn_rate: float = 1.0
    is_burning: bool = False
    fire_intensity: float = 0.0
    ignition_temp: float = 50.0      # How hard to ignite
    smoke_output: float = 1.0        # Affects visibility nearby


@dataclass
class Structural:
    """Object has physical integrity that can degrade."""
    hp: float = 100.0
    max_hp: float = 100.0
    material: str = "wood"  # wood, stone, marble, concrete, brick, bronze, granite
    weather_resistance: float = 0.5  # 0=fragile in weather, 1=immune
    repair_material: str = "stone"   # What item is needed to repair


@dataclass
class Liquid:
    """Contains liquid volume."""
    amount: float = 0.0
    liquid_type: str = "water"  # water, oil, wine, garum
    max_amount: float = 500.0
    evaporation_rate: float = 0.01


# ============================================================
# Visual / Spatial Components
# ============================================================

@dataclass
class Footprint:
    """Multi-tile building footprint."""
    width: int = 1
    height: int = 1
    origin_x: int = 0
    origin_y: int = 0
    tiles: List[tuple] = field(default_factory=list)


@dataclass
class Elevation:
    """Height above base terrain — affects shadow, visibility."""
    height: float = 0.0
    casts_shadow: bool = True
    shadow_length: float = 1.0
    blocks_vision: bool = False      # Tall buildings block line of sight


@dataclass
class Decoration:
    """Visual rendering hints."""
    sprite_key: str = "default"
    color_override: Optional[tuple] = None
    layer: int = 0
    animation: Optional[str] = None
    frame: int = 0
    frame_timer: float = 0.0


# ============================================================
# Interaction Components
# ============================================================

@dataclass
class Interactable:
    """Can be used by agents. Defines what kind of interaction is possible."""
    interaction_type: str = "inspect"
    # Valid types: inspect, trade, pray, rest, drink, eat, train, 
    #              spectate, speak, deliberate, audience, craft
    capacity: int = 1
    current_users: int = 0
    cooldown: float = 0.0
    cooldown_max: float = 10.0
    requires_item: Optional[str] = None   # Item needed to interact
    grants_item: Optional[str] = None     # Item given on interaction
    grants_effect: Optional[str] = None   # Status effect given


@dataclass
class Container:
    """Object holds items that agents can take or deposit."""
    items: List[str] = field(default_factory=list)
    max_items: int = 20
    is_locked: bool = False
    owner: Optional[str] = None  # Agent UID who owns it


@dataclass
class WaterFeature:
    """Fountains, aqueducts, pools — provides water."""
    flow_rate: float = 1.0
    is_active: bool = True
    splash_radius: float = 1.0
    purified: bool = True


@dataclass
class CraftingStation:
    """Allows agents to craft items here."""
    station_type: str = "general"  # general, forge, kitchen, altar
    recipes_available: List[str] = field(default_factory=list)
    speed_bonus: float = 1.0


@dataclass
class Shelter:
    """Provides protection from weather and a place to sleep."""
    warmth: float = 1.0         # Multiplier on comfort
    rain_protection: float = 1.0
    bed_count: int = 0
    current_sleepers: int = 0


@dataclass
class InfoSource:
    """Provides knowledge to agents who interact (inscriptions, scrolls, gossip)."""
    knowledge_type: str = "rumor"  # rumor, law, history, location, recipe
    content: str = ""
    is_public: bool = True
    discovery_chance: float = 1.0  # Probability agent actually learns it
