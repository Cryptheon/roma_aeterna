"""
Prompt System — Dynamic context assembly for LLM inference.

Prompt zones (in order):
  1. WHO YOU ARE    — Identity, personality, goals, fears, world rules  (static per agent)
  2. YOUR STATE     — Body, drives, position, current action, last thought, inventory
  3. THE WORLD      — Time/weather + perception snapshot + market goods + incoming conversation
  4. RECENT PAST    — Compressed decision history + event outcomes + drive trends
  5. YOUR MIND      — Plan, important memories, recent memories, notes, relationships, beliefs, locations, prefs
  6. YOUR CONSCIENCE — Urgency warnings (⚠) + plan nudges + stagnation hints + vita activa
  7. SITUATION NOW   — Recency anchor: 2-3 line distillation of what matters RIGHT NOW
  →  CHOOSE ACTION   — Contextually filtered actions + examples + JSON schema

Changes from v1:
  - Added persistent PLAN system (populated via REFLECT, shown in YOUR MIND)
  - Added SITUATION NOW recency anchor right before CHOOSE ACTION
  - Added 2-3 contextual action examples before JSON schema
  - Contextually filter available actions (only show what's possible)
  - Compressed decision history (no repeated thoughts)
  - Deduplicated between RECENT PAST and RECENT MEMORIES
  - Auto-generate preferences from negative experiences (hook provided)
  - Added explicit weather/time to THE WORLD zone
  - Reduced conscience verbosity (1 hint max, shorter vita activa)
  - Added conversation patience tracking
"""

from typing import Dict, List, Optional, Any, Set
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
- You can REFLECT to write notes to memory OR set a multi-step plan for yourself.
- IMPORTANT: Respond ONLY with valid JSON. No other text."""

# Zone 2 — who the agent IS right now
NOW_YOU_TEMPLATE = """══ YOUR STATE ══  (Tick {current_tick})
Position:  {position}
Health:    {health}/{max_health}{health_warning}   |   Denarii: {denarii}
Drives:    {drives_summary}{status_effects_block}
Feel:      {self_assessment}{mood_line}

Currently: {current_action}
Last thought: "{last_thought}"

INVENTORY:
{inventory_summary}"""

# Zone 3 — the world right now (weather/time added)
NOW_WORLD_TEMPLATE = """══ THE WORLD ══
{time_weather_line}
{perception_text}"""

MARKET_BLOCK_TEMPLATE = """GOODS FOR SALE NEARBY:
{market_listings}"""

INCOMING_MESSAGE_TEMPLATE = """⚡ SOMEONE IS SPEAKING TO YOU RIGHT NOW:
{speaker}: "{message}"
Your relationship: {relationship}
Recent conversation:
{convo_history}
You may reply with TALK, ignore them, or do anything else."""

# Zone 4 — what has happened (compressed)
PAST_TEMPLATE = """══ RECENT PAST ══
YOUR LAST ACTIONS:
{decision_history}

EVENTS:
{outcomes}

DRIVE TRENDS:
{past_states}"""

# Zone 5 — everything the agent knows (PLAN added at top)
MIND_TEMPLATE = """══ YOUR MIND ══
{plan_block}
IMPORTANT MEMORIES:
{important_memories}

RECENT MEMORIES:
{recent_memories}

PERSONAL NOTES:
{reflections}

PEOPLE YOU KNOW:
{relationships}

BELIEFS:
{beliefs}

KNOWN LOCATIONS:
{known_locations}

