"""
MockDecisionMaker — Fallback decision-maker when the LLM is unavailable.

Extracted from LLMWorker so that worker.py stays focused on async
orchestration. The mock covers what the autopilot doesn't handle:
exploration, novel interactions, complex needs.
"""

import math
import random
from typing import Any, Dict, List

from roma_aeterna.config import NEARBY_AGENT_RADIUS


class MockDecisionMaker:
    """Generates sensible fallback decisions when the real LLM is unavailable."""

    def __init__(self, engine: Any) -> None:
        self.engine = engine

    async def decide(self, agent: Any) -> Dict:
        """Generate a mock decision based on agent state."""
        import asyncio
        await asyncio.sleep(0.03)

        drives = agent.drives

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
                    "thought": (f"I should introduce myself to {target.name}."
                                if not rel else f"Good to see {target.name} again."),
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
        nearby = []
        for other in self.engine.agents:
            if other.uid == agent.uid or not other.is_alive:
                continue
            dist = math.sqrt((other.x - agent.x) ** 2 + (other.y - agent.y) ** 2)
            if dist < NEARBY_AGENT_RADIUS:
                nearby.append(other)
        return nearby
