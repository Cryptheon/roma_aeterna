"""Base class for all simulation scenarios."""


class BaseScenario:
    """
    A scenario defines a self-contained simulation environment:
    the world map, the initial agents, and the startup title.

    Subclass this and register in SCENARIO_REGISTRY (__init__.py) to add
    a new scenario.  The engine and renderer are scenario-agnostic — they
    work entirely through the GameMap / Agent / Animal public interfaces.
    """

    name: str = ""
    description: str = ""
    # Lines printed at startup between the "===" banners.
    title_lines: list = ["ROME: AETERNA"]

    def generate_world(self):
        """Generate and return a fully-populated GameMap for this scenario."""
        raise NotImplementedError

    def create_agents(self, world) -> list:
        """Return the list of human Agent objects (named + random citizens)."""
        raise NotImplementedError

    def create_animals(self, world) -> list:
        """Return the list of Animal objects."""
        raise NotImplementedError
