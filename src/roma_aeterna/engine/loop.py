"""
Simulation Engine — The tick orchestrator.

Decision flow per agent per tick:
  1. Biology updates (drives, health, status effects)
  2. LIF neuron integrates urgency → fires or doesn't
  3. If fired (or path-following): Autopilot tries to handle it
  4. If autopilot returns None: Queue for LLM inference
  5. If autopilot returns a decision: Execute immediately

This means most ticks, most agents are on autopilot. The LLM only
fires for novel situations, first meetings, and complex decisions.
"""

import threading
import math
import random
from typing import Any, List, Optional

from .weather import WeatherSystem
from .chaos import ChaosEngine
from roma_aeterna.core.events import EventBus, Event, EventType
from roma_aeterna.engine.economy import EconomySystem
from roma_aeterna.llm.worker import LLMWorker
from roma_aeterna.config import TPS, AUTOSAVE_INTERVAL, LIF_ENV_UPDATE_INTERVAL, DEAD_REMOVAL_DELAY


class SimulationEngine:
    """Top-level simulation coordinator."""

    def __init__(self, world: Any, agents: List[Any],
                 save_path: Optional[str] = None) -> None:
        self.world = world
        self.agents = agents
        self.weather = WeatherSystem()
        self.chaos = ChaosEngine(world)
        self.event_bus = EventBus()
        self.economy = EconomySystem()
        self.llm_worker = LLMWorker(self)
        self.lock = threading.RLock()

        # Simulation state
        self.tick_count: int = 0
        self.paused: bool = False
        self.running: bool = True
        self.save_path: Optional[str] = save_path
        self.pending_prayers: list = []  # [{agent_uid, agent_name, temple, prayer, tick}]
        self.notifications: list = []   # [{text, category}] — drained by renderer each frame

        # Track previous time of day for dawn/dusk events
        self._prev_time_of_day: str = ""

        # Initialize
        self._initialize_agents()
        self._try_load_save()
        self.llm_worker.start()

    def _initialize_agents(self) -> None:
        """Give agents personalities, starting items, and world knowledge."""
        from roma_aeterna.llm.personalities import assign_personality, ROLE_STARTING_INVENTORY
        from roma_aeterna.world.items import ITEM_DB

        for agent in self.agents:
            # Animals are autopilot-only — skip personality/inventory init
            if getattr(agent, "is_animal", False):
                continue

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

        # Seed world locations — every citizen knows where key buildings are
        self._seed_world_knowledge()

    def _seed_world_knowledge(self) -> None:
        """Teach every non-animal agent the locations of key world buildings.

        Scans world.objects for markets, fountains, and temples so that
        GOTO works from the first LLM call without requiring prior exploration.
        """
        from roma_aeterna.world.components import Interactable, WaterFeature

        markets: list = []
        fountains: list = []
        temples: list = []

        for obj in self.world.objects:
            pos = (int(obj.x), int(obj.y))
            interact = obj.get_component(Interactable)
            if interact and interact.interaction_type == "trade":
                markets.append((obj.name, pos))
            wf = obj.get_component(WaterFeature)
            if wf:
                fountains.append((obj.name, pos))
            if "temple" in obj.name.lower():
                temples.append((obj.name, pos))

        for agent in self.agents:
            if getattr(agent, "is_animal", False):
                continue
            for name, pos in markets:
                agent.memory.learn_location(name, pos)
            for name, pos in fountains:
                agent.memory.learn_location(name, pos)
            for name, pos in temples:
                agent.memory.learn_location(name, pos)

    def _try_load_save(self) -> None:
        from roma_aeterna.core.persistence import load_game, has_save
        if has_save(self.save_path):
            if load_game(self, self.save_path):
                print(f"[ENGINE] Resumed from save (tick {self.tick_count})")
            else:
                print("[ENGINE] Save found but failed to load. Starting fresh.")
        else:
            print("[ENGINE] No save file. Starting new simulation.")

    # ================================================================
    # MAIN UPDATE
    # ================================================================

    def update(self, dt: float) -> None:
        if self.paused:
            return

        with self.lock:
            self.tick_count += 1

            # --- 1. Environment ---
            self.weather.update()
            self._sync_weather_to_world()
            self._emit_time_events()

            if self.tick_count % 2 == 0:
                self.chaos.tick_environment(self.weather)

            self.chaos.tick_agents(self.agents, self.weather)

            # Tick interactable cooldowns so buildings become usable again
            self._tick_interactable_cooldowns(dt)

            # --- 2. Economy ---
            self.economy.tick(
                self.world, self.agents, self.event_bus, self.tick_count
            )

            # --- 3. Event Bus ---
            self.event_bus.process(self.agents, self.world, self.tick_count)

            # --- 4. Agents ---
            weather_fx = self.weather.get_effects()
            for agent in self.agents:
                # Sync engine tick onto every agent so base.py / autopilot.py
                # can timestamp memory events consistently with action handlers.
                agent.sim_tick = self.tick_count
                if not agent.is_alive:
                    continue
                if getattr(agent, "is_animal", False):
                    agent.tick(
                        self.world, self.agents,
                        self.tick_count, self.weather.time_of_day.value,
                    )
                    continue
                self._update_agent(agent, dt, weather_fx)

            # --- 5. Purge old corpses ---
            if self.tick_count % 100 == 0:
                self.agents = [
                    a for a in self.agents
                    if a.is_alive or (self.tick_count - a.death_tick) < DEAD_REMOVAL_DELAY
                ]

            # --- 6. Autosave ---
            if self.tick_count % AUTOSAVE_INTERVAL == 0:
                self._autosave()

    def _sync_weather_to_world(self) -> None:
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

    def _emit_time_events(self) -> None:
        """Emit dawn/dusk/new day events when time changes."""
        current = self.weather.time_of_day.value
        if current == self._prev_time_of_day:
            return

        if current == "dawn" and self._prev_time_of_day == "night":
            self.event_bus.emit(Event(
                event_type=EventType.DAWN.value,
                radius=0,  # Global
                importance=0.5,
            ))
        elif current == "dusk" and self._prev_time_of_day in ("afternoon", "evening"):
            self.event_bus.emit(Event(
                event_type=EventType.DUSK.value,
                radius=0,
                importance=0.5,
            ))

        self._prev_time_of_day = current

    # ================================================================
    # PER-AGENT UPDATE — The dual-brain decision flow
    # ================================================================

    def _update_agent(self, agent: Any, dt: float,
                      weather_fx: dict) -> None:
        """Run one tick of agent simulation.

        Decision flow:
          1. Update biology → LIF neuron fires or doesn't
          2. If following a path (autopilot navigating): let autopilot handle movement
          3. If brain fired:
             a. Try autopilot first (System 1)
             b. If autopilot returns None → queue for LLM (System 2)
          4. Execute the decision
        """
        # Periodically scan environment so LIF urgency reflects threats, not just drives
        if self.tick_count % LIF_ENV_UPDATE_INTERVAL == 0:
            agent.update_env_urgency(self.world, self.agents)

        did_fire = agent.update_biological(dt, weather_fx)

        # Notify renderer when an agent dies from starvation/dehydration
        if not agent.is_alive:
            self.push_notification(f"☠ {agent.name} has perished!", "death")
            return

        # --- Autopilot path-following (runs even without brain fire) ---
        if (agent.autopilot.path and
                not did_fire and
                not agent.waiting_for_llm and
                agent.movement_cooldown == 0):
            decision = agent.autopilot._follow_path(agent, self.world)
            if decision:
                self._execute_autopilot_decision(agent, decision)
                return

        # --- Brain fired: time to decide ---
        if did_fire and not agent.waiting_for_llm:
            # System 1: Try autopilot
            decision = agent.autopilot.decide(agent, self.agents, self.world)

            if decision:
                # Autopilot handled it
                self._execute_autopilot_decision(agent, decision)
            else:
                # System 2: Need LLM
                agent.waiting_for_llm = True
                self.llm_worker.queue_request(agent)

    def _tick_interactable_cooldowns(self, dt: float) -> None:
        """Decrement cooldown on all interactable world objects each tick."""
        from roma_aeterna.world.components import Interactable
        for obj in self.world.objects:
            interact = obj.get_component(Interactable)
            if interact and interact.cooldown > 0:
                interact.cooldown = max(0.0, interact.cooldown - dt)

    def _execute_autopilot_decision(self, agent: Any, decision: dict) -> None:
        """Execute a decision from the autopilot (same format as LLM decisions)."""
        decision["_autopilot"] = True  # Tag for history tracking
        # Reuse the LLM worker's apply logic
        self.llm_worker._apply_decision(agent, decision)

    # ================================================================
    # PERSISTENCE
    # ================================================================

    def save(self, path: Optional[str] = None) -> str:
        from roma_aeterna.core.persistence import save_game
        return save_game(self, path or self.save_path)

    def _autosave(self) -> None:
        try:
            from roma_aeterna.core.persistence import save_game
            save_game(self, self.save_path)
        except Exception as e:
            print(f"[ENGINE] Autosave failed: {e}")

    def shutdown(self) -> None:
        self.running = False
        print("[ENGINE] Shutting down...")
        try:
            self.save()
        except Exception as e:
            print(f"[ENGINE] Shutdown save failed: {e}")
        print("[ENGINE] Goodbye.")

    # ================================================================
    # QUERY METHODS
    # ================================================================

    def push_notification(self, text: str, category: str = "info") -> None:
        """Queue a UI notification for the renderer. Safe to call from any thread."""
        self.notifications.append({"text": text, "category": category})
        if len(self.notifications) > 50:
            self.notifications.pop(0)

    def deliver_divine_response(self, agent_uid: str, response: str) -> bool:
        """Called by the renderer when the player submits a divine oracle response.

        Injects the response as importance-7.0 memory and spikes the LIF
        neuron so the agent reacts immediately on the next brain-fire cycle.
        Returns True if the agent was found alive.
        """
        with self.lock:
            agent = next(
                (a for a in self.agents if a.uid == agent_uid and a.is_alive),
                None,
            )
            if agent is None:
                return False

            agent.memory.add_event(
                f"⚡ Jupiter has spoken: \"{response}\"",
                tick=self.tick_count,
                importance=7.0,
                memory_type="observation",
                tags=["divine", "jupiter", "oracle", "revelation"],
            )
            if agent.brain is not None:
                agent.brain.potential += 20.0  # Force immediate LIF fire
            self.push_notification(
                f"⚡ Jupiter speaks to {agent.name}!", "divine"
            )
            return True

    def get_time_info(self) -> dict:
        return {
            "tick": self.tick_count,
            "day": self.weather.day_count,
            "time_of_day": self.weather.time_of_day.value,
            "weather": self.weather.current.value,
            "temperature": self.weather.temperature,
        }