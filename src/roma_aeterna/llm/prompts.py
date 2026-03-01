"""
Prompt System — Dynamic context assembly for LLM inference.

Self-assessment (health, drives, status effects) lives here in the
STATUS section — single source of truth, no duplication with perceive().
"""

from typing import Dict, List, Optional, Any
import random

from roma_aeterna.config import (
    PROMPT_RECENT_MEMORIES_N, PROMPT_IMPORTANT_MEMORIES_N,
    PROMPT_DECISION_HISTORY_N, PROMPT_STATE_TRENDS_N, PROMPT_ENV_INTERVAL,
    PROMPT_OUTCOMES_N,
)
from .personalities import assign_personality, ROLE_STARTING_INVENTORY

# ============================================================
# Dynamic Prompt Builder
# ============================================================

SYSTEM_PROMPT_TEMPLATE = """You are {name}, a {role} living in Ancient Rome during the reign of Emperor Marcus Aurelius (161 AD).

PERSONALITY:
{personality_block}

YOUR GOALS:
{goals_block}

YOUR FEARS:
{fears_block}

RULES OF THE WORLD:
- You exist on a grid. You can move one tile at a time in 8 directions or use GOTO to navigate to known places automatically.
- You have physical needs. If hunger or thirst reach critical levels, you will die.
- You can carry items, trade, buy from markets, and consume food/drink. Spoiled food will make you sick.
- Buildings have functions: temples for prayer, fountains for drinking, markets for buying, bathhouses for rest.
- You can work at specific buildings corresponding to your role to earn denarii.
- Fire is deadly. If you see burning or smell smoke, get away.
- You remember things and have preferences based on past experiences (e.g., if you got sick from bread, you dislike bread).
- Pay attention to how you feel! Prioritize survival over routine.
- IMPORTANT: You must respond ONLY with valid JSON. No other text."""

STATUS_TEMPLATE = """YOUR BODY (Tick {current_tick}):
Health: {health}/{max_health}{health_warning}
Denarii (money): {denarii}
{drives_summary}{status_effects_block}

INVENTORY:
{inventory_summary}"""

CONDITION_TEMPLATE = """HOW YOU FEEL RIGHT NOW:
{self_assessment}{urgency_hints}"""

MARKET_TEMPLATE = """GOODS FOR SALE NEARBY:
{market_listings}"""

TRENDS_TEMPLATE = """STATE TRENDS (how your drives have changed):
{past_states}"""

PERCEPTION_TEMPLATE = """WHAT YOU PERCEIVE:
{perception_text}"""

MEMORY_TEMPLATE = """YOUR RECENT MEMORIES:
{recent_memories}

IMPORTANT MEMORIES:
{important_memories}

YOUR PERSONAL NOTES (things you chose to remember):
{reflections}

RELATIONSHIPS:
{relationships}

BELIEFS:
{beliefs}

KNOWN LOCATIONS:
{known_locations}

YOUR PREFERENCES (Likes/Dislikes):
{preferences}"""

INCOMING_MESSAGE_TEMPLATE = """SOMEONE JUST SPOKE TO YOU:
{speaker} said: "{message}"

Your relationship with them: {relationship}
Recent conversation history:
{convo_history}

You may respond with TALK, continue what you were doing, walk away, or do anything else. This is entirely your choice."""

DECISION_HISTORY_TEMPLATE = """YOUR RECENT ACTIONS (what you did recently):
{decision_history}"""

OUTCOMES_TEMPLATE = """WHAT RECENTLY HAPPENED (chronological — most recent at the bottom):
{outcomes}"""

ACTION_TEMPLATE = """DECIDE YOUR NEXT ACTION.
Consider how you feel, what you see, your memories, and your personality.
Available actions:
- MOVE: Move one tile. Specify `direction` (north, south, east, west, northeast, northwest, southeast, southwest).
- GOTO: Autopilot to a known location. `target` MUST be an exact name from KNOWN LOCATIONS.
- BUY: Purchase an item from a nearby market. Specify item as `target` and market name as `market`.
- WORK: Perform your role duties at an appropriate nearby building to earn money.
- CRAFT: Create an item from materials in your inventory. Specify the item name as `target`.
- TALK: Speak to someone nearby. `target` MUST match a name from PEOPLE NEARBY. Specify `speech`.
- INTERACT: Use a nearby building or object (fountain, temple, bench…). `target` MUST be in STRUCTURES NEARBY.
- CONSUME: Eat or drink an item from your inventory. `target` MUST be an exact item name from INVENTORY.
- PICK_UP: Pick up an item from the ground at your location. `target` MUST be an exact item name.
- DROP: Drop an item from your inventory. `target` MUST be an exact item name from INVENTORY.
- REST: Stand still and catch your breath (light recovery).
- SLEEP: Sleep deeply to restore energy fully (takes longer).
- TRADE: Barter with a nearby person. Specify `target` (their name), `offer` (your item), `want` (their item).
- ATTACK: Strike a nearby person. `target` MUST be a name from PEOPLE NEARBY. Optionally specify `item` (a weapon from your INVENTORY) — unarmed if omitted.
- INSPECT: Examine something closely to learn more about it. Specify `target`.
- REFLECT: Write a note to your long-term memory — use this as a scratchpad for anything you don't want to forget: plans, observations, people's secrets, prices you noticed, dangers to avoid, goals. Specify the note as `note` (free text, any length).
- IDLE: Do nothing this turn.

CRITICAL INSTRUCTIONS:
1. You must respond with raw JSON only. Do NOT wrap the output in ```json ... ``` markdown blocks.
2. Only include keys that are needed for your chosen action — omit the rest.

Respond with this EXACT format:
{{
    "thought": "your inner monologue (1-2 sentences)",
    "action": "ACTION_NAME",
    "direction": "one of the 8 valid directions (only if MOVE)",
    "target": "exact name of person/object/item/location (if applicable, not for REFLECT)",
    "market": "exact name of market (only if BUY)",
    "speech": "what you say out loud (only if TALK)",
    "offer": "item you offer (only if TRADE)",
    "want": "item you want (only if TRADE)",
    "note": "free-text note to remember (only if REFLECT)"
}}/no_think"""

