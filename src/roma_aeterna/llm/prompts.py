"""
Prompt System — Dynamic context assembly for LLM inference.

Prompt zones (in order):
  1. WHO YOU ARE    — Identity, personality, goals, fears, world rules  (static per agent)
  2. YOUR STATE     — Body, drives, position, current action, last thought, inventory
  3. THE WORLD      — Perception snapshot + market goods + any incoming conversation
  4. RECENT PAST    — Decision history + event outcomes + drive trends (all history together)
  5. YOUR MIND      — Important memories, recent memories, notes, relationships, beliefs, locations, prefs
  6. YOUR CONSCIENCE — Urgency warnings (⚠) + stagnation hints + vita activa reminder
  →  CHOOSE ACTION
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
# Templates
# ============================================================

SYSTEM_PROMPT_TEMPLATE = """You are {name}, a {role} living in Ancient Rome during the reign of Emperor Marcus Aurelius (161 AD).

PERSONALITY:
{personality_block}

YOUR GOALS:
{goals_block}

YOUR FEARS:
{fears_block}

RULES OF THIS WORLD:
- You exist on a grid. Move one tile at a time or use GOTO to navigate to known places automatically.
- Physical needs are real. If hunger or thirst reach critical levels, you will die.
- You can carry items, trade, buy from markets, consume food and drink. Spoiled food causes sickness.
- Buildings have functions: temples for prayer, fountains for drinking, markets for goods, bathhouses for rest.
- Work at buildings suited to your role to earn denarii.
- Fire is deadly — flee if you see flames or smell smoke.
- Your memories and preferences are shaped by what you experience.
- IMPORTANT: Respond ONLY with valid JSON. No other text."""

# Zone 2 — who the agent IS right now, physically and mentally
NOW_YOU_TEMPLATE = """══ YOUR STATE ══  (Tick {current_tick})
Position:  {position}
Health:    {health}/{max_health}{health_warning}   |   Denarii: {denarii}
Drives:    {drives_summary}{status_effects_block}
Feel:      {self_assessment}{mood_line}

Currently: {current_action}
Thinking:  "{last_thought}"

INVENTORY:
{inventory_summary}"""

# Zone 3 — the world right now
NOW_WORLD_TEMPLATE = """══ THE WORLD ══
{perception_text}"""

MARKET_BLOCK_TEMPLATE = """GOODS FOR SALE NEARBY:
{market_listings}"""

INCOMING_MESSAGE_TEMPLATE = """⚡ RIGHT NOW — SOMEONE IS SPEAKING TO YOU:
{speaker}: "{message}"
Your relationship with them: {relationship}
Conversation so far:
{convo_history}
You may reply with TALK, ignore them, or do anything else. Your choice."""

# Zone 4 — what has happened (all history together)
PAST_TEMPLATE = """══ RECENT PAST ══
WHAT YOU JUST DID:
{decision_history}

WHAT HAPPENED AROUND YOU:
{outcomes}

HOW YOUR DRIVES CHANGED:
{past_states}"""

# Zone 5 — everything the agent knows and remembers
MIND_TEMPLATE = """══ YOUR MIND ══
IMPORTANT MEMORIES:
{important_memories}

RECENT MEMORIES:
{recent_memories}

YOUR PERSONAL NOTES:
{reflections}

PEOPLE YOU KNOW:
{relationships}

BELIEFS:
{beliefs}

KNOWN LOCATIONS:
{known_locations}

