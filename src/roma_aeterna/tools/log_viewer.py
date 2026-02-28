#!/usr/bin/env python3
"""
Rome: Aeterna — Session Log Viewer
====================================

Reads a session JSONL log and lets you browse everything that happened.

Usage:
    python -m roma_aeterna.tools.log_viewer logs/session.jsonl
    python -m roma_aeterna.tools.log_viewer logs/session.jsonl --agent "Marcus Aurelius"
    python -m roma_aeterna.tools.log_viewer logs/session.jsonl --type llm_response
    python -m roma_aeterna.tools.log_viewer logs/session.jsonl --agent "Spartacus" --type decision
    python -m roma_aeterna.tools.log_viewer logs/session.jsonl --summary
    python -m roma_aeterna.tools.log_viewer logs/session.jsonl --failures
"""

import json
import sys
import argparse
from collections import Counter, defaultdict
from typing import List, Dict, Any


def load_log(path: str) -> List[Dict[str, Any]]:
    """Load all events from a JSONL file."""
    events = []
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"  Warning: bad JSON on line {line_num}: {e}", file=sys.stderr)
    return events


def filter_events(events: List[Dict], agent: str = None,
                  event_type: str = None) -> List[Dict]:
    """Filter events by agent name and/or event type."""
    result = events
    if event_type:
        result = [e for e in result if e.get("type") == event_type]
    if agent:
        agent_lower = agent.lower()
        result = [e for e in result
                  if agent_lower in e.get("agent", "").lower()
                  or e.get("type") in ("snapshot", "session_start", "session_end")]
    return result


def print_summary(events: List[Dict]) -> None:
    """Print a high-level summary of the session."""
    type_counts = Counter(e["type"] for e in events)
    agent_decisions = Counter()
    agent_llm_responses = Counter()
    agent_failures = Counter()
    deaths = []

    for e in events:
        if e["type"] == "decision":
            agent_decisions[e["agent"]] += 1
        elif e["type"] == "llm_response":
            agent_llm_responses[e["agent"]] += 1
            if e.get("error"):
                agent_failures[e["agent"]] += 1
        elif e["type"] == "death":
            deaths.append(e["agent"])

    # Session info
    starts = [e for e in events if e["type"] == "session_start"]
    ends = [e for e in events if e["type"] == "session_end"]

    print("=" * 60)
    print("  SESSION SUMMARY")
    print("=" * 60)

    if starts:
        s = starts[0]
        print(f"  Started: {s.get('timestamp', '?')}")
        print(f"  Agents:  {s.get('n_agents', '?')}")
    if ends:
        print(f"  Ended:   {ends[-1].get('timestamp', '?')}")
        print(f"  Final tick: {ends[-1].get('tick', '?')}")

    print()
    print("  Event counts:")
    for etype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"    {etype:<20} {count:>5}")

    print()
    print(f"  {'Agent':<25} {'Decisions':>10} {'LLM Calls':>10} {'Failures':>10}")
    print("  " + "-" * 57)

    all_agents = set(agent_decisions.keys()) | set(agent_llm_responses.keys())
    for name in sorted(all_agents):
        dec = agent_decisions.get(name, 0)
        llm = agent_llm_responses.get(name, 0)
        fail = agent_failures.get(name, 0)
        flag = " ⚠" if llm > 0 and dec == 0 else ""
        print(f"  {name:<25} {dec:>10} {llm:>10} {fail:>10}{flag}")

    if deaths:
        print()
        print(f"  Deaths: {', '.join(deaths)}")

    # Flag issues
    print()
    for name in all_agents:
        llm = agent_llm_responses.get(name, 0)
        dec = agent_decisions.get(name, 0)
        fail = agent_failures.get(name, 0)
        if llm > 0 and dec == 0:
            print(f"  ⚠ {name}: {llm} LLM calls but 0 decisions → all responses failed to parse")
        if fail > 0:
            print(f"  ⚠ {name}: {fail}/{llm} LLM responses had parse errors")


def print_failures(events: List[Dict]) -> None:
    """Show all LLM responses that failed to parse."""
    failures = [e for e in events if e["type"] == "llm_response" and e.get("error")]

    if not failures:
        print("  No LLM parse failures found.")
        return

    print(f"  Found {len(failures)} failed LLM responses:\n")

    for i, e in enumerate(failures):
        print(f"  [{i+1}] Agent: {e['agent']} | Tick: {e.get('response_tick', '?')}")
        print(f"      Error: {e['error']}")
        raw = e.get("raw", "")
        if raw:
            # Show first 300 chars of raw output
            preview = raw[:300].replace('\n', '\n      ')
            print(f"      Raw output:")
            print(f"      {preview}")
            if len(raw) > 300:
                print(f"      ... ({len(raw) - 300} more chars)")
        print()