PREFERENCES:
{preferences}"""

PLAN_BLOCK_TEMPLATE = """YOUR CURRENT PLAN:
{plan_steps}
"""

NO_PLAN_BLOCK = """YOUR CURRENT PLAN:
No plan set. Use REFLECT with "plan" to set your priorities.
"""

# Zone 6 — conscience
CONSCIENCE_TEMPLATE = """══ YOUR CONSCIENCE ══
{body}"""

# Zone 7 — recency anchor (NEW)
SITUATION_NOW_TEMPLATE = """══ SITUATION NOW ══
{summary_lines}"""

# Zone 8 — action selection (contextually filtered + examples)
ACTION_HEADER = """══ CHOOSE YOUR ACTION ══
Consider your state, the world, your past, your plan, and your conscience."""

# Individual action descriptions — keyed for contextual filtering
ACTION_DESCRIPTIONS = {
    "MOVE":     "MOVE: Move one tile. `direction`: north/south/east/west/northeast/northwest/southeast/southwest.",
    "GOTO":     "GOTO: Autopilot to a known location. `target` MUST be an exact name from KNOWN LOCATIONS.",
    "BUY":      "BUY: Purchase from a nearby market. `target` is the item name. `market` is the market name.",
    "WORK":     "WORK: Perform role duties at a nearby building to earn denarii.",
    "CRAFT":    "CRAFT: Create an item from inventory materials. `target` is the item to make.",
    "TALK":     "TALK: Speak to someone nearby. `target` MUST match a name from PEOPLE NEARBY. Specify `speech`.",
    "INTERACT": "INTERACT: Use a nearby building or object. `target` MUST be in STRUCTURES NEARBY.",
    "CONSUME":  "CONSUME: Eat or drink from inventory. `target` MUST be an exact item name from INVENTORY.",
    "PICK_UP":  "PICK_UP: Pick up an item from the ground. `target` MUST be an exact item name.",
    "DROP":     "DROP: Drop an item from inventory. `target` MUST be an exact item name from INVENTORY.",
    "REST":     "REST: Catch your breath (light energy recovery).",
    "SLEEP":    "SLEEP: Sleep deeply to restore energy fully.",
    "TRADE":    "TRADE: Barter with someone nearby. `target` is their name. `offer` is your item. `want` is their item.",
    "ATTACK":   "ATTACK: Strike a nearby person or animal. `target` is their name. `item` is a weapon from INVENTORY (unarmed if omitted).",
    "GIVE":     "GIVE: Give an item to someone nearby. `target` is their name. `item` is from INVENTORY.",
    "SHOUT":    "SHOUT: Call out loudly so everyone nearby hears. Specify `speech`.",
    "INSPECT":  "INSPECT: Examine something closely to learn more. Specify `target`.",
    "REFLECT":  "REFLECT: Write a note OR set your plan. Use `note` for observations. Use `plan` (list of strings) to set your prioritized goals.",
    "PRAY":     "PRAY: Pray at a nearby temple. `target` MUST be a temple from STRUCTURES NEARBY. `speech` is your prayer.",
    "IDLE":     "IDLE: Do nothing. Almost never the right choice.",
}

# Actions always available regardless of context
ALWAYS_AVAILABLE = {"MOVE", "REST", "SLEEP", "REFLECT", "SHOUT", "IDLE"}

ACTION_EXAMPLES_TEMPLATE = """
EXAMPLES (for format only — choose your OWN action):
{examples}"""

ACTION_JSON_TEMPLATE = """
Respond with raw JSON only. No markdown. Only include keys your action needs. When you TALK/SHOUT/PRAY or think (thought) be brief! Don't talk a lot.

