"""
LLM Worker — Async inference thread that processes agent decisions.

Orchestration only: queue management, async batching, prompt building,
and result routing. All action execution lives in actions.py; JSON
parsing in parser.py; mock decisions in mock.py.
"""

import threading
import asyncio
from typing import Any, Dict, Optional, List

from openai import AsyncOpenAI

from roma_aeterna.config import (
    VLLM_URL, VLLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS, LLM_BATCH_SIZE,
)
from .prompts import build_prompt
from .parser import parse_json
from .actions import ActionExecutor
from .mock import MockDecisionMaker


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
        self._action_executor = ActionExecutor(engine)
        self._mock_maker = MockDecisionMaker(engine)

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

            tasks = [self._process_agent(client, agent) for agent in batch]
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
            # Conversation context consumed — clear it regardless of outcome.
            agent._pending_conversation = None
            agent.waiting_for_llm = False

    # ================================================================
    # DECISION HANDLING
    # ================================================================

    async def _handle_decision(self, client: Any,
                               agent: Any) -> Optional[Dict]:
        """Generate a full decision for the agent."""
        if self.use_mock:
            return await self._mock_maker.decide(agent)

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
            parsed = parse_json(content)

            if parsed:
                agent.record_llm_response(content, parsed)
            else:
                agent.record_llm_response(content, None, error="JSON parse failed")
                print(f"[LLM] Parse failed for {agent.name}. Raw: {content[:150]}")

            return parsed
        except Exception as e:
            agent.record_llm_response("", None, error=str(e))
            print(f"[LLM] Inference error: {e}")

        return await self._mock_maker.decide(agent)

    # ================================================================
    # APPLY DECISION — delegate to ActionExecutor
    # ================================================================

    def _apply_decision(self, agent: Any, decision: Dict) -> None:
        """Validate and execute the agent's decision."""
        with self.engine.lock:
            source = "autopilot" if decision.get("_autopilot") else "llm"
            agent.record_decision(decision, source=source)
            agent.current_thought = decision.get("thought", "...")
            self._action_executor.execute(agent, decision)
