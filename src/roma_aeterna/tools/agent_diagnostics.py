#!/usr/bin/env python3
"""
Rome: Aeterna — Agent Diagnostic Dashboard
============================================

Run this ALONGSIDE the simulation. It connects to the same engine
and provides a terminal-based live view of:

  1. Each agent's last LLM prompt and raw response
  2. Decision history (autopilot + LLM)
  3. Current drives, health, LIF state
  4. What the LLM actually returned (raw text) vs what was parsed

Usage:
    # Option A: Import and attach to a running engine
    from roma_aeterna.tools.agent_diagnostics import AgentDiagnostics
    diag = AgentDiagnostics(engine)
    diag.dump_all()          # Print everything
    diag.dump_agent("Marcus Aurelius")  # Single agent
    diag.watch(interval=5)   # Auto-refresh every 5 seconds

    # Option B: Standalone script — import your engine and run
    python -m roma_aeterna.tools.agent_diagnostics
"""

import json
import time
import sys
from typing import Any, List, Optional


class AgentDiagnostics:
    """Diagnostic viewer for agent LLM interactions."""

    def __init__(self, engine: Any) -> None:
        self.engine = engine

    def get_agent(self, name: str) -> Optional[Any]:
        """Find an agent by name (case-insensitive partial match)."""
        name_lower = name.lower()
        for agent in self.engine.agents:
            if name_lower in agent.name.lower():
                return agent
        return None

    def dump_agent(self, name: str) -> str:
        """Generate a full diagnostic report for one agent."""
        agent = self.get_agent(name)
        if not agent:
            return f"Agent '{name}' not found. Available: {[a.name for a in self.engine.agents]}"

        lines = []
        lines.append("=" * 72)
        lines.append(f"  AGENT DIAGNOSTIC: {agent.name}")
        lines.append(f"  Role: {agent.role}  |  Alive: {agent.is_alive}  |  Tick: {int(agent.current_time)}")
        lines.append("=" * 72)

        # --- Health & Drives ---
        lines.append("")
        lines.append("--- VITALS ---")
        lines.append(f"  Health: {agent.health:.1f}/{agent.max_health:.1f}")
        lines.append(f"  Denarii: {agent.denarii}")
        lines.append(f"  Position: ({agent.x:.1f}, {agent.y:.1f})")
        lines.append(f"  Action: {agent.action}")
        lines.append(f"  Waiting for LLM: {agent.waiting_for_llm}")
        lines.append("")
        for drive, val in agent.drives.items():
            bar = "█" * int(val / 5) + "░" * (20 - int(val / 5))
            lines.append(f"  {drive:>10}: [{bar}] {val:.1f}%")

        # --- LIF Neuron State ---
        lines.append("")
        lines.append("--- LIF NEURON ---")
        brain = agent.brain
        lines.append(f"  Potential: {brain.potential:.3f}")
        lines.append(f"  Threshold: {brain.params.threshold:.1f}")
        lines.append(f"  Decay rate: {brain.params.decay_rate}")
        lines.append(f"  Refractory: {brain.is_refractory}")
        lines.append(f"  Last spike: tick {brain.last_spike_time:.1f}")

        urgency = agent._compute_urgency()
        equilibrium = urgency / brain.params.decay_rate if brain.params.decay_rate > 0 else float('inf')
        will_fire = equilibrium >= brain.params.threshold
        lines.append(f"  Current urgency (input): {urgency:.2f}")
        lines.append(f"  Equilibrium V: {equilibrium:.2f}")
        lines.append(f"  Will eventually fire: {'YES' if will_fire else 'NO'}")

        fire_count = sum(1 for f in brain.fire_history if f)
        lines.append(f"  Fires in last 120 samples: {fire_count}")

        # --- Status Effects ---
        lines.append("")
        lines.append("--- STATUS EFFECTS ---")
        if agent.status_effects.active:
            for effect in agent.status_effects.active:
                lines.append(f"  - {effect.name} (ticks remaining: {effect.remaining_ticks})")
        else:
            lines.append("  (none)")

        # --- Inventory ---
        lines.append("")
        lines.append("--- INVENTORY ---")
        if agent.inventory:
            for item in agent.inventory:
                spoil = f" [freshness: {item.freshness:.0%}]" if item.spoilable else ""
                lines.append(f"  - {item.name} ({item.item_type}, {item.trade_value}d){spoil}")
        else:
            lines.append("  (empty)")

        # --- Decision History ---
        lines.append("")
        lines.append("--- DECISION HISTORY ---")
        if hasattr(agent, 'decision_history') and agent.decision_history:
            for i, d in enumerate(agent.decision_history):
                src_tag = "AUTO" if d["source"] == "autopilot" else " LLM"
                lines.append(f"  [{src_tag}] Tick {d['tick']:>6}: {d['action']:<12} {d.get('target', '')}")
                lines.append(f"           Thought: {d['thought'][:70]}")
                if d.get("speech"):
                    lines.append(f"           Speech: \"{d['speech'][:60]}\"")
        else:
            lines.append("  *** NO DECISIONS RECORDED ***")
            lines.append("  This means either:")
            lines.append("  a) The LIF neuron hasn't fired yet (check urgency/threshold above)")
            lines.append("  b) The LLM returned invalid JSON (check raw responses below)")
            lines.append("  c) The autopilot returned None and LLM queue is backed up")

        # --- Last LLM Prompts ---
        lines.append("")
        lines.append("--- LAST LLM PROMPT (most recent) ---")
        if hasattr(agent, 'prompt_history') and agent.prompt_history:
            last_prompt = agent.prompt_history[-1]
            # Show first 40 lines to keep it readable
            prompt_lines = last_prompt.split('\n')
            for pl in prompt_lines[:40]:
                lines.append(f"  {pl}")
            if len(prompt_lines) > 40:
                lines.append(f"  ... ({len(prompt_lines) - 40} more lines)")
        else:
            lines.append("  *** NO PROMPTS SENT YET ***")
            lines.append("  The agent has never been queued for LLM inference.")

        # --- Last Raw LLM Responses ---
        lines.append("")
        lines.append("--- LAST RAW LLM RESPONSES ---")
        if hasattr(agent, 'llm_response_log') and agent.llm_response_log:
            for i, entry in enumerate(agent.llm_response_log[-3:]):
                lines.append(f"  [Response {i+1}] tick={entry.get('tick', '?')}")
                lines.append(f"    Raw: {entry.get('raw', '(none)')[:200]}")
                lines.append(f"    Parsed: {entry.get('parsed', '(none)')}")
                if entry.get('error'):
                    lines.append(f"    ERROR: {entry['error']}")
                lines.append("")
        else:
            lines.append("  *** NO RAW RESPONSES LOGGED ***")
            lines.append("  To enable this, add response logging to the worker")
            lines.append("  (see instructions in PATCH_GUIDE.md)")

        # --- Memory Summary ---
        lines.append("")
        lines.append("--- MEMORY ---")
        lines.append(f"  Short-term entries: {len(agent.memory.short_term)}")
        lines.append(f"  Long-term entries: {len(agent.memory.long_term)}")
        lines.append(f"  Known locations: {len(agent.memory.known_locations)}")
        lines.append(f"  Relationships: {len(agent.memory.relationships)}")
        lines.append(f"  Beliefs: {len(agent.memory.beliefs)}")

        if agent.memory.short_term:
            lines.append("  Recent memories:")
            for m in agent.memory.short_term[-5:]:
                lines.append(f"    [tick {m.tick}] {m.text[:60]}")

        lines.append("")
        lines.append("=" * 72)

        return "\n".join(lines)

    def dump_all(self) -> str:
        """Generate a summary report for all agents."""
        lines = []
        lines.append("")
        lines.append("╔══════════════════════════════════════════════════════════════╗")
        lines.append("║          ROME: AETERNA — AGENT DIAGNOSTIC REPORT           ║")
        lines.append(f"║  Tick: {self.engine.tick_count:<8} Agents: {len(self.engine.agents):<4}                       ║")
        lines.append("╚══════════════════════════════════════════════════════════════╝")
        lines.append("")

        # Quick overview table
        lines.append(f"  {'Name':<22} {'Role':<18} {'HP':>5} {'Hung':>5} {'Thst':>5} {'LIF V':>7} {'Decs':>5} {'Status'}")
        lines.append("  " + "-" * 95)

        for agent in self.engine.agents:
            n_decisions = len(agent.decision_history) if hasattr(agent, 'decision_history') else 0
            status = "DEAD" if not agent.is_alive else ("WAIT" if agent.waiting_for_llm else "OK")
            lif_v = f"{agent.brain.potential:.2f}"
            lines.append(
                f"  {agent.name:<22} {agent.role:<18} {agent.health:>5.0f} "
                f"{agent.drives['hunger']:>5.1f} {agent.drives['thirst']:>5.1f} "
                f"{lif_v:>7} {n_decisions:>5} {status}"
            )

        lines.append("")

        # Flag issues
        issues = []
        for agent in self.engine.agents:
            n_dec = len(agent.decision_history) if hasattr(agent, 'decision_history') else 0
            n_prompts = len(agent.prompt_history) if hasattr(agent, 'prompt_history') else 0

            if agent.is_alive and n_prompts > 0 and n_dec == 0:
                issues.append(f"  ⚠ {agent.name}: Sent {n_prompts} prompts but 0 decisions recorded → LLM likely returning bad JSON")
            elif agent.is_alive and n_prompts == 0 and agent.current_time > 30:
                issues.append(f"  ⚠ {agent.name}: No prompts sent after {agent.current_time:.0f}s → LIF never fired or autopilot handles everything")
            elif not agent.is_alive:
                issues.append(f"  ✗ {agent.name}: DEAD (health={agent.health:.0f})")

        if issues:
            lines.append("  ISSUES DETECTED:")
            lines.extend(issues)
        else:
            lines.append("  No issues detected.")

        lines.append("")
        return "\n".join(lines)

    def dump_llm_queue(self) -> str:
        """Show the current LLM worker queue."""
        worker = self.engine.llm_worker
        with worker.lock:
            queue = list(worker.input_queue)
        if not queue:
            return "  LLM queue: (empty)"
        return "  LLM queue:\n" + "\n".join(f"    - {a.name}" for a in queue)

    def watch(self, interval: float = 5.0, agent_name: Optional[str] = None):
        """Auto-refresh diagnostic output in the terminal."""
        print(f"[Diagnostics] Watching {'all agents' if not agent_name else agent_name} every {interval}s...")
        print("[Diagnostics] Press Ctrl+C to stop.\n")
        try:
            while True:
                # Clear screen
                print("\033[2J\033[H", end="")
                if agent_name:
                    print(self.dump_agent(agent_name))
                else:
                    print(self.dump_all())
                print(self.dump_llm_queue())
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[Diagnostics] Stopped.")

    def export_json(self, filepath: str = "agent_diagnostics.json") -> None:
        """Export all agent states as JSON for external analysis."""
        data = {
            "tick": self.engine.tick_count,
            "agents": []
        }
        for agent in self.engine.agents:
            agent_data = {
                "name": agent.name,
                "role": agent.role,
                "alive": agent.is_alive,
                "health": agent.health,
                "position": [agent.x, agent.y],
                "drives": dict(agent.drives),
                "lif": {
                    "potential": agent.brain.potential,
                    "threshold": agent.brain.params.threshold,
                    "decay": agent.brain.params.decay_rate,
                    "refractory": agent.brain.is_refractory,
                    "urgency": agent._compute_urgency(),
                },
                "decisions": agent.decision_history if hasattr(agent, 'decision_history') else [],
                "prompts_sent": len(agent.prompt_history) if hasattr(agent, 'prompt_history') else 0,
                "raw_responses": agent.llm_response_log if hasattr(agent, 'llm_response_log') else [],
                "memory_count": len(agent.memory.short_term) + len(agent.memory.long_term),
            }
            data["agents"].append(agent_data)

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"[Diagnostics] Exported to {filepath}")


# ============================================================
# Standalone runner — attach to a running engine
# ============================================================

if __name__ == "__main__":
    print("Agent Diagnostics — Standalone Mode")
    print("=" * 50)
    print()
    print("To use this, import it in your main script:")
    print()
    print("  from roma_aeterna.tools.agent_diagnostics import AgentDiagnostics")
    print("  diag = AgentDiagnostics(engine)")
    print()
    print("Then call:")
    print("  diag.dump_all()              # Overview of all agents")
    print("  diag.dump_agent('Marcus')    # Detailed view of one agent")
    print("  diag.watch(interval=5)       # Live terminal dashboard")
    print("  diag.export_json()           # Export for analysis")
    print()
    print("Or add to your renderer's run loop (e.g. press F1 to dump):")
    print()
    print("  if event.key == pygame.K_F1:")
    print("      print(diag.dump_all())")
    print("  if event.key == pygame.K_F2:")
    print("      print(diag.dump_agent('Marcus Aurelius'))")