{{
    "thought": "your inner monologue (1-2 sentences)",
    "action": "ACTION_NAME",
    "direction": "direction (MOVE only)",
    "target": "exact name of person/object/item/location",
    "market": "market name (BUY only)",
    "speech": "what you say (TALK/SHOUT/PRAY)",
    "offer": "item you offer (TRADE only)",
    "want": "item you want (TRADE only)",
    "item": "weapon (ATTACK) or item (GIVE)",
    "note": "observation text (REFLECT without plan)",
    "plan": ["step 1", "step 2", "..."]
}}/no_think"""

# ============================================================
# Example bank — picked contextually per agent situation
# ============================================================

EXAMPLE_BANK = {
    "REFLECT_plan": '{"thought": "I have been reacting all day. Time to set priorities.", "action": "REFLECT", "plan": ["Sell Salt at Market for profit", "Find Spartacus to hire as porter", "Visit Temple of Jupiter to pray"]}',
    "REFLECT_note": '{"thought": "That bread nearly killed me. I must remember.", "action": "REFLECT", "note": "Bread from Market was rotten — never buy bread there again."}',
    "ATTACK": '{"thought": "This wolf is circling me. I draw my gladius.", "action": "ATTACK", "target": "Wolf", "item": "Gladius"}',
    "CRAFT": '{"thought": "I have wood and rope. A torch would help tonight.", "action": "CRAFT", "target": "Torch"}',
    "PRAY": '{"thought": "Jupiter watches over Rome. I should ask for guidance.", "action": "PRAY", "target": "TempleOfVesta", "speech": "Great Jupiter, grant me strength and wisdom."}',
    "TRADE": '{"thought": "He needs water and I need coin. A fair exchange.", "action": "TRADE", "target": "Spartacus", "offer": "Water", "want": "Bread"}',
    "GIVE": '{"thought": "This man is parched. Generosity builds allies.", "action": "GIVE", "target": "Spartacus", "item": "Water"}',
    "INSPECT": '{"thought": "That column looks ancient. I may learn something.", "action": "INSPECT", "target": "Column"}',
    "WORK": '{"thought": "My purse is light. Time to earn.", "action": "WORK"}',
    "BUY": '{"thought": "Water is cheap here and I am parched.", "action": "BUY", "target": "Water", "market": "Taberna"}',
    "GOTO": '{"thought": "The Market is far but I know the way.", "action": "GOTO", "target": "MarketsOfTrajan"}',
}


# ============================================================
# Main builder
# ============================================================

def build_prompt(agent: Any, world: Any, agents: List[Any], weather: Any,
                 economy: Any = None) -> str:
    """Assemble the full prompt for one LLM inference.

    Section order:
      SYSTEM → YOUR STATE → THE WORLD → [MARKET] → [CONVERSATION]
             → RECENT PAST → YOUR MIND (with PLAN) → YOUR CONSCIENCE
             → SITUATION NOW → CHOOSE ACTION (filtered + examples)
    """
    persona = agent.personality_seed

    # ------------------------------------------------------------------
    # Zone 1: WHO YOU ARE
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
    # Zone 2: YOUR STATE
    # ------------------------------------------------------------------
    health_warning = ""
    if agent.health < 20:
        health_warning = " ⚠ DYING"
    elif agent.health < 50:
        health_warning = " ⚠ WOUNDED"

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
    # Zone 3: THE WORLD — time/weather + perception + market + conversation
    # ------------------------------------------------------------------
    time_weather_line = _get_time_weather_line(weather, world)

    llm_decision_count = sum(1 for d in agent.decision_history if d.get("source") == "llm")
    include_environment = (llm_decision_count % PROMPT_ENV_INTERVAL == 0)
    perception_text = agent.perceive(world, agents, include_environment=include_environment)

    now_world = NOW_WORLD_TEMPLATE.format(
        time_weather_line=time_weather_line,
        perception_text=perception_text,
    )

    world_extras: List[str] = []
    if economy is not None:
        market_listings = _get_nearby_market_listings(agent, world, economy)
        if market_listings:
            world_extras.append(MARKET_BLOCK_TEMPLATE.format(market_listings=market_listings))

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
    # Zone 4: RECENT PAST — compressed
    # ------------------------------------------------------------------
    decision_history_text = _get_compressed_decision_history(agent, n=PROMPT_DECISION_HISTORY_N)
    outcomes_text = agent.memory.get_recent_outcomes(n=PROMPT_OUTCOMES_N)
    past_states_text = agent.get_past_states_summary(n=PROMPT_STATE_TRENDS_N)

    past = PAST_TEMPLATE.format(
        decision_history=decision_history_text,
        outcomes=outcomes_text,
        past_states=past_states_text,
    )

    # ------------------------------------------------------------------
    # Zone 5: YOUR MIND — plan + memories + knowledge
    # ------------------------------------------------------------------
    plan_block = _build_plan_block(agent)
    reflections = agent.memory.get_reflections()
    prefs = agent.memory.get_preferences_summary()

    # Auto-inject preferences from negative experiences
    if not prefs or prefs == "No strong preferences yet.":
        auto_prefs = _auto_generate_preferences(agent)
        if auto_prefs:
            prefs = auto_prefs

    mind = MIND_TEMPLATE.format(
        plan_block=plan_block,
        important_memories=agent.memory.get_important_memories(n=PROMPT_IMPORTANT_MEMORIES_N),
        recent_memories=agent.memory.get_recent_context(n=PROMPT_RECENT_MEMORIES_N),
        reflections=reflections if reflections else "None yet.",
        relationships=agent.memory.get_relationship_summary(),
        beliefs=agent.memory.get_beliefs_summary(),
        known_locations=agent.memory.get_known_locations_summary(),
        preferences=prefs if prefs else "No strong preferences yet.",
    )

    # ------------------------------------------------------------------
    # Zone 6: YOUR CONSCIENCE
    # ------------------------------------------------------------------
    conscience_text = _build_conscience(agent, agents, world)

    # ------------------------------------------------------------------
    # Zone 7: SITUATION NOW — recency anchor
    # ------------------------------------------------------------------
    situation_now = _build_situation_now(agent, agents, world, weather, pending)

    # ------------------------------------------------------------------
    # Zone 8: CHOOSE ACTION — filtered + examples
    # ------------------------------------------------------------------
    action_block = _build_action_block(agent, agents, world, economy, pending)

    # ------------------------------------------------------------------
    # Assemble
    # ------------------------------------------------------------------
    sections = [system, now_you, now_world]
    sections.extend(world_extras)
    sections += [past, mind, conscience_text, situation_now, action_block]
    return "\n\n".join(sections)


# ============================================================
# Plan system
# ============================================================

def _build_plan_block(agent: Any) -> str:
    """Build the PLAN section from agent's stored plan.

    Expects agent.memory.plan as a list of dicts:
        [{"step": "text", "status": "pending|done|active"}, ...]
    """
    plan = getattr(agent.memory, "plan", None)
    if not plan:
        return NO_PLAN_BLOCK

    lines = []
    for i, step in enumerate(plan, 1):
        status = step.get("status", "pending")
        text = step.get("step", "")
        if status == "done":
            marker = "[DONE]"
        elif status == "active":
            marker = "[NOW]"
        else:
            marker = f"[{i}]"
        lines.append(f"  {marker} {text}")

    return PLAN_BLOCK_TEMPLATE.format(plan_steps="\n".join(lines)) if lines else NO_PLAN_BLOCK


def parse_plan_from_response(response: Dict) -> Optional[List[Dict]]:
    """Parse a plan from an LLM REFLECT response with a plan key.

    Call from your action handler when processing REFLECT:
        if response["action"] == "REFLECT" and "plan" in response:
            new_plan = parse_plan_from_response(response)
            if new_plan:
                agent.memory.plan = new_plan
    """
    plan_data = response.get("plan")
    if not plan_data or not isinstance(plan_data, list):
        return None

    steps = []
    for i, item in enumerate(plan_data):
        text = str(item).strip()
        if text:
            steps.append({
                "step": text,
                "status": "active" if i == 0 else "pending",
            })
    return steps if steps else None


def advance_plan_step(agent: Any):
    """Mark current active step as done, promote next to active.

    Call when the agent completes a plan step (your action resolution
    logic should detect this).
    """
    plan = getattr(agent.memory, "plan", None)
    if not plan:
        return

    promoted = False
    for step in plan:
        if step["status"] == "active":
            step["status"] = "done"
            promoted = True
            continue
        if promoted and step["status"] == "pending":
            step["status"] = "active"
            break


# ============================================================
# Situation Now (recency anchor)
# ============================================================

def _build_situation_now(agent: Any, agents: List[Any], world: Any,
                         weather: Any, pending: Optional[Dict]) -> str:
    """Build a 2-4 line summary of the most critical facts RIGHT NOW.

    Sits directly before CHOOSE ACTION to re-anchor the model's
    attention after scrolling through memory/beliefs/locations.
    """
    import math as _math
    from roma_aeterna.config import PERCEPTION_RADIUS

    lines = []

    # Line 1: Critical status flags + location
    status_parts = [e.name.upper() for e in agent.status_effects.active]
    drive_warnings = []
    if agent.drives["thirst"] > 60:
        drive_warnings.append("THIRSTY")
    if agent.drives["hunger"] > 60:
        drive_warnings.append("HUNGRY")
    if agent.drives["energy"] > 65:
        drive_warnings.append("EXHAUSTED")
    if agent.health < 50:
        drive_warnings.append("WOUNDED")

    all_flags = status_parts + drive_warnings
    if all_flags:
        lines.append(f"Status: {', '.join(all_flags)}.")
    else:
        lines.append("You are healthy and well.")

    # Line 2: Pending conversation or nearby people
    if pending:
        lines.append(f"{pending['speaker']} is speaking to you RIGHT NOW.")
    else:
        nearby_humans = [
            a for a in agents
            if (a.uid != agent.uid and a.is_alive
                and not getattr(a, "is_animal", False)
                and _math.sqrt((a.x - agent.x) ** 2 + (a.y - agent.y) ** 2) <= PERCEPTION_RADIUS)
        ]
        if nearby_humans:
            names = [a.name for a in nearby_humans[:3]]
            lines.append(f"Nearby: {', '.join(names)}.")

    # Line 3: Current plan step
    plan = getattr(agent.memory, "plan", None)
    if plan:
        active = next((s for s in plan if s["status"] == "active"), None)
        if active:
            lines.append(f"Your plan: {active['step']}")
    else:
        lines.append("You have no plan. What do you want to accomplish?")

    # Line 4: Most urgent physical need
    urgency = _get_top_urgency(agent)
    if urgency:
        lines.append(f"Most urgent: {urgency}")

    return SITUATION_NOW_TEMPLATE.format(summary_lines="\n".join(lines))


def _get_top_urgency(agent: Any) -> str:
    """Single sentence describing the most pressing physical need."""
    if agent.health < 20:
        return "You are DYING. Act to survive."
    if agent.status_effects.has_effect("Burned"):
        return "You are BURNING. Flee from fire."
    if agent.status_effects.has_effect("Smoke Inhalation"):
        return "You are CHOKING on smoke. Move to clear air."
    if agent.drives["thirst"] > 80:
        return "Find water NOW or die of thirst."
    if agent.drives["hunger"] > 80:
        return "Find food NOW or starve."
    if agent.status_effects.has_effect("Heatstroke"):
        return "Get to shade and water for heatstroke."
    if agent.status_effects.has_effect("Food Poisoning"):
        return "Rest and drink clean water for food poisoning."
    if agent.drives["energy"] > 80:
        return "You will collapse from exhaustion. Rest or sleep."
    if agent.drives["thirst"] > 60:
        return "Find water soon."
    if agent.drives["hunger"] > 60:
        return "Find food soon."
    return ""


# ============================================================
# Contextually filtered action block + examples
# ============================================================

def _build_action_block(agent: Any, agents: List[Any], world: Any,
                        economy: Any, pending: Optional[Dict]) -> str:
    """Build CHOOSE ACTION with only relevant actions and contextual examples."""
    import math as _math
    from roma_aeterna.config import PERCEPTION_RADIUS

    available: Set[str] = set(ALWAYS_AVAILABLE)

    # --- Detect context ---
    has_inventory = bool(agent.inventory)
    has_consumables = any(
        getattr(i, "item_type", None) in ("food", "drink")
        for i in agent.inventory
    )
    has_known_locations = bool(agent.memory.known_locations)

    nearby_humans = []
    nearby_animals = []
    nearby_temples = []
    nearby_markets = []
    has_structures = False

    for a in agents:
        if a.uid == agent.uid or not a.is_alive:
            continue
        dist = _math.sqrt((a.x - agent.x) ** 2 + (a.y - agent.y) ** 2)
        if dist > PERCEPTION_RADIUS:
            continue
        if getattr(a, "is_animal", False):
            nearby_animals.append(a)
        else:
            nearby_humans.append(a)

    # Scan structures
    try:
        from roma_aeterna.world.components import Interactable
        for obj in world.objects:
            dist = _math.sqrt((obj.x - agent.x) ** 2 + (obj.y - agent.y) ** 2)
            if dist > PERCEPTION_RADIUS:
                continue
            has_structures = True
            interact = obj.get_component(Interactable)
            if interact:
                if interact.interaction_type == "trade":
                    nearby_markets.append(obj)
                elif interact.interaction_type == "pray":
                    nearby_temples.append(obj)
    except ImportError:
        has_structures = True  # safe fallback

    # Ground items
    nearby_ground_items = getattr(agent, "_visible_ground_items", [])

    # --- Build available set ---
    if has_known_locations:
        available.add("GOTO")
    if has_structures:
        available.add("INTERACT")
        available.add("WORK")
        available.add("INSPECT")
    if nearby_markets and economy:
        available.add("BUY")
    if nearby_humans or nearby_animals:
        available.add("ATTACK")
    if nearby_humans:
        available.add("TALK")
        available.add("TRADE")
    if has_inventory:
        available.add("DROP")
        available.add("CRAFT")
    if has_inventory and nearby_humans:
        available.add("GIVE")
    if has_consumables:
        available.add("CONSUME")
    if nearby_ground_items:
        available.add("PICK_UP")
    if nearby_temples:
        available.add("PRAY")
    if pending:
        available.add("TALK")

    # --- Action descriptions ---
    action_lines = []
    for action_name in ACTION_DESCRIPTIONS:
        if action_name in available:
            action_lines.append(f"- {ACTION_DESCRIPTIONS[action_name]}")

    # --- Contextual examples (2-3) ---
    examples = _pick_contextual_examples(
        agent, nearby_humans, nearby_temples, nearby_markets,
        has_inventory, nearby_animals
    )
    examples_text = ACTION_EXAMPLES_TEMPLATE.format(
        examples="\n".join(f"  {e}" for e in examples)
    )

    # --- Assemble ---
    parts = [
        ACTION_HEADER,
        "Available actions:",
        "\n".join(action_lines),
        examples_text,
        ACTION_JSON_TEMPLATE,
    ]
    return "\n".join(parts)


def _pick_contextual_examples(agent: Any, nearby_humans: List,
                              nearby_temples: List, nearby_markets: List,
                              has_inventory: bool, nearby_animals: List) -> List[str]:
    """Pick 2-3 relevant examples from the bank."""
    picked = []

    # 1. Always show a REFLECT example
    plan = getattr(agent.memory, "plan", None)
    if not plan:
        picked.append(EXAMPLE_BANK["REFLECT_plan"])
    else:
        picked.append(EXAMPLE_BANK["REFLECT_note"])

    # 2. Context-driven pick
    if nearby_animals:
        picked.append(EXAMPLE_BANK["ATTACK"])
    elif nearby_humans and has_inventory:
        picked.append(random.choice([
            EXAMPLE_BANK["TRADE"],
            EXAMPLE_BANK["GIVE"],
        ]))
    elif nearby_temples:
        picked.append(EXAMPLE_BANK["PRAY"])
    elif nearby_markets:
        picked.append(EXAMPLE_BANK["BUY"])
    else:
        picked.append(EXAMPLE_BANK["GOTO"])

    # 3. Something the agent hasn't done recently
    recent_actions = set()
    for d in agent.decision_history[-10:]:
        recent_actions.add(d.get("action", "").upper())

    for action in ["INSPECT", "CRAFT", "WORK", "PRAY"]:
        if action not in recent_actions and action in EXAMPLE_BANK:
            picked.append(EXAMPLE_BANK[action])
            break

    return picked[:3]


# ============================================================
# Compressed decision history
# ============================================================

def _get_compressed_decision_history(agent: Any, n: int = 8) -> str:
    """Compressed version of recent decisions — no thought repetition.

    Shows: [Tick X] ACTION → target (×count)
    """
    history = agent.decision_history[-n:] if agent.decision_history else []
    if not history:
        return "No actions yet."

    lines = []
    i = 0
    while i < len(history):
        entry = history[i]
        action = entry.get("action", "IDLE").upper()
        target = entry.get("target", "")
        tick = entry.get("tick", "?")

        # Count consecutive identical actions
        count = 1
        while (i + count < len(history)
               and history[i + count].get("action", "").upper() == action
               and history[i + count].get("target", "") == target):
            count += 1

        target_str = f" → {target}" if target else ""
        count_str = f" (×{count})" if count > 1 else ""
        lines.append(f"  [Tick {tick}] {action}{target_str}{count_str}")
        i += count

    return "\n".join(lines)


# ============================================================
# Auto-generate preferences from negative experiences
# ============================================================

def _auto_generate_preferences(agent: Any) -> str:
    """Scan recent outcomes for negative experiences, generate preference text.

    Prompt-time fallback. Ideally preferences should be created in the
    memory system when negative events occur.
    """
    prefs = []

    outcomes = ""
    if hasattr(agent.memory, "get_recent_outcomes"):
        outcomes = agent.memory.get_recent_outcomes(n=20)

    if "rotten" in outcomes.lower() or "sick" in outcomes.lower() or "poisoning" in outcomes.lower():
        prefs.append("- Wary of stale or old food after getting sick.")

    if "burn" in outcomes.lower() or "fire" in outcomes.lower() or "flame" in outcomes.lower():
        prefs.append("- Avoids fire and flames at all costs.")

    if "attack" in outcomes.lower() or "stole" in outcomes.lower():
        prefs.append("- Distrusts strangers after a bad encounter.")

    return "\n".join(prefs) if prefs else ""


# ============================================================
# Time/weather line
# ============================================================

def _get_time_weather_line(weather: Any, world: Any) -> str:
    """Human-readable time + weather status for THE WORLD zone.

    Adapts to whatever attributes the weather/world objects expose.
    """
    parts = []

    # Time of day (may be an enum like TimeOfDay.MIDDAY, a string, etc.)
    time_of_day = getattr(weather, "time_of_day", None) or getattr(world, "time_of_day", None)
    if time_of_day is not None:
        # Handle enums: try .name first, then .value, then str()
        if hasattr(time_of_day, "name"):
            tod_str = time_of_day.name.replace("_", " ").capitalize()
        elif hasattr(time_of_day, "value"):
            tod_str = str(time_of_day.value).capitalize()
        else:
            tod_str = str(time_of_day).capitalize()
        parts.append(tod_str)

    # Temperature
    temp = getattr(weather, "temperature", None)
    if temp is not None:
        if temp > 38:
            parts.append("SCORCHING heat")
        elif temp > 32:
            parts.append("Very hot")
        elif temp > 25:
            parts.append("Warm")
        elif temp > 15:
            parts.append("Mild")
        elif temp > 5:
            parts.append("Cold")
        else:
            parts.append("Freezing")

    # Weather condition
    condition = getattr(weather, "condition", None) or getattr(weather, "state", None)
    if condition:
        c = str(condition).lower()
        if "storm" in c:
            parts.append("A storm rages")
        elif "rain" in c:
            parts.append("Rain falls")
        elif "heatwave" in c or "heat" in c:
            parts.append("Brutal heatwave")
        elif "sunny" in c or "clear" in c:
            parts.append("Clear skies")
        elif "cloud" in c:
            parts.append("Overcast")
        else:
            parts.append(str(condition).capitalize())

    # Wind
    wind = getattr(weather, "wind_speed", None)
    if wind and wind > 5:
        parts.append(f"{'Strong' if wind > 15 else 'Moderate'} wind")

    return " | ".join(parts) + "." if parts else "The day passes in Rome."


# ============================================================
# Helpers
# ============================================================

def _get_current_action_desc(agent: Any) -> str:
    """Human-readable description of the agent's current action."""
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
    """Return ⚠ warning lines for life-threatening situations."""
    hints: List[str] = []
    if agent.health < 20:
        hints.append("⚠ CRITICALLY INJURED. Survival depends on your next action.")
    if agent.status_effects.has_effect("Burned"):
        hints.append("⚠ BURNED. Get away from fire NOW.")
    if agent.status_effects.has_effect("Smoke Inhalation"):
        hints.append("⚠ CHOKING on smoke. Move to clear air.")
    if agent.drives["thirst"] > 80:
        hints.append("⚠ DYING OF THIRST. Find water now.")
    if agent.drives["hunger"] > 80:
        hints.append("⚠ STARVING. Find food urgently.")
    if agent.status_effects.has_effect("Food Poisoning"):
        hints.append("⚠ FOOD POISONING. Rest and find clean water.")
    if agent.status_effects.has_effect("Heatstroke"):
        hints.append("⚠ HEATSTROKE. Find shade and water.")

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

    return "\n".join(hints) if hints else ""


