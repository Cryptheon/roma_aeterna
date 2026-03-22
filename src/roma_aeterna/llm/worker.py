"""
LLM Worker — Async inference thread that processes agent decisions.

Orchestration only: queue management, async batching, prompt building,
and result routing. All action execution lives in actions.py; JSON
parsing in parser.py; mock decisions in mock.py.

Supports two provider backends (set LLM_PROVIDER in config / env):
  "openai"  — AsyncOpenAI client pointing at any OpenAI-compatible endpoint
               (local vLLM, OpenAI, Mistral, etc.)
  "gemini"  — Google's native google-genai SDK; reads GEMINI_API_KEY automatically.
"""

import threading
import asyncio
from typing import Any, Dict, Optional, List

from roma_aeterna.config import (
    LLM_PROVIDER, LLM_BASE_URL, LLM_MODEL, LLM_API_KEY,
    LLM_TEMPERATURE, LLM_MAX_TOKENS, LLM_BATCH_SIZE,
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

    def _build_client(self) -> Any:
        """Create the inference client for the configured provider."""
        if LLM_PROVIDER == "gemini":
            from google import genai
            return genai.Client()  # picks up GEMINI_API_KEY automatically
        else:
            from openai import AsyncOpenAI
            return AsyncOpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)

    async def _async_loop(self) -> None:
        print("[LLM] Worker started")
        client = self._build_client()
        print(f"[LLM] Provider: {LLM_PROVIDER}  Model: {LLM_MODEL}")

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
            if LLM_PROVIDER == "gemini":
                content = await self._call_gemini(client, prompt)
            else:
                content = await self._call_openai(client, prompt)

            parsed = parse_json(content)

            # Record tick for the timeline graph (thread-safe append, capped)
            ticks = self.engine.llm_call_ticks
            ticks.append(agent.sim_tick)
            if len(ticks) > 2000:
                del ticks[:500]

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

    async def _call_openai(self, client: Any, prompt: str) -> str:
        """Call any OpenAI-compatible endpoint (vLLM, OpenAI, Mistral, etc.)."""
        response = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
        )
        return response.choices[0].message.content

    async def _call_gemini(self, client: Any, prompt: str) -> str:
        """Call Google Gemini via the native google-genai SDK."""
        from google.genai import types
        response = await client.aio.models.generate_content(
            model=LLM_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=LLM_TEMPERATURE,
                max_output_tokens=LLM_MAX_TOKENS,
            ),
        )
        return response.text

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
