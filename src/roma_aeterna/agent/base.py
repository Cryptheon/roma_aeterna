"""
Agent — The autonomous citizen of Rome.

Dual-brain architecture:
  - System 1 (Autopilot): Handles routine decisions — flee fire, eat when
    starving, follow paths, basic greetings. Fast, no LLM needed.
  - System 2 (LLM): Handles novel situations — first meetings, conflicting
    goals, complex reasoning. Slow but creative.

The LIF neuron determines WHEN to think. The autopilot determines IF the
LLM is even needed. If the autopilot handles it, the LLM is never called.
"""

import uuid
import math
from typing import List, Dict, Optional, Tuple, Any

from .memory import Memory
from .neuro import LeakyIntegrateAndFire, LIFParameters
from .autopilot import Autopilot
from .status_effects import StatusEffectManager, create_effect
from roma_aeterna.config import (
    PERCEPTION_RADIUS, INTERACTION_RADIUS, MAX_INVENTORY_SIZE,
    HUNGER_RATE, ENERGY_RATE, SOCIAL_RATE, THIRST_RATE, COMFORT_RATE,
    HEALTH_REGEN_RATE,
)


VALID_ACTIONS = {
    "MOVE", "TALK", "INTERACT", "PICK_UP", "DROP", "CONSUME",
    "CRAFT", "TRADE", "REST", "SLEEP", "INSPECT", "IDLE",
    "GOTO",     # Multi-step navigation to a named location
    "BUY",      # Purchase from a market
    "WORK",     # Perform role duties at a building
}

DIRECTION_DELTAS: Dict[str, Tuple[int, int]] = {
    "north":      (0, -1),
    "south":      (0, 1),
    "east":       (1, 0),
    "west":       (-1, 0),
    "northeast":  (1, -1),
    "northwest":  (-1, -1),
    "southeast":  (1, 1),
    "southwest":  (-1, 1),
}