def build_prompt(agent: Any, world: Any, agents: List[Any], weather: Any,
                 economy: Any = None) -> str:
    persona = agent.personality_seed

    personality_parts = []
    if persona.get("motivation"):
        personality_parts.append(f"Core motivation: {persona['motivation']}")
    if persona.get("traits"):
        personality_parts.append(f"Traits: {', '.join(persona['traits'])}")
    if persona.get("speech_style"):
        personality_parts.append(f"Speech style: {persona['speech_style']}")
    if persona.get("quirks"):
        personality_parts.append(f"Quirks: {', '.join(persona['quirks'])}")
    personality_block = "\n".join(personality_parts) or "A typical Roman citizen."

    goals = persona.get("goals", ["survive", "find purpose"])
    fears = persona.get("fears", ["death", "dishonor"])

    system = SYSTEM_PROMPT_TEMPLATE.format(
        name=agent.name,
        role=agent.role,
        personality_block=personality_block,
        goals_block="\n".join(f"- {g}" for g in goals),
        fears_block="\n".join(f"- {f}" for f in fears),
    )

    health_warning = ""
    if agent.health < 20:
        health_warning = " ⚠ CRITICAL — YOU ARE DYING"
    elif agent.health < 50:
        health_warning = " ⚠ WOUNDED"

    self_assessment_parts = []
    if agent.health < 20:
        self_assessment_parts.append("⚠ CRITICAL: You are gravely injured. Your vision blurs and your body screams in pain. You could die without help.")
    elif agent.health < 50:
        self_assessment_parts.append("You are wounded and in pain. Moving is difficult.")

    sensation_text = agent.status_effects.get_sensation_summary()
    if sensation_text:
        self_assessment_parts.append(sensation_text)

    if agent.drives["thirst"] > 80:
        self_assessment_parts.append("Your throat is parched and cracked. You MUST find water soon or you will collapse.")
    elif agent.drives["thirst"] > 60:
        self_assessment_parts.append("Your mouth is dry. You need water.")

    if agent.drives["hunger"] > 80:
        self_assessment_parts.append("Your stomach cramps with hunger. You feel weak and dizzy.")
    elif agent.drives["hunger"] > 60:
        self_assessment_parts.append("You are very hungry. Your stomach growls audibly.")

    if agent.drives["energy"] > 80:
        self_assessment_parts.append("You can barely keep your eyes open. Your body begs for rest.")

    if agent.drives["comfort"] > 70:
        self_assessment_parts.append("You feel deeply miserable and uncomfortable.")

    if agent.drives["social"] > 70:
        self_assessment_parts.append("A profound loneliness gnaws at you. You crave human connection.")

    if not self_assessment_parts:
        self_assessment_parts.append("You feel normal. No ailments.")

    self_assessment = "\n".join(self_assessment_parts)

    # Active status effects block (empty string if none)
    if agent.status_effects.active:
        effects_list = ", ".join(e.name for e in agent.status_effects.active)
        status_effects_block = f"\nActive conditions: {effects_list}"
    else:
        status_effects_block = ""

    status = STATUS_TEMPLATE.format(
        current_tick=int(agent.current_time),
        health=int(agent.health),
        max_health=int(agent.max_health),
        health_warning=health_warning,
        denarii=agent.denarii,
        drives_summary=agent.get_drives_summary(),
        status_effects_block=status_effects_block,
        inventory_summary=agent.get_inventory_summary(),
    )

    urgency_hints = _build_urgency_hint(agent)
    condition = CONDITION_TEMPLATE.format(
        self_assessment=self_assessment,
        urgency_hints=urgency_hints,
    )

    trends = TRENDS_TEMPLATE.format(
        past_states=agent.get_past_states_summary(n=PROMPT_STATE_TRENDS_N),
    )

    # Throttle verbose environment: show full prose every PROMPT_ENV_INTERVAL LLM calls
    llm_decision_count = sum(1 for d in agent.decision_history if d.get("source") == "llm")
    include_environment = (llm_decision_count % PROMPT_ENV_INTERVAL == 0)
    perception_text = agent.perceive(world, agents, include_environment=include_environment)
    perception = PERCEPTION_TEMPLATE.format(perception_text=perception_text)

    reflections = agent.memory.get_reflections()
    prefs = agent.memory.get_preferences_summary()
    memory = MEMORY_TEMPLATE.format(
        recent_memories=agent.memory.get_recent_context(n=PROMPT_RECENT_MEMORIES_N),
        important_memories=agent.memory.get_important_memories(n=PROMPT_IMPORTANT_MEMORIES_N),
        reflections=reflections if reflections else "You haven't noted anything yet.",
        relationships=agent.memory.get_relationship_summary(),
        beliefs=agent.memory.get_beliefs_summary(),
        known_locations=agent.memory.get_known_locations_summary(),
        preferences=prefs if prefs else "You have no strong preferences yet.",
    )

    action = ACTION_TEMPLATE.format()

    # Decision history — tells the LLM what the agent did recently
    decision_history_text = agent.get_decision_history_summary(n=PROMPT_DECISION_HISTORY_N)
    decision_history = DECISION_HISTORY_TEMPLATE.format(
        decision_history=decision_history_text,
    )

    # New section order: IDENTITY → BODY → CONDITION → TRENDS → WORLD → [MARKET] → MIND → HISTORY → [MESSAGE] → DECIDE
    sections = [system, status, condition, trends, perception]
    if economy is not None:
        market_listings = _get_nearby_market_listings(agent, world, economy)
        if market_listings:
            sections.append(MARKET_TEMPLATE.format(market_listings=market_listings))
    outcomes_text = agent.memory.get_recent_outcomes(n=PROMPT_OUTCOMES_N)
    outcomes = OUTCOMES_TEMPLATE.format(outcomes=outcomes_text)
    sections += [memory, decision_history, outcomes]

    # Incoming speech — surfaced as explicit context so the agent can
    # freely decide whether to respond, ignore, or do something else.
    pending = agent._pending_conversation
    if pending:
        incoming = INCOMING_MESSAGE_TEMPLATE.format(
            speaker=pending["speaker"],
            message=pending["message"],
            relationship=_get_relationship_desc(agent, pending["speaker"]),
            convo_history=agent.memory.get_conversation_context(pending["speaker"]),
        )
        sections.append(incoming)

    sections.append(action)
    print("\n\n".join(sections))
    return "\n\n".join(sections)

