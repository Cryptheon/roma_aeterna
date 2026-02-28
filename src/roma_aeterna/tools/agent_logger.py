"""
Rome: Aeterna — Agent Session Logger
======================================

Writes ALL agent data to disk in real-time so nothing is lost when
the game closes. Produces a JSONL (JSON Lines) file where each line
is a timestamped event.

Event types:
  - "snapshot"    : Full state of all agents (periodic)
  - "llm_request" : Prompt sent to the LLM
  - "llm_response": Raw LLM output + parse result
  - "decision"    : Action taken (LLM or autopilot)
  - "death"       : Agent died

Usage:
    from roma_aeterna.tools.agent_logger import AgentLogger

    engine = SimulationEngine(world, agents)
    logger = AgentLogger(engine, path="logs/session.jsonl")
    logger.start()  # Runs in background thread

    renderer.run()

    logger.stop()   # Flush and close
"""

import json
import os
import time
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional


class AgentLogger:
    """Continuously logs agent state, LLM I/O, and decisions to a JSONL file."""

    def __init__(self, engine: Any, path: str = "logs/session.jsonl",
                 snapshot_interval: float = 15.0) -> None:
        self.engine = engine
        self.path = path
        self.snapshot_interval = snapshot_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._file = None

        # Track what we've already logged to avoid duplicates
        self._last_decision_counts: Dict[str, int] = {}
        self._last_response_counts: Dict[str, int] = {}
        self._last_prompt_counts: Dict[str, int] = {}
        self._logged_deaths: set = set()

        # Ensure directory exists
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    def start(self) -> None:
        """Start the background logging thread."""
        self._running = True
        self._file = open(self.path, "a", encoding="utf-8")

        # Write session header
        self._write_event("session_start", {
            "timestamp": datetime.now().isoformat(),
            "n_agents": len(self.engine.agents),
            "agents": [
                {"name": a.name, "role": a.role, "x": a.x, "y": a.y}
                for a in self.engine.agents
            ],
        })

        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print(f"[Logger] Writing to {self.path}")

    def stop(self) -> None:
        """Stop logging and flush."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        # Final snapshot
        self._log_snapshot()
        self._write_event("session_end", {
            "tick": self.engine.tick_count,
            "timestamp": datetime.now().isoformat(),
        })
        if self._file:
            self._file.close()
            self._file = None
        print(f"[Logger] Session saved to {self.path}")

    def _loop(self) -> None:
        """Main logging loop — checks for new events and writes snapshots."""
        while self._running:
            try:
                self._log_new_events()
                self._log_snapshot()
            except Exception as e:
                print(f"[Logger] Error: {e}")
            time.sleep(self.snapshot_interval)

    def _write_event(self, event_type: str, data: dict) -> None:
        """Write a single event line to the log file."""
        if not self._file:
            return
        record = {
            "type": event_type,
            "tick": getattr(self.engine, 'tick_count', 0),
            "wall_time": datetime.now().isoformat(),
            **data,
        }
        self._file.write(json.dumps(record, default=str) + "\n")
        self._file.flush()

    def _log_new_events(self) -> None:
        """Check each agent for new decisions, LLM responses, and prompts."""
        for agent in self.engine.agents:
            name = agent.name

            # --- New decisions ---
            n_dec = len(agent.decision_history) if hasattr(agent, 'decision_history') else 0
            prev_dec = self._last_decision_counts.get(name, 0)
            if n_dec > prev_dec:
                for d in agent.decision_history[prev_dec:]:
                    self._write_event("decision", {
                        "agent": name,
                        "role": agent.role,
                        "source": d.get("source", "unknown"),
                        "action": d.get("action", ""),
                        "target": d.get("target", ""),
                        "thought": d.get("thought", ""),
                        "speech": d.get("speech", ""),
                        "decision_tick": d.get("tick", 0),
                    })
                self._last_decision_counts[name] = n_dec

            # --- New LLM responses ---
            n_resp = len(agent.llm_response_log) if hasattr(agent, 'llm_response_log') else 0
            prev_resp = self._last_response_counts.get(name, 0)
            if n_resp > prev_resp:
                for r in agent.llm_response_log[prev_resp:]:
                    self._write_event("llm_response", {
                        "agent": name,
                        "role": agent.role,
                        "raw": r.get("raw", ""),
                        "parsed": r.get("parsed", None),
                        "error": r.get("error", ""),
                        "response_tick": r.get("tick", 0),
                    })
                self._last_response_counts[name] = n_resp

            # --- New prompts ---
            n_prompt = len(agent.prompt_history) if hasattr(agent, 'prompt_history') else 0
            prev_prompt = self._last_prompt_counts.get(name, 0)
            if n_prompt > prev_prompt:
                for p in agent.prompt_history[prev_prompt:]:
                    self._write_event("llm_request", {
                        "agent": name,
                        "role": agent.role,
                        "prompt": p,
                    })
                self._last_prompt_counts[name] = n_prompt

            # --- Deaths ---
            if not agent.is_alive and name not in self._logged_deaths:
                self._logged_deaths.add(name)
                self._write_event("death", {
                    "agent": name,
                    "role": agent.role,
                    "health": agent.health,
                    "drives": dict(agent.drives),
                    "position": [agent.x, agent.y],
                    "status_effects": [e.name for e in agent.status_effects.active],
                    "last_thought": agent.current_thought,
                })

    def _log_snapshot(self) -> None:
        """Write a full state snapshot of all agents."""
        agents_data = []
        for agent in self.engine.agents:
            brain = agent.brain
            agents_data.append({
                "name": agent.name,
                "role": agent.role,
                "alive": agent.is_alive,
                "health": round(agent.health, 1),
                "position": [round(agent.x, 1), round(agent.y, 1)],
                "action": agent.action,
                "thought": agent.current_thought,
                "drives": {k: round(v, 1) for k, v in agent.drives.items()},
                "denarii": agent.denarii,
                "lif_potential": round(brain.potential, 3),
                "lif_threshold": round(brain.params.threshold, 2),
                "lif_refractory": brain.is_refractory,
                "waiting_for_llm": agent.waiting_for_llm,
                "n_decisions": len(agent.decision_history) if hasattr(agent, 'decision_history') else 0,
                "n_llm_responses": len(agent.llm_response_log) if hasattr(agent, 'llm_response_log') else 0,
                "n_memories": len(agent.memory.short_term) + len(agent.memory.long_term),
                "inventory": [item.name for item in agent.inventory],
                "status_effects": [e.name for e in agent.status_effects.active],
            })

        self._write_event("snapshot", {"agents": agents_data})
