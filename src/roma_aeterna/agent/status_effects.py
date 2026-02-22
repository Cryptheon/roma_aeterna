"""
Status Effects — Temporary modifiers applied to agents by the environment,
items, social interactions, or combat.

Each effect now carries an `urgency_weight` that feeds directly into the
agent's LIF neuron. This replaces hardcoded threat detection — the agent
feels danger through its own body, not through an omniscient scanner.

Urgency weights guide how strongly an effect drives the agent to act:
  - 0.0 = no urgency impact (neutral effects)
  - 1-5  = mild pressure (discomfort, minor needs)
  - 5-15 = significant pressure (pain, danger)
  - 15+  = critical (life-threatening, act NOW)
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, List


@dataclass
class StatusEffect:
    """A temporary modifier on an agent."""
    name: str
    description: str
    duration_ticks: int                 # -1 = permanent until removed
    remaining_ticks: int = -1
    stat_modifiers: Dict[str, float] = field(default_factory=dict)
    # Keys: "hunger_rate", "energy_rate", "thirst_rate", "speed",
    #        "social_bonus", "health_regen", "perception_radius",
    #        "trade_bonus", "comfort_rate"
    tags: List[str] = field(default_factory=list)
    stackable: bool = False
    source: str = "unknown"

    # How strongly this effect pushes the agent to act.
    # High values make the LIF neuron fire sooner.
    urgency_weight: float = 0.0

    # Short text the agent perceives about this effect (for LLM context).
    # If empty, falls back to self.description.
    sensation: str = ""

    def __post_init__(self) -> None:
        if self.remaining_ticks == -1:
            self.remaining_ticks = self.duration_ticks

    def is_expired(self) -> bool:
        return self.duration_ticks > 0 and self.remaining_ticks <= 0

    def tick(self) -> None:
        if self.duration_ticks > 0:
            self.remaining_ticks -= 1

    def get_sensation(self) -> str:
        """What the agent subjectively feels from this effect."""
        return self.sensation or self.description


# ============================================================
# Predefined Effect Templates
# ============================================================

def create_effect(name: str, **kwargs) -> Optional[StatusEffect]:
    """Factory for common status effects."""
    effects = {
        # --- Weather ---
        "wet": StatusEffect(
            "Wet", "Drenched by rain. Movement slowed, uncomfortable.",
            duration_ticks=100,
            stat_modifiers={"speed": -0.3, "comfort_rate": 2.0, "energy_rate": 1.3},
            tags=["weather", "negative"],
            urgency_weight=2.0,
            sensation="Your clothes are soaked through. The wet fabric clings and chafes.",
        ),
        "heatstroke": StatusEffect(
            "Heatstroke", "The sun is merciless. Thirst and exhaustion accelerate.",
            duration_ticks=150,
            stat_modifiers={"thirst_rate": 2.5, "energy_rate": 2.0, "speed": -0.2},
            tags=["weather", "negative", "dangerous"],
            urgency_weight=12.0,
            sensation="Your head pounds. The world swims. You desperately need water and shade.",
        ),
        "chilled": StatusEffect(
            "Chilled", "Cold night air seeps into your bones.",
            duration_ticks=80,
            stat_modifiers={"energy_rate": 1.5, "comfort_rate": 1.5},
            tags=["weather", "negative"],
            urgency_weight=3.0,
            sensation="You shiver. The cold night air cuts through your clothing.",
        ),

        # --- Environmental ---
        "burned": StatusEffect(
            "Burned", "Fire has scorched your skin. Painful and slow to heal.",
            duration_ticks=200,
            stat_modifiers={"health_regen": -0.5, "speed": -0.2, "comfort_rate": 3.0},
            tags=["fire", "negative", "injury"],
            urgency_weight=18.0,
            sensation="Searing pain radiates from your burns. Every movement hurts. You need to get away from fire and find help.",
        ),
        "smoke_inhalation": StatusEffect(
            "Smoke Inhalation", "Lungs burn from thick smoke.",
            duration_ticks=60,
            stat_modifiers={"energy_rate": 2.0, "perception_radius": -3},
            tags=["fire", "negative"],
            urgency_weight=10.0,
            sensation="Your lungs burn and your eyes water from thick smoke. You can barely see or breathe.",
        ),
        "refreshed": StatusEffect(
            "Refreshed", "Cool fountain water has reinvigorated you.",
            duration_ticks=50,
            stat_modifiers={"energy_rate": 0.5, "health_regen": 0.3},
            tags=["positive", "water"],
            urgency_weight=0.0,
            sensation="Cool water has refreshed your body. You feel alert and clearheaded.",
        ),

        # --- Social ---
        "inspired": StatusEffect(
            "Inspired", "A stimulating conversation has lifted your spirits.",
            duration_ticks=100,
            stat_modifiers={"social_rate": 0.3, "comfort_rate": 0.5},
            tags=["positive", "social"],
            urgency_weight=0.0,
            sensation="Your mind buzzes with new ideas from the conversation.",
        ),
        "humiliated": StatusEffect(
            "Humiliated", "A public shaming weighs on your mind.",
            duration_ticks=150,
            stat_modifiers={"social_rate": 2.0, "comfort_rate": 2.0},
            tags=["negative", "social"],
            urgency_weight=6.0,
            sensation="Shame burns in your chest. You can feel people staring. You want to hide.",
        ),

        # --- Items ---
        "well_fed": StatusEffect(
            "Well Fed", "A hearty meal sits warmly in your belly.",
            duration_ticks=120,
            stat_modifiers={"hunger_rate": 0.3, "energy_rate": 0.8, "health_regen": 0.2},
            tags=["positive", "food"],
            urgency_weight=0.0,
            sensation="A warm fullness in your belly. The world seems a little kinder.",
        ),
        "intoxicated": StatusEffect(
            "Intoxicated", "The wine has gone to your head.",
            duration_ticks=80,
            stat_modifiers={"speed": -0.15, "social_bonus": 5.0, "perception_radius": -2},
            tags=["neutral", "drink"],
            urgency_weight=1.0,
            sensation="A pleasant warmth spreads through you. Your thoughts are loose and your tongue is looser.",
        ),
        "food_poisoning": StatusEffect(
            "Food Poisoning", "Rotten food rebels in your stomach.",
            duration_ticks=100,
            stat_modifiers={"energy_rate": 3.0, "speed": -0.4, "health_regen": -0.3},
            tags=["negative", "food", "dangerous"],
            urgency_weight=14.0,
            sensation="Violent nausea wracks your body. Your stomach cramps and you break into a cold sweat.",
        ),

        # --- Activity ---
        "rested": StatusEffect(
            "Rested", "Sleep has restored your body and mind.",
            duration_ticks=200,
            stat_modifiers={"energy_rate": 0.5, "health_regen": 0.3},
            tags=["positive"],
            urgency_weight=0.0,
            sensation="You feel well-rested and ready to face the day.",
        ),
        "exercised": StatusEffect(
            "Exercised", "Training at the ludus has toughened you.",
            duration_ticks=100,
            stat_modifiers={"speed": 0.1, "energy_rate": 1.2},
            tags=["positive", "physical"],
            urgency_weight=0.0,
            sensation="Your muscles ache pleasantly. You feel strong.",
        ),
        "blessed": StatusEffect(
            "Blessed", "The gods smile upon you — or so you feel.",
            duration_ticks=150,
            stat_modifiers={"comfort_rate": 0.3, "social_bonus": 3.0},
            tags=["positive", "spiritual"],
            urgency_weight=0.0,
            sensation="A calm certainty fills you. The gods are watching over you.",
        ),
    }

    template = effects.get(name)
    if not template:
        return None

    # Return a copy
    return StatusEffect(
        name=template.name,
        description=template.description,
        duration_ticks=template.duration_ticks,
        stat_modifiers=dict(template.stat_modifiers),
        tags=list(template.tags),
        stackable=template.stackable,
        source=kwargs.get("source", "unknown"),
        urgency_weight=template.urgency_weight,
        sensation=template.sensation,
    )


class StatusEffectManager:
    """Manages active status effects on an agent."""

    def __init__(self) -> None:
        self.active: List[StatusEffect] = []

    def add(self, effect: StatusEffect) -> None:
        """Add a status effect. Non-stackable effects replace existing."""
        if not effect.stackable:
            self.active = [e for e in self.active if e.name != effect.name]
        self.active.append(effect)

    def remove(self, name: str) -> None:
        """Remove a named effect."""
        self.active = [e for e in self.active if e.name != name]

    def tick(self) -> None:
        """Advance all effects by one tick and remove expired ones."""
        for effect in self.active:
            effect.tick()
        self.active = [e for e in self.active if not e.is_expired()]

    def get_modifier(self, stat: str, default: float = 1.0) -> float:
        """Get the combined modifier for a stat from all active effects.

        For rate modifiers, values are multiplied together.
        For additive bonuses, they're summed.
        """
        if stat.endswith("_bonus"):
            return sum(e.stat_modifiers.get(stat, 0.0) for e in self.active)
        else:
            result = default
            for e in self.active:
                if stat in e.stat_modifiers:
                    result *= e.stat_modifiers[stat]
            return result

    def has_effect(self, name: str) -> bool:
        return any(e.name == name for e in self.active)

    def get_total_urgency(self) -> float:
        """Sum urgency weights from all active effects.

        This replaces hardcoded threat detection. The agent feels danger
        through accumulated status effects, each weighted by severity.
        """
        return sum(e.urgency_weight for e in self.active)

    def get_summary(self) -> str:
        """Text summary for LLM context."""
        if not self.active:
            return "You feel normal."
        return ", ".join(
            f"{e.name} ({e.remaining_ticks} ticks left)" for e in self.active
        )

    def get_sensation_summary(self) -> str:
        """Rich first-person description of what the agent feels.

        This is the primary interface between status effects and the LLM.
        The agent doesn't know about 'stat modifiers' — it knows how it feels.
        """
        if not self.active:
            return ""

        sensations: List[str] = []

        # Sort by urgency (most pressing first)
        for effect in sorted(self.active, key=lambda e: e.urgency_weight, reverse=True):
            sensation = effect.get_sensation()
            if sensation:
                sensations.append(sensation)

        if not sensations:
            return ""

        return "\n".join(sensations)

    def get_negative_effects(self) -> List[StatusEffect]:
        return [e for e in self.active if "negative" in e.tags]

    def get_positive_effects(self) -> List[StatusEffect]:
        return [e for e in self.active if "positive" in e.tags]
