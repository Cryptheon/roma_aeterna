"""
LLM Worker — Async inference thread that processes agent decisions.

Now handles two types of requests:
  1. Regular decisions (what should I do next?)
  2. Conversation responses (someone spoke to me, what do I say back?)

The worker checks for pending conversations first. If present, it builds
a conversation-specific prompt. Otherwise, it builds the standard
decision prompt.
"""

import threading
import asyncio
import json
import random
from typing import Any, Dict, Optional, List

from openai import AsyncOpenAI

from roma_aeterna.config import (
    VLLM_URL, VLLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS, LLM_BATCH_SIZE,
    NEARBY_AGENT_RADIUS, REST_ENERGY_REDUCTION, SLEEP_ENERGY_REDUCTION,
    SLEEP_COMFORT_REDUCTION, INSPECT_OBJECT_RADIUS, INSPECT_AGENT_RADIUS,
    MEMORY_IMMEDIATE_LT_IMPORTANCE,
)
from .prompts import build_prompt


class LLMWorker(threading.Thread):
    """Background thread for batched LLM inference."""

    def __init__(self, engine: Any) -> None:
        super().__init__()
        self.engine = engine
        self.input_queue: List[Any] = []
        self.lock = threading.Lock()
        self.daemon = True
        self.batch_size: int = LLM_BATCH_SIZE
        self.use_mock: bool = False
        
    def queue_request(self, agent: Any) -> None:
        with self.lock:
            if agent not in self.input_queue:
                self.input_queue.append(agent)

    def run(self) -> None:
        asyncio.run(self._async_loop())

    async def _async_loop(self) -> None:
        print("[LLM] Worker started")
        client = AsyncOpenAI(base_url=VLLM_URL, api_key="vllm")

        while True:
            batch: List[Any] = []
            with self.lock:
                if self.input_queue:
                    chunk = self.input_queue[:self.batch_size]
                    self.input_queue = self.input_queue[len(chunk):]
                    batch = chunk

            if not batch:
                await asyncio.sleep(0.1)
                continue

            tasks = []
            for agent in batch:
                tasks.append(self._process_agent(client, agent))
            await asyncio.gather(*tasks)

    async def _process_agent(self, client: Any, agent: Any) -> None:
        """Run a single unified decision cycle.

        Incoming speech (if any) is surfaced as context inside the regular
        prompt — the agent freely decides whether to reply, ignore, or do
        something else entirely.
        """
        try:
            decision = await self._handle_decision(client, agent)
            if decision:
                self._apply_decision(agent, decision)
        except Exception as e:
            print(f"[LLM] Error for {agent.name}: {e}")
        finally:
            # Conversation context consumed — clear it regardless of what
            # the agent decided to do.
            agent._pending_conversation = None
            agent.waiting_for_llm = False

    # ================================================================
    # DECISION HANDLING
    # ================================================================

    async def _handle_decision(self, client: Any,
                               agent: Any) -> Optional[Dict]:
        """Generate a full decision for the agent."""
        if self.use_mock:
            return await self._mock_decision(agent)

        prompt = build_prompt(
            agent, self.engine.world,
            self.engine.agents, self.engine.weather,
            economy=self.engine.economy,
        )
        agent.record_prompt(prompt)
        try:
            response = await client.chat.completions.create(
                model=VLLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_TOKENS,
            )
            content = response.choices[0].message.content
            parsed = self._parse_json(content)
            
            # Log the raw response for diagnostics
            if parsed:
                agent.record_llm_response(content, parsed)
            else:
                agent.record_llm_response(content, None, error="JSON parse failed")
                print(f"[LLM] Parse failed for {agent.name}. Raw: {content[:150]}")
            
            return parsed
        except Exception as e:
            agent.record_llm_response("", None, error=str(e))
            print(f"[LLM] Inference error: {e}")

        return await self._mock_decision(agent)

    async def _mock_decision(self, agent: Any) -> Dict:
        """Mock decision when LLM is unavailable.

        This is the fallback, not the primary decision-maker.
        The autopilot handles most routine cases; this covers
        what's left: exploration, novel interactions, complex needs.
        """
        await asyncio.sleep(0.03)

        drives = agent.drives

        # Use memory to find resources for unmet needs
        if drives["thirst"] > 50:
            loc = agent.memory.get_location_for_need("thirst")
            if loc:
                name, pos = loc
                return {
                    "thought": f"I'm thirsty. I should head to {name}.",
                    "action": "GOTO",
                    "target": name,
                }

        if drives["hunger"] > 50:
            # Try to buy food if we have money
            if agent.denarii >= 3:
                loc = agent.memory.get_location_for_need("hunger")
                if loc:
                    name, pos = loc
                    return {
                        "thought": f"I'm hungry and have coin. Let me visit {name}.",
                        "action": "GOTO",
                        "target": name,
                    }

            loc = agent.memory.get_location_for_need("hunger")
            if loc:
                name, pos = loc
                return {
                    "thought": f"I need food. Maybe I can find some at {name}.",
                    "action": "GOTO",
                    "target": name,
                }

        if drives["social"] > 50:
            nearby = self._find_nearby_agents(agent)
            if nearby:
                target = random.choice(nearby)
                rel = agent.memory.relationships.get(target.name)

                # Different greetings for strangers vs friends
                if rel and rel.familiarity > 10:
                    greetings = [
                        f"Salve, {target.name}! How have you been?",
                        f"{target.name}! What news from the city?",
                    ]
                else:
                    greetings = [
                        f"Salve, friend. I am {agent.name}, a {agent.role}.",
                        f"Ave! I don't believe we've met. I'm {agent.name}.",
                    ]

                return {
                    "thought": f"I should introduce myself to {target.name}." if not rel
                               else f"Good to see {target.name} again.",
                    "action": "TALK",
                    "target": target.name,
                    "speech": random.choice(greetings),
                }

        if drives["comfort"] > 50:
            loc = agent.memory.get_location_for_need("comfort")
            if loc:
                name, pos = loc
                return {
                    "thought": f"I need some peace. {name} might help.",
                    "action": "GOTO",
                    "target": name,
                }

        # Default: explore
        directions = list(agent._scan_directions(self.engine.world))
        if not directions:
            directions = ["north", "south", "east", "west"]

        thoughts = [
            "Let me see what lies in this direction.",
            "I should explore the area.",
            f"As a {agent.role}, I should be about my duties.",
            "Perhaps I'll find something interesting nearby.",
        ]
        return {
            "thought": random.choice(thoughts),
            "action": "MOVE",
            "direction": random.choice(directions),
        }

    def _inspect_target(self, agent: Any, target: str) -> str:
        """Return a detailed observation of a named target (building, agent, or item)."""
        import math

        # --- World objects (buildings, fountains, etc.) ---
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

        # --- Nearby agents ---
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
        import math
        nearby = []
        for other in self.engine.agents:
            if other.uid == agent.uid or not other.is_alive:
                continue
            dist = math.sqrt((other.x - agent.x) ** 2 + (other.y - agent.y) ** 2)
            if dist < NEARBY_AGENT_RADIUS:
                nearby.append(other)
        return nearby

    # ================================================================
    # APPLY DECISION — Execute validated actions
    # ================================================================

    def _apply_decision(self, agent: Any, decision: Dict) -> None:
        """Validate and execute the agent's decision."""
        with self.engine.lock:
            # Record this decision in the agent's history
            source = "autopilot" if decision.get("_autopilot") else "llm"
            agent.record_decision(decision, source=source)

            thought = decision.get("thought", "...")
            action = decision.get("action", "IDLE").upper()
            agent.current_thought = thought

            tick = self.engine.tick_count

            if action == "MOVE":
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

            elif action == "TALK":
                target = decision.get("target", "")
                speech = decision.get("speech", "...")
                success, msg = agent.talk_to(
                    target, speech, self.engine.agents, tick
                )
                if success:
                    agent.action = "TALKING"
                    # Broadcast speech event for nearby agents
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

            elif action == "INTERACT":
                target = decision.get("target", "")
                success, msg = agent.interact_with_object(target, self.engine.world)
                agent.memory.add_event(msg, tick=tick, importance=2.0,
                                       memory_type="event")
                # If this was a market visit, record the current stock so the
                # agent knows what to BUY on the next decision cycle.
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

            elif action == "CONSUME":
                target = decision.get("target", "")
                success, msg = agent.consume_item(target)
                agent.memory.add_event(msg, tick=tick, importance=1.5,
                                       memory_type="event")
                agent.action = "CONSUMING" if success else "IDLE"

            elif action == "PICK_UP":
                target = decision.get("target", "")
                success, msg = agent.pick_up_item(target, self.engine.world)
                agent.memory.add_event(
                    msg, tick=tick,
                    importance=1.5 if success else 1.0,
                    tags=[] if success else ["blocked"],
                )
                agent.action = "IDLE"

            elif action == "DROP":
                target = decision.get("target", "")
                success, msg = agent.drop_item(target, self.engine.world)
                agent.memory.add_event(
                    msg, tick=tick,
                    importance=0.5 if success else 1.0,
                    tags=[] if success else ["blocked"],
                )
                agent.action = "IDLE"

            elif action == "REST":
                agent.drives["energy"] = max(0, agent.drives["energy"] - REST_ENERGY_REDUCTION)
                agent.action = "RESTING"

            elif action == "SLEEP":
                agent.drives["energy"] = max(0, agent.drives["energy"] - SLEEP_ENERGY_REDUCTION)
                agent.drives["comfort"] = max(0, agent.drives["comfort"] - SLEEP_COMFORT_REDUCTION)
                agent.action = "SLEEPING"
                from roma_aeterna.agent.status_effects import create_effect
                effect = create_effect("rested")
                if effect:
                    agent.status_effects.add(effect)

            elif action == "TRADE":
                target_name = decision.get("target", "")
                offer_name = decision.get("offer", "")
                want_name = decision.get("want", "")

                # Locate target agent within interaction range
                import math
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
                        # Execute the exchange
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

            elif action == "BUY":
                target_item = decision.get("target", "")
                market = decision.get("market", "")
                market_pos = None
                # Find nearest market if not specified
                if not market:
                    from roma_aeterna.world.components import Interactable
                    for obj in self.engine.world.objects:
                        interact = obj.get_component(Interactable)
                        if interact and interact.interaction_type == "trade":
                            import math
                            dist = math.sqrt(
                                (obj.x - agent.x) ** 2 + (obj.y - agent.y) ** 2
                            )
                            if dist <= NEARBY_AGENT_RADIUS:
                                market = obj.name
                                market_pos = (int(obj.x), int(obj.y))
                                break
                else:
                    # Resolve position for a named market (case-insensitive + proximity check)
                    import math as _math
                    from roma_aeterna.world.components import Interactable
                    for obj in self.engine.world.objects:
                        if obj.name.lower() == market.lower():
                            dist = _math.sqrt(
                                (obj.x - agent.x) ** 2 + (obj.y - agent.y) ** 2
                            )
                            if dist <= NEARBY_AGENT_RADIUS:
                                market_pos = (int(obj.x), int(obj.y))
                            else:
                                # Named market found but too far — fall through to "no market" path
                                market = ""
                                market_pos = None
                            break

                if market:
                    success, msg = self.engine.economy.buy_item(
                        agent, market, target_item
                    )
                    agent.memory.add_event(msg, tick=tick, importance=2.0,
                                           memory_type="event", tags=["trade"])
                    # Teach the agent where this market is so they can return
                    if market_pos:
                        agent.memory.learn_location(market, market_pos)
                    agent.action = "TRADING" if success else "IDLE"
                else:
                    agent.memory.add_event(
                        f"Tried to buy {target_item} but there is no market nearby.",
                        tick=tick, importance=1.0, tags=["blocked"],
                    )
                    agent.action = "IDLE"

            elif action == "GOTO":
                # Multi-step navigation to a named location (case-insensitive lookup)
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

            elif action == "WORK":
                # Placeholder: agent performs their role at a building
                agent.action = "WORKING"
                agent.drives["comfort"] = max(0, agent.drives["comfort"] - 3)
                agent.memory.add_event(
                    f"Worked as a {agent.role}.", tick=tick, importance=1.0,
                    tags=["work"],
                )

            elif action == "INSPECT":
                target = decision.get("target", "")
                result = self._inspect_target(agent, target)
                agent.memory.add_event(
                    result, tick=tick, importance=1.5,
                    memory_type="observation",
                )
                agent.action = "INSPECTING"
                
            elif action == "CRAFT":
                target_item = decision.get("target", "")
                from roma_aeterna.world.items import ITEM_DB

                # Find a recipe that produces the target item
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
                else:
                    # Check station type requirement
                    station_ok = True
                    if recipe.station_type != "general":
                        import math as _math
                        from roma_aeterna.world.components import Interactable as _IA
                        from roma_aeterna.config import INTERACTION_RADIUS as _IR
                        station_ok = False
                        for obj in self.engine.world.objects:
                            interact = obj.get_component(_IA)
                            if interact and interact.interaction_type == recipe.station_type:
                                dist = _math.sqrt(
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
                    else:
                        # Check if agent has all required inputs
                        has_all = True
                        for req in recipe.inputs:
                            if not any(i.name.lower() == req.lower() for i in agent.inventory):
                                has_all = False
                                break

                        if has_all:
                            # Verify output template exists BEFORE consuming inputs
                            new_item = ITEM_DB.create_item(recipe.output)
                            if not new_item:
                                agent.memory.add_event(
                                    f"Tried to craft {target_item} but the output couldn't be created (missing template).",
                                    tick=tick, importance=1.0, tags=["blocked"],
                                )
                                agent.action = "IDLE"
                            else:
                                # Remove inputs only after confirming output is available
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
                        
            elif action == "REFLECT":
                # Accept either the dedicated `note` field or fall back to `target`
                # so old and new prompt formats both work.
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

            else:
                agent.action = "IDLE"

    @staticmethod
    def _parse_json(text: str) -> Optional[Dict]:
        if not text:
            return None
            
        text = text.strip()
        
        # Qwen3 often wraps output in <think>...</think> tags
        # Strip those first
        import re
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
        
        # Strip common markdown wrappers
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
            
        # Fallback: extract first JSON object from the text
        # This handles cases where the model adds explanation before/after
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            candidate = text[start:end]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass
            
            # Try fixing common issues: trailing commas, single quotes
            try:
                # Remove trailing commas before closing braces
                fixed = re.sub(r',\s*}', '}', candidate)
                fixed = re.sub(r',\s*]', ']', fixed)
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass

        return None