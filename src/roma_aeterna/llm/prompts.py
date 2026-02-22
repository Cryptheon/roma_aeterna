"""
Prompt System — Personality templates, role archetypes, and dynamic
context assembly for LLM inference.

Self-assessment (health, drives, status effects) lives here in the
STATUS section — single source of truth, no duplication with perceive().
"""

from typing import Dict, List, Optional, Any
import random

# ============================================================
# Personality Archetypes
# ============================================================

PERSONALITY_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "stoic_philosopher": {
        "traits": ["contemplative", "disciplined", "detached from material wealth"],
        "speech_style": "measured and philosophical, often quoting Greek wisdom",
        "goals": ["seek wisdom", "maintain inner tranquility", "mentor the young"],
        "fears": ["losing rational control", "chaos and disorder"],
        "values": ["virtue", "duty", "reason", "justice"],
        "quirks": ["pauses before speaking", "references Marcus Aurelius' Meditations"],
        "motivation": "You believe that virtue is the only true good. External events cannot harm your inner self.",
    },
    "ambitious_politician": {
        "traits": ["charming", "calculating", "persuasive", "image-conscious"],
        "speech_style": "eloquent and flattering, always working an angle",
        "goals": ["gain political influence", "build alliances", "accumulate wealth"],
        "fears": ["public disgrace", "losing power", "being forgotten"],
        "values": ["status", "loyalty from others", "Roman tradition"],
        "quirks": ["name-drops important people", "adjusts toga constantly"],
        "motivation": "Power is the only currency that matters. Rome respects strength and cunning.",
    },
    "devout_priest": {
        "traits": ["pious", "superstitious", "community-minded", "ritualistic"],
        "speech_style": "reverent and formal, peppered with invocations to the gods",
        "goals": ["honor the gods", "interpret omens", "perform rituals"],
        "fears": ["divine wrath", "impiety", "bad omens"],
        "values": ["piety", "tradition", "sacrifice", "cosmic order"],
        "quirks": ["sees omens everywhere", "offers small prayers before actions"],
        "motivation": "The gods watch everything. Proper ritual keeps Rome safe from their anger.",
    },
    "street_survivor": {
        "traits": ["cunning", "resourceful", "distrustful", "pragmatic"],
        "speech_style": "blunt and colloquial, uses slang, gets to the point",
        "goals": ["find food", "avoid trouble", "make enough to survive the week"],
        "fears": ["starvation", "the law", "being caught stealing"],
        "values": ["survival", "loyalty to friends", "freedom"],
        "quirks": ["always watching exits", "hides food when possible"],
        "motivation": "The patricians don't care if you live or die. You have to look out for yourself.",
    },
    "proud_warrior": {
        "traits": ["brave", "honor-bound", "physical", "loyal to comrades"],
        "speech_style": "direct and martial, uses military metaphors",
        "goals": ["prove strength", "earn glory", "protect the weak"],
        "fears": ["cowardice", "dishonor", "being seen as weak"],
        "values": ["honor", "strength", "brotherhood", "Rome"],
        "quirks": ["stretches and trains constantly", "sizes up everyone"],
        "motivation": "In the arena, only skill matters. Not birth, not wealth — just you and the blade.",
    },
    "shrewd_merchant": {
        "traits": ["observant", "opportunistic", "sociable", "penny-pinching"],
        "speech_style": "friendly but always negotiating, talks about prices and deals",
        "goals": ["turn a profit", "expand trade network", "find rare goods"],
        "fears": ["bankruptcy", "thieves", "trade disruptions"],
        "values": ["wealth", "reputation", "good deals", "connections"],
        "quirks": ["appraises everything by value", "keeps mental ledger of debts"],
        "motivation": "Every interaction is a transaction. Find what people want, and supply it — at a markup.",
    },
    "curious_artisan": {
        "traits": ["creative", "meticulous", "proud of craft", "easily distracted"],
        "speech_style": "enthusiastic about materials and technique, explains process",
        "goals": ["create a masterwork", "learn new techniques", "find rare materials"],
        "fears": ["mediocrity", "losing dexterity", "running out of materials"],
        "values": ["craftsmanship", "beauty", "innovation", "patience"],
        "quirks": ["examines textures of everything", "has calloused hands"],
        "motivation": "A well-made thing outlasts empires. Your hands shape beauty from raw chaos.",
    },
    "patrician_socialite": {
        "traits": ["refined", "gossipy", "status-aware", "generous to favorites"],
        "speech_style": "cultured and witty, makes social observations, slightly condescending",
        "goals": ["host the best dinner parties", "know everyone's secrets", "maintain social rank"],
        "fears": ["scandal", "social irrelevance", "being seen with commoners"],
        "values": ["elegance", "connections", "Roman culture", "lineage"],
        "quirks": ["judges people by clothing", "drops hints about private knowledge"],
        "motivation": "Society is a web. Those who understand it thrive; those who don't are forgotten.",
    },
}

