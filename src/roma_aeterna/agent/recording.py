"""
DecisionRecorder — Tracks and summarises agent decision history.

Extracted from Agent in base.py so that base.py stays focused on
state and lifecycle. All recording/summarisation methods live here.
"""

from typing import Any, Dict, List

from roma_aeterna.config import DECISION_THOUGHT_TRUNCATE, DECISION_SPEECH_TRUNCATE


class DecisionRecorder:
    """Records decisions, prompts, and LLM responses for one agent."""

    def __init__(self, agent: Any) -> None:
        self._agent = agent
        self.decision_history: List[Dict[str, Any]] = []
        self.prompt_history: List[str] = []
        self.llm_response_log: List[Dict[str, Any]] = []
        self._max_decision_history: int = 20

    # ================================================================
    # RECORDING
    # ================================================================

    def record_decision(self, decision: Dict[str, Any], source: str = "llm") -> None:
        """Record a decision for history tracking."""
        agent = self._agent
        entry = {
            "tick": int(agent.current_time),
            "source": source,
            "thought": decision.get("thought", "..."),
            "action": decision.get("action", "IDLE"),
            "target": decision.get("target", ""),
            "speech": decision.get("speech", ""),
        }
        self.decision_history.append(entry)
        if len(self.decision_history) > self._max_decision_history:
            self.decision_history.pop(0)

    def record_prompt(self, prompt: str) -> None:
        """Store the last prompt sent to the LLM for inspection."""
        self.prompt_history.append(prompt)
        if len(self.prompt_history) > 5:
            self.prompt_history.pop(0)

    def record_llm_response(self, raw_text: str, parsed: Any = None,
                            error: str = "") -> None:
        """Store the raw LLM response for debugging."""
        agent = self._agent
        entry = {
            "tick": int(agent.current_time),
            "raw": raw_text[:500],  # Truncate to avoid memory bloat
            "parsed": str(parsed)[:200] if parsed else None,
            "error": error,
        }
        self.llm_response_log.append(entry)
        if len(self.llm_response_log) > 10:
            self.llm_response_log.pop(0)

    # ================================================================
    # SUMMARIES
    # ================================================================

    def get_decision_history_summary(self, n: int = 10) -> str:
        """Return last N decisions, newest first.

        Consecutive entries with the same action + target + source are collapsed
        into a single line with a (×N) count — this prevents autopilot MOVE
        runs from consuming every slot in the history view.
        """
        if not self.decision_history:
            return "You have not taken any actions yet."
        recent = self.decision_history[-n:]

        # Collapse consecutive identical (action, target, source) runs
        groups: List[Dict[str, Any]] = []
        for d in recent:
            key = (d["action"], d.get("target", ""), d["source"])
            if groups and groups[-1]["key"] == key:
                groups[-1]["entries"].append(d)
            else:
                groups.append({"key": key, "entries": [d]})

        lines = []
        for g in reversed(groups):  # newest first
            d = g["entries"][-1]    # most recent entry in this run
            src = "[auto]" if d["source"] == "autopilot" else "[think]"
            action_desc = d["action"]
            if d.get("target"):
                action_desc += f" → {d['target']}"
            if d.get("speech"):
                action_desc += f' (said: "{d["speech"][:DECISION_SPEECH_TRUNCATE]}")'
            count = len(g["entries"])
            count_suffix = f" (×{count})" if count > 1 else ""
            lines.append(
                f"  [Tick {d['tick']}] {src} {action_desc}{count_suffix}: {d['thought'][:DECISION_THOUGHT_TRUNCATE]}"
            )
        return "\n".join(lines)

    def get_full_history_text(self) -> str:
        """Return full decision history for the inspection window."""
        if not self.decision_history:
            return "No decisions recorded yet."
        lines = []
        for d in self.decision_history:
            src = "AUTOPILOT" if d["source"] == "autopilot" else "LLM"
            lines.append(f"[Tick {d['tick']}] ({src}) Action: {d['action']}")
            lines.append(f"  Thought: {d['thought']}")
            if d.get("target"):
                lines.append(f"  Target: {d['target']}")
            if d.get("speech"):
                lines.append(f"  Speech: \"{d['speech']}\"")
            lines.append("")
        return "\n".join(lines)

    def get_past_states_summary(self, n: int = 6) -> str:
        """Return recent drive snapshots as text for LLM context."""
        snapshots = self._agent.drive_snapshots
        if len(snapshots) < 2:
            return "No prior state data yet."

        recent = snapshots[-n:]
        lines = []
        for snap in recent:
            d = snap["drives"]
            lines.append(
                f"  Tick {snap['tick']}: HP={snap['health']}, "
                f"Hunger={d['hunger']:.0f}%, Thirst={d['thirst']:.0f}%, "
                f"Energy={d['energy']:.0f}%, Social={d['social']:.0f}%, "
                f"Comfort={d.get('comfort', 0):.0f}%"
            )
        return "\n".join(lines)
