from dataclasses import dataclass

@dataclass
class Flammable:
    fuel: float = 100.0
    burn_rate: float = 1.0
    is_burning: bool = False
    fire_intensity: float = 0.0

@dataclass
class Structural:
    hp: float = 100.0
    max_hp: float = 100.0
    material: str = "wood"  # wood, stone, straw

@dataclass
class Liquid:
    amount: float = 0.0
    type: str = "water"  # water, oil, wine
