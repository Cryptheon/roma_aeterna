"""
Agent Memory System — Short-term buffer, long-term storage,
relationship tracking, beliefs, and knowledge graph.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import time as _time


@dataclass
class MemoryEntry:
    """A single memory with metadata."""
    text: str
    tick: int                       # Simulation tick when this happened
    importance: float = 1.0         # 0.0 = trivial, 10.0 = life-changing
    memory_type: str = "event"      # event, conversation, observation, feeling, discovery
    related_agent: Optional[str] = None
    location: Optional[Tuple[int, int]] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class Relationship:
    """How this agent feels about another agent."""
    agent_name: str
    trust: float = 0.0         # -100 to +100
    familiarity: float = 0.0   # 0 to 100 (how well they know them)
    last_interaction_tick: int = 0
    interaction_count: int = 0
    notes: List[str] = field(default_factory=list)  # What they remember about them


@dataclass
class Belief:
    """Something the agent believes to be true (may or may not be)."""
    subject: str               # e.g. "Forum Romanum", "Marcus", "bread prices"
    claim: str                 # e.g. "is dangerous at night", "is trustworthy"
    confidence: float = 0.5    # 0.0 = uncertain, 1.0 = absolute
    source: str = "unknown"    # Where they learned this


class Memory:
    """Full cognitive memory model for an agent."""

    def __init__(
        self,
        short_term_cap: int = 20,
        long_term_cap: int = 50,
    ) -> None:
        self.short_term: List[MemoryEntry] = []
        self.long_term: List[MemoryEntry] = []
        self.relationships: Dict[str, Relationship] = {}
        self.beliefs: List[Belief] = []
        self.known_locations: Dict[str, Tuple[int, int]] = {}
        self.preferences: Dict[str, float] = {}  # item/activity -> -1.0 to 1.0

        self._short_cap = short_term_cap
        self._long_cap = long_term_cap

    def add_event(
        self,
        text: str,
        tick: int,
        importance: float = 1.0,
        memory_type: str = "event",
        related_agent: Optional[str] = None,
        location: Optional[Tuple[int, int]] = None,
        tags: Optional[List[str]] = None,
    ) -> None:
        """Record a new memory. High-importance events also go to long-term."""
        entry = MemoryEntry(
            text=text,
            tick=tick,
            importance=importance,
            memory_type=memory_type,
            related_agent=related_agent,
            location=location,
            tags=tags or [],
        )
        self.short_term.append(entry)

        # Overflow: evict least important
        if len(self.short_term) > self._short_cap:
            self.short_term.sort(key=lambda m: m.importance, reverse=True)
            evicted = self.short_term.pop()
            # Consolidate important short-term to long-term
            if evicted.importance >= 3.0:
                self._promote_to_long_term(evicted)

        # Immediately promote very important events
        if importance >= 5.0:
            self._promote_to_long_term(entry)

    def _promote_to_long_term(self, entry: MemoryEntry) -> None:
        """Move a memory to long-term storage."""
        if entry not in self.long_term:
            self.long_term.append(entry)
        if len(self.long_term) > self._long_cap:
            # Evict oldest low-importance
            self.long_term.sort(key=lambda m: m.importance, reverse=True)
            self.long_term.pop()

    def update_relationship(
        self,
        agent_name: str,
        trust_delta: float = 0.0,
        familiarity_delta: float = 1.0,
        tick: int = 0,
        note: Optional[str] = None,
    ) -> None:
        """Update or create a relationship with another agent."""
        if agent_name not in self.relationships:
            self.relationships[agent_name] = Relationship(agent_name=agent_name)

        rel = self.relationships[agent_name]
        rel.trust = max(-100.0, min(100.0, rel.trust + trust_delta))
        rel.familiarity = min(100.0, rel.familiarity + familiarity_delta)
        rel.last_interaction_tick = tick
        rel.interaction_count += 1
        if note:
            rel.notes.append(note)
            if len(rel.notes) > 10:
                rel.notes.pop(0)

    def add_belief(self, subject: str, claim: str, confidence: float = 0.5,
                   source: str = "observation") -> None:
        """Add or update a belief."""
        for belief in self.beliefs:
            if belief.subject == subject and belief.claim == claim:
                # Reinforce existing belief
                belief.confidence = min(1.0, belief.confidence + 0.1)
                return
        self.beliefs.append(Belief(subject, claim, confidence, source))
        if len(self.beliefs) > 30:
            # Drop least confident
            self.beliefs.sort(key=lambda b: b.confidence, reverse=True)
            self.beliefs.pop()

    def learn_location(self, name: str, pos: Tuple[int, int]) -> None:
        """Remember where something is."""
        self.known_locations[name] = pos

    def update_preference(self, subject: str, delta: float) -> None:
        """Adjust preference for an item or activity."""
        current = self.preferences.get(subject, 0.0)
        self.preferences[subject] = max(-1.0, min(1.0, current + delta * 0.1))

    # ---- Context Generation for LLM ----

    def get_recent_context(self, n: int = 5) -> str:
        """Return the N most recent short-term memories as text."""
        recent = self.short_term[-n:]
        if not recent:
            return "Nothing notable has happened recently."
        return "\n".join(f"- {m.text}" for m in recent)

    def get_important_memories(self, n: int = 3) -> str:
        """Return the N most important long-term memories."""
        if not self.long_term:
            return "No significant memories yet."
        top = sorted(self.long_term, key=lambda m: m.importance, reverse=True)[:n]
        return "\n".join(f"- {m.text}" for m in top)

    def get_relationship_summary(self) -> str:
        """Summarize known relationships."""
        if not self.relationships:
            return "You don't know anyone well yet."
        lines = []
        for name, rel in self.relationships.items():
            sentiment = "neutral"
            if rel.trust > 20:
                sentiment = "friendly"
            elif rel.trust > 50:
                sentiment = "trusted ally"
            elif rel.trust < -20:
                sentiment = "distrusted"
            elif rel.trust < -50:
                sentiment = "hostile"
            lines.append(f"- {name}: {sentiment} (met {rel.interaction_count} times)")
        return "\n".join(lines)

    def get_beliefs_summary(self) -> str:
        """Summarize current beliefs."""
        if not self.beliefs:
            return "You have no strong beliefs about the world yet."
        confident = [b for b in self.beliefs if b.confidence > 0.4]
        if not confident:
            return "Your understanding of the world is still forming."
        return "\n".join(
            f"- You believe {b.subject} {b.claim} (confidence: {b.confidence:.0%})"
            for b in confident[:5]
        )

    def get_known_locations_summary(self) -> str:
        """Summarize discovered locations."""
        if not self.known_locations:
            return "You haven't discovered any notable locations yet."
        return "\n".join(
            f"- {name} is at ({x}, {y})"
            for name, (x, y) in list(self.known_locations.items())[:8]
        )
