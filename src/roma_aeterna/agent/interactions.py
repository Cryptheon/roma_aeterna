"""
Interaction handlers for agent↔world-object interactions.

All logic that was in Agent._execute_interaction lives here as a
module-level function so base.py stays lean.
"""

import random
from typing import Any


def execute_interaction(agent: Any, target: Any, interact: Any) -> str:
    """Execute an interaction between an agent and a world object.

    Returns a natural-language result string.
    """
    from .status_effects import create_effect

    itype = interact.interaction_type
    name = target.name

    if itype == "pray":
        agent.drives["comfort"] = max(0, agent.drives["comfort"] - 15)
        agent.drives["social"] = max(0, agent.drives["social"] - 5)
        effect = create_effect("blessed")
        if effect:
            agent.status_effects.add(effect)
        return f"You pray at {name}. A sense of peace washes over you."

    elif itype == "drink":
        from roma_aeterna.world.components import Liquid, WaterFeature
        water_feature = target.get_component(WaterFeature)
        if water_feature and water_feature.is_active:
            agent.drives["thirst"] = max(0, agent.drives["thirst"] - 40)
            effect = create_effect("refreshed")
            if effect:
                agent.status_effects.add(effect)
            return f"You drink fresh water from {name}. Refreshing!"
        liquid = target.get_component(Liquid)
        if liquid and liquid.amount > 0:
            agent.drives["thirst"] = max(0, agent.drives["thirst"] - 40)
            liquid.amount -= 5
            effect = create_effect("refreshed")
            if effect:
                agent.status_effects.add(effect)
            return f"You drink from {name}. Refreshing!"
        return f"{name} is dry."

    elif itype == "rest":
        from roma_aeterna.world.components import WaterFeature
        water = target.get_component(WaterFeature)
        if water and water.is_active:
            # Bathhouse — full bathing experience
            agent.drives["energy"] = max(0, agent.drives["energy"] - 30)
            agent.drives["comfort"] = max(0, agent.drives["comfort"] - 20)
            agent.drives["thirst"] = max(0, agent.drives["thirst"] - 10)
            effect = create_effect("refreshed")
            if effect:
                agent.status_effects.add(effect)
            return (f"You bathe at {name}. The warm waters soothe your tired muscles "
                    f"and the steam clears your mind.")
        agent.drives["energy"] = max(0, agent.drives["energy"] - 20)
        agent.drives["comfort"] = max(0, agent.drives["comfort"] - 10)
        return f"You rest at {name}. Your body relaxes."

    elif itype == "rest_shade":
        agent.drives["energy"] = max(0, agent.drives["energy"] - 15)
        agent.drives["comfort"] = max(0, agent.drives["comfort"] - 8)
        name_lower = name.lower()
        if "cypress" in name_lower or "pine" in name_lower:
            return (f"You sit in the shade of {name}. The cool shadow offers "
                    f"relief from the midday heat.")
        elif "porticus" in name_lower or "portico" in name_lower:
            return (f"You rest beneath the colonnade of {name}. Merchants and "
                    f"citizens stroll past in the shade.")
        return f"You rest in the shade of {name}. The cool shadow relieves the heat."

    elif itype == "forage":
        agent.drives["comfort"] = max(0, agent.drives["comfort"] - 3)
        if random.random() < 0.40:
            agent.drives["hunger"] = max(0, agent.drives["hunger"] - 15)
            return (f"You gather olives from {name}. A handful of ripe fruit "
                    f"fills your palm — bitter but nourishing.")
        return (f"You search {name} but the branches are picked clean. "
                f"You find little worth taking today.")

    elif itype == "read_records":
        agent.drives["social"] = max(0, agent.drives["social"] - 5)
        agent.drives["comfort"] = max(0, agent.drives["comfort"] - 3)
        return (f"You study the public records at {name}. Rows of tablets "
                f"record Rome's laws, census rolls, and the names of the dead. "
                f"History presses against your fingertips.")

    elif itype == "trade":
        return f"You browse the wares at {name}."

    elif itype == "spectate":
        agent.drives["social"] = max(0, agent.drives["social"] - 15)
        agent.drives["comfort"] = max(0, agent.drives["comfort"] - 5)
        return f"You watch the spectacle at {name}. The crowd roars!"

    elif itype == "train":
        agent.drives["energy"] += 15
        effect = create_effect("exercised")
        if effect:
            agent.status_effects.add(effect)
        return f"You train at {name}. Your muscles burn but you feel stronger."

    elif itype == "speak":
        agent.drives["social"] = max(0, agent.drives["social"] - 20)
        return f"You address the crowd from {name}. Your voice carries across the Forum."

    elif itype == "deliberate":
        agent.drives["social"] = max(0, agent.drives["social"] - 15)
        agent.drives["comfort"] = max(0, agent.drives["comfort"] - 5)
        return (f"You join the public deliberations at {name}. "
                f"Citizens argue, senators posture, and voices echo off the marble.")

    elif itype == "audience":
        agent.drives["social"] = max(0, agent.drives["social"] - 8)
        agent.drives["comfort"] = max(0, agent.drives["comfort"] - 5)
        return (f"You wait at {name}, hoping for an audience. "
                f"The halls are filled with petitioners clutching their tablets.")

    elif itype == "inspect":
        agent.drives["comfort"] = max(0, agent.drives["comfort"] - 3)
        name_lower = name.lower()
        if "statue" in name_lower and "equestrian" in name_lower:
            return (f"You study the equestrian statue of {name}. The bronze rider "
                    f"commands the square, frozen mid-triumph.")
        elif "statue" in name_lower:
            return (f"You stand before {name}. The sculptor's chisel has captured "
                    f"godlike calm in cold marble.")
        elif "column of trajan" in name_lower:
            return (f"You crane your neck to read {name}'s spiral reliefs. "
                    f"Thousands of soldiers — Dacian wars in stone — wind endlessly upward.")
        elif "column" in name_lower:
            return f"You trace the fluting of {name}. Fine marble, quarried from distant hills."
        elif "obelisk" in name_lower:
            return (f"You read the hieroglyphs on {name}. Egyptian writing — older than Rome "
                    f"itself — speaks of distant pharaohs.")
        elif "arch" in name_lower:
            return (f"You walk beneath {name} and read the dedication carved in the frieze. "
                    f"Triumph and glory, written in stone for all to see.")
        elif "regia" in name_lower:
            return (f"You examine {name} — the ancient seat of the Pontifex Maximus. "
                    f"Its stones remember kings. Rome barely does.")
        elif "shrub" in name_lower:
            return (f"You crouch beside {name}. A lizard flickers between the stems "
                    f"and vanishes into the shade.")
        elif "flower" in name_lower:
            return (f"You lean close to {name}. The blooms smell faintly sweet "
                    f"and a bee drifts past, indifferent to Rome's troubles.")
        return f"You carefully inspect {name}."

    return f"You interact with {name}."