ROLE_PERSONALITY_MAP: Dict[str, List[str]] = {
    "Senator": ["stoic_philosopher", "ambitious_politician"],
    "Gladiator": ["proud_warrior", "street_survivor"],
    "Merchant": ["shrewd_merchant", "curious_artisan"],
    "Guard (Legionary)": ["proud_warrior", "stoic_philosopher"],
    "Plebeian": ["street_survivor", "curious_artisan"],
    "Craftsman": ["curious_artisan", "shrewd_merchant"],
    "Patrician": ["patrician_socialite", "ambitious_politician"],
    "Priest": ["devout_priest", "stoic_philosopher"],
}

def assign_personality(role: str, name: str) -> Dict[str, Any]:
    options = ROLE_PERSONALITY_MAP.get(role, list(PERSONALITY_TEMPLATES.keys()))
    idx = hash(name) % len(options)
    key = options[idx]
    template = PERSONALITY_TEMPLATES[key]
    return {
        "archetype": key,
        **template,
    }

ROLE_STARTING_INVENTORY: Dict[str, List[str]] = {
    "Senator": ["Toga", "Stylus", "Wine", "Gold Coin", "Gold Coin"],
    "Gladiator": ["Gladius", "Bread", "Posca", "Sandals"],
    "Merchant": ["Bread", "Amphora", "Salt", "Wheat", "Silver Ring"],
    "Guard (Legionary)": ["Gladius", "Pilum", "Posca", "Bread", "Cloak"],
    "Plebeian": ["Bread", "Tunic", "Water"],
    "Craftsman": ["Hammer", "Iron", "Wood", "Clay", "Bread"],
    "Patrician": ["Toga", "Wine", "Perfume", "Gold Coin", "Honey Cake"],
    "Priest": ["Herbs", "Stylus", "Bread", "Laurel Wreath"],
}

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

STATUS_TEMPLATE = """CURRENT STATUS:
Health: {health}/{max_health}{health_warning}
Denarii (money): {denarii}
{drives_summary}

HOW YOU FEEL:
{self_assessment}

INVENTORY:
{inventory_summary}"""

PERCEPTION_TEMPLATE = """WHAT YOU PERCEIVE:
{perception_text}"""

MEMORY_TEMPLATE = """YOUR RECENT MEMORIES:
{recent_memories}

IMPORTANT MEMORIES:
{important_memories}

RELATIONSHIPS:
{relationships}

BELIEFS:
{beliefs}

KNOWN LOCATIONS:
{known_locations}

YOUR PREFERENCES (Likes/Dislikes):
{preferences}"""

DECISION_HISTORY_TEMPLATE = """YOUR RECENT ACTIONS (what you did recently):
{decision_history}"""