def print_agent_timeline(events: List[Dict], agent_name: str) -> None:
    """Show the full timeline for one agent."""
    agent_lower = agent_name.lower()

    print(f"\n  Timeline for: {agent_name}")
    print("  " + "=" * 58)

    for e in events:
        if e.get("type") == "snapshot":
            continue  # Skip snapshots in timeline view

        name = e.get("agent", "")
        if agent_lower not in name.lower():
            continue

        tick = e.get("tick", e.get("decision_tick", e.get("response_tick", "?")))
        etype = e["type"]

        if etype == "decision":
            src = "AUTO" if e.get("source") == "autopilot" else " LLM"
            print(f"\n  [Tick {tick}] DECISION ({src})")
            print(f"    Action:  {e.get('action', '?')} → {e.get('target', '')}")
            print(f"    Thought: {e.get('thought', '')[:80]}")
            if e.get("speech"):
                print(f"    Speech:  \"{e['speech'][:80]}\"")

        elif etype == "llm_request":
            prompt = e.get("prompt", "")
            n_lines = prompt.count('\n') + 1
            n_chars = len(prompt)
            print(f"\n  [Tick {tick}] LLM REQUEST ({n_lines} lines, {n_chars} chars)")
            # Show just the action section (last ~15 lines)
            lines = prompt.split('\n')
            action_start = None
            for j, line in enumerate(lines):
                if "DECIDE YOUR NEXT ACTION" in line:
                    action_start = j
                    break
            if action_start is not None:
                print(f"    (prompt truncated, showing action section)")
                for line in lines[max(0, action_start - 3):action_start]:
                    print(f"    {line[:90]}")
            else:
                # Show last 5 lines
                for line in lines[-5:]:
                    print(f"    {line[:90]}")

        elif etype == "llm_response":
            status = "✓ OK" if not e.get("error") else f"✗ FAILED: {e['error']}"
            print(f"\n  [Tick {tick}] LLM RESPONSE ({status})")
            raw = e.get("raw", "")
            if raw:
                preview = raw[:200].replace('\n', '\n    ')
                print(f"    Raw: {preview}")
            if e.get("parsed"):
                print(f"    Parsed: {e['parsed'][:150]}")

        elif etype == "death":
            print(f"\n  [Tick {tick}] ☠ DIED")
            print(f"    Health: {e.get('health', '?')}")
            print(f"    Drives: {e.get('drives', {})}")
            print(f"    Effects: {e.get('status_effects', [])}")
            print(f"    Last thought: {e.get('last_thought', '?')}")


def print_events(events: List[Dict]) -> None:
    """Print filtered events in a readable format."""
    for e in events:
        etype = e.get("type", "?")

        if etype == "snapshot":
            tick = e.get("tick", "?")
            agents = e.get("agents", [])
            alive = sum(1 for a in agents if a.get("alive"))
            print(f"[Tick {tick}] SNAPSHOT — {alive}/{len(agents)} alive")
            for a in agents:
                status = "OK" if a["alive"] else "DEAD"
                print(f"  {a['name']:<22} {a['role']:<18} HP={a['health']:>5.1f} "
                      f"Act={a['action']:<8} LIF={a['lif_potential']:.2f}/{a['lif_threshold']:.1f} "
                      f"Dec={a['n_decisions']} LLM={a['n_llm_responses']} [{status}]")
            print()

        elif etype in ("decision", "llm_response", "llm_request", "death"):
            # These are handled by print_agent_timeline format
            tick = e.get("tick", "?")
            agent = e.get("agent", "?")
            if etype == "decision":
                print(f"[Tick {tick}] {agent}: {e.get('source','?').upper()} → "
                      f"{e.get('action','?')} {e.get('target','')} "
                      f"| {e.get('thought','')[:60]}")
            elif etype == "llm_response":
                ok = "✓" if not e.get("error") else "✗"
                print(f"[Tick {tick}] {agent}: LLM {ok} | {e.get('raw','')[:80]}")
            elif etype == "death":
                print(f"[Tick {tick}] {agent}: ☠ DIED (HP={e.get('health','?')})")


def main():
    parser = argparse.ArgumentParser(description="Browse Rome: Aeterna session logs")
    parser.add_argument("logfile", help="Path to the JSONL session log")
    parser.add_argument("--agent", "-a", help="Filter by agent name (partial match)")
    parser.add_argument("--type", "-t", choices=[
        "decision", "llm_request", "llm_response", "snapshot", "death"
    ], help="Filter by event type")
    parser.add_argument("--summary", "-s", action="store_true",
                        help="Show session summary only")
    parser.add_argument("--failures", "-f", action="store_true",
                        help="Show only failed LLM parses")
    parser.add_argument("--timeline", action="store_true",
                        help="Show full timeline for --agent (requires --agent)")

    args = parser.parse_args()

    print(f"  Loading {args.logfile}...")
    events = load_log(args.logfile)
    print(f"  Loaded {len(events)} events.\n")

    if args.summary:
        print_summary(events)
    elif args.failures:
        print_failures(events)
    elif args.timeline and args.agent:
        print_agent_timeline(events, args.agent)
    else:
        filtered = filter_events(events, agent=args.agent, event_type=args.type)
        if args.agent and not args.type:
            # Default to timeline view for single agent
            print_agent_timeline(filtered, args.agent)
        else:
            print_events(filtered)


if __name__ == "__main__":
    main()