PREFERENCES:
{preferences}"""

# Zone 6 — warnings + behavioral guidance (urgency first, then coaching, then reminder)
CONSCIENCE_TEMPLATE = """══ YOUR CONSCIENCE ══
{body}"""

ACTION_TEMPLATE = """══ CHOOSE YOUR ACTION ══
Consider your state, the world around you, your recent past, your memories, and your conscience.
Available actions:
- MOVE: Move one tile. `direction` must be one of: north, south, east, west, northeast, northwest, southeast, southwest.
- GOTO: Autopilot to a known location. `target` MUST be an exact name from KNOWN LOCATIONS.
- BUY: Purchase from a nearby market. `target` is the item name. `market` is the market name.
- WORK: Perform your role duties at an appropriate nearby building to earn denarii.
- CRAFT: Create an item from materials in your inventory. `target` is the item name.
- TALK: Speak to someone nearby. `target` MUST match a name from PEOPLE NEARBY. Specify `speech`.
- INTERACT: Use a nearby building or object. `target` MUST be in STRUCTURES NEARBY.
- CONSUME: Eat or drink from inventory. `target` MUST be an exact item name from INVENTORY.
- PICK_UP: Pick up an item from the ground. `target` MUST be an exact item name.
- DROP: Drop an item from inventory. `target` MUST be an exact item name from INVENTORY.
- REST: Catch your breath (light energy recovery).
- SLEEP: Sleep deeply to restore energy fully.
- TRADE: Barter with someone nearby. `target` is their name. `offer` is your item. `want` is their item.
- ATTACK: Strike a nearby person or animal. `target` is their name. `item` is a weapon from INVENTORY (unarmed if omitted).
- GIVE: Give an item to someone nearby — no reciprocation expected. `target` is their name. `item` is from INVENTORY.
- SHOUT: Call out loudly so everyone nearby hears. Specify `speech`. Wider range than TALK.
- INSPECT: Examine something closely to learn more. Specify `target`.
- REFLECT: Write a note to long-term memory — plans, secrets, prices, dangers, goals. Specify as `note`.
- PRAY: Address Jupiter at a nearby temple. `target` MUST be a temple from STRUCTURES NEARBY. `speech` is your prayer.
- IDLE: Do nothing this turn.

CRITICAL INSTRUCTIONS:
1. Respond with raw JSON only. Do NOT wrap in ```json ... ``` markdown blocks.
2. Only include keys needed for your chosen action — omit the rest.