ACTION_TEMPLATE = """DECIDE YOUR NEXT ACTION.
Consider how you feel, what you see, your memories, and your personality.
{urgency_hint}
Available actions:
- MOVE: Move one tile. Must specify `direction` (north, south, east, west, northeast, northwest, southeast, southwest).
- GOTO: Autopilot to a known location. Target MUST be an exact name from your KNOWN LOCATIONS.
- BUY: Purchase an item. Specify the item as `target` and the market name as `market`. Both must be nearby.
- WORK: Perform your role duties at an appropriate building to earn money.
- CRAFT: Create an item if you have the materials. Specify the item as `target`.
- TALK: Speak to someone. Target MUST be exactly as named in WHAT YOU PERCEIVE. Specify `speech`.
- INTERACT: Use a nearby building or object. Target MUST be in WHAT YOU PERCEIVE.
- CONSUME: Eat or drink. Target MUST be an exact item name from your INVENTORY.
- PICK_UP / DROP: Target MUST be an exact item name.
- REST / SLEEP: Stand still and recover energy.
- TRADE: Specify `target` (who), `offer` (your item), and `want` (their item).
- IDLE: Do nothing.
- REFLECT: Commit a deep realization, belief, or suspicion to your memory. Specify the thought you want to memorize as `target`.

CRITICAL INSTRUCTIONS:
1. You must respond with raw JSON only. Do NOT wrap the output in ```json ... ``` markdown blocks.
2. Only include keys in the JSON that are required for your chosen action.

Respond with this EXACT format:
{{
    "thought": "your inner monologue (1-2 sentences)",
    "action": "ACTION_NAME",
    "direction": "one of the 8 valid directions (only if MOVE)",
    "target": "exact name of person/object/item/location (if applicable)",
    "market": "exact name of market (only if BUY)",
    "speech": "what you say out loud (only if TALK)",
    "offer": "item you offer (only if TRADE)",
    "want": "item you want (only if TRADE)"
}}"""

def build_prompt(agent: Any, world: Any, agents: List[Any], weather: Any) -> str:
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

    status = STATUS_TEMPLATE.format(
        health=int(agent.health),
        max_health=int(agent.max_health),
        health_warning=health_warning,
        denarii=agent.denarii,
        drives_summary=agent.get_drives_summary(),
        self_assessment=self_assessment,
        inventory_summary=agent.get_inventory_summary(),
    )

    perception_text = agent.perceive(world, agents)
    perception = PERCEPTION_TEMPLATE.format(perception_text=perception_text)

    # Added preferences to memory template
    prefs = agent.memory.get_preferences_summary()
    memory = MEMORY_TEMPLATE.format(
        recent_memories=agent.memory.get_recent_context(n=5),
        important_memories=agent.memory.get_important_memories(n=3),
        relationships=agent.memory.get_relationship_summary(),
        beliefs=agent.memory.get_beliefs_summary(),
        known_locations=agent.memory.get_known_locations_summary(),
        preferences=prefs if prefs else "You have no strong preferences yet.",
    )

    urgency_hint = _build_urgency_hint(agent)
    action = ACTION_TEMPLATE.format(urgency_hint=urgency_hint)

    # Decision history — tells the LLM what the agent did recently
    decision_history_text = agent.get_decision_history_summary(n=5)
    decision_history = DECISION_HISTORY_TEMPLATE.format(
        decision_history=decision_history_text,
    )

    full_prompt = "\n\n".join([system, status, perception, memory, decision_history, action])
    return full_prompt

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

def build_conversation_prompt(agent: Any, speaker_name: str, speech: str) -> str:
    """Build a prompt for generating a response to being spoken to, using context history."""
    persona = agent.personality_seed

    state_note = ""
    if agent.health < 50:
        state_note = "\nNote: You are injured and in pain. This affects how you respond."
    sensation = agent.status_effects.get_sensation_summary()
    if sensation:
        state_note += f"\nYou currently feel: {sensation}"

    # Injecting the conversation back-and-forth history
    convo_context = agent.memory.get_conversation_context(speaker_name)

    return f"""You are {agent.name}, a {agent.role} in Ancient Rome (161 AD).
Personality: {persona.get('speech_style', 'speaks normally')}
{state_note}

Your relationship with {speaker_name}: {_get_relationship_desc(agent, speaker_name)}
Recent conversation history with them: 
{convo_context}

{speaker_name} just said to you: "{speech}"

Respond ONLY with JSON:
{{
    "thought": "your inner reaction (1 sentence)",
    "speech": "what you say back (keep it natural and in-character, 1-3 sentences)",
    "attitude": "friendly/neutral/hostile/suspicious"
}}"""

def _get_relationship_desc(agent: Any, name: str) -> str:
    rel = agent.memory.relationships.get(name)
    if not rel:
        return "You don't know this person."
    if rel.trust > 30:
        return f"You consider them a friend (trust: {int(rel.trust)})"
    elif rel.trust < -30:
        return f"You distrust them (trust: {int(rel.trust)})"
    return f"An acquaintance (met {rel.interaction_count} times)"