def _build_conscience(agent: Any, agents: List[Any], world: Any) -> str:
    """Zone 6: urgency + plan nudges + stagnation + one opportunity hint."""
    import math as _math
    from roma_aeterna.config import PERCEPTION_RADIUS

    lines: List[str] = []

    # 1. Urgency warnings
    urgency = _build_urgency_hint(agent, agents)
    if urgency:
        lines.append(urgency)

    # 2. Plan adherence
    plan = getattr(agent.memory, "plan", None)
    if plan:
        active = next((s for s in plan if s["status"] == "active"), None)
        if active:
            recent_actions = [d.get("action", "").upper() for d in agent.decision_history[-5:]]
            passive = sum(1 for a in recent_actions if a in ("IDLE", "REST"))
            if passive >= 2:
                lines.append(
                    f"Your plan says: \"{active['step']}\" — but you've been passive. "
                    "Act on your plan or REFLECT to change it."
                )
    else:
        if agent.sim_tick > 100 and random.random() < 0.3:
            lines.append("You have no plan. REFLECT to set priorities.")

    # 3. Stagnation detection
    history = agent.decision_history[-10:] if agent.decision_history else []
    recent5 = [d.get("action", "IDLE").upper() for d in history[-5:]]

    idle_count = sum(1 for a in recent5 if a == "IDLE")
    rest_count = sum(1 for a in recent5 if a in ("REST", "SLEEP"))
    goto_count = sum(1 for a in recent5 if a == "GOTO")
    all_same = (len(set(recent5)) == 1 and len(recent5) == 5
                and recent5[0] not in ("MOVE", "MOVING"))

    if idle_count >= 3:
        lines.append(f"IDLE {idle_count}/5 recent actions. Choose something meaningful.")
    elif goto_count >= 3:
        lines.append("GOTO repeated without arriving. Path may be blocked — try MOVE or a new goal.")
    elif rest_count >= 3:
        lines.append("You've rested enough. Rise and act.")
    elif all_same:
        lines.append(f"Stuck on {recent5[0]}. Try a different action.")

    # 4. Conversation patience
    if agent._pending_conversation:
        speaker = agent._pending_conversation["speaker"]
        convo_len = 0
        if hasattr(agent.memory, "get_conversation_length"):
            convo_len = agent.memory.get_conversation_length(speaker)
        if convo_len > 5:
            lines.append(
                f"Conversation with {speaker} has gone {convo_len} rounds. "
                "Consider ending it and moving on."
            )

    # 5. One opportunity hint (max 1, most relevant)
    recent10 = [d.get("action", "IDLE").upper() for d in history]
    food_items = [i for i in agent.inventory if getattr(i, "item_type", None) in ("food", "drink")]
    if food_items and (agent.drives.get("hunger", 0) > 45 or agent.drives.get("thirst", 0) > 45):
        lines.append(f"→ You carry {food_items[0].name} and are hungry/thirsty. CONSUME it.")
    else:
        nearby_humans = [
            a for a in agents
            if (a.uid != agent.uid and a.is_alive
                and not getattr(a, "is_animal", False)
                and _math.sqrt((a.x - agent.x) ** 2 + (a.y - agent.y) ** 2) <= PERCEPTION_RADIUS)
        ]
        recent_social = sum(1 for a in recent10 if a in ("TALK", "TRADE", "GIVE", "SHOUT"))
        if nearby_humans and recent_social == 0:
            name = nearby_humans[0].name
            lines.append(f"→ {name} is nearby. Consider TALK, TRADE, or GIVE.")

    # 6. Vita activa (short)
    lines.append("Act with purpose. IDLE is almost never right.")

    return CONSCIENCE_TEMPLATE.format(body="\n".join(lines))


def _get_nearby_market_listings(agent: Any, world: Any, economy: Any) -> str:
    """Goods listings for trade buildings within perception range."""
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
    """Grid coords + nearest known landmark."""
    import math as _math
    pos = f"({int(agent.x)}, {int(agent.y)})"
    nearest_name, nearest_dist = None, 999.0
    for name, (lx, ly) in agent.memory.known_locations.items():
        d = _math.sqrt((lx - agent.x) ** 2 + (ly - agent.y) ** 2)
        if d < nearest_dist:
            nearest_dist = d
            nearest_name = name
    if nearest_name and nearest_dist < 20:
        return f"{pos} — near {nearest_name} ({int(nearest_dist)} tiles)"
    return pos


def _get_relationship_desc(agent: Any, name: str) -> str:
    rel = agent.memory.relationships.get(name)
    if not rel:
        return "Stranger."
    if rel.trust > 30:
        return f"Friend (trust: {int(rel.trust)})"
    elif rel.trust < -30:
        return f"Distrusted (trust: {int(rel.trust)})"
    return f"Acquaintance (met {rel.interaction_count} times)"