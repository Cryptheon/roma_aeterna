"""
Shared constants for the agent subsystem.
"""

from typing import Dict, Tuple

VALID_ACTIONS = {
    "MOVE", "TALK", "INTERACT", "PICK_UP", "DROP", "CONSUME",
    "CRAFT", "TRADE", "REST", "SLEEP", "INSPECT", "IDLE",
    "GOTO",     # Multi-step navigation to a named location
    "BUY",      # Purchase from a market
    "WORK",     # Perform role duties at a building
    "REFLECT",  # Write a personal note to long-term memory
    "ATTACK",   # Strike a nearby agent with a weapon or bare hands
}

DIRECTION_DELTAS: Dict[str, Tuple[int, int]] = {
    "north":      (0, -1),
    "south":      (0, 1),
    "east":       (1, 0),
    "west":       (-1, 0),
    "northeast":  (1, -1),
    "northwest":  (-1, -1),
    "southeast":  (1, 1),
    "southwest":  (-1, 1),
}
