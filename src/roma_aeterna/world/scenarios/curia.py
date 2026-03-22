"""
Curia of Pompey scenario — 44 BC, Ides of March.

The Theatre of Pompey's annexe where the Senate convened after the main
Curia Hostilia burned down.  A rectangular marble hall with columns,
a statue of Pompey, and the curule chair at the north end.

  ┌────────────────────────────────────────────────────────┐
  │  ║ col ║                 PODIUM                ║ col ║  │
  │  ║     ║   [Statue of Pompey]  [Curule Chair]  ║     ║  │
  │  ║     ║───────────────────────────────────────║     ║  │
  │  ║     ║                                       ║     ║  │
  │  ║     ║          SENATE FLOOR                 ║     ║  │
  │  ║     ║    (senators mingle and debate)        ║     ║  │
  │  ║     ║                                       ║     ║  │
  │  ║     ║───────────────────────────────────────║     ║  │
  │  ║     ║         ENTRANCE VESTIBULE            ║     ║  │
  └──╨─────╨───────────────────────────────────────╨─────╨──┘
"""

import random

from .base import BaseScenario
from roma_aeterna.config import RANDOM_SEED

# ── Map geometry ──────────────────────────────────────────────────────────────

_W  = 60    # map width  (tiles)
_H  = 50    # map height (tiles)
_CX = _W // 2  # 30
_CY = _H // 2  # 25

# Interior floor bounds (inside the outer walls)
_FX1, _FY1 = 3,  3        # floor top-left
_FX2, _FY2 = _W-4, _H-4  # floor bottom-right

# Column rows (x) and the y-range they span
_COL_X_L = 6           # left column row x
_COL_X_R = _W - 7      # right column row x
_COL_Y_START = 6
_COL_Y_END   = _H - 7
_COL_STEP    = 4        # one column every 4 tiles

# Podium tier at north end
_POD_Y1, _POD_Y2 = _FY1, _FY1 + 6   # north 6 rows are the raised dais
_POD_X1, _POD_X2 = _COL_X_L + 2, _COL_X_R - 2

# Vestibule (entrance) at south end
_VES_Y1, _VES_Y2 = _FY2 - 4, _FY2
_DOOR_X1, _DOOR_X2 = _CX - 3, _CX + 3


