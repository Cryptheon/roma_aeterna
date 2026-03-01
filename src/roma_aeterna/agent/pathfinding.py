"""
Pathfinder — A* pathfinding and direction utilities.

Extracted from Autopilot so that autopilot.py stays focused on
behaviour logic rather than graph search.
"""

import heapq
import math
import random
from typing import Any, Dict, List, Optional, Tuple

from roma_aeterna.config import PATHFINDING_MAX_STEPS, PATHFINDING_ROAD_BIAS
from .constants import DIRECTION_DELTAS


class Pathfinder:
    """Static A* pathfinding utilities."""

    @staticmethod
    def find_path(start: Tuple[int, int], goal: Tuple[int, int],
                  world: Any,
                  max_steps: int = PATHFINDING_MAX_STEPS) -> List[Tuple[int, int]]:
        """A* search from start to goal.

        Returns a path (list of tiles, not including start) or [] if
        unreachable. If the goal is beyond max_steps expansions, returns a
        partial path to the closest explored point — successive GOTO calls
        chain partial paths until the agent arrives.
        """
        sx, sy = start
        tx, ty = goal

        if (sx, sy) == (tx, ty):
            return []

        # open_heap entries: (f_score, tiebreaker, x, y)
        counter = 0
        open_heap: List = []
        heapq.heappush(open_heap, (0.0, counter, sx, sy))

        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
        g_cost: Dict[Tuple[int, int], float] = {(sx, sy): 0.0}
        closed: set = set()

        best_partial: Tuple[int, int] = (sx, sy)
        best_dist = math.sqrt((sx - tx) ** 2 + (sy - ty) ** 2)
        goal_found = False

        while open_heap:
            _, _, cx, cy = heapq.heappop(open_heap)

            if (cx, cy) in closed:
                continue
            closed.add((cx, cy))

            # Track the closest explored point for partial-path fallback
            d = math.sqrt((cx - tx) ** 2 + (cy - ty) ** 2)
            if d < best_dist:
                best_dist = d
                best_partial = (cx, cy)

            if (cx, cy) == (tx, ty):
                goal_found = True
                break

            # Expansion limit — return partial path to closest point found
            if len(closed) >= max_steps:
                break

            current_g = g_cost.get((cx, cy), 0.0)
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = cx + dx, cy + dy
                    if (nx, ny) in closed:
                        continue
                    tile = world.get_tile(nx, ny)
                    if not tile or not tile.is_walkable:
                        continue

                    # Diagonal moves cost √2, cardinal moves cost 1
                    move_cost = 1.414 if (dx != 0 and dy != 0) else 1.0
                    if tile.terrain_type == "road":
                        move_cost *= PATHFINDING_ROAD_BIAS

                    ng = current_g + move_cost
                    if (nx, ny) not in g_cost or ng < g_cost[(nx, ny)]:
                        g_cost[(nx, ny)] = ng
                        h = math.sqrt((nx - tx) ** 2 + (ny - ty) ** 2)
                        counter += 1
                        heapq.heappush(open_heap, (ng + h, counter, nx, ny))
                        came_from[(nx, ny)] = (cx, cy)

        end = (tx, ty) if goal_found else best_partial
        if end == (sx, sy):
            return []  # No progress possible

        # Reconstruct path by tracing came_from back to start
        path: List[Tuple[int, int]] = []
        node = end
        while node in came_from:
            path.append(node)
            node = came_from[node]
        path.reverse()
        return path

    @staticmethod
    def find_safe_direction(agent: Any, world: Any) -> str:
        """Score all 8 directions and return the safest one (fire escape)."""
        best_dir = "north"
        best_score = -999.0

        for direction, (dx, dy) in DIRECTION_DELTAS.items():
            nx, ny = int(agent.x) + dx, int(agent.y) + dy
            tile = world.get_tile(nx, ny)
            if not tile or not tile.is_walkable:
                continue

            score = 0.0
            # Prefer tiles without smoke
            if "smoke" not in getattr(tile, "effects", []):
                score += 5.0
            # Prefer tiles without fire
            if not tile.building or not any(
                getattr(c, "is_burning", False)
                for c in getattr(tile.building, "components", {}).values()
            ):
                score += 10.0
            # Prefer roads (faster escape)
            if tile.terrain_type == "road":
                score += 2.0
            # Small randomness to prevent oscillation
            score += random.random()

            if score > best_score:
                best_score = score
                best_dir = direction

        return best_dir

    @staticmethod
    def direction_to(ax: float, ay: float, tx: int, ty: int) -> str:
        """Angle → 8-direction string."""
        dx, dy = tx - ax, ty - ay
        if dx == 0 and dy == 0:
            return "north"
        angle = math.degrees(math.atan2(dy, dx))
        if angle < 0:
            angle += 360
        dirs = ["east", "southeast", "south", "southwest",
                "west", "northwest", "north", "northeast"]
        idx = int((angle + 22.5) // 45) % 8
        return dirs[idx]
