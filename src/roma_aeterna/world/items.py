from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Item:
    name: str
    type: str  # resource, food, tool
    properties: dict = None

@dataclass
class Recipe:
    inputs: List[str]
    output: str

class ItemDatabase:
    def __init__(self):
        self.items = {
            "Wheat": Item("Wheat", "resource"),
            "Stone": Item("Stone", "resource"),
            "Flour": Item("Flour", "resource"),
            "Bread": Item("Bread", "food", {"nutrition": 30}),
            "Rotten Bread": Item("Rotten Bread", "food", {"nutrition": 5, "sickness": 20})
        }
        self.recipes = [
            Recipe(["Wheat", "Stone"], "Flour"),
            Recipe(["Flour", "Water"], "Dough")
        ]

    def craft(self, inputs: List[str]) -> Optional[Item]:
        sorted_inputs = sorted(inputs)
        for r in self.recipes:
            if sorted(r.inputs) == sorted_inputs:
                return self.items.get(r.output)
        return None
