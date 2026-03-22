"""
World Scenarios — pluggable simulation environments.

Select the active scenario in config.py:

    SCENARIO = "rome"             # Full historical Rome c. 161 AD
    SCENARIO = "gladiator_arena"  # Flavian Amphitheatre arena c. 80 AD
    SCENARIO = "curia_pompei"     # Curia of Pompey, 44 BC — senators only

To add a new scenario, subclass BaseScenario, implement the three
required methods, and register the class in SCENARIO_REGISTRY below.
"""

from .base import BaseScenario
from .rome import RomeScenario
from .arena import GladiatorArenaScenario
from .curia import CuriaPompeiScenario

SCENARIO_REGISTRY: dict = {
    "rome": RomeScenario,
    "gladiator_arena": GladiatorArenaScenario,
    "curia_pompei": CuriaPompeiScenario,
}


def get_scenario(name: str) -> BaseScenario:
    """Instantiate and return the named scenario.

    Raises ValueError for unknown scenario names so the user gets an
    informative message rather than a cryptic AttributeError.
    """
    cls = SCENARIO_REGISTRY.get(name)
    if cls is None:
        available = list(SCENARIO_REGISTRY.keys())
        raise ValueError(
            f"Unknown scenario {name!r}. "
            f"Available scenarios: {available}"
        )
    return cls()
