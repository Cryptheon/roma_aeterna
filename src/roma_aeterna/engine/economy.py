"""
Economy — The economic loop that keeps agents alive and motivated.

Systems:
  1. WAGES: Agents earn denarii by "working" at role-appropriate buildings.
     Working consumes a few ticks and grants money + reduces relevant drives.
  2. MARKETS: Market buildings restock food/drink/goods on a cycle.
     Agents can buy items with denarii.
  3. PRICES: Supply/demand adjusts prices. Scarcity drives prices up.
  4. TRADE: Agent-to-agent trade uses a simple barter/money exchange.

The economy runs on a tick-based cycle:
  - Every WAGE_INTERVAL ticks, agents near their workplace earn wages.
  - Every RESTOCK_INTERVAL ticks, markets receive new inventory.
"""

import random
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from roma_aeterna.config import (
    TPS, WAGE_INTERVAL, RESTOCK_INTERVAL, WORKING_PROXIMITY,
    MARKET_CAPACITY, PRICE_VARIANCE_MIN, PRICE_VARIANCE_MAX,
    SCARCITY_PRICE_MULTIPLIER,
)


# Base prices in denarii
BASE_PRICES: Dict[str, int] = {
    "Bread": 2,
    "Wine": 5,
    "Posca": 2,
    "Water": 1,
    "Honey Cake": 4,
    "Wheat": 3,
    "Salt": 4,
    "Herbs": 3,
    "Olive Oil": 6,
    "Fish": 4,
    "Amphora": 8,
    "Iron": 10,
    "Wood": 5,
    "Clay": 3,
    "Perfume": 12,
    "Silver Ring": 15,
    "Gold Coin": 25,
}

# What each role earns per wage cycle
ROLE_WAGES: Dict[str, int] = {
    "Senator": 15,
    "Patrician": 12,
    "Merchant": 8,
    "Guard (Legionary)": 6,
    "Craftsman": 5,
    "Priest": 4,
    "Gladiator": 10,  # Prize money
    "Plebeian": 3,
}

# Where each role "works" (building interaction_type)
ROLE_WORKPLACES: Dict[str, List[str]] = {
    "Senator": ["deliberate", "speak"],
    "Patrician": ["audience", "deliberate"],
    "Merchant": ["trade"],
    "Guard (Legionary)": ["train"],  # Patrols are implicit
    "Craftsman": ["trade"],  # At workshops
    "Priest": ["pray"],
    "Gladiator": ["train", "spectate"],
    "Plebeian": ["trade"],  # Day labor at markets
}

# What markets restock
MARKET_RESTOCK_ITEMS: List[str] = [
    "Bread", "Bread", "Bread", "Bread",   # Common staples
    "Wine", "Wine",
    "Posca", "Posca", "Posca",
    "Water", "Water", "Water",
    "Honey Cake",
    "Wheat", "Wheat",
    "Salt",
    "Fish", "Fish",
    "Olive Oil",
    "Herbs",
]


@dataclass
class MarketInventory:
    """Tracks what a market building currently has in stock."""
    items: List[str] = field(default_factory=list)
    prices: Dict[str, int] = field(default_factory=dict)
    max_capacity: int = MARKET_CAPACITY


