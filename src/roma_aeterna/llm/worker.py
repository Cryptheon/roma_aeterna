import threading
import asyncio
import json
import os
from openai import AsyncOpenAI
from ..config import VLLM_URL
from .prompts import build_prompt

class LLMWorker(threading.Thread):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.queue = asyncio.Queue() # Using asyncio queue inside the loop
        self.input_queue = [] # Simple list buffer for thread-safety bridging
        self.lock = threading.Lock()
        self.daemon = True
        self.batch_size = 10
        self.batch_timeout = 0.1 # Seconds to wait for filling batch

    def queue_request(self, agent):
        # Called from Main Thread
        with self.lock:
            self.input_queue.append(agent)

    def run(self):
        # Entry point for the thread
        asyncio.run(self._async_loop())

    async def _async_loop(self):
        print("[LLM] Async Worker Started")
        client = AsyncOpenAI(base_url=VLLM_URL, api_key="vllm")
        
        while True:
            batch = []
            
            # 1. Drain input buffer into local batch
            with self.lock:
                if self.input_queue:
                    # Take up to batch_size
                    chunk = self.input_queue[:self.batch_size]
                    self.input_queue = self.input_queue[len(chunk):]
                    batch = chunk
            
            # 2. If no work, small sleep (prevent CPU spin)
            if not batch:
                await asyncio.sleep(0.1)
                continue

            # 3. Process Batch
            # We generate prompts here (in the worker thread) to offload logic from main
            tasks = []
            for agent in batch:
                # Note: Reading agent state here is technically a race condition 
                # vs the Simulation loop, but acceptable for fuzzy game AI.
                prompt = build_prompt(agent, self.engine.world, self.engine.weather)
                tasks.append(self._process_single_agent(client, agent, prompt))
            
            # Run all concurrently
            await asyncio.gather(*tasks)

    async def _process_single_agent(self, client, agent, prompt):
        try:
            # Fallback for demo if no server running
            # response = await client.chat.completions.create(
            #     model="mistralai/Mistral-7B-Instruct-v0.2",
            #     messages=[{"role": "user", "content": prompt}],
            #     temperature=0.7,
            #     max_tokens=150
            # )
            # content = response.choices[0].message.content
            # decision = self._parse_json(content)
            
            # Mock Decision for Stability
            await asyncio.sleep(0.05) # Simulate latency
            import random
            decision = {
                "thought": f"I see {random.randint(1,5)} things. I should move.",
                "action": "MOVE",
                "target": (agent.x + random.randint(-2, 2), agent.y + random.randint(-2, 2))
            }

            self._apply_result(agent, decision)

        except Exception as e:
            print(f"[LLM] Error processing {agent.name}: {e}")
        finally:
            agent.waiting_for_llm = False

    def _apply_result(self, agent, decision):
        # Push changes back to engine safely
        with self.engine.lock:
            agent.current_thought = decision.get("thought", "...")
            
            if decision["action"] == "MOVE":
                tx, ty = decision["target"]
                # Clamp and Pathfind
                tx = max(0, min(tx, 127))
                ty = max(0, min(ty, 127))
                path = self.engine.get_path((int(agent.x), int(agent.y)), (int(tx), int(ty)))
                if path:
                    agent.path = path
                    agent.action = "MOVING"
                    # Reset stimulus on successful action plan
                    agent.stimulus_score = 0.0