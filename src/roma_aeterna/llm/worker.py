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

from roma_aeterna.config import VLLM_URL, VLLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS
from .prompts import build_prompt


class LLMWorker(threading.Thread):
    """Background thread for batched LLM inference."""

    def __init__(self, engine: Any) -> None:
        super().__init__()
        self.engine = engine
        self.input_queue: List[Any] = []
        self.lock = threading.Lock()
        self.daemon = True
        self.batch_size: int = 10
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

    def _find_nearby_agents(self, agent: Any) -> List[Any]:
        import math
        nearby = []
        for other in self.engine.agents:
            if other.uid == agent.uid or not other.is_alive:
                continue
            dist = math.sqrt((other.x - agent.x) ** 2 + (other.y - agent.y) ** 2)
            if dist < 5.0:
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

            tick = int(agent.current_time)

            if action == "MOVE":
                direction = decision.get("direction", "north")
                success, msg = agent.move(direction, self.engine.world)
                if success:
                    agent.memory.add_event(
                        f"Walked {direction}.", tick=tick, importance=0.5,
                        memory_type="event",
                    )
                else:
                    agent.memory.add_event(
                        f"Tried to go {direction} but: {msg}", tick=tick,
                        importance=1.0, tags=["blocked"],
                    )
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
                    agent.action = "IDLE"

            elif action == "INTERACT":
                target = decision.get("target", "")
                success, msg = agent.interact_with_object(target, self.engine.world)
                agent.memory.add_event(msg, tick=tick, importance=2.0,
                                       memory_type="event")
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
                if success:
                    agent.memory.add_event(
                        f"Picked up {target}.", tick=tick, importance=1.5,
                    )
                agent.action = "IDLE"

            elif action == "DROP":
                target = decision.get("target", "")
                agent.drop_item(target, self.engine.world)
                agent.action = "IDLE"

            elif action == "REST":
                agent.drives["energy"] = max(0, agent.drives["energy"] - 5)
                agent.action = "RESTING"

            elif action == "SLEEP":
                agent.drives["energy"] = max(0, agent.drives["energy"] - 15)
                agent.drives["comfort"] = max(0, agent.drives["comfort"] - 5)
                agent.action = "SLEEPING"
                from roma_aeterna.agent.status_effects import create_effect
                effect = create_effect("rested")
                if effect:
                    agent.status_effects.add(effect)

            elif action == "TRADE":
                target = decision.get("target", "")
                agent.action = "TRADING"
                agent.drives["social"] = max(0, agent.drives["social"] - 5)

            elif action == "BUY":
                target_item = decision.get("target", "")
                market = decision.get("market", "")
                # Find nearest market if not specified
                if not market:
                    for obj in self.engine.world.objects:
                        from roma_aeterna.world.components import Interactable
                        interact = obj.get_component(Interactable)
                        if interact and interact.interaction_type == "trade":
                            import math
                            dist = math.sqrt(
                                (obj.x - agent.x) ** 2 + (obj.y - agent.y) ** 2
                            )
                            if dist <= 5.0:
                                market = obj.name
                                break

                if market:
                    success, msg = self.engine.economy.buy_item(
                        agent, market, target_item
                    )
                    agent.memory.add_event(msg, tick=tick, importance=2.0,
                                           memory_type="event", tags=["trade"])
                agent.action = "TRADING" if market else "IDLE"

            elif action == "GOTO":
                # Multi-step navigation to a named location
                target = decision.get("target", "")
                location = agent.memory.known_locations.get(target)
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
                agent.memory.add_event(
                    f"Inspected {target} closely.", tick=tick, importance=1.0,
                    memory_type="observation",
                )
                agent.action = "INSPECTING"
                
            elif action == "CRAFT":
                target_item = decision.get("target", "")
                
                # Check if they are at a crafting station
                # (You could refine this to check the specific station type)
                from roma_aeterna.world.items import ITEM_DB
                
                # Find a recipe that produces the target item
                recipe = next((r for r in ITEM_DB.recipes if r.output.lower() == target_item.lower()), None)
                
                if not recipe:
                    agent.memory.add_event(f"I don't know how to craft {target_item}.", tick=tick, tags=["blocked"])
                    agent.action = "IDLE"
                else:
                    # Check if agent has all required inputs
                    has_all = True
                    for req in recipe.inputs:
                        if not any(i.name.lower() == req.lower() for i in agent.inventory):
                            has_all = False
                            break
                            
                    if has_all:
                        # Remove inputs
                        for req in recipe.inputs:
                            for item in agent.inventory:
                                if item.name.lower() == req.lower():
                                    agent.inventory.remove(item)
                                    break
                        # Add output
                        new_item = ITEM_DB.create_item(recipe.output)
                        if new_item:
                            agent.inventory.append(new_item)
                            agent.memory.add_event(f"Successfully crafted {new_item.name}.", tick=tick, importance=2.0)
                            agent.action = "CRAFTING"
                    else:
                        missing = ", ".join(recipe.inputs)
                        agent.memory.add_event(f"Tried to craft {target_item} but lacked the materials ({missing}).", tick=tick, tags=["blocked"])
                        agent.action = "IDLE"
                        
            elif action == "REFLECT":
                # The LLM puts what it wants to remember in the "target" field
                insight = decision.get("target", "")
                if insight:
                    agent.memory.add_event(
                        f"Personal Reflection: {insight}", 
                        tick=tick, 
                        importance=3.0, # Give it high importance so it sticks around
                        memory_type="feeling",
                        tags=["reflection"]
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