"""
Item System — Items, recipes, trade values, and spoilage.

Items exist in agent inventories and world containers.
Each item has typed properties that affect agent drives when consumed.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
import random


@dataclass
class Item:
    """A single item instance."""
    name: str
    item_type: str          # resource, food, drink, tool, weapon, clothing, luxury, medicine
    description: str = ""
    properties: Dict = field(default_factory=dict)
    trade_value: int = 1    # Base denarii value
    weight: float = 1.0
    spoilable: bool = False
    freshness: float = 1.0  # 1.0 = fresh, 0.0 = rotten
    
    def is_spoiled(self) -> bool:
        return self.freshness <= 0.1


@dataclass
class Recipe:
    """Crafting recipe."""
    name: str
    inputs: List[str]
    output: str
    station_type: str = "general"   # What CraftingStation is needed
    skill_required: Optional[str] = None  # Agent role that gets bonus
    time_ticks: int = 10


class ItemDatabase:
    """Registry of all item templates and recipes."""

    def __init__(self) -> None:
        self.templates: Dict[str, Item] = self._build_templates()
        self.recipes: List[Recipe] = self._build_recipes()

    def create_item(self, name: str) -> Optional[Item]:
        """Create a fresh copy of a template item."""
        template = self.templates.get(name)
        if not template:
            return None
        return Item(
            name=template.name,
            item_type=template.item_type,
            description=template.description,
            properties=dict(template.properties),
            trade_value=template.trade_value,
            weight=template.weight,
            spoilable=template.spoilable,
            freshness=1.0,
        )

    def find_recipe(self, inputs: List[str], station: str = "general") -> Optional[Recipe]:
        """Find a recipe matching the given input items and station."""
        sorted_inputs = sorted(inputs)
        for recipe in self.recipes:
            if sorted(recipe.inputs) == sorted_inputs:
                if recipe.station_type == "general" or recipe.station_type == station:
                    return recipe
        return None

    def tick_spoilage(self, item: Item, dt: float, temperature: float = 22.0) -> None:
        """Degrade perishable items over time. Heat accelerates spoilage."""
        if not item.spoilable:
            return
        heat_factor = max(1.0, (temperature - 15.0) / 10.0)
        item.freshness -= 0.002 * dt * heat_factor
        item.freshness = max(0.0, item.freshness)

    @staticmethod
    def _build_templates() -> Dict[str, Item]:
        items = {}

        def _add(name: str, item_type: str, desc: str, props: Dict,
                 value: int = 1, weight: float = 1.0, spoilable: bool = False) -> None:
            items[name] = Item(name, item_type, desc, props, value, weight, spoilable)

        # --- Raw Resources ---
        _add("Wheat", "resource", "Golden grain from the fields of Latium.",
             {}, value=2, weight=0.5)
        _add("Barley", "resource", "Coarse grain, good for porridge and beer.",
             {}, value=1, weight=0.5)
        _add("Stone", "resource", "A rough block of tufa stone.",
             {}, value=3, weight=5.0)
        _add("Marble", "resource", "Fine Carrara marble, prized by sculptors.",
             {"quality": "fine"}, value=15, weight=8.0)
        _add("Wood", "resource", "Seasoned timber.",
             {}, value=2, weight=3.0)
        _add("Iron", "resource", "A lump of raw iron ore.",
             {}, value=8, weight=4.0)
        _add("Clay", "resource", "Wet clay suitable for pottery.",
             {}, value=1, weight=2.0)
        _add("Olive", "resource", "Fresh olives from the grove.",
             {"nutrition": 5}, value=2, weight=0.3, spoilable=True)
        _add("Grapes", "resource", "Ripe grapes, sweet and fragrant.",
             {"nutrition": 5}, value=3, weight=0.3, spoilable=True)
        _add("Wool", "resource", "Raw sheep's wool.",
             {}, value=4, weight=1.0)
        _add("Linen", "resource", "Woven linen cloth.",
             {}, value=6, weight=0.5)
        _add("Salt", "resource", "Precious salt — white gold.",
             {"preservative": True}, value=10, weight=0.5)
        _add("Herbs", "resource", "Fragrant Mediterranean herbs.",
             {"medicinal": True}, value=3, weight=0.2, spoilable=True)

        # --- Food ---
        _add("Bread", "food", "A round loaf of panis, warm from the oven.",
             {"nutrition": 30, "thirst_increase": 5}, value=3, weight=0.5, spoilable=True)
        _add("Porridge", "food", "Puls — simple barley porridge. The food of old Rome.",
             {"nutrition": 20}, value=1, weight=0.8, spoilable=True)
        _add("Roast Meat", "food", "Spit-roasted pork seasoned with garum.",
             {"nutrition": 45, "energy_restore": 10}, value=8, weight=1.0, spoilable=True)
        _add("Dates", "food", "Honeyed dates from North Africa.",
             {"nutrition": 15, "comfort": 5}, value=5, weight=0.2, spoilable=True)
        _add("Cheese", "food", "Aged sheep's cheese.",
             {"nutrition": 20}, value=4, weight=0.5, spoilable=True)
        _add("Garum", "food", "Fermented fish sauce — the ketchup of Rome.",
             {"nutrition": 5, "flavor": True}, value=6, weight=0.5)
        _add("Honey Cake", "food", "Sweet pastry drizzled with Hymettus honey.",
             {"nutrition": 15, "comfort": 10}, value=7, weight=0.3, spoilable=True)
        _add("Fish", "food", "Fresh-caught Tiber fish.",
             {"nutrition": 25}, value=4, weight=1.0, spoilable=True)
        _add("Apple", "food", "A crisp Roman apple.",
             {"nutrition": 10, "thirst_reduce": 5}, value=2, weight=0.3, spoilable=True)
        _add("Olive Oil", "food", "Cold-pressed olive oil, liquid gold.",
             {"nutrition": 10, "medicinal": True}, value=8, weight=1.0)

        # --- Drinks ---
        _add("Water", "drink", "Clean water from the aqueduct.",
             {"thirst_reduce": 40}, value=0, weight=1.0)
        _add("Wine", "drink", "Falernian wine — the finest vintage.",
             {"thirst_reduce": 20, "comfort": 15, "intoxication": 10}, value=10, weight=1.5)
        _add("Posca", "drink", "Sour wine mixed with water — a soldier's drink.",
             {"thirst_reduce": 30, "comfort": 3}, value=1, weight=1.0)
        _add("Mulsum", "drink", "Honeyed wine, served at fine banquets.",
             {"thirst_reduce": 25, "comfort": 20, "intoxication": 5}, value=12, weight=1.5)

        # --- Tools ---
        _add("Hammer", "tool", "A simple iron hammer.",
             {"craft_bonus": 1.2, "can_repair": True}, value=10, weight=2.0)
        _add("Stylus", "tool", "A bronze writing stylus and wax tablet.",
             {"can_write": True}, value=5, weight=0.2)
        _add("Fishing Rod", "tool", "A reed fishing rod with gut line.",
             {"can_fish": True}, value=6, weight=1.0)
        _add("Amphora", "tool", "Large clay storage jar.",
             {"storage_bonus": 5}, value=4, weight=3.0)
        _add("Cooking Pot", "tool", "Bronze cooking vessel.",
             {"cook_bonus": 1.5}, value=8, weight=3.0)

        # --- Weapons ---
        _add("Gladius", "weapon", "Standard Roman short sword.",
             {"damage": 15, "intimidation": 10}, value=25, weight=2.0)
        _add("Pugio", "weapon", "A dagger favored by soldiers and assassins.",
             {"damage": 8, "concealable": True}, value=12, weight=0.5)
        _add("Pilum", "weapon", "Roman javelin — one throw, one kill.",
             {"damage": 20, "ranged": True, "single_use": True}, value=15, weight=3.0)

        # --- Clothing ---
        _add("Toga", "clothing", "A fine wool toga — mark of a citizen.",
             {"social_bonus": 10, "comfort": 5}, value=20, weight=2.0)
        _add("Tunic", "clothing", "A simple linen tunic.",
             {"comfort": 3}, value=3, weight=0.5)
        _add("Sandals", "clothing", "Leather caligae.",
             {"speed_bonus": 0.1, "comfort": 2}, value=5, weight=0.5)
        _add("Cloak", "clothing", "A heavy wool travelling cloak.",
             {"warmth": 15, "rain_protection": 0.5}, value=8, weight=1.5)

        # --- Luxury ---
        _add("Gold Coin", "luxury", "An aureus — worth 25 denarii.",
             {"value_multiplier": 25}, value=25, weight=0.1)
        _add("Silver Ring", "luxury", "A simple silver band.",
             {"social_bonus": 3}, value=15, weight=0.1)
        _add("Perfume", "luxury", "Scented oil from Arabia.",
             {"social_bonus": 8, "comfort": 10}, value=20, weight=0.2)
        _add("Laurel Wreath", "luxury", "Symbol of triumph and honor.",
             {"social_bonus": 20}, value=50, weight=0.2)
        _add("Dice", "luxury", "Carved bone dice for tabula and gambling.",
             {"entertainment": True}, value=2, weight=0.1)

        # --- Medicine ---
        _add("Herbal Poultice", "medicine", "Crushed herbs bound in linen.",
             {"heal": 15}, value=5, weight=0.3)
        _add("Willow Bark Tea", "medicine", "Nature's pain relief.",
             {"heal": 10, "comfort": 5}, value=4, weight=0.2)
        _add("Theriac", "medicine", "The universal antidote — or so they say.",
             {"heal": 30, "cure_poison": True}, value=30, weight=0.3)

        return items

    @staticmethod
    def _build_recipes() -> List[Recipe]:
        return [
            Recipe("Grind Flour", ["Wheat", "Stone"], "Flour", "general"),
            Recipe("Bake Bread", ["Flour", "Water"], "Bread", "kitchen", "Craftsman", 15),
            Recipe("Cook Porridge", ["Barley", "Water"], "Porridge", "kitchen"),
            Recipe("Press Oil", ["Olive", "Amphora"], "Olive Oil", "general", "Craftsman", 20),
            Recipe("Make Wine", ["Grapes", "Amphora"], "Wine", "general", time_ticks=50),
            Recipe("Mix Posca", ["Wine", "Water"], "Posca", "general", time_ticks=3),
            Recipe("Mix Mulsum", ["Wine", "Honey Cake"], "Mulsum", "kitchen", time_ticks=5),
            Recipe("Forge Hammer", ["Iron", "Wood"], "Hammer", "forge", "Craftsman", 30),
            Recipe("Forge Gladius", ["Iron", "Iron"], "Gladius", "forge", "Craftsman", 50),
            Recipe("Forge Pugio", ["Iron", "Wood"], "Pugio", "forge", "Craftsman", 25),
            Recipe("Weave Tunic", ["Linen", "Linen"], "Tunic", "general", time_ticks=20),
            Recipe("Make Poultice", ["Herbs", "Linen"], "Herbal Poultice", "general"),
            Recipe("Brew Remedy", ["Herbs", "Water"], "Willow Bark Tea", "kitchen"),
            Recipe("Fire Pottery", ["Clay", "Wood"], "Amphora", "forge", "Craftsman", 15),
            Recipe("Prepare Fish", ["Fish", "Salt"], "Garum", "kitchen", time_ticks=30),
        ]

        # Note: "Flour" and other intermediate items are added implicitly;
        # they need to be in templates if they're outputs:
        # We'll handle missing templates gracefully in create_item.


# Singleton for global access
ITEM_DB = ItemDatabase()