{{
    "thought": "your inner monologue (1-2 sentences)",
    "action": "ACTION_NAME",
    "direction": "direction (only if MOVE)",
    "target": "exact name of person/object/item/location (if applicable)",
    "market": "market name (only if BUY)",
    "speech": "what you say out loud (only if TALK, SHOUT, or PRAY)",
    "offer": "item you offer (only if TRADE)",
    "want": "item you want (only if TRADE)",
    "item": "weapon from INVENTORY (ATTACK) or item to give (GIVE)",
    "note": "free-text note to remember (only if REFLECT)"
}}/no_think"""


# ============================================================
# Main builder
# ============================================================

def build_prompt(agent: Any, world: Any, agents: List[Any], weather: Any,
                 economy: Any = None) -> str:
    """Assemble the full prompt for one LLM inference.

    Section order:
      SYSTEM → YOUR STATE → THE WORLD → [MARKET] → [CONVERSATION]
             → RECENT PAST → YOUR MIND → YOUR CONSCIENCE → CHOOSE ACTION
    """
    persona = agent.personality_seed

    # ------------------------------------------------------------------
    # Zone 1: WHO YOU ARE — system prompt
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Zone 2: YOUR STATE — body + current action + inventory
    # ------------------------------------------------------------------
    health_warning = ""
    if agent.health < 20:
        health_warning = " ⚠ DYING"
    elif agent.health < 50:
        health_warning = " ⚠ WOUNDED"

    # Physical self-assessment (visceral description, not ⚠ commands — those go in CONSCIENCE)
    feel_parts = []
    if agent.health < 20:
        feel_parts.append("Gravely injured — vision blurs, pain everywhere.")
    elif agent.health < 50:
        feel_parts.append("Wounded and in pain.")

    sensation_text = agent.status_effects.get_sensation_summary()
    if sensation_text:
        feel_parts.append(sensation_text)

    if agent.drives["thirst"] > 80:
        feel_parts.append("Throat cracked — desperately thirsty.")
    elif agent.drives["thirst"] > 60:
        feel_parts.append("Dry mouth, growing thirst.")

    if agent.drives["hunger"] > 80:
        feel_parts.append("Stomach cramps, dizzy from hunger.")
    elif agent.drives["hunger"] > 60:
        feel_parts.append("Hungry, stomach growling.")

    if agent.drives["energy"] > 80:
        feel_parts.append("Exhausted — barely keeping eyes open.")
    elif agent.drives["energy"] > 65:
        feel_parts.append("Tired, limbs heavy.")

    if agent.drives["comfort"] > 70:
        feel_parts.append("Deeply uncomfortable and miserable.")

    if agent.drives["social"] > 70:
        feel_parts.append("Lonely — craving company.")

    if not feel_parts:
        feel_parts.append("Fine. No ailments.")

    self_assessment = " | ".join(feel_parts)

    mood_text = agent.memory.get_mood_summary()
    mood_line = f" | {mood_text}" if mood_text else ""

    if agent.status_effects.active:
        effects_list = ", ".join(e.name for e in agent.status_effects.active)
        status_effects_block = f"\nConditions: {effects_list}"
    else:
        status_effects_block = ""

    current_action = _get_current_action_desc(agent)
    last_thought = "..."
    if agent.decision_history:
        raw = agent.decision_history[-1].get("thought", "").strip()
        if raw:
            last_thought = raw[:200]

    now_you = NOW_YOU_TEMPLATE.format(
        current_tick=agent.sim_tick,
        position=_get_position_desc(agent),
        health=int(agent.health),
        max_health=int(agent.max_health),
        health_warning=health_warning,
        denarii=agent.denarii,
        drives_summary=agent.get_drives_summary(),
        status_effects_block=status_effects_block,
        self_assessment=self_assessment,
        mood_line=mood_line,
        current_action=current_action,
        last_thought=last_thought,
        inventory_summary=agent.get_inventory_summary(),
    )

    # ------------------------------------------------------------------
    # Zone 3: THE WORLD — perception + market + conversation
    # ------------------------------------------------------------------
    llm_decision_count = sum(1 for d in agent.decision_history if d.get("source") == "llm")
    include_environment = (llm_decision_count % PROMPT_ENV_INTERVAL == 0)
    perception_text = agent.perceive(world, agents, include_environment=include_environment)

    now_world = NOW_WORLD_TEMPLATE.format(perception_text=perception_text)

    world_extras: List[str] = []
    if economy is not None:
        market_listings = _get_nearby_market_listings(agent, world, economy)
        if market_listings:
            world_extras.append(MARKET_BLOCK_TEMPLATE.format(market_listings=market_listings))

    # Incoming conversation — it's happening RIGHT NOW, so it belongs in the world zone
    pending = agent._pending_conversation
    if pending:
        incoming = INCOMING_MESSAGE_TEMPLATE.format(
            speaker=pending["speaker"],
            message=pending["message"],
            relationship=_get_relationship_desc(agent, pending["speaker"]),
            convo_history=agent.memory.get_conversation_context(pending["speaker"]),
        )
        world_extras.append(incoming)

    # ------------------------------------------------------------------
    # Zone 4: RECENT PAST — what you did + what happened + drive trends
    # ------------------------------------------------------------------
    decision_history_text = agent.get_decision_history_summary(n=PROMPT_DECISION_HISTORY_N)
    outcomes_text = agent.memory.get_recent_outcomes(n=PROMPT_OUTCOMES_N)
    past_states_text = agent.get_past_states_summary(n=PROMPT_STATE_TRENDS_N)

    past = PAST_TEMPLATE.format(
        decision_history=decision_history_text,
        outcomes=outcomes_text,
        past_states=past_states_text,
    )

    # ------------------------------------------------------------------
    # Zone 5: YOUR MIND — memories, knowledge, relationships
    # ------------------------------------------------------------------
    reflections = agent.memory.get_reflections()
    prefs = agent.memory.get_preferences_summary()
    mind = MIND_TEMPLATE.format(
        important_memories=agent.memory.get_important_memories(n=PROMPT_IMPORTANT_MEMORIES_N),
        recent_memories=agent.memory.get_recent_context(n=PROMPT_RECENT_MEMORIES_N),
        reflections=reflections if reflections else "None yet.",
        relationships=agent.memory.get_relationship_summary(),
        beliefs=agent.memory.get_beliefs_summary(),
        known_locations=agent.memory.get_known_locations_summary(),
        preferences=prefs if prefs else "No strong preferences yet.",
    )

    # ------------------------------------------------------------------
    # Zone 6: YOUR CONSCIENCE — urgency warnings first, then coaching
    # ------------------------------------------------------------------
    conscience_text = _build_conscience(agent, agents, world)

    # ------------------------------------------------------------------
    # Assemble
    # ------------------------------------------------------------------
    action = ACTION_TEMPLATE.format()

    sections = [system, now_you, now_world]
    sections.extend(world_extras)
    sections += [past, mind, conscience_text, action]
    print("\n\n".join(sections))
    return "\n\n".join(sections)


# ============================================================
# Helpers
# ============================================================

def _get_current_action_desc(agent: Any) -> str:
    """Human-readable description of what the agent is currently doing."""
    import math as _math
    action = agent.action.upper()

    if action in ("MOVING", "GOTO"):
        dest = agent.autopilot.destination_name
        if dest:
            loc = agent.memory.known_locations.get(dest)
            if loc:
                dist = int(_math.sqrt((loc[0] - agent.x) ** 2 + (loc[1] - agent.y) ** 2))
                return f"Walking to {dest} ({dist} tiles away)"
            return f"Walking to {dest}"
        return "Moving"

    readable = {
        "IDLE":        "Standing still (idle)",
        "WORKING":     "Working",
        "TRADING":     "Trading",
        "TALKING":     "In conversation",
        "SLEEPING":    "Sleeping",
        "RESTING":     "Resting",
        "INTERACTING": "Interacting with something",
        "ATTACKING":   "Fighting",
        "DEAD":        "Dead",
    }
    return readable.get(action, action.capitalize())


def _build_urgency_hint(agent: Any, agents: List[Any] = None) -> str:
    """Return ⚠ warning lines for life-threatening situations. Empty string if safe."""
    hints: List[str] = []
    if agent.health < 20:
        hints.append("⚠ YOU ARE CRITICALLY INJURED. Your survival depends on your next action.")
    if agent.status_effects.has_effect("Burned"):
        hints.append("⚠ You are BURNED. Get away from fire and find help or water.")
    if agent.status_effects.has_effect("Smoke Inhalation"):
        hints.append("⚠ You are choking on SMOKE. Move to clear air immediately.")
    if agent.drives["thirst"] > 80:
        hints.append("⚠ You are desperately THIRSTY. Find water now or you will die.")
    if agent.drives["hunger"] > 80:
        hints.append("⚠ You are STARVING. Find food urgently.")
    if agent.status_effects.has_effect("Food Poisoning"):
        hints.append("⚠ You have FOOD POISONING. Rest and find clean water.")
    if agent.status_effects.has_effect("Heatstroke"):
        hints.append("⚠ You have HEATSTROKE. Find shade and water immediately.")

    # Hostile animal proximity (scan within 12 tiles)
    if agents:
        import math as _math
        DANGER_RADIUS = 12.0
        for a in agents:
            if not getattr(a, "is_animal", False) or not a.is_alive:
                continue
            dist = _math.sqrt((a.x - agent.x) ** 2 + (a.y - agent.y) ** 2)
            if dist > DANGER_RADIUS:
                continue
            if a.action in ("ATTACKING", "HUNTING", "CHARGING"):
                hints.append(f"⚠ DANGER: A {a.animal_type} is {a.action.lower()} nearby!")
                break

    if not hints:
        return ""
    return "\n".join(hints)


def _build_conscience(agent: Any, agents: List[Any], world: Any) -> str:
    """Build Zone 6: urgency warnings + stagnation detection + opportunity hints + vita activa."""
    import math as _math
    from roma_aeterna.config import PERCEPTION_RADIUS

    lines: List[str] = []

    # ------------------------------------------------------------------
    # 1. Urgency warnings — first and loudest if anything is critical
    # ------------------------------------------------------------------
    urgency = _build_urgency_hint(agent, agents)
    if urgency:
        lines.append(urgency)

    # ------------------------------------------------------------------
    # 2. Stagnation detection — what has the agent been doing?
    # ------------------------------------------------------------------
    history = agent.decision_history[-10:] if agent.decision_history else []
    recent5  = [d.get("action", "IDLE").upper() for d in history[-5:]]
    recent10 = [d.get("action", "IDLE").upper() for d in history]

    idle_count = sum(1 for a in recent5 if a == "IDLE")
    rest_count = sum(1 for a in recent5 if a in ("REST", "SLEEP"))
    all_same   = (len(set(recent5)) == 1 and len(recent5) == 5
                  and recent5[0] not in ("MOVE", "MOVING"))
    goto_count = sum(1 for a in recent5 if a == "GOTO")

    if idle_count >= 3:
        lines.append(
            f"You have chosen IDLE {idle_count} times in your last 5 actions. "
            "This is unacceptable. Choose a meaningful action this turn — not IDLE, not REST."
        )
    elif goto_count >= 3:
        lines.append(
            f"You have chosen GOTO {goto_count} times in a row without arriving anywhere. "
            "The path may be blocked. Try a different action: MOVE in a direction manually, "
            "INTERACT with something nearby, or choose a completely different goal."
        )
    elif rest_count >= 3:
        lines.append(
            "You have been resting far too long. Your body has recovered. "
            "Rise and do something — the world will not wait."
        )
    elif all_same:
        lines.append(
            f"You keep choosing {recent5[0]} over and over. Pick a completely different action."
        )
    elif idle_count >= 1 and rest_count >= 1:
        lines.append(
            "You have been passive — idling and resting without purpose. A Roman does not squander their hours."
        )

    # ------------------------------------------------------------------
    # 3. Situational opportunity hints — up to 2, most relevant first
    # ------------------------------------------------------------------
    hints: List[str] = []

    nearby_humans = [
        a for a in agents
        if (a.uid != agent.uid and a.is_alive
            and not getattr(a, "is_animal", False)
            and _math.sqrt((a.x - agent.x) ** 2 + (a.y - agent.y) ** 2) <= PERCEPTION_RADIUS)
    ]
    recent_social = sum(1 for a in recent10 if a in ("TALK", "TRADE", "GIVE", "SHOUT"))
    if nearby_humans and recent_social == 0:
        names = ", ".join(a.name for a in nearby_humans[:2])
        hints.append(
            f"→ {names} {'is' if len(nearby_humans) == 1 else 'are'} nearby and you haven't spoken "
            f"to anyone recently. TALK, GIVE something, or TRADE."
        )

    food_items = [i for i in agent.inventory if getattr(i, "item_type", None) in ("food", "drink")]
    if food_items and (agent.drives.get("hunger", 0) > 45 or agent.drives.get("thirst", 0) > 45):
        hints.append(
            f"→ You carry {food_items[0].name} and you are hungry or thirsty. "
            f"CONSUME it — no reason to suffer with food in hand."
        )

    if agent.denarii >= 8 and not any(a in recent10 for a in ("BUY", "TRADE", "GIVE")):
        hints.append(
            f"→ You have {agent.denarii} denarii sitting unused. "
            "Visit a market to BUY supplies, or GIVE some to someone in need."
        )

    creative = {"INSPECT", "REFLECT", "PRAY", "INTERACT", "SHOUT", "WORK"}
    if not any(a in creative for a in recent10):
        if any("temple" in loc.lower() for loc in agent.memory.known_locations):
            hints.append(
                "→ You haven't used a temple, inspected anything, worked, or reflected recently. "
                "PRAY at a temple, INSPECT something, WORK at a nearby building, or REFLECT."
            )
        else:
            hints.append(
                "→ You haven't inspected, reflected, shouted, or interacted with the world recently. "
                "INSPECT something nearby, SHOUT to the crowd, or REFLECT on your situation."
            )

    if agent.memory.known_locations and not any(a in recent10 for a in ("GOTO",)):
        loc_name = next(iter(agent.memory.known_locations))
        hints.append(f"→ You know where {loc_name} is. GOTO it and see what awaits you there.")

    for h in hints[:2]:
        lines.append(h)

    # ------------------------------------------------------------------
    # 4. Vita activa — always present, always last
    # ------------------------------------------------------------------
    lines.append(
        "You are a living person in Rome. Every moment matters. "
        "Use the full range of your actions: GOTO to explore, TALK to connect, PRAY to worship, "
        "REFLECT to remember, INSPECT to learn, SHOUT to be heard, GIVE to show generosity, WORK to earn. "
        "IDLE is your last resort — almost never the right choice."
    )

    return CONSCIENCE_TEMPLATE.format(body="\n".join(lines))


def _get_nearby_market_listings(agent: Any, world: Any, economy: Any) -> str:
    """Return goods listings for all trade buildings within perception range."""
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


def _get_position_desc(agent: Any) -> str:
    """Return grid coords plus the nearest known landmark (if within 20 tiles)."""
    import math as _math
    pos = f"({int(agent.x)}, {int(agent.y)})"
    nearest_name, nearest_dist = None, 999.0
    for name, (lx, ly) in agent.memory.known_locations.items():
        d = _math.sqrt((lx - agent.x) ** 2 + (ly - agent.y) ** 2)
        if d < nearest_dist:
            nearest_dist = d
            nearest_name = name
    if nearest_name and nearest_dist < 20:
        return f"{pos} — near {nearest_name} ({int(nearest_dist)} tiles away)"
    return pos


def _get_relationship_desc(agent: Any, name: str) -> str:
    rel = agent.memory.relationships.get(name)
    if not rel:
        return "You don't know this person."
    if rel.trust > 30:
        return f"You consider them a friend (trust: {int(rel.trust)})"
    elif rel.trust < -30:
        return f"You distrust them (trust: {int(rel.trust)})"
    return f"An acquaintance (met {rel.interaction_count} times)"
