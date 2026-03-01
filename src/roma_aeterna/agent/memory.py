"""
Agent Memory System — Short-term buffer, long-term storage,
relationship tracking, beliefs, and knowledge graph.

Enhanced with:
  - Preference-driven recall (bad experience with bread → avoid bread)
  - Gossip collection (events to spread during conversations)
  - Conversation context (who said what recently, for back-and-forth)
  - Emotional valence on memories (positive/negative tagging)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from roma_aeterna.config import (
    MEMORY_PROMOTION_IMPORTANCE, MEMORY_IMMEDIATE_LT_IMPORTANCE,
    GOSSIP_IMPORTANCE_THRESHOLD, GOSSIP_BUFFER_CAP,
)


@dataclass
class MemoryEntry:
    """A single memory with metadata."""
    text: str
    tick: int
    importance: float = 1.0
    memory_type: str = "event"      # event, conversation, observation, feeling, discovery
    related_agent: Optional[str] = None
    location: Optional[Tuple[int, int]] = None
    tags: List[str] = field(default_factory=list)
    valence: float = 0.0           # -1.0 = very negative, +1.0 = very positive


@dataclass
class Relationship:
    """How this agent feels about another agent."""
    agent_name: str
    trust: float = 0.0
    familiarity: float = 0.0
    last_interaction_tick: int = 0
    interaction_count: int = 0
    notes: List[str] = field(default_factory=list)
    # Track conversation state for back-and-forth
    last_said_to_me: str = ""
    last_i_said: str = ""
    awaiting_response: bool = False


@dataclass
class Belief:
    """Something the agent believes to be true (may or may not be)."""
    subject: str
    claim: str
    confidence: float = 0.5
    source: str = "unknown"
    tick_learned: int = 0


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

        # Gossip buffer: interesting events to share in conversations
        self.gossip_buffer: List[MemoryEntry] = []

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
        valence: float = 0.0,
    ) -> None:
        """Record a new memory. High-importance events also go to long-term."""
        tags = tags or []

        # Auto-detect valence from tags
        if valence == 0.0:
            if any(t in tags for t in ["negative", "danger", "death", "fire"]):
                valence = -0.5
            elif any(t in tags for t in ["positive", "trade", "social"]):
                valence = 0.3

        entry = MemoryEntry(
            text=text, tick=tick, importance=importance,
            memory_type=memory_type, related_agent=related_agent,
            location=location, tags=tags, valence=valence,
        )
        self.short_term.append(entry)

        # Overflow: evict the least important entry.
        # Use min() rather than sort-then-pop so that insertion (chronological)
        # order is preserved — get_recent_context relies on short_term[-n:] to
        # return the n most recently added memories.
        if len(self.short_term) > self._short_cap:
            min_idx = min(
                range(len(self.short_term)),
                key=lambda i: self.short_term[i].importance,
            )
            evicted = self.short_term.pop(min_idx)
            if evicted.importance >= MEMORY_PROMOTION_IMPORTANCE:
                self._promote_to_long_term(evicted)

        # Immediately promote very important events
        if importance >= MEMORY_IMMEDIATE_LT_IMPORTANCE:
            self._promote_to_long_term(entry)

        # High-importance events are gossip-worthy
        if importance >= GOSSIP_IMPORTANCE_THRESHOLD and memory_type != "conversation":
            self.gossip_buffer.append(entry)
            if len(self.gossip_buffer) > GOSSIP_BUFFER_CAP:
                self.gossip_buffer.pop(0)

    def _promote_to_long_term(self, entry: MemoryEntry) -> None:
        """Move a memory to long-term storage."""
        if entry not in self.long_term:
            self.long_term.append(entry)
        if len(self.long_term) > self._long_cap:
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

    def record_conversation(self, other_name: str, they_said: str = "",
                            i_said: str = "") -> None:
        """Track conversation state for back-and-forth dialogue."""
        if other_name not in self.relationships:
            self.relationships[other_name] = Relationship(agent_name=other_name)

        rel = self.relationships[other_name]
        if they_said:
            rel.last_said_to_me = they_said
            rel.awaiting_response = False
        if i_said:
            rel.last_i_said = i_said
            rel.awaiting_response = True

    def add_belief(self, subject: str, claim: str, confidence: float = 0.5,
                   source: str = "observation", tick: int = 0) -> None:
        """Add or update a belief."""
        for belief in self.beliefs:
            if belief.subject == subject and belief.claim == claim:
                belief.confidence = min(1.0, belief.confidence + 0.1)
                return
            # Contradicting belief — lower confidence of old one
            if belief.subject == subject and belief.claim != claim:
                belief.confidence = max(0.0, belief.confidence - 0.2)

        self.beliefs.append(Belief(subject, claim, confidence, source, tick))
        if len(self.beliefs) > 30:
            self.beliefs.sort(key=lambda b: b.confidence, reverse=True)
            self.beliefs.pop()

    def learn_location(self, name: str, pos: Tuple[int, int]) -> None:
        """Remember where something is."""
        self.known_locations[name] = pos

    def update_preference(self, subject: str, delta: float) -> None:
        """Adjust preference for an item or activity.

        Negative experiences compound (food poisoning from bread → strong aversion).
        Positive experiences grow slowly.
        """
        current = self.preferences.get(subject, 0.0)
        if delta < 0:
            # Negative experiences have stronger impact
            new_val = current + delta * 0.3
        else:
            new_val = current + delta * 0.1
        self.preferences[subject] = max(-1.0, min(1.0, new_val))

    def get_preference(self, subject: str) -> float:
        """Get preference score for an item/activity."""
        return self.preferences.get(subject, 0.0)

    # ================================================================
    # RETRIEVAL — For autopilot and LLM decision-making
    # ================================================================

    def recall_about(self, subject: str, n: int = 3) -> List[MemoryEntry]:
        """Recall memories related to a specific subject (person, place, item).

        Searches both short and long-term memory.
        """
        all_memories = self.short_term + self.long_term
        relevant = []
        subject_lower = subject.lower()

        for m in all_memories:
            if (subject_lower in m.text.lower() or
                    (m.related_agent and subject_lower in m.related_agent.lower())):
                relevant.append(m)

        # Sort by importance, return top N
        relevant.sort(key=lambda m: m.importance, reverse=True)
        return relevant[:n]

    def get_gossip_for_conversation(self) -> Optional[MemoryEntry]:
        """Get something interesting to share in a conversation.

        Returns the most recent gossip-worthy memory, or None.
        """
        if not self.gossip_buffer:
            return None
        return self.gossip_buffer[-1]

    def get_conversation_context(self, agent_name: str) -> str:
        """Get context for an ongoing conversation with a specific agent."""
        rel = self.relationships.get(agent_name)
        if not rel:
            return "You have never spoken to this person before."

        parts = []
        if rel.last_said_to_me:
            parts.append(f"They last said: \"{rel.last_said_to_me}\"")
        if rel.last_i_said:
            parts.append(f"You last said: \"{rel.last_i_said}\"")

        # Recent conversation memories with this person
        recent_convos = [
            m for m in self.short_term
            if m.memory_type == "conversation" and m.related_agent == agent_name
        ][-3:]
        if recent_convos:
            parts.append("Recent exchange:")
            for m in recent_convos:
                parts.append(f"  {m.text}")

        return "\n".join(parts) if parts else "No recent conversation."

    def get_location_for_need(self, need: str) -> Optional[Tuple[str, Tuple[int, int]]]:
        """Find a known location that could satisfy a need.

        Returns (location_name, (x, y)) or None.
        """
        need_locations = {
            "thirst": ["Fountain", "Bathhouse", "Taverna"],
            "hunger": ["Market", "Bakery", "Taverna", "Forum Market"],
            "energy": ["Bathhouse", "Insula", "Domus"],
            "social": ["Forum", "Colosseum", "Bathhouse", "Taverna"],
            "comfort": ["Temple", "Bathhouse", "Domus"],
        }

        targets = need_locations.get(need, [])
        for target in targets:
            # Check exact match and partial match
            for name, pos in self.known_locations.items():
                if target.lower() in name.lower():
                    return (name, pos)

        return None

    # ================================================================
    # CONTEXT GENERATION — For LLM prompts
    # ================================================================

    def get_recent_context(self, n: int = 5) -> str:
        """Return the N most recently occurring unique memories, newest first.

        All short-term memories are included regardless of importance — the
        global deduplication handles repetition by collapsing identical texts
        with a (×N) suffix and surfacing the most recent occurrence.
        """
        if not self.short_term:
            return "Nothing notable has happened recently."

        # Group all entries by text: track most-recent tick and total count
        text_groups: Dict[str, List] = {}  # text -> [max_tick, count]
        for m in self.short_term:
            if m.text in text_groups:
                entry = text_groups[m.text]
                if m.tick > entry[0]:
                    entry[0] = m.tick
                entry[1] += 1
            else:
                text_groups[m.text] = [m.tick, 1]

        # Sort by most-recent occurrence, take top n unique entries
        sorted_entries = sorted(
            text_groups.items(), key=lambda x: x[1][0], reverse=True
        )[:n]

        lines = []
        for text, (tick, count) in sorted_entries:
            suffix = f" (×{count})" if count > 1 else ""
            lines.append(f"- [Tick {tick}] {text}{suffix}")
        return "\n".join(lines)

    def get_recent_outcomes(self, n: int = 8) -> str:
        """Return the N most recent non-trivial events as a raw chronological log.

        Unlike get_recent_context() this does NOT deduplicate by text — it preserves
        the raw timeline so agents can read progression (e.g. "Set off toward X" →
        several walk steps → "You have arrived near X"). Entries with importance <= 0.5
        (walk noise) are excluded.
        """
        candidates = [m for m in self.short_term if m.importance > 0.5]
        recent = candidates[-n:]   # oldest-to-newest slice from the tail
        if not recent:
            return "Nothing notable has happened yet."
        return "\n".join(f"- [Tick {m.tick}] {m.text}" for m in recent)

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
            if rel.trust > 50:
                sentiment = "trusted ally"
            elif rel.trust > 20:
                sentiment = "friendly"
            elif rel.trust < -50:
                sentiment = "hostile"
            elif rel.trust < -20:
                sentiment = "distrusted"

            # Include conversation state
            convo = ""
            if rel.awaiting_response:
                convo = " [waiting for their reply]"
            elif rel.last_said_to_me:
                convo = " [they spoke to you recently]"

            lines.append(
                f"- {name}: {sentiment} (met {rel.interaction_count} times){convo}"
            )
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

    def get_reflections(self, n: int = 10) -> str:
        """Return personal notes the agent has REFLECT-ed into long-term memory."""
        notes = [
            m for m in self.long_term
            if m.memory_type == "reflection"
        ]
        if not notes:
            return ""
        notes.sort(key=lambda m: m.tick, reverse=True)
        return "\n".join(f"- {m.text}" for m in notes[:n])

    def get_preferences_summary(self) -> str:
        """Summarize learned preferences for LLM context."""
        if not self.preferences:
            return ""

        likes = []
        dislikes = []
        for item, score in self.preferences.items():
            if score > 0.3:
                likes.append(item)
            elif score < -0.3:
                dislikes.append(item)

        parts = []
        if likes:
            parts.append(f"You like: {', '.join(likes)}")
        if dislikes:
            parts.append(f"You dislike: {', '.join(dislikes)}")

        return "\n".join(parts)