class EconomySystem:
    """Manages the simulation's economic loop."""

    def __init__(self) -> None:
        self.market_inventories: Dict[str, MarketInventory] = {}
        self.price_modifiers: Dict[str, float] = {}  # item -> multiplier
        self._wage_timer: int = 0
        # Start one tick before the interval so markets are stocked immediately
        # on the first simulation tick, not three minutes in.
        self._restock_timer: int = RESTOCK_INTERVAL - 1

    def tick(self, world: Any, agents: List[Any],
             event_bus: Any, current_tick: int) -> None:
        """Run one economy tick."""
        self._wage_timer += 1
        self._restock_timer += 1

        # --- Wage cycle ---
        if self._wage_timer >= WAGE_INTERVAL:
            self._wage_timer = 0
            self._pay_wages(agents, world, event_bus, current_tick)

        # --- Restock cycle ---
        if self._restock_timer >= RESTOCK_INTERVAL:
            self._restock_timer = 0
            self._restock_markets(world, event_bus, current_tick)

    def _pay_wages(self, agents: List[Any], world: Any,
                   event_bus: Any, tick: int) -> None:
        """Pay agents who are near their workplace."""
        from roma_aeterna.core.events import Event, EventType

        for agent in agents:
            if not agent.is_alive:
                continue
            if getattr(agent, "is_animal", False):
                continue

            wage = ROLE_WAGES.get(agent.role, 2)
            workplaces = ROLE_WORKPLACES.get(agent.role, [])

            # Check if agent is near a relevant building
            is_working = False
            for obj in world.objects:
                from roma_aeterna.world.components import Interactable
                interact = obj.get_component(Interactable)
                if not interact:
                    continue
                if interact.interaction_type not in workplaces:
                    continue

                import math
                dist = math.sqrt(
                    (obj.x - agent.x) ** 2 + (obj.y - agent.y) ** 2
                )
                if dist <= WORKING_PROXIMITY and agent.action in ("WORKING", "WORK"):
                    is_working = True
                    break

            if is_working:
                agent.denarii += wage
                agent.memory.add_event(
                    f"Earned {wage} denarii for your work as a {agent.role}.",
                    tick=tick, importance=1.5,
                    memory_type="event", tags=["money", "work"],
                )
                # Working satisfies comfort slightly
                agent.drives["comfort"] = max(0, agent.drives["comfort"] - 3)
            else:
                # Small stipend for existing (the dole)
                dole = max(1, wage // 3)
                agent.denarii += dole

    def _restock_markets(self, world: Any, event_bus: Any,
                         tick: int) -> None:
        """Refill market buildings with fresh goods."""
        from roma_aeterna.world.components import Interactable, Container
        from roma_aeterna.core.events import Event, EventType

        for obj in world.objects:
            interact = obj.get_component(Interactable)
            if not interact or interact.interaction_type != "trade":
                continue

            # Get or create market inventory
            market_name = obj.name
            if market_name not in self.market_inventories:
                self.market_inventories[market_name] = MarketInventory()

            inv = self.market_inventories[market_name]

            # Add random items up to capacity
            while len(inv.items) < inv.max_capacity:
                item_name = random.choice(MARKET_RESTOCK_ITEMS)
                inv.items.append(item_name)

                # Set price with variance
                base = BASE_PRICES.get(item_name, 5)
                modifier = self.price_modifiers.get(item_name, 1.0)
                variance = random.uniform(PRICE_VARIANCE_MIN, PRICE_VARIANCE_MAX)
                inv.prices[item_name] = max(1, int(base * modifier * variance))

            # Emit restock event
            event_bus.emit(Event(
                event_type=EventType.MARKET_RESTOCK.value,
                origin=(obj.x, obj.y),
                radius=15.0,
                data={"market": market_name},
                importance=1.0,
            ))

    def buy_item(self, agent: Any, market_name: str,
                 item_name: str) -> Tuple[bool, str]:
        """Agent attempts to buy an item from a market.

        Returns (success, message).
        """
        inv = self.market_inventories.get(market_name)
        if not inv:
            return False, f"{market_name} has no goods."

        # Case-insensitive search — LLM output may not match DB capitalisation
        actual_name = next(
            (i for i in inv.items if i.lower() == item_name.lower()), None
        )
        if actual_name is None:
            return False, f"{market_name} doesn't have {item_name}."

        price = inv.prices.get(actual_name, 5)
        if agent.denarii < price:
            return False, (
                f"You can't afford {actual_name} ({price} denarii). "
                f"You have {agent.denarii}."
            )

        from roma_aeterna.config import MAX_INVENTORY_SIZE
        if len(agent.inventory) >= MAX_INVENTORY_SIZE:
            return False, "Your inventory is full."

        # Create the item object before touching money or stock —
        # so a missing template can't silently eat denarii.
        from roma_aeterna.world.items import ITEM_DB
        item = ITEM_DB.create_item(actual_name)
        if not item:
            return False, f"{actual_name} is not available."

        # Commit transaction
        agent.denarii -= price
        inv.items.remove(actual_name)
        agent.inventory.append(item)

        # Scarcity: if stock is low, increase price modifier
        remaining = inv.items.count(actual_name)
        if remaining <= 1:
            self.price_modifiers[actual_name] = (
                self.price_modifiers.get(actual_name, 1.0) * SCARCITY_PRICE_MULTIPLIER
            )

        return True, f"You bought {actual_name} for {price} denarii."

    def get_market_listing(self, market_name: str) -> str:
        """Get a text description of what's for sale."""
        inv = self.market_inventories.get(market_name)
        if not inv or not inv.items:
            return f"{market_name} has nothing for sale."

        # Deduplicate with counts
        counts: Dict[str, int] = {}
        for item in inv.items:
            counts[item] = counts.get(item, 0) + 1

        lines = []
        for item_name, count in sorted(counts.items()):
            price = inv.prices.get(item_name, "?")
            lines.append(f"- {item_name} x{count}: {price} denarii each")

        return f"Goods at {market_name}:\n" + "\n".join(lines)

    # ================================================================
    # SERIALIZATION
    # ================================================================

    def serialize(self) -> Dict:
        """Serialize economy state for saving."""
        return {
            "wage_timer": self._wage_timer,
            "restock_timer": self._restock_timer,
            "price_modifiers": dict(self.price_modifiers),
            "markets": {
                name: {
                    "items": inv.items,
                    "prices": dict(inv.prices),
                }
                for name, inv in self.market_inventories.items()
            },
        }

    def restore(self, data: Dict) -> None:
        """Restore economy state from save data."""
        self._wage_timer = data.get("wage_timer", 0)
        self._restock_timer = data.get("restock_timer", 0)
        self.price_modifiers = data.get("price_modifiers", {})
        for name, mdata in data.get("markets", {}).items():
            inv = MarketInventory()
            inv.items = mdata.get("items", [])
            inv.prices = mdata.get("prices", {})
            self.market_inventories[name] = inv
