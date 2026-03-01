"""
Event Bus — Decoupled communication between agents, world, and systems.

Events propagate through the world like information would in reality:
  - IMMEDIATE: Agents within earshot hear speech, see fire start.
  - GOSSIP: Agents spread news to each other during conversations.
    Events decay in importance as they pass through more people.
  - GLOBAL: System-level events (day change, market restock).

Usage:
    from roma_aeterna.core.events import EventBus, Event

    bus = EventBus()
    bus.emit(Event("fire_started", origin=(50, 30), radius=10,
                   data={"building": "Bakery"}))

    # In the tick loop:
    bus.process(agents, world, tick)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Callable
from enum import Enum
import math

from roma_aeterna.config import MAX_GOSSIP_HOPS, EVENT_HISTORY_CAP, GOSSIP_IMPORTANCE_DECAY


class EventType(Enum):
    """Categories of events in the simulation."""
    # World events
    FIRE_STARTED = "fire_started"
    FIRE_EXTINGUISHED = "fire_extinguished"
    BUILDING_COLLAPSED = "building_collapsed"
    WEATHER_CHANGED = "weather_changed"

    # Agent events
    SPEECH = "speech"
    AGENT_DIED = "agent_died"
    FIGHT = "fight"
    TRADE_COMPLETED = "trade_completed"

    # Economic events
    MARKET_RESTOCK = "market_restock"
    PRICE_CHANGE = "price_change"
    WAGES_PAID = "wages_paid"

    # Time events
    DAWN = "dawn"
    DUSK = "dusk"
    NEW_DAY = "new_day"

    # Social
    GOSSIP = "gossip"
    PUBLIC_ANNOUNCEMENT = "public_announcement"

    # Generic
    CUSTOM = "custom"


@dataclass
class Event:
    """A single event in the world."""
    event_type: str                     # EventType value or custom string
    origin: Optional[Tuple[int, int]] = None  # Where it happened
    radius: float = 0.0                 # How far it can be perceived (0 = global)
    data: Dict[str, Any] = field(default_factory=dict)
    source_agent: Optional[str] = None  # Name of agent who caused it
    tick: int = 0                       # When it happened
    importance: float = 1.0             # For memory storage
    gossip_hops: int = 0                # How many times this has been retold
    max_gossip_hops: int = MAX_GOSSIP_HOPS  # Stops spreading after this
    consumed_by: List[str] = field(default_factory=list)  # Agent UIDs who've seen it


class EventBus:
    """Central event dispatcher for the simulation."""

    def __init__(self) -> None:
        self.pending: List[Event] = []
        self.history: List[Event] = []
        self._listeners: Dict[str, List[Callable]] = {}
        self._history_cap: int = EVENT_HISTORY_CAP

    def emit(self, event: Event) -> None:
        """Queue an event for processing next tick."""
        self.pending.append(event)

    def subscribe(self, event_type: str, callback: Callable) -> None:
        """Register a system-level listener for an event type."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)

    def process(self, agents: List[Any], world: Any, tick: int) -> None:
        """Process all pending events: deliver to nearby agents, fire callbacks."""
        events = list(self.pending)
        self.pending = []

        for event in events:
            event.tick = tick

            # System-level listeners
            for callback in self._listeners.get(event.event_type, []):
                try:
                    callback(event, agents, world)
                except Exception as e:
                    print(f"[EVENT] Listener error for {event.event_type}: {e}")

            # Deliver to agents in range
            self._deliver_to_agents(event, agents)

            # Archive
            self.history.append(event)

        # Trim history
        if len(self.history) > self._history_cap:
            self.history = self.history[-self._history_cap:]

    def _deliver_to_agents(self, event: Event, agents: List[Any]) -> None:
        """Deliver an event to agents within its radius."""
        for agent in agents:
            if not agent.is_alive:
                continue
            if agent.uid in event.consumed_by:
                continue

            # Check range
            if event.origin and event.radius > 0:
                dist = math.sqrt(
                    (agent.x - event.origin[0]) ** 2 +
                    (agent.y - event.origin[1]) ** 2
                )
                if dist > event.radius:
                    continue

            # Deliver — agent remembers this event
            self._agent_perceive_event(agent, event)
            event.consumed_by.append(agent.uid)

    def _agent_perceive_event(self, agent: Any, event: Event) -> None:
        """Make an agent aware of an event through memory."""
        etype = event.event_type

        # Scale importance by gossip hops (secondhand info is less important)
        importance = event.importance * (GOSSIP_IMPORTANCE_DECAY ** event.gossip_hops)

        if etype == EventType.FIRE_STARTED.value:
            bld = event.data.get("building", "something")
            text = f"A fire has broken out at {bld}!"
            agent.memory.add_event(
                text, tick=event.tick, importance=max(3.0, importance),
                memory_type="observation", tags=["fire", "danger"],
                location=event.origin,
            )
            # Also update beliefs
            if event.origin:
                agent.memory.add_belief(bld, "caught fire", 0.9, "witnessed")

        elif etype == EventType.BUILDING_COLLAPSED.value:
            bld = event.data.get("building", "a building")
            text = f"{bld} has collapsed!"
            agent.memory.add_event(
                text, tick=event.tick, importance=max(4.0, importance),
                memory_type="observation", tags=["collapse", "danger"],
                location=event.origin,
            )

        elif etype == EventType.SPEECH.value:
            speaker = event.source_agent or "Someone"
            speech = event.data.get("speech", "...")
            # Only if not the speaker themselves
            if agent.name != speaker:
                text = f"You overheard {speaker} say: \"{speech}\""
                agent.memory.add_event(
                    text, tick=event.tick, importance=importance,
                    memory_type="conversation", related_agent=speaker,
                )

        elif etype == EventType.AGENT_DIED.value:
            dead_name = event.data.get("name", "someone")
            text = f"{dead_name} has died!"
            agent.memory.add_event(
                text, tick=event.tick, importance=max(5.0, importance),
                memory_type="observation", tags=["death"],
            )
            agent.memory.add_belief(dead_name, "is dead", 1.0, "witnessed")

        elif etype == EventType.MARKET_RESTOCK.value:
            market = event.data.get("market", "the market")
            text = f"Fresh goods have arrived at {market}."
            agent.memory.add_event(
                text, tick=event.tick, importance=importance,
                memory_type="observation", tags=["trade"],
            )

        elif etype == EventType.WEATHER_CHANGED.value:
            weather = event.data.get("weather", "changed")
            text = f"The weather has turned to {weather}."
            agent.memory.add_event(
                text, tick=event.tick, importance=0.5,
                memory_type="observation", tags=["weather"],
            )

        elif etype == EventType.DAWN.value:
            agent.memory.add_event(
                "A new day begins.", tick=event.tick, importance=0.3,
                memory_type="observation", tags=["time"],
            )

        elif etype == EventType.DUSK.value:
            agent.memory.add_event(
                "Night falls over Rome.", tick=event.tick, importance=0.5,
                memory_type="observation", tags=["time", "danger"],
            )

        elif etype == EventType.GOSSIP.value:
            gossip_text = event.data.get("text", "something interesting")
            source = event.source_agent or "someone"
            hops = event.gossip_hops
            prefix = "You heard that" if hops <= 1 else "Rumor has it that"
            text = f"{prefix} {gossip_text} (from {source})"
            agent.memory.add_event(
                text, tick=event.tick, importance=importance,
                memory_type="conversation", tags=["gossip"],
                related_agent=source,
            )

        elif etype == EventType.PUBLIC_ANNOUNCEMENT.value:
            text = event.data.get("text", "An announcement was made.")
            agent.memory.add_event(
                text, tick=event.tick, importance=max(2.0, importance),
                memory_type="observation", tags=["announcement"],
            )

        else:
            # Generic event
            text = event.data.get("text", f"Something happened ({etype}).")
            agent.memory.add_event(
                text, tick=event.tick, importance=importance,
                memory_type="observation",
            )

    def create_gossip(self, agent: Any, event: Event) -> Optional[Event]:
        """Create a gossip version of an event for an agent to spread.

        Called during conversations — agent A tells agent B about
        something they witnessed or heard.
        """
        if event.gossip_hops >= event.max_gossip_hops:
            return None

        return Event(
            event_type=EventType.GOSSIP.value,
            origin=None,  # Gossip has no spatial origin
            radius=0,     # Delivered directly to conversation partner
            data={
                "text": event.data.get("text", event.data.get("speech", "something")),
                "original_type": event.event_type,
            },
            source_agent=agent.name,
            importance=event.importance * 0.7,
            gossip_hops=event.gossip_hops + 1,
            max_gossip_hops=event.max_gossip_hops,
        )

    def get_recent_events(self, n: int = 10,
                          event_type: Optional[str] = None) -> List[Event]:
        """Get recent events, optionally filtered by type."""
        if event_type:
            filtered = [e for e in self.history if e.event_type == event_type]
            return filtered[-n:]
        return self.history[-n:]