def _build_urgency_hint(agent: Any) -> str:
    hints: List[str] = []
    if agent.health < 20:
        hints.append("⚠ YOU ARE CRITICALLY INJURED. Your survival depends on your next action.")
    if agent.status_effects.has_effect("Burned"):
        hints.append("⚠ You are BURNED. Get away from fire and find help or water.")
    if agent.status_effects.has_effect("Smoke Inhalation"):
        hints.append("⚠ You are choking on SMOKE. Move to clear air immediately.")
    if agent.drives["thirst"] > 80:
        hints.append("⚠ You are desperately THIRSTY. Find water or you will die.")
    if agent.drives["hunger"] > 80:
        hints.append("⚠ You are STARVING. Find food urgently.")
    if agent.status_effects.has_effect("Food Poisoning"):
        hints.append("⚠ You have FOOD POISONING. Rest and find clean water.")
    if agent.status_effects.has_effect("Heatstroke"):
        hints.append("⚠ You have HEATSTROKE. Find shade and water immediately.")

    if not hints:
        return ""
    return "\n" + "\n".join(hints) + "\n"

def _get_nearby_market_listings(agent: Any, world: Any, economy: Any) -> str:
    """Return goods listings for all trade buildings within perception range.

    Shows price and stock so the agent can make an informed BUY decision
    without needing a separate INTERACT action.
    """
    import math
    from roma_aeterna.config import PERCEPTION_RADIUS
    from roma_aeterna.world.components import Interactable

    listings: List[str] = []
    seen: set = set()

    for obj in world.objects:
        if obj.name in seen:
            continue
        dist = math.sqrt((obj.x - agent.x) ** 2 + (obj.y - agent.y) ** 2)
        if dist > PERCEPTION_RADIUS:
            continue
        interact = obj.get_component(Interactable)
        if not interact or interact.interaction_type != "trade":
            continue
        seen.add(obj.name)
        listing = economy.get_market_listing(obj.name)
        listings.append(listing)

    return "\n\n".join(listings)

def _get_relationship_desc(agent: Any, name: str) -> str:
    rel = agent.memory.relationships.get(name)
    if not rel:
        return "You don't know this person."
    if rel.trust > 30:
        return f"You consider them a friend (trust: {int(rel.trust)})"
    elif rel.trust < -30:
        return f"You distrust them (trust: {int(rel.trust)})"
    return f"An acquaintance (met {rel.interaction_count} times)"