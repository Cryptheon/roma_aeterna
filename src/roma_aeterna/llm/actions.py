"""
ActionExecutor — Executes validated agent decisions within the simulation engine.

All action handler logic that was in LLMWorker._apply_decision lives here
so that worker.py stays focused on async orchestration.
"""

import math
from typing import Any, Dict, List

from roma_aeterna.config import (
    NEARBY_AGENT_RADIUS, REST_ENERGY_REDUCTION, SLEEP_ENERGY_REDUCTION,
    SLEEP_COMFORT_REDUCTION, INSPECT_OBJECT_RADIUS, INSPECT_AGENT_RADIUS,
    MEMORY_IMMEDIATE_LT_IMPORTANCE, INTERACTION_RADIUS,
    UNARMED_DAMAGE, ATTACK_PROXIMITY_RADIUS,
)


class ActionExecutor:
    """Executes validated agent decisions within the simulation engine."""

    def __init__(self, engine: Any) -> None:
        self.engine = engine

    # ================================================================
    # DISPATCH
    # ================================================================

    def execute(self, agent: Any, decision: Dict) -> None:
        """Dispatch the decision to the appropriate handler."""
        action = decision.get("action", "IDLE").upper()
        tick = self.engine.tick_count
        handler = self._handlers.get(action, self._handle_idle)
        handler(agent, decision, tick)

    @property
    def _handlers(self) -> Dict:
        return {
            "MOVE":     self._handle_move,
            "TALK":     self._handle_talk,
            "INTERACT": self._handle_interact,
            "CONSUME":  self._handle_consume,
            "PICK_UP":  self._handle_pick_up,
            "DROP":     self._handle_drop,
            "REST":     self._handle_rest,
            "SLEEP":    self._handle_sleep,
            "TRADE":    self._handle_trade,
            "BUY":      self._handle_buy,
            "GOTO":     self._handle_goto,
            "WORK":     self._handle_work,
            "INSPECT":  self._handle_inspect,
            "CRAFT":    self._handle_craft,
            "REFLECT":  self._handle_reflect,
            "ATTACK":   self._handle_attack,
            "IDLE":     self._handle_idle,
        }

    # ================================================================
    # HANDLERS
    # ================================================================

    def _handle_move(self, agent: Any, decision: Dict, tick: int) -> None:
        direction = decision.get("direction", "north")
        success, msg = agent.move(direction, self.engine.world)
        if success:
            agent.autopilot._consecutive_path_blocks = 0
            agent.memory.add_event(
                f"Walked {direction}.", tick=tick, importance=0.5,
                memory_type="event",
            )
        else:
            agent.autopilot._consecutive_path_blocks += 1
            agent.memory.add_event(
                f"Tried to go {direction} but: {msg}", tick=tick,
                importance=1.0, tags=["blocked"],
            )
            if agent.autopilot._consecutive_path_blocks >= 3:
                agent.autopilot.clear_path()
            agent.action = "IDLE"

    def _handle_talk(self, agent: Any, decision: Dict, tick: int) -> None:
        target = decision.get("target", "")
        speech = decision.get("speech", "...")
        success, msg = agent.talk_to(
            target, speech, self.engine.agents, tick
        )
        if success:
            agent.action = "TALKING"
            from roma_aeterna.core.events import Event, EventType
            self.engine.event_bus.emit(
                Event(
                    event_type=EventType.SPEECH.value,
                    origin=(int(agent.x), int(agent.y)),
                    radius=6.0,
                    data={"speech": speech, "target": target},
                    source_agent=agent.name,
                    importance=1.5,
                )
            )
        else:
            agent.memory.add_event(
                f"Tried to speak to {target} but they were not nearby.",
                tick=tick, importance=1.0, tags=["blocked"],
            )
            agent.action = "IDLE"

    def _handle_interact(self, agent: Any, decision: Dict, tick: int) -> None:
        target = decision.get("target", "")
        success, msg = agent.interact_with_object(target, self.engine.world)
        agent.memory.add_event(msg, tick=tick, importance=2.0,
                               memory_type="event")
        if success:
            from roma_aeterna.world.components import Interactable
            for obj in self.engine.world.objects:
                if obj.name.lower() == target.lower():
                    interact_comp = obj.get_component(Interactable)
                    if interact_comp and interact_comp.interaction_type == "trade":
                        listing = self.engine.economy.get_market_listing(obj.name)
                        agent.memory.add_event(
                            listing, tick=tick, importance=1.5,
                            memory_type="observation", tags=["market"],
                        )
                    break
        agent.action = "INTERACTING" if success else "IDLE"

    def _handle_consume(self, agent: Any, decision: Dict, tick: int) -> None:
        target = decision.get("target", "")
        success, msg = agent.consume_item(target)
        agent.memory.add_event(msg, tick=tick, importance=1.5,
                               memory_type="event")
        agent.action = "CONSUMING" if success else "IDLE"

    def _handle_pick_up(self, agent: Any, decision: Dict, tick: int) -> None:
        target = decision.get("target", "")
        success, msg = agent.pick_up_item(target, self.engine.world)
        agent.memory.add_event(
            msg, tick=tick,
            importance=1.5 if success else 1.0,
            tags=[] if success else ["blocked"],
        )
        agent.action = "IDLE"

    def _handle_drop(self, agent: Any, decision: Dict, tick: int) -> None:
        target = decision.get("target", "")
        success, msg = agent.drop_item(target, self.engine.world)
        agent.memory.add_event(
            msg, tick=tick,
            importance=0.5 if success else 1.0,
            tags=[] if success else ["blocked"],
        )
        agent.action = "IDLE"

    def _handle_rest(self, agent: Any, decision: Dict, tick: int) -> None:
        agent.drives["energy"] = max(0, agent.drives["energy"] - REST_ENERGY_REDUCTION)
        agent.action = "RESTING"
        agent.memory.add_event(
            "You rest briefly. Your energy eases.", tick=tick,
            importance=0.8, memory_type="event",
        )

    def _handle_sleep(self, agent: Any, decision: Dict, tick: int) -> None:
        agent.drives["energy"] = max(0, agent.drives["energy"] - SLEEP_ENERGY_REDUCTION)
        agent.drives["comfort"] = max(0, agent.drives["comfort"] - SLEEP_COMFORT_REDUCTION)
        agent.action = "SLEEPING"
        from roma_aeterna.agent.status_effects import create_effect
        effect = create_effect("rested")
        if effect:
            agent.status_effects.add(effect)
        agent.memory.add_event(
            "You sleep deeply. Your body recovers.", tick=tick,
            importance=1.0, memory_type="event",
        )

    def _handle_trade(self, agent: Any, decision: Dict, tick: int) -> None:
        target_name = decision.get("target", "")
        offer_name = decision.get("offer", "")
        want_name = decision.get("want", "")

        target_agent = None
        for other in self.engine.agents:
            if (other.name.lower() == target_name.lower()
                    and other.is_alive and other.uid != agent.uid):
                dist = math.sqrt(
                    (other.x - agent.x) ** 2 + (other.y - agent.y) ** 2
                )
                if dist <= NEARBY_AGENT_RADIUS:
                    target_agent = other
                    break

        if not target_agent:
            agent.memory.add_event(
                f"{target_name} is not close enough to trade with.",
                tick=tick, importance=1.0, tags=["blocked"],
            )
            agent.action = "IDLE"
        elif not offer_name or not want_name:
            agent.memory.add_event(
                "Tried to trade but didn't specify what to offer or want.",
                tick=tick, importance=0.5, tags=["blocked"],
            )
            agent.action = "IDLE"
        else:
            offered = next(
                (i for i in agent.inventory
                 if i.name.lower() == offer_name.lower()), None
            )
            wanted = next(
                (i for i in target_agent.inventory
                 if i.name.lower() == want_name.lower()), None
            )

            if not offered:
                agent.memory.add_event(
                    f"You don't have {offer_name} to trade.",
                    tick=tick, importance=1.0, tags=["blocked"],
                )
                agent.action = "IDLE"
            elif not wanted:
                agent.memory.add_event(
                    f"{target_name} doesn't have {want_name}.",
                    tick=tick, importance=1.0, tags=["blocked"],
                )
                agent.action = "IDLE"
            else:
                agent.inventory.remove(offered)
                target_agent.inventory.remove(wanted)
                agent.inventory.append(wanted)
                target_agent.inventory.append(offered)

                agent.memory.add_event(
                    f"Traded your {offer_name} with {target_name} for their {want_name}.",
                    tick=tick, importance=2.5,
                    memory_type="event", tags=["trade"],
                    related_agent=target_name,
                )
                target_agent.memory.add_event(
                    f"{agent.name} traded their {offer_name} for your {want_name}.",
                    tick=tick, importance=2.5,
                    memory_type="event", tags=["trade"],
                    related_agent=agent.name,
                )
                agent.memory.update_relationship(
                    target_name, trust_delta=2.0, tick=tick
                )
                target_agent.memory.update_relationship(
                    agent.name, trust_delta=2.0, tick=tick
                )
                agent.drives["social"] = max(0, agent.drives["social"] - 10)
                agent.action = "TRADING"

    def _handle_buy(self, agent: Any, decision: Dict, tick: int) -> None:
        target_item = decision.get("target", "")
        market = decision.get("market", "")
        market_pos = None

        if not market:
            from roma_aeterna.world.components import Interactable
            for obj in self.engine.world.objects:
                interact = obj.get_component(Interactable)
                if interact and interact.interaction_type == "trade":
                    dist = math.sqrt(
                        (obj.x - agent.x) ** 2 + (obj.y - agent.y) ** 2
                    )
                    if dist <= NEARBY_AGENT_RADIUS:
                        market = obj.name
                        market_pos = (int(obj.x), int(obj.y))
                        break
        else:
            from roma_aeterna.world.components import Interactable
            for obj in self.engine.world.objects:
                if obj.name.lower() == market.lower():
                    dist = math.sqrt(
                        (obj.x - agent.x) ** 2 + (obj.y - agent.y) ** 2
                    )
                    if dist <= NEARBY_AGENT_RADIUS:
                        market_pos = (int(obj.x), int(obj.y))
                    else:
                        market = ""
                        market_pos = None
                    break

        if market:
            success, msg = self.engine.economy.buy_item(
                agent, market, target_item
            )
            agent.memory.add_event(msg, tick=tick, importance=2.0,
                                   memory_type="event", tags=["trade"])
            if market_pos:
                agent.memory.learn_location(market, market_pos)
            agent.action = "TRADING" if success else "IDLE"
        else:
            agent.memory.add_event(
                f"Tried to buy {target_item} but there is no market nearby.",
                tick=tick, importance=1.0, tags=["blocked"],
            )
            agent.action = "IDLE"

    def _handle_goto(self, agent: Any, decision: Dict, tick: int) -> None:
        target = decision.get("target", "")
        target_lower = target.lower()
        location = next(
            (v for k, v in agent.memory.known_locations.items()
             if k.lower() == target_lower),
            None,
        )
        if location:
            agent.autopilot._set_path_toward(
                agent, location, target, self.engine.world
            )
            agent.action = "MOVING"
            agent.memory.add_event(
                f"Set off toward {target}.", tick=tick, importance=1.0,
            )
        else:
            agent.memory.add_event(
                f"Wanted to go to {target} but don't know where it is.",
                tick=tick, importance=1.0, tags=["blocked"],
            )
            agent.action = "IDLE"

    def _handle_work(self, agent: Any, decision: Dict, tick: int) -> None:
        agent.action = "WORKING"
        agent.drives["comfort"] = max(0, agent.drives["comfort"] - 3)
        agent.memory.add_event(
            f"Worked as a {agent.role}.", tick=tick, importance=1.0,
            tags=["work"],
        )

    def _handle_inspect(self, agent: Any, decision: Dict, tick: int) -> None:
        target = decision.get("target", "")
        result = self._inspect_target(agent, target)
        agent.memory.add_event(
            result, tick=tick, importance=1.5,
            memory_type="observation",
        )
        agent.action = "INSPECTING"

    def _handle_craft(self, agent: Any, decision: Dict, tick: int) -> None:
        target_item = decision.get("target", "")
        from roma_aeterna.world.items import ITEM_DB

        recipe = next(
            (r for r in ITEM_DB.recipes if r.output.lower() == target_item.lower()),
            None,
        )

        if not recipe:
            agent.memory.add_event(
                f"I don't know how to craft {target_item}.",
                tick=tick, tags=["blocked"],
            )
            agent.action = "IDLE"
            return

        station_ok = True
        if recipe.station_type != "general":
            from roma_aeterna.world.components import Interactable as _IA
            from roma_aeterna.config import INTERACTION_RADIUS as _IR
            station_ok = False
            for obj in self.engine.world.objects:
                interact = obj.get_component(_IA)
                if interact and interact.interaction_type == recipe.station_type:
                    dist = math.sqrt(
                        (obj.x - agent.x) ** 2 + (obj.y - agent.y) ** 2
                    )
                    if dist <= _IR + 4:
                        station_ok = True
                        break

        if not station_ok:
            agent.memory.add_event(
                f"Tried to craft {target_item} but there is no {recipe.station_type} nearby.",
                tick=tick, importance=1.0, tags=["blocked"],
            )
            agent.action = "IDLE"
            return

        has_all = all(
            any(i.name.lower() == req.lower() for i in agent.inventory)
            for req in recipe.inputs
        )

        if has_all:
            new_item = ITEM_DB.create_item(recipe.output)
            if not new_item:
                agent.memory.add_event(
                    f"Tried to craft {target_item} but the output couldn't be created (missing template).",
                    tick=tick, importance=1.0, tags=["blocked"],
                )
                agent.action = "IDLE"
            else:
                for req in recipe.inputs:
                    for item in agent.inventory:
                        if item.name.lower() == req.lower():
                            agent.inventory.remove(item)
                            break
                agent.inventory.append(new_item)
                agent.memory.add_event(
                    f"Successfully crafted {new_item.name}.",
                    tick=tick, importance=2.0,
                )
                agent.action = "CRAFTING"
        else:
            missing = ", ".join(recipe.inputs)
            agent.memory.add_event(
                f"Tried to craft {target_item} but lacked the materials ({missing}).",
                tick=tick, tags=["blocked"],
            )
            agent.action = "IDLE"

    def _handle_reflect(self, agent: Any, decision: Dict, tick: int) -> None:
        insight = decision.get("note") or decision.get("target", "")
        if insight:
            agent.memory.add_event(
                insight,
                tick=tick,
                importance=MEMORY_IMMEDIATE_LT_IMPORTANCE,
                memory_type="reflection",
                tags=["reflection"],
            )
            agent.action = "REFLECTING"
        else:
            agent.action = "IDLE"

    def _handle_attack(self, agent: Any, decision: Dict, tick: int) -> None:
        target_name = decision.get("target", "")
        item_name = decision.get("item", "")

        target_agent = None
        for other in self.engine.agents:
            if (other.name.lower() == target_name.lower()
                    and other.is_alive and other.uid != agent.uid):
                dist = math.sqrt(
                    (other.x - agent.x) ** 2 + (other.y - agent.y) ** 2
                )
                if dist <= ATTACK_PROXIMITY_RADIUS:
                    target_agent = other
                    break

        if not target_agent:
            agent.memory.add_event(
                f"Tried to attack {target_name} but they are not nearby.",
                tick=tick, importance=1.5, tags=["blocked"],
            )
            agent.action = "IDLE"
            return

        # Resolve weapon damage
        weapon_item = next(
            (i for i in agent.inventory if i.name.lower() == item_name.lower()),
            None,
        ) if item_name else None

        if weapon_item:
            damage = weapon_item.properties.get("damage", UNARMED_DAMAGE)
            weapon_name = weapon_item.name
        else:
            damage = UNARMED_DAMAGE
            weapon_name = "bare hands"

        target_agent.take_damage(damage)
        died = not target_agent.is_alive

        agent.memory.add_event(
            f"You attacked {target_agent.name} with {weapon_name}, dealing {damage:.0f} damage."
            + (" They are dead." if died else ""),
            tick=tick, importance=3.0, tags=["violence"],
        )

        is_animal_target = getattr(target_agent, "is_animal", False)
        if not is_animal_target:
            target_agent.memory.add_event(
                f"{agent.name} attacked you with {weapon_name}! You lost {damage:.0f} health."
                + (" You are dying." if target_agent.health < 20 else ""),
                tick=tick, importance=5.0, tags=["danger", "violence", "negative"],
            )
            target_agent.memory.update_relationship(agent.name, trust_delta=-20, tick=tick)
            if not died:
                target_agent.brain.potential += 5.0

        agent.memory.update_relationship(target_agent.name, trust_delta=-10, tick=tick)
        agent.action = "ATTACKING"

    def _handle_idle(self, agent: Any, decision: Dict, tick: int) -> None:
        agent.action = "IDLE"

    # ================================================================
    # HELPERS
    # ================================================================

    def _inspect_target(self, agent: Any, target: str) -> str:
        """Return a detailed observation of a named target."""
        for obj in self.engine.world.objects:
            if obj.name.lower() == target.lower():
                dist = math.sqrt((obj.x - agent.x) ** 2 + (obj.y - agent.y) ** 2)
                if dist > INSPECT_OBJECT_RADIUS:
                    return f"{target} is too far away to inspect properly."

                parts = [f"You inspect {obj.name} closely."]

                from roma_aeterna.world.components import (
                    Interactable, Structural, WaterFeature, Flammable,
                )
                interact = obj.get_component(Interactable)
                if interact:
                    parts.append(f"It can be used for: {interact.interaction_type}.")
                    if interact.grants_item:
                        parts.append(f"Interacting grants: {interact.grants_item}.")
                    if interact.requires_item:
                        parts.append(f"Requires: {interact.requires_item} to use.")

                struct = obj.get_component(Structural)
                if struct:
                    pct = int(struct.hp / struct.max_hp * 100)
                    cond = (
                        "in excellent condition" if pct > 80 else
                        "in good condition" if pct > 60 else
                        "noticeably damaged" if pct > 30 else
                        "severely damaged and dangerous"
                    )
                    parts.append(f"The structure is {cond} ({pct}% integrity).")

                water = obj.get_component(WaterFeature)
                if water:
                    state = "flowing freely" if water.is_active else "not currently flowing"
                    parts.append(f"The water here is {state}.")

                flam = obj.get_component(Flammable)
                if flam and flam.is_burning:
                    parts.append(f"It is ON FIRE (intensity: {int(flam.fire_intensity)})!")

                return " ".join(parts)

        for other in self.engine.agents:
            if other.name.lower() == target.lower() and other.uid != agent.uid:
                dist = math.sqrt((other.x - agent.x) ** 2 + (other.y - agent.y) ** 2)
                if dist > INSPECT_AGENT_RADIUS:
                    return f"{target} is too far away to observe closely."

                parts = [f"You study {other.name} carefully."]
                parts.append(f"They are a {other.role}, currently {other.action.lower()}.")

                if other.health < 25:
                    parts.append("They look gravely injured — on the verge of collapse.")
                elif other.health < 60:
                    parts.append("They appear hurt and unwell.")
                else:
                    parts.append("They look healthy enough.")

                if other.last_speech:
                    parts.append(f'Their last words were: "{other.last_speech[:60]}".')

                if other.inventory:
                    visible = [i.name for i in other.inventory[:4]]
                    parts.append(f"You notice they carry: {', '.join(visible)}.")

                effects = [e.name for e in other.status_effects.active]
                if effects:
                    parts.append(f"They appear to be: {', '.join(effects)}.")

                return " ".join(parts)

        return f"You look carefully for {target} but find nothing to inspect nearby."

    def _find_nearby_agents(self, agent: Any) -> List[Any]:
        nearby = []
        for other in self.engine.agents:
            if other.uid == agent.uid or not other.is_alive:
                continue
            dist = math.sqrt((other.x - agent.x) ** 2 + (other.y - agent.y) ** 2)
            if dist < NEARBY_AGENT_RADIUS:
                nearby.append(other)
        return nearby
