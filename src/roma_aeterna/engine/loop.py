"""
Simulation Engine — The tick orchestrator.

Runs the core simulation loop: weather, chaos physics, agent biology,
neuro-cognitive decision triggers, and movement execution.

Design philosophy: Agents are self-aware. The engine does NOT inject
external threat knowledge into agents. Instead:
  1. The Chaos Engine applies status effects (Burned, Smoke Inhalation, Wet...)
  2. Status effects modify biological drives and carry urgency weights.
  3. The agent's LIF neuron integrates urgency from its OWN internal state.
  4. When the neuron fires, the LLM receives perception + self-assessment.
  5. The LLM decides what to do based on what the agent sees and feels.

This means threat response is fully emergent — no hardcoded threat scores.

Persistence: The engine autosaves periodically and on shutdown.
On startup, it attempts to load the most recent save.
"""

import threading
import math
import random
from typing import Any, List, Optional

from .weather import WeatherSystem
from .chaos import ChaosEngine
from roma_aeterna.llm.worker import LLMWorker
from roma_aeterna.config import TPS


# Autosave interval in ticks (every ~5 minutes at 10 TPS)
AUTOSAVE_INTERVAL: int = 3000


class SimulationEngine:
    """Top-level simulation coordinator."""

    def __init__(self, world: Any, agents: List[Any],
                 save_path: Optional[str] = None) -> None:
        self.world = world
        self.agents = agents
        self.weather = WeatherSystem()
        self.chaos = ChaosEngine(world)
        self.llm_worker = LLMWorker(self)
        self.lock = threading.Lock()

        # Simulation state
        self.tick_count: int = 0
        self.paused: bool = False
        self.running: bool = True
        self.save_path: Optional[str] = save_path

        # Assign personalities and starting inventories
        self._initialize_agents()

        # Try to load existing save
        self._try_load_save()

        # Start LLM inference thread
        self.llm_worker.start()

    def _initialize_agents(self) -> None:
        """Give agents personalities and starting items if not already set."""
        from roma_aeterna.llm.prompts import assign_personality, ROLE_STARTING_INVENTORY
        from roma_aeterna.world.items import ITEM_DB

        for agent in self.agents:
            if not agent.personality_seed:
                agent.personality_seed = assign_personality(agent.role, agent.name)
                agent.personal_goals = agent.personality_seed.get("goals", [])
                agent.fears = agent.personality_seed.get("fears", [])
                agent.values = agent.personality_seed.get("values", [])

            if not agent.inventory:
                item_names = ROLE_STARTING_INVENTORY.get(agent.role, ["Bread"])
                for item_name in item_names:
                    try:
                        item = ITEM_DB.create_item(item_name)
                        if item:
                            agent.inventory.append(item)
                    except Exception:
                        pass

    def _try_load_save(self) -> None:
        """Attempt to restore state from a save file."""
        from roma_aeterna.core.persistence import load_game, has_save

        path = self.save_path
        if has_save(path):
            loaded = load_game(self, path)
            if loaded:
                print(f"[ENGINE] Resumed from save (tick {self.tick_count}, "
                      f"day {self.weather.day_count})")
            else:
                print("[ENGINE] Save file found but could not be loaded. "
                      "Starting fresh.")
        else:
            print("[ENGINE] No save file found. Starting new simulation.")

    # ================================================================
    # MAIN UPDATE
    # ================================================================

    def update(self, dt: float) -> None:
        """Advance the simulation by one tick."""
        if self.paused:
            return

        with self.lock:
            self.tick_count += 1

            # --- 1. Environment ---
            self.weather.update()
            self._sync_weather_to_world()

            # Chaos physics: fire spread, structural collapse, water levels.
            # Runs every 2 ticks as optimization (fire doesn't need per-tick).
            if self.tick_count % 2 == 0:
                self.chaos.tick_environment(self.weather)

            # Weather/fire effects on agents: EVERY tick.
            # This is critical — agents must receive status effects promptly
            # so their internal urgency reflects reality without delay.
            self.chaos.tick_agents(self.agents, self.weather)

            # --- 2. Agents ---
            weather_fx = self.weather.get_effects()

            for agent in self.agents:
                if not agent.is_alive:
                    continue
                self._update_agent(agent, dt, weather_fx)

            # --- 3. Autosave ---
            if self.tick_count % AUTOSAVE_INTERVAL == 0:
                self._autosave()

    def _sync_weather_to_world(self) -> None:
        """Push weather description onto world for agent perception."""
        self.world._current_weather_desc = self.weather.get_description()
        time_descs = {
            "night": "It is deep night.",
            "dawn": "Dawn is breaking.",
            "morning": "It is morning.",
            "midday": "It is midday.",
            "afternoon": "It is afternoon.",
            "dusk": "Dusk is settling.",
            "evening": "It is evening.",
        }
        self.world._current_time_desc = time_descs.get(
            self.weather.time_of_day.value, ""
        )

    # ================================================================
    # PER-AGENT UPDATE
    # ================================================================

    def _update_agent(self, agent: Any, dt: float,
                      weather_fx: dict) -> None:
        """Run one tick of agent simulation.

        The agent's own internal state (drives, health, status effects)
        determines urgency. No external threat injection.
        """

        # --- 1. Biology & Neuro-Cognitive Model ---
        # update_biological ticks drives, status effects, health, and the
        # LIF neuron. Returns True if urgency crossed threshold ("spike").
        did_fire = agent.update_biological(dt, weather_fx)

        # --- 2. Decision Trigger ---
        # If the brain fired, the agent needs to think (LLM inference).
        if did_fire and not agent.waiting_for_llm:
            agent.waiting_for_llm = True
            self.llm_worker.queue_request(agent)

    # ================================================================
    # PERSISTENCE
    # ================================================================

    def save(self, path: Optional[str] = None) -> str:
        """Manually save the simulation state.

        Args:
            path: Optional save file path.

        Returns:
            The path the save was written to.
        """
        from roma_aeterna.core.persistence import save_game
        return save_game(self, path or self.save_path)

    def _autosave(self) -> None:
        """Periodic autosave (called from update loop)."""
        try:
            from roma_aeterna.core.persistence import save_game
            save_game(self, self.save_path)
        except Exception as e:
            print(f"[ENGINE] Autosave failed: {e}")

    def shutdown(self) -> None:
        """Clean shutdown: save state and stop threads.

        Call this when the application is closing (e.g., ESC pressed,
        window closed, or renderer exits).
        """
        self.running = False
        print("[ENGINE] Shutting down...")

        # Final save
        try:
            self.save()
        except Exception as e:
            print(f"[ENGINE] Shutdown save failed: {e}")

        print("[ENGINE] Goodbye.")

    # ================================================================
    # QUERY METHODS (for GUI / external callers)
    # ================================================================

    def get_time_info(self) -> dict:
        """Return current simulation time info for the GUI."""
        return {
            "tick": self.tick_count,
            "day": self.weather.day_count,
            "time_of_day": self.weather.time_of_day.value,
            "weather": self.weather.current.value,
            "temperature": self.weather.temperature,
        }
