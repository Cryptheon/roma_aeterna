import threading
import queue
import time
import json
import random
from .prompts import build_prompt

class LLMWorker(threading.Thread):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.queue = queue.Queue()
        self.daemon = True # Kill when main dies

    def queue_request(self, agent):
        agent.waiting_for_llm = True
        self.queue.put(agent)

    def run(self):
        while True:
            agent = self.queue.get()
            try:
                # Simulate Latency / Call API
                time.sleep(0.5) 
                
                # Mock Decision
                prompt = build_prompt(agent, self.engine.weather)
                
                # Logic to determine random target for demo
                target = (agent.x + random.randint(-5, 5), agent.y + random.randint(-5, 5))
                
                decision = {
                    "action": "MOVE",
                    "target": target
                }
                
                # Apply Result
                self._apply(agent, decision)
                
            except Exception as e:
                print(f"LLM Error: {e}")
            finally:
                agent.waiting_for_llm = False

    def _apply(self, agent, decision):
        if decision["action"] == "MOVE":
            tx, ty = decision["target"]
            # Clamp to map
            tx = max(0, min(tx, 127))
            ty = max(0, min(ty, 127))
            
            # Request path from engine
            path = self.engine.get_path((int(agent.x), int(agent.y)), (int(tx), int(ty)))
            if path:
                agent.path = path
                agent.action = "MOVING"