class CuriaPompeiScenario(BaseScenario):
    name = "curia_pompei"
    description = "Senate session in the Curia of Pompey, 44 BC."
    title_lines = [
        "CURIA POMPEIANA",
        "Rome, 44 BC — Beware the Ides of March",
    ]

    def generate_world(self):
        from roma_aeterna.world.map import GameMap
        from roma_aeterna.world.objects import WorldObject, create_prefab
        from roma_aeterna.world.components import Interactable, Structural

        rng = random.Random(RANDOM_SEED)
        world = GameMap(_W, _H)
        world.camera_start = (_CX, _CY)

        # ── Terrain ───────────────────────────────────────────────────────────

        # Base: all wall
        world.fill_rect(0, 0, _W - 1, _H - 1, "wall")

        # Main floor — marble (use "plaza" for walkability; renderer colours it)
        world.fill_rect(_FX1, _FY1, _FX2, _FY2, "plaza")

        # Raised podium at north
        world.fill_rect(_POD_X1, _POD_Y1, _POD_X2, _POD_Y2, "steps")

        # Vestibule at south (same level as floor)
        world.fill_rect(_FX1, _VES_Y1, _FX2, _VES_Y2, "plaza")

        # Door gap through south wall so agents can reach the map edge if needed
        world.fill_rect(_DOOR_X1, _H - 3, _DOOR_X2, _H - 1, "road_paved")

        # ── Columns ───────────────────────────────────────────────────────────
        # Left and right colonnade — solid column tiles (non-walkable wall)
        for cy in range(_COL_Y_START, _COL_Y_END + 1, _COL_STEP):
            world.set_tile(_COL_X_L, cy, "wall")
            world.set_tile(_COL_X_R, cy, "wall")
            # Place decorative Column objects on the floor beside each pillar
            col_l = create_prefab("Column", _COL_X_L + 1, cy)
            col_r = create_prefab("Column", _COL_X_R - 1, cy)
            if col_l:
                world.add_object(col_l)
            if col_r:
                world.add_object(col_r)

        # ── Objects ───────────────────────────────────────────────────────────

        # Statue of Pompey — north podium, centre-left
        statue = WorldObject("Statue of Pompey", _CX - 4, _POD_Y1 + 1)
        statue.width, statue.height = 2, 2
        statue.add_component(Structural(material="marble"))
        statue.add_component(Interactable(interaction_type="inspect", capacity=10))
        world.add_object(statue)

        # Curule Chair — north podium, centre-right
        chair = WorldObject("Curule Chair", _CX + 2, _POD_Y1 + 2)
        chair.add_component(Interactable(interaction_type="inspect", capacity=5))
        world.add_object(chair)

        # Altar of the Lares at south-east corner
        altar = WorldObject("Altar of the Lares", _FX2 - 3, _VES_Y1 + 1)
        altar.add_component(Interactable(interaction_type="pray", capacity=4))
        world.add_object(altar)

        # Notice board (Tabularium-style) — west wall near entrance
        notice = WorldObject("Senate Notice Board", _FX1 + 1, _VES_Y1 + 2)
        notice.add_component(Interactable(interaction_type="read_records", capacity=6))
        world.add_object(notice)

        # Wall torches — decorative, inspectable
        for fx, fy in [
            (_COL_X_L + 1, _POD_Y2 + 2),
            (_COL_X_R - 1, _POD_Y2 + 2),
            (_COL_X_L + 1, _VES_Y1 - 2),
            (_COL_X_R - 1, _VES_Y1 - 2),
        ]:
            torch = WorldObject("Wall Torch", fx, fy)
            torch.add_component(Interactable(interaction_type="inspect", capacity=1))
            world.add_object(torch)

        # Register key locations in the world landmarks dict
        world.landmarks = {
            "Curia of Pompey": (_CX, _CY),
            "Statue of Pompey": (_CX - 4, _POD_Y1 + 1),
            "Curule Chair": (_CX + 2, _POD_Y1 + 2),
            "Altar of the Lares": (_FX2 - 3, _VES_Y1 + 1),
        }

        return world

    # ── Agent creation ────────────────────────────────────────────────────────

    def create_agents(self, world) -> list:
        from roma_aeterna.agent.base import Agent
        from roma_aeterna.world.items import ITEM_DB

        # ── Named historical senators ──────────────────────────────────────────
        # Arranged naturally in the hall: Caesar near the podium, others spread
        named = [
            Agent("Gaius Julius Caesar",      "Senator", _CX,      _POD_Y2 + 3),
            Agent("Marcus Junius Brutus",      "Senator", _CX - 7,  _CY - 2),
            Agent("Gaius Cassius Longinus",    "Senator", _CX + 7,  _CY - 2),
            Agent("Marcus Tullius Cicero",     "Senator", _CX - 9,  _CY + 4),
            Agent("Marcus Antonius",           "Senator", _CX + 4,  _POD_Y2 + 5),
        ]

        # Give soldiers their gladii (append on top of the role's base inventory)
        _arm = ["Gaius Julius Caesar", "Marcus Junius Brutus",
                "Gaius Cassius Longinus", "Marcus Antonius"]
        for agent in named:
            if agent.name in _arm:
                gladius = ITEM_DB.create_item("Gladius")
                if gladius:
                    agent.inventory.append(gladius)

        # Teach everyone the key locations
        curia_pos = (_CX, _CY)
        statue_pos = (_CX - 4, _POD_Y1 + 1)
        for a in named:
            a.memory.learn_location("Curia of Pompey", curia_pos)
            a.memory.learn_location("Statue of Pompey", statue_pos)
            # Inject scenario context so the LLM knows the date and setting
            a.memory.add_event(
                "The Senate has convened in the Curia of Pompey. "
                "Tensions run high over Caesar's growing power. "
                "The Ides of March approach.",
                tick=0, importance=5.0, memory_type="observation",
                tags=["context", "politics"],
            )

        return named

    def create_animals(self, world) -> list:
        return []