class Agent:
    """A single autonomous agent in the simulation."""

    def __init__(self, name: str, role: str, x: int, y: int,
                 personality_seed: Optional[Dict[str, Any]] = None) -> None:
        self.uid: str = str(uuid.uuid4())[:8]
        self.name: str = name
        self.role: str = role
        self.x: float = float(x)
        self.y: float = float(y)

        # --- Inventory ---
        self.inventory: List[Any] = []
        self.denarii: int = 20

        # --- Biological Drives ---
        self.drives: Dict[str, float] = {
            "hunger":  10.0,
            "thirst":  10.0,
            "energy":  5.0,
            "social":  15.0,
            "comfort": 5.0,
        }
        self.health: float = 100.0
        self.max_health: float = 100.0
        self.is_alive: bool = True

        # --- Personality (must be set before brain, which uses self.role) ---
        self.personality_seed: Dict[str, Any] = personality_seed or {}
        self.personal_goals: List[str] = []
        self.fears: List[str] = []
        self.values: List[str] = []

        # --- Cognitive ---
        self.brain = LeakyIntegrateAndFire(
            self._make_lif_params()
        )
        self.autopilot = Autopilot()
        self.current_time: float = 0.0

        # --- State ---
        self.action: str = "IDLE"
        self.action_target: Optional[str] = None
        self.current_thought: str = "I have just woken up."
        self.waiting_for_llm: bool = False
        self.last_speech: str = ""
        self.movement_cooldown: int = 0
        self.interaction_cooldown: int = 0

        # --- Conversation System ---
        self._pending_conversation: Optional[Dict[str, str]] = None

        # --- Memory & Effects ---
        self.memory = Memory()
        self.status_effects = StatusEffectManager()

        # --- Decision History (for LLM context + inspection) ---
        self.decision_history: List[Dict[str, Any]] = []
        self.prompt_history: List[str] = []
        self.llm_response_log: List[Dict[str, Any]] = []
        self._max_decision_history: int = 20

        # --- Drive History (for past state awareness) ---
        self.drive_snapshots: List[Dict[str, Any]] = []
        self._snapshot_interval: float = 10.0
        self._last_snapshot_time: float = 0.0

        self._init_common_knowledge()

    def _make_lif_params(self) -> "LIFParameters":
        """Create LIF parameters unique to this agent.
        
        Different roles have different cognitive rhythms:
        - Warriors/Guards: low threshold, fast reactions (trained reflexes)
        - Senators/Priests: higher threshold, more deliberate (thoughtful)
        - Merchants/Craftsmen: medium threshold (balanced)
        - Plebeians: slightly random (diverse population)
        
        A per-agent random offset prevents synchronized firing.
        """
        import random as _rng
        
        # Seed per-agent so it's deterministic but unique
        _rng.seed(hash(self.uid) + 42)
        
        role_profiles = {
            "Senator":          {"threshold": 10.0, "decay": 0.06, "refractory": 4.0},
            "Patrician":        {"threshold": 9.0,  "decay": 0.07, "refractory": 3.5},
            "Priest":           {"threshold": 11.0, "decay": 0.05, "refractory": 4.5},
            "Gladiator":        {"threshold": 5.0,  "decay": 0.12, "refractory": 2.0},
            "Guard (Legionary)":{"threshold": 5.5,  "decay": 0.10, "refractory": 2.5},
            "Merchant":         {"threshold": 7.0,  "decay": 0.08, "refractory": 3.0},
            "Craftsman":        {"threshold": 8.0,  "decay": 0.07, "refractory": 3.5},
            "Plebeian":         {"threshold": 7.0,  "decay": 0.09, "refractory": 3.0},
        }
        
        profile = role_profiles.get(self.role, {"threshold": 8.0, "decay": 0.08, "refractory": 3.0})
        
        # Add per-agent randomness (±20%) to desynchronize
        jitter = lambda v: v * (0.8 + _rng.random() * 0.4)
        
        # Restore global random state
        _rng.seed()
        
        return LIFParameters(
            decay_rate=jitter(profile["decay"]),
            threshold=jitter(profile["threshold"]),
            refractory_period=jitter(profile["refractory"]),
        )

    def _init_common_knowledge(self) -> None:
        """Things every Roman citizen would know."""
        self.memory.add_belief("Rome", "is the center of the world", 0.9, "common knowledge")
        self.memory.add_belief("Emperor Marcus Aurelius", "rules Rome wisely", 0.8, "common knowledge")
        self.memory.add_belief("The Forum", "is where business and politics happen", 0.9, "common knowledge")
        self.memory.add_belief("The Colosseum", "hosts gladiatorial games", 0.9, "common knowledge")
        self.memory.add_belief("fire", "is extremely dangerous and spreads fast", 1.0, "common knowledge")
        self.memory.add_belief("the Tiber", "provides water but floods sometimes", 0.7, "common knowledge")
        self.memory.add_belief("fountains", "provide clean drinking water", 0.9, "common knowledge")

    # ================================================================
    # CONVERSATION — Incoming speech triggers responses
    # ================================================================

    def receive_speech(self, speaker_name: str, message: str, tick: int) -> None:
        """Called when another agent speaks to this agent.

        Queues a pending conversation that will be processed on the next
        brain fire or autopilot cycle. This creates actual back-and-forth.
        """
        self._pending_conversation = {
            "speaker": speaker_name,
            "message": message,
            "tick": tick,
        }

        # Record in memory
        self.memory.add_event(
            f"{speaker_name} said to you: \"{message}\"",
            tick=tick, importance=2.5, memory_type="conversation",
            related_agent=speaker_name,
        )
        self.memory.record_conversation(speaker_name, they_said=message)

        # Update relationship
        self.memory.update_relationship(speaker_name, trust_delta=1.0, tick=tick,
                                        note=f"Said: {message[:50]}")

        # Social need reduction
        self.drives["social"] = max(0, self.drives["social"] - 5)

        # Force the brain to fire soon (someone is talking to us!)
        self.brain.potential += 30.0

    def has_pending_conversation(self) -> bool:
        return self._pending_conversation is not None

    def consume_pending_conversation(self) -> Optional[Dict[str, str]]:
        """Retrieve and clear the pending conversation."""
        convo = self._pending_conversation
        self._pending_conversation = None
        return convo

    # ================================================================
    # PERCEPTION
    # ================================================================

    def perceive(self, world: Any, agents: List["Agent"],
                 radius: Optional[int] = None) -> str:
        """Build a natural-language description of what the agent sees."""
        radius = radius or PERCEPTION_RADIUS
        radius_mod = int(self.status_effects.get_modifier("perception_radius", 0))
        effective_radius = max(2, radius + radius_mod)

        sections: List[str] = []

        tile_desc = self._describe_current_tile(world)
        if tile_desc:
            sections.append(f"YOU ARE STANDING ON: {tile_desc}")

        buildings = self._scan_buildings(world, effective_radius)
        if buildings:
            sections.append("STRUCTURES NEARBY:\n" + "\n".join(buildings))

        ground_items = self._scan_ground_items(world, effective_radius)
        if ground_items:
            sections.append("ITEMS ON THE GROUND:\n" + "\n".join(ground_items))

        nearby_agents = self._scan_agents(agents, effective_radius)
        if nearby_agents:
            sections.append("PEOPLE NEARBY:\n" + "\n".join(nearby_agents))

        env = self._describe_environment(world)
        if env:
            sections.append("ENVIRONMENT:\n" + env)

        directions = self._scan_directions(world)
        if directions:
            sections.append("PASSABLE DIRECTIONS: " + ", ".join(directions))

        if not sections:
            return "You see nothing remarkable around you. The area is quiet."

        return "\n\n".join(sections)

    def _scan_buildings(self, world: Any, radius: int) -> List[str]:
        results: List[str] = []
        seen_names: set = set()

        min_x = max(0, int(self.x) - radius)
        max_x = min(world.width, int(self.x) + radius)
        min_y = max(0, int(self.y) - radius)
        max_y = min(world.height, int(self.y) + radius)

        for ty in range(min_y, max_y):
            for tx in range(min_x, max_x):
                tile = world.get_tile(tx, ty)
                if not tile or not tile.building:
                    continue

                bld = tile.building
                if bld.name in seen_names:
                    continue
                seen_names.add(bld.name)

                dist = math.sqrt((tx - self.x) ** 2 + (ty - self.y) ** 2)
                direction = self._get_direction(tx, ty)

                modifiers: List[str] = []
                for comp in bld.components.values():
                    if getattr(comp, "is_burning", False):
                        intensity = getattr(comp, "fire_intensity", 0)
                        if intensity > 10:
                            modifiers.append("ENGULFED IN FLAMES!")
                        else:
                            modifiers.append("ON FIRE!")

                from roma_aeterna.world.components import Structural, Interactable
                struct = bld.get_component(Structural)
                if struct and struct.hp < struct.max_hp * 0.3:
                    modifiers.append("badly damaged, looks about to collapse")
                elif struct and struct.hp < struct.max_hp * 0.5:
                    modifiers.append("damaged")

                interact = bld.get_component(Interactable)
                if interact:
                    modifiers.append(f"[{interact.interaction_type}]")

                mod_str = f" ({', '.join(modifiers)})" if modifiers else ""
                results.append(
                    f"- {bld.name}{mod_str}: {dist:.0f}m to the {direction}"
                )
                self.memory.learn_location(bld.name, (tx, ty))

        return results

    def _scan_ground_items(self, world: Any, radius: int) -> List[str]:
        results: List[str] = []
        min_x = max(0, int(self.x) - radius)
        max_x = min(world.width, int(self.x) + radius)
        min_y = max(0, int(self.y) - radius)
        max_y = min(world.height, int(self.y) + radius)

        for ty in range(min_y, max_y):
            for tx in range(min_x, max_x):
                tile = world.get_tile(tx, ty)
                if not tile:
                    continue
                for item in getattr(tile, "ground_items", []):
                    dist = math.sqrt((tx - self.x) ** 2 + (ty - self.y) ** 2)
                    direction = self._get_direction(tx, ty)
                    results.append(f"- {item.name}: {dist:.0f}m to the {direction}")
        return results

    def _scan_agents(self, agents: List["Agent"], radius: int) -> List[str]:
        results: List[str] = []
        for other in agents:
            if other.uid == self.uid or not other.is_alive:
                continue
            dist = math.sqrt((other.x - self.x) ** 2 + (other.y - self.y) ** 2)
            if dist > radius:
                continue

            direction = self._get_direction(other.x, other.y)
            rel = self.memory.relationships.get(other.name)
            known = f" (you know them)" if rel and rel.familiarity > 10 else ""

            activity = other.action.lower()
            speech = ""
            if other.last_speech and dist < INTERACTION_RADIUS * 2:
                speech = f', saying: "{other.last_speech}"'

            distress = ""
            if other.health < 30:
                distress = ", looks badly injured"
            elif other.status_effects.has_effect("Burned"):
                distress = ", appears burned"

            results.append(
                f"- {other.name}, a {other.role}, {dist:.0f}m to the {direction}, "
                f"appears to be {activity}{distress}{known}{speech}"
            )
        return results

    def _describe_environment(self, world: Any) -> str:
        parts: List[str] = []
        weather = getattr(world, "_current_weather_desc", None)
        if weather:
            parts.append(weather)
        time_of_day = getattr(world, "_current_time_desc", None)
        if time_of_day:
            parts.append(time_of_day)

        tile = world.get_tile(int(self.x), int(self.y))
        if tile:
            effects = getattr(tile, "effects", [])
            if "smoke" in effects:
                parts.append("Thick smoke fills the air here, stinging your eyes.")
            if "rubble" in effects:
                parts.append("The ground is covered in rubble from a collapsed building.")

        return " ".join(parts) if parts else ""

    def _describe_current_tile(self, world: Any) -> str:
        tile = world.get_tile(int(self.x), int(self.y))
        if not tile:
            return "unknown terrain"

        terrain_names = {
            "road": "a paved Roman road",
            "grass": "a grassy patch",
            "dirt": "bare earth",
            "sand": "sandy ground",
            "water": "shallow water",
            "marble_floor": "polished marble flooring",
            "plaza": "an open plaza",
            "forest": "dense woodland",
            "mountain": "rocky rubble",
        }
        desc = terrain_names.get(tile.terrain_type, tile.terrain_type)
        if tile.building:
            desc += f" (inside/near {tile.building.name})"
        return desc

    def _scan_directions(self, world: Any) -> List[str]:
        passable: List[str] = []
        for direction, (dx, dy) in DIRECTION_DELTAS.items():
            nx, ny = int(self.x) + dx, int(self.y) + dy
            tile = world.get_tile(nx, ny)
            if tile and tile.is_walkable:
                passable.append(direction)
        return passable

    def _get_direction(self, tx: float, ty: float) -> str:
        dx, dy = tx - self.x, ty - self.y
        if dx == 0 and dy == 0:
            return "here"
        angle = math.degrees(math.atan2(dy, dx))
        if angle < 0:
            angle += 360
        dirs = ["east", "southeast", "south", "southwest",
                "west", "northwest", "north", "northeast"]
        idx = int((angle + 22.5) // 45) % 8
        return dirs[idx]

    # ================================================================
    # MOVEMENT
    # ================================================================

    def move(self, direction: str, world: Any) -> Tuple[bool, str]:
        """Attempt to move one tile in the given direction."""
        if self.movement_cooldown > 0:
            return False, "You are still catching your breath."

        direction = direction.lower().strip()
        delta = DIRECTION_DELTAS.get(direction)
        if delta is None:
            return False, f"Unknown direction: {direction}"

        dx, dy = delta
        nx, ny = int(self.x) + dx, int(self.y) + dy

        tile = world.get_tile(nx, ny)
        if tile is None:
            return False, "You cannot go that way — edge of the world."
        if not tile.is_walkable:
            return False, f"The way {direction} is blocked ({tile.terrain_type})."

        base_cost = max(1, int(tile.movement_cost))
        self.movement_cooldown = base_cost

        self.x = float(nx)
        self.y = float(ny)
        self.action = "MOVING"
        self.drives["energy"] += 0.5 * tile.movement_cost

        return True, f"You move {direction}."

    # ================================================================
    # INTERACTION
    # ================================================================

    def interact_with_object(self, obj_name: str, world: Any) -> Tuple[bool, str]:
        from roma_aeterna.world.components import (
            Interactable, WaterFeature, Container, CraftingStation,
            Shelter, InfoSource, Liquid,
        )

        target = None
        for obj in world.objects:
            if obj.name.lower() == obj_name.lower():
                dist = math.sqrt((obj.x - self.x) ** 2 + (obj.y - self.y) ** 2)
                if dist <= INTERACTION_RADIUS + 3:
                    target = obj
                    break

        if target is None:
            return False, f"Cannot find '{obj_name}' nearby."

        interact = target.get_component(Interactable)
        if not interact:
            return False, f"{obj_name} cannot be interacted with."

        if interact.cooldown > 0:
            return False, f"{obj_name} is busy right now."

        if interact.current_users >= interact.capacity:
            return False, f"{obj_name} is full."

        if interact.requires_item:
            has_item = any(i.name == interact.requires_item for i in self.inventory)
            if not has_item:
                return False, f"You need a {interact.requires_item} to use {obj_name}."

        result = self._execute_interaction(target, interact)

        if interact.grants_effect:
            effect = create_effect(interact.grants_effect)
            if effect:
                self.status_effects.add(effect)

        if interact.grants_item:
            from roma_aeterna.world.items import ITEM_DB
            item = ITEM_DB.create_item(interact.grants_item)
            if item and len(self.inventory) < MAX_INVENTORY_SIZE:
                self.inventory.append(item)
                result += f" You receive {item.name}."

        interact.cooldown = interact.cooldown_max
        return True, result

    def _execute_interaction(self, target: Any, interact: Any) -> str:
        itype = interact.interaction_type

        if itype == "pray":
            self.drives["comfort"] = max(0, self.drives["comfort"] - 15)
            self.drives["social"] = max(0, self.drives["social"] - 5)
            effect = create_effect("blessed")
            if effect:
                self.status_effects.add(effect)
            return f"You pray at {target.name}. A sense of peace washes over you."
        elif itype == "drink":
            from roma_aeterna.world.components import Liquid
            liquid = target.get_component(Liquid)
            if liquid and liquid.amount > 0:
                self.drives["thirst"] = max(0, self.drives["thirst"] - 40)
                liquid.amount -= 5
                effect = create_effect("refreshed")
                if effect:
                    self.status_effects.add(effect)
                return f"You drink fresh water from {target.name}. Refreshing!"
            return f"{target.name} is dry."
        elif itype == "rest":
            self.drives["energy"] = max(0, self.drives["energy"] - 20)
            self.drives["comfort"] = max(0, self.drives["comfort"] - 10)
            return f"You rest at {target.name}. Your body relaxes."
        elif itype == "trade":
            return f"You browse the wares at {target.name}."
        elif itype == "spectate":
            self.drives["social"] = max(0, self.drives["social"] - 15)
            self.drives["comfort"] = max(0, self.drives["comfort"] - 5)
            return f"You watch the spectacle at {target.name}. The crowd roars!"
        elif itype == "train":
            self.drives["energy"] += 15
            effect = create_effect("exercised")
            if effect:
                self.status_effects.add(effect)
            return f"You train at {target.name}. Your muscles burn but you feel stronger."
        elif itype == "speak":
            self.drives["social"] = max(0, self.drives["social"] - 20)
            return f"You address the crowd from {target.name}."
        elif itype == "deliberate":
            self.drives["social"] = max(0, self.drives["social"] - 10)
            return f"You participate in deliberation at {target.name}."
        elif itype == "audience":
            return f"You seek an audience at {target.name}."
        elif itype == "inspect":
            return f"You carefully inspect {target.name}."

        return f"You interact with {target.name}."

    def talk_to(self, target_name: str, message: str, agents: List["Agent"],
                tick: int) -> Tuple[bool, str]:
        """Speak to a nearby agent. Triggers their conversation response."""
        target = None
        for other in agents:
            if other.name.lower() == target_name.lower() and other.uid != self.uid:
                dist = math.sqrt((other.x - self.x) ** 2 + (other.y - self.y) ** 2)
                if dist <= INTERACTION_RADIUS * 2:
                    target = other
                    break

        if target is None:
            return False, f"{target_name} is not nearby."

        # Record in speaker's memory
        self.last_speech = message
        self.memory.add_event(
            f"You said to {target.name}: \"{message}\"",
            tick=tick, importance=2.0, memory_type="conversation",
            related_agent=target.name,
        )
        self.memory.record_conversation(target.name, i_said=message)
        self.memory.update_relationship(target.name, trust_delta=1.0, tick=tick)
        self.drives["social"] = max(0, self.drives["social"] - 10)

        # Deliver to listener — this queues their response
        target.receive_speech(self.name, message, tick)

        # Share gossip during conversation
        gossip = self.memory.get_gossip_for_conversation()
        if gossip and target.name not in gossip.text:
            target.memory.add_event(
                f"{self.name} told you: \"{gossip.text}\"",
                tick=tick, importance=gossip.importance * 0.7,
                memory_type="conversation", related_agent=self.name,
                tags=["gossip"],
            )

        return True, f"You speak to {target.name}."

    def consume_item(self, item_name: str) -> Tuple[bool, str]:
        target_item = None
        for item in self.inventory:
            if item.name.lower() == item_name.lower():
                target_item = item
                break

        if target_item is None:
            return False, f"You don't have '{item_name}'."

        props = target_item.properties

        if target_item.is_spoiled():
            self.inventory.remove(target_item)
            effect = create_effect("food_poisoning")
            if effect:
                self.status_effects.add(effect)
            self.memory.add_event(
                f"Ate rotten {target_item.name} and got sick!",
                tick=int(self.current_time), importance=4.0,
                tags=["negative", "food"],
            )
            # Strong negative preference — remember this!
            self.memory.update_preference(target_item.name, -0.5)
            return True, f"The {target_item.name} was rotten! You feel terrible."

        results: List[str] = []

        if target_item.item_type in ("food", "drink", "medicine"):
            if "nutrition" in props:
                self.drives["hunger"] = max(0, self.drives["hunger"] - props["nutrition"])
                results.append("satisfying")
            if "thirst_reduce" in props:
                self.drives["thirst"] = max(0, self.drives["thirst"] - props["thirst_reduce"])
                results.append("quenching")
            if "thirst_increase" in props:
                self.drives["thirst"] += props["thirst_increase"]
            if "energy_restore" in props:
                self.drives["energy"] = max(0, self.drives["energy"] - props["energy_restore"])
            if "comfort" in props:
                self.drives["comfort"] = max(0, self.drives["comfort"] - props["comfort"])
                results.append("comforting")
            if "heal" in props:
                self.health = min(self.max_health, self.health + props["heal"])
                results.append("healing")
            if "intoxication" in props and props["intoxication"] > 5:
                effect = create_effect("intoxicated")
                if effect:
                    self.status_effects.add(effect)
                results.append("intoxicating")

            if props.get("nutrition", 0) >= 20:
                effect = create_effect("well_fed")
                if effect:
                    self.status_effects.add(effect)

            self.inventory.remove(target_item)
            # Positive preference for good food
            self.memory.update_preference(target_item.name, 0.3)
            desc = " and ".join(results) if results else "unremarkable"
            return True, f"You consume the {target_item.name}. It is {desc}."

        return False, f"You can't consume {target_item.name}."

    def pick_up_item(self, item_name: str, world: Any) -> Tuple[bool, str]:
        if len(self.inventory) >= MAX_INVENTORY_SIZE:
            return False, "Your inventory is full."

        tile = world.get_tile(int(self.x), int(self.y))
        if not tile:
            return False, "Nothing here."

        ground_items = getattr(tile, "ground_items", [])
        for item in ground_items:
            if item.name.lower() == item_name.lower():
                ground_items.remove(item)
                self.inventory.append(item)
                return True, f"You pick up {item.name}."

        return False, f"No '{item_name}' here on the ground."

    def drop_item(self, item_name: str, world: Any) -> Tuple[bool, str]:
        for item in self.inventory:
            if item.name.lower() == item_name.lower():
                self.inventory.remove(item)
                tile = world.get_tile(int(self.x), int(self.y))
                if tile:
                    if not hasattr(tile, "ground_items"):
                        tile.ground_items = []
                    tile.ground_items.append(item)
                return True, f"You drop {item.name} on the ground."
        return False, f"You don't have '{item_name}'."

    # ================================================================
    # BIOLOGY
    # ================================================================

    def update_biological(self, dt: float, weather_fx: Dict) -> bool:
        """Update drives, health, status effects. Returns True if brain fires."""
        self.current_time += dt

        if not self.is_alive:
            return False

        self.status_effects.tick()

        if self.movement_cooldown > 0:
            self.movement_cooldown -= 1
        if self.interaction_cooldown > 0:
            self.interaction_cooldown -= 1

        # Metabolic rates
        hunger_mult = self.status_effects.get_modifier("hunger_rate", 1.0)
        energy_mult = self.status_effects.get_modifier("energy_rate", 1.0)
        thirst_mult = self.status_effects.get_modifier("thirst_rate", 1.0)
        comfort_mult = self.status_effects.get_modifier("comfort_rate", 1.0)

        if "heatwave" in weather_fx or weather_fx.get("thirst", 0) > 0:
            thirst_mult *= 1.8
            energy_mult *= 1.3
        if "energy_drain" in weather_fx:
            energy_mult *= weather_fx["energy_drain"]

        if self.action == "MOVING":
            hunger_mult *= 1.5
            energy_mult *= 1.5
            thirst_mult *= 1.3

        self.drives["hunger"] += HUNGER_RATE * hunger_mult * dt
        self.drives["thirst"] += THIRST_RATE * thirst_mult * dt
        self.drives["energy"] += ENERGY_RATE * energy_mult * dt
        self.drives["social"] += SOCIAL_RATE * dt
        self.drives["comfort"] += COMFORT_RATE * comfort_mult * dt

        for k in self.drives:
            self.drives[k] = min(100.0, max(0.0, self.drives[k]))

        # Health
        regen = HEALTH_REGEN_RATE + self.status_effects.get_modifier("health_regen", 0.0)
        if self.drives["hunger"] > 90:
            self.health -= 0.5 * dt
        if self.drives["thirst"] > 90:
            self.health -= 0.8 * dt
        elif regen > 0 and self.drives["hunger"] < 50 and self.drives["energy"] < 50:
            self.health = min(self.max_health, self.health + regen * dt)

        if self.health <= 0:
            self.is_alive = False
            self.action = "DEAD"
            return False

        input_current = self._compute_urgency()
        
        # Periodically snapshot drives for trend awareness
        if self.current_time - self._last_snapshot_time >= self._snapshot_interval:
            self._last_snapshot_time = self.current_time
            self.drive_snapshots.append({
                "tick": int(self.current_time),
                "health": round(self.health, 1),
                "drives": {k: round(v, 1) for k, v in self.drives.items()},
            })
            if len(self.drive_snapshots) > 6:  # Keep last ~60 seconds
                self.drive_snapshots.pop(0)
        
        return self.brain.update(dt, input_current, self.current_time)

    def _compute_urgency(self) -> float:
        urgency = 0.0

        drive_weights = {
            "hunger": 10.0, "thirst": 12.0, "energy": 5.0,
            "social": 2.0, "comfort": 1.5,
        }
        for drive_name, drive_val in self.drives.items():
            ratio = drive_val / 100.0
            weight = drive_weights.get(drive_name, 1.0)
            urgency += (ratio ** 2) * weight

        urgency += self.status_effects.get_total_urgency()

        if self.health < self.max_health:
            health_ratio = 1.0 - (self.health / self.max_health)
            urgency += (health_ratio ** 1.5) * 20.0

        # Pending conversation adds urgency (someone is talking to us!)
        if self._pending_conversation:
            urgency += 25.0

        urgency += 1.0
        return urgency

    # ================================================================
    # INSPECTION DATA
    # ================================================================

    def get_inspection_data(self) -> List[str]:
        lines = [
            f"Name: {self.name}",
            f"Role: {self.role}",
            f"Health: {int(self.health)}/{int(self.max_health)}",
            f"Denarii: {self.denarii}",
            f"--- Drives ---",
            f"Hunger: {int(self.drives['hunger'])}%",
            f"Thirst: {int(self.drives['thirst'])}%",
            f"Energy: {int(self.drives['energy'])}%",
            f"Social: {int(self.drives['social'])}%",
            f"Comfort: {int(self.drives['comfort'])}%",
            f"--- Mind ---",
            f"Urgency: {int(self.brain.potential)}/{int(self.brain.params.threshold)}",
            f"Action: {self.action}",
            f"Autopilot: {self.autopilot.state.value}",
            f"Thought: {self.current_thought[:40]}...",
        ]
        effects = [e.name for e in self.status_effects.active]
        if effects:
            lines.append(f"Effects: {', '.join(effects)}")
        inv_names = [i.name for i in self.inventory[:5]]
        if inv_names:
            lines.append(f"Carrying: {', '.join(inv_names)}")
        if self.autopilot.path:
            lines.append(f"Path: {self.autopilot.destination_name} ({len(self.autopilot.path)} steps)")
        return lines

    def record_decision(self, decision: Dict[str, Any], source: str = "llm") -> None:
        """Record a decision for history tracking.
        
        Args:
            decision: The decision dict (thought, action, target, etc.)
            source: 'llm' or 'autopilot'
        """
        entry = {
            "tick": int(self.current_time),
            "source": source,
            "thought": decision.get("thought", "..."),
            "action": decision.get("action", "IDLE"),
            "target": decision.get("target", ""),
            "speech": decision.get("speech", ""),
        }
        self.decision_history.append(entry)
        if len(self.decision_history) > self._max_decision_history:
            self.decision_history.pop(0)

    def record_prompt(self, prompt: str) -> None:
        """Store the last prompt sent to the LLM for inspection."""
        self.prompt_history.append(prompt)
        if len(self.prompt_history) > 5:
            self.prompt_history.pop(0)

    def record_llm_response(self, raw_text: str, parsed: Any = None, error: str = "") -> None:
        """Store the raw LLM response for debugging."""
        entry = {
            "tick": int(self.current_time),
            "raw": raw_text[:500],  # Truncate to avoid memory bloat
            "parsed": str(parsed)[:200] if parsed else None,
            "error": error,
        }
        self.llm_response_log.append(entry)
        if len(self.llm_response_log) > 10:
            self.llm_response_log.pop(0)

    def get_decision_history_summary(self, n: int = 5) -> str:
        """Return last N decisions as text for LLM context."""
        if not self.decision_history:
            return "You have not taken any actions yet."
        recent = self.decision_history[-n:]
        lines = []
        for d in recent:
            src = "[auto]" if d["source"] == "autopilot" else "[think]"
            action_desc = f"{d['action']}"
            if d.get("target"):
                action_desc += f" → {d['target']}"
            if d.get("speech"):
                action_desc += f' (said: "{d["speech"][:40]}")'
            lines.append(f"  {src} {action_desc}: {d['thought'][:60]}")
        return "\n".join(lines)

    def get_full_history_text(self) -> str:
        """Return full decision history for the inspection window."""
        if not self.decision_history:
            return "No decisions recorded yet."
        lines = []
        for i, d in enumerate(self.decision_history):
            src = "AUTOPILOT" if d["source"] == "autopilot" else "LLM"
            lines.append(f"[Tick {d['tick']}] ({src}) Action: {d['action']}")
            lines.append(f"  Thought: {d['thought']}")
            if d.get("target"):
                lines.append(f"  Target: {d['target']}")
            if d.get("speech"):
                lines.append(f"  Speech: \"{d['speech']}\"")
            lines.append("")
        return "\n".join(lines)

    def get_inventory_summary(self) -> str:
        if not self.inventory:
            return "You are carrying nothing."
        items_desc = []
        for item in self.inventory:
            freshness = ""
            if getattr(item, "spoilable", False) and getattr(item, "freshness", 1.0) < 0.5:
                freshness = " (going stale)"
            items_desc.append(f"- {item.name}{freshness}")
        return f"You carry ({len(self.inventory)}/{MAX_INVENTORY_SIZE}):\n" + "\n".join(items_desc)

    def get_drives_summary(self) -> str:
        labels = {
            "hunger": ["satisfied", "peckish", "hungry", "starving"],
            "thirst": ["hydrated", "thirsty", "parched", "desperately thirsty"],
            "energy": ["energetic", "a bit tired", "exhausted", "about to collapse"],
            "social": ["content", "wanting company", "lonely", "desperately lonely"],
            "comfort": ["comfortable", "uneasy", "miserable", "in agony"],
        }
        parts: List[str] = []
        for drive, value in self.drives.items():
            bucket = min(3, int(value / 25))
            word = labels.get(drive, ["fine", "ok", "bad", "terrible"])[bucket]
            
            # Add trend indicator from snapshots
            trend = ""
            if len(self.drive_snapshots) >= 2:
                prev_val = self.drive_snapshots[-2]["drives"].get(drive, value)
                delta = value - prev_val
                if delta > 5:
                    trend = " ↑ rising"
                elif delta < -5:
                    trend = " ↓ falling"
            
            parts.append(f"- {drive.capitalize()}: {word} ({int(value)}%){trend}")
        return "\n".join(parts)

    def get_past_states_summary(self, n: int = 3) -> str:
        """Return recent drive snapshots as text for LLM context."""
        if len(self.drive_snapshots) < 2:
            return "No prior state data yet."
        
        recent = self.drive_snapshots[-n:]
        lines = []
        for snap in recent:
            d = snap["drives"]
            lines.append(
                f"  Tick {snap['tick']}: HP={snap['health']}, "
                f"Hunger={d['hunger']:.0f}%, Thirst={d['thirst']:.0f}%, "
                f"Energy={d['energy']:.0f}%, Social={d['social']:.0f}%"
            )
        return "\n".join(lines)