"""
LLM Worker — Async inference thread that processes agent decisions.

Runs on a dedicated thread. Receives agents who need to "think",
builds prompts, queries the LLM, parses JSON responses, and
applies validated actions back to the engine.
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
        self.use_mock: bool = True  # Set False when vLLM server is running

    def queue_request(self, agent: Any) -> None:
        """Called from the simulation thread to enqueue an agent for inference."""
        with self.lock:
            if agent not in self.input_queue:
                self.input_queue.append(agent)

    def run(self) -> None:
        """Thread entry point."""
        asyncio.run(self._async_loop())

    async def _async_loop(self) -> None:
        """Main async loop: drain queue, build prompts, run inference."""
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
                prompt = build_prompt(
                    agent, self.engine.world,
                    self.engine.agents, self.engine.weather,
                )
                tasks.append(self._process_agent(client, agent, prompt))
            await asyncio.gather(*tasks)

    async def _process_agent(self, client: Any, agent: Any, prompt: str) -> None:
        """Run inference for a single agent and apply the result."""
        try:
            if self.use_mock:
                decision = await self._mock_decision(agent)
            else:
                decision = await self._llm_decision(client, prompt)

            if decision:
                self._apply_decision(agent, decision)
        except Exception as e:
            print(f"[LLM] Error for {agent.name}: {e}")
        finally:
            agent.waiting_for_llm = False

    async def _llm_decision(self, client: Any, prompt: str) -> Optional[Dict]:
        """Query the actual vLLM server."""
        try:
            response = await client.chat.completions.create(
                model=VLLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_TOKENS,
            )
            content = response.choices[0].message.content
            return self._parse_json(content)
        except Exception as e:
            print(f"[LLM] Inference error: {e}")
            return None

    async def _mock_decision(self, agent: Any) -> Dict:
        """Generate a plausible mock decision for testing without LLM.

        The mock system mirrors how a real agent would reason:
        it checks how the agent FEELS (status effects + drives) and
        acts on internal state, not on omniscient world knowledge.
        """
        await asyncio.sleep(0.03)

        drives = agent.drives

        # === SURVIVAL PRIORITY: React to status effects ===
        # The agent feels burned/smoke — flee in a random direction
        if agent.status_effects.has_effect("Burned") or agent.status_effects.has_effect("Smoke Inhalation"):
            return {
                "thought": "I'm choking! I need to get away from this smoke and fire!",
                "action": "MOVE",
                "direction": random.choice(["north", "south", "east", "west"]),
            }

        # Food poisoning — rest
        if agent.status_effects.has_effect("Food Poisoning"):
            return {
                "thought": "My stomach... I can barely stand. I need to rest.",
                "action": "REST",
            }

        # Heatstroke — seek water
        if agent.status_effects.has_effect("Heatstroke"):
            for item in agent.inventory:
                if getattr(item, "item_type", None) == "drink":
                    return {
                        "thought": f"The heat is killing me. I must drink my {item.name}.",
                        "action": "CONSUME",
                        "target": item.name,
                    }
            if "Fountain" in agent.memory.known_locations:
                return {
                    "thought": "I'm burning up. I remember a fountain nearby.",
                    "action": "MOVE",
                    "direction": self._direction_toward(
                        agent, agent.memory.known_locations["Fountain"]
                    ),
                }
            return {
                "thought": "The heat is unbearable. I need to find water or shade.",
                "action": "MOVE",
                "direction": random.choice(["north", "south", "east", "west"]),
            }

        # === BIOLOGICAL NEEDS ===
        # Critical thirst
        if drives["thirst"] > 60:
            for item in agent.inventory:
                if getattr(item, "item_type", None) == "drink":
                    return {
                        "thought": f"I'm parched. I need to drink my {item.name}.",
                        "action": "CONSUME",
                        "target": item.name,
                    }
            if "Fountain" in agent.memory.known_locations:
                return {
                    "thought": "I need water desperately. I remember a fountain.",
                    "action": "MOVE",
                    "direction": self._direction_toward(
                        agent, agent.memory.known_locations["Fountain"]
                    ),
                }

        # Hunger
        if drives["hunger"] > 60:
            for item in agent.inventory:
                if getattr(item, "item_type", None) == "food":
                    spoiled = getattr(item, "is_spoiled", lambda: False)
                    if not spoiled():
                        return {
                            "thought": f"My stomach growls. Time to eat the {item.name}.",
                            "action": "CONSUME",
                            "target": item.name,
                        }

        # Exhaustion
        if drives["energy"] > 70:
            return {
                "thought": "I'm exhausted. I need to rest.",
                "action": "REST",
            }

        # Loneliness
        if drives["social"] > 50:
            nearby = self._find_nearby_agents(agent)
            if nearby:
                target = random.choice(nearby)
                greetings = [
                    f"Salve, {target.name}! How goes your day?",
                    f"Ave! What news do you bring, {target.name}?",
                    f"By Jupiter, {target.name}, this weather...",
                    f"Well met, {target.name}. What brings you here?",
                ]
                return {
                    "thought": f"I'm feeling lonely. I should talk to {target.name}.",
                    "action": "TALK",
                    "target": target.name,
                    "speech": random.choice(greetings),
                }

        # === DEFAULT: Wander ===
        directions = ["north", "south", "east", "west",
                       "northeast", "northwest", "southeast", "southwest"]
        thoughts = [
            "I should explore the area. What's around the next corner?",
            "The Forum calls to me. Let me wander.",
            "Perhaps I'll find something interesting this way.",
            "A change of scenery would do me good.",
            f"As a {agent.role}, I should be about my duties.",
        ]
        return {
            "thought": random.choice(thoughts),
            "action": "MOVE",
            "direction": random.choice(directions),
        }

    def _direction_toward(self, agent: Any, target: tuple) -> str:
        """Compute approximate direction from agent to target coords."""
        import math
        dx = target[0] - agent.x
        dy = target[1] - agent.y
        if abs(dx) < 1 and abs(dy) < 1:
            return "north"
        angle = math.degrees(math.atan2(dy, dx))
        if angle < 0:
            angle += 360
        dirs = ["east", "southeast", "south", "southwest",
                "west", "northwest", "north", "northeast"]
        idx = int((angle + 22.5) // 45) % 8
        return dirs[idx]

    def _find_nearby_agents(self, agent: Any) -> List[Any]:
        """Find agents within interaction range."""
        import math
        nearby = []
        for other in self.engine.agents:
            if other.uid == agent.uid or not other.is_alive:
                continue
            dist = math.sqrt((other.x - agent.x) ** 2 + (other.y - agent.y) ** 2)
            if dist < 5.0:
                nearby.append(other)
        return nearby

    def _apply_decision(self, agent: Any, decision: Dict) -> None:
        """Validate and execute the agent's decision on the world."""
        with self.engine.lock:
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
                    agent.action = "IDLE"

            elif action == "TALK":
                target = decision.get("target", "")
                speech = decision.get("speech", "...")
                success, msg = agent.talk_to(
                    target, speech, self.engine.agents, tick
                )
                if success:
                    agent.action = "TALKING"
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
                success, msg = agent.drop_item(target, self.engine.world)
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

            elif action == "INSPECT":
                target = decision.get("target", "")
                agent.memory.add_event(
                    f"Inspected {target} closely.", tick=tick, importance=1.0,
                    memory_type="observation",
                )
                agent.action = "INSPECTING"

            else:
                agent.action = "IDLE"

    @staticmethod
    def _parse_json(text: str) -> Optional[Dict]:
        """Extract JSON from LLM response text."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass

        return None
