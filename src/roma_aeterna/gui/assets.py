"""
Sprite & Color System — Roman Aesthetic
=========================================
All sprites are generated programmatically as pygame Surfaces.
Color palette inspired by Roman frescoes, terracotta, and marble.
"""

import pygame
import math
import random

# ============================================================
# COLOR PALETTE — Pompeii Fresco Tones
# ============================================================

COLORS = {
    # --- Terrain ---
    "dirt":             (194, 170, 137),
    "dirt_dark":        (168, 143, 110),
    "grass":            (142, 170, 108),
    "grass_dry":        (175, 175, 115),
    "garden":           (108, 155, 88),
    "garden_flower":    (165, 130, 95),
    "hill":             (160, 148, 120),
    "hill_steep":       (138, 122, 98),
    "cliff":            (105, 90, 72),
    
    # Roads
    "via_sacra":        (215, 200, 175),
    "road_paved":       (195, 185, 168),
    "road_cobble":      (178, 168, 150),
    "forum_floor":      (225, 218, 200),
    "plaza":            (205, 195, 178),
    "steps":            (210, 205, 192),
    
    # Water
    "water":            (72, 120, 168),
    "water_shallow":    (108, 150, 180),
    "aqueduct_channel": (62, 105, 148),
    
    # Arena
    "sand_arena":       (215, 195, 155),
    
    # Circus
    "circus_sand":      (210, 190, 148),
    "circus_spina":     (180, 165, 135),
    
    # Structure
    "wall":             (188, 175, 155),
    "building_floor":   (178, 165, 142),
    
    # --- Building Materials ---
    "marble_white":     (238, 232, 220),
    "marble_cream":     (228, 218, 198),
    "travertine":       (218, 208, 185),
    "brick_roman":      (185, 120, 95),
    "brick_dark":       (155, 98, 72),
    "terracotta":       (198, 132, 88),
    "terracotta_roof":  (195, 115, 75),
    "wood_beam":        (125, 90, 55),
    "wood_dark":        (88, 62, 38),
    "plaster_white":    (235, 228, 215),
    "plaster_ochre":    (218, 188, 142),
    "concrete_roman":   (195, 188, 172),
    
    # --- Fresco Colors (for decoration) ---
    "pompeii_red":      (165, 42, 42),
    "pompeii_yellow":   (218, 185, 92),
    "pompeii_blue":     (58, 82, 128),
    "pompeii_green":    (72, 108, 72),
    "pompeii_black":    (45, 38, 32),
    
    # --- Vegetation ---
    "cypress_dark":     (48, 72, 42),
    "cypress_mid":      (62, 88, 52),
    "cypress_light":    (78, 105, 62),
    "olive_trunk":      (95, 78, 55),
    "olive_leaf":       (128, 145, 98),
    "shrub_green":      (95, 125, 75),
    "flower_red":       (185, 62, 55),
    "flower_yellow":    (215, 195, 85),
    "flower_purple":    (128, 72, 138),
    
    # --- Agents ---
    "skin_roman":       (225, 190, 155),
    "toga_white":       (238, 232, 222),
    "toga_purple":      (128, 52, 82),
    "tunic_red":        (175, 55, 48),
    "tunic_brown":      (145, 105, 68),
    "legionary_red":    (165, 38, 38),
    "legionary_gold":   (195, 168, 72),
    "senator_purple":   (108, 42, 88),
    
    # --- Effects ---
    "fire_core":        (255, 200, 60),
    "fire_mid":         (255, 130, 30),
    "fire_outer":       (200, 60, 20),
    "smoke":            (120, 115, 108),
    "shadow":           (60, 55, 48),
    "highlight":        (255, 248, 230),
    
    # --- UI ---
    "ui_bg":            (42, 35, 28),
    "ui_bg_light":      (62, 52, 42),
    "ui_border":        (148, 120, 78),
    "ui_border_gold":   (195, 168, 92),
    "ui_text":          (228, 218, 195),
    "ui_text_dim":      (158, 148, 128),
    "ui_text_accent":   (215, 185, 92),
}


# ============================================================
# SPRITE GENERATOR
# ============================================================

class SpriteSheet:
    """Generates and caches all game sprites programmatically."""
    
    _cache = {}
    _initialized = False
    
    @classmethod
    def init(cls, tile_size=16):
        """Generate all sprites at the given tile size."""
        if cls._initialized:
            return
        cls.tile_size = tile_size
        cls._generate_all()
        cls._initialized = True
    
    @classmethod
    def get(cls, key, size=None):
        """Get a cached sprite surface."""
        if size and (key, size) in cls._cache:
            return cls._cache[(key, size)]
        return cls._cache.get(key)
    
    @classmethod
    def _generate_all(cls):
        ts = cls.tile_size
        
        # --- MONUMENTAL BUILDINGS ---
        cls._gen_colosseum(ts)
        cls._gen_temple_large(ts)
        cls._gen_temple_round(ts)
        cls._gen_temple_medium(ts)
        cls._gen_temple_podium(ts)
        cls._gen_basilica(ts)
        cls._gen_basilica_aemilia(ts)
        cls._gen_rostra(ts)
        cls._gen_palace(ts)
        cls._gen_domus_augustana(ts)
        cls._gen_stadium(ts)
        cls._gen_triumphal_arch(ts)
        cls._gen_arch_large(ts)
        cls._gen_temple_venus_roma(ts)
        cls._gen_circus_maximus(ts)
        cls._gen_curia(ts)
        cls._gen_tabularium(ts)
        cls._gen_forum_imperiale(ts)
        cls._gen_markets_trajan(ts)
        cls._gen_regia(ts)
        
        # --- RESIDENTIAL & COMMERCIAL ---
        cls._gen_insula(ts)
        cls._gen_domus(ts)
        cls._gen_house(ts)
        cls._gen_taberna(ts)
        cls._gen_market_stall(ts)
        cls._gen_bathhouse(ts)
        cls._gen_ludus(ts)
        cls._gen_porticus(ts)
        cls._gen_theatre(ts)
        
        # --- INFRASTRUCTURE ---
        cls._gen_fountain(ts)
        cls._gen_fountain_large(ts)
        cls._gen_column(ts)
        cls._gen_statue(ts)
        cls._gen_statue_equestrian(ts)
        cls._gen_aqueduct(ts)
        cls._gen_torch(ts)
        cls._gen_obelisk(ts)
        cls._gen_cloaca(ts)
        
        # --- VEGETATION ---
        cls._gen_cypress(ts)
        cls._gen_olive_tree(ts)
        cls._gen_shrub(ts)
        cls._gen_flowers(ts)
        cls._gen_pine_tree(ts)
        
        # --- GROUND DECORATIONS ---
        cls._gen_ground_decorations(ts)
    
    # ----------------------------------------------------------------
    # Monumental Buildings
    # ----------------------------------------------------------------
    
    @classmethod
    def _gen_colosseum(cls, ts):
        """The Colosseum — drawn as an elliptical amphitheatre from top-down."""
        w, h = 24 * ts, 20 * ts
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        
        cx, cy = w // 2, h // 2
        rx_o, ry_o = w // 2 - 4, h // 2 - 4
        rx_i, ry_i = int(rx_o * 0.48), int(ry_o * 0.42)
        
        # Outer wall tiers (4 levels of arcades)
        for ring in range(6):
            color_val = 218 - ring * 12
            c = (color_val, color_val - 8, color_val - 22)
            rx, ry = rx_o - ring * 4, ry_o - ring * 4
            pygame.draw.ellipse(surf, c, (cx - rx, cy - ry, rx * 2, ry * 2))
        
        # Seating cavea tiers
        for tier in range(3):
            t_rx = int(rx_o * (0.85 - tier * 0.12))
            t_ry = int(ry_o * (0.85 - tier * 0.12))
            tier_color = (200 - tier * 15, 190 - tier * 15, 170 - tier * 15)
            pygame.draw.ellipse(surf, tier_color,
                                (cx - t_rx, cy - t_ry, t_rx * 2, t_ry * 2))
        
        # Inner arena (sand)
        pygame.draw.ellipse(surf, COLORS["sand_arena"],
                            (cx - rx_i, cy - ry_i, rx_i * 2, ry_i * 2))
        
        # Arena edge wall (podium)
        pygame.draw.ellipse(surf, COLORS["brick_dark"],
                            (cx - rx_i, cy - ry_i, rx_i * 2, ry_i * 2), 3)
        
        # Arched openings (80 arches around the outer ring)
        for angle in range(0, 360, 4):
            rad = math.radians(angle)
            ax = int(cx + (rx_o - 3) * math.cos(rad))
            ay = int(cy + (ry_o - 3) * math.sin(rad))
            pygame.draw.circle(surf, COLORS["shadow"], (ax, ay), 2)
        
        # Second ring of arches
        for angle in range(2, 360, 4):
            rad = math.radians(angle)
            ax = int(cx + (rx_o - 12) * math.cos(rad))
            ay = int(cy + (ry_o - 12) * math.sin(rad))
            pygame.draw.circle(surf, (170, 158, 140), (ax, ay), 1)
        
        # Main entrances (4 cardinal points)
        for angle_deg in [0, 90, 180, 270]:
            rad = math.radians(angle_deg)
            ex = int(cx + (rx_o - 2) * math.cos(rad))
            ey = int(cy + (ry_o - 2) * math.sin(rad))
            pygame.draw.circle(surf, COLORS["marble_cream"], (ex, ey), 5)
            pygame.draw.circle(surf, COLORS["shadow"], (ex, ey), 5, 1)
        
        # Cross lines in arena (hypogeum suggestion)
        pygame.draw.line(surf, (200, 180, 140),
                         (cx - rx_i + 8, cy), (cx + rx_i - 8, cy), 1)
        pygame.draw.line(surf, (200, 180, 140),
                         (cx, cy - ry_i + 8), (cx, cy + ry_i - 8), 1)
        
        # Hypogeum passages
        for i in range(-2, 3):
            pygame.draw.line(surf, (190, 175, 145),
                             (cx + i * 8, cy - ry_i + 8),
                             (cx + i * 8, cy + ry_i - 8), 1)
        
        cls._cache["colosseum"] = surf
    
    @classmethod
    def _gen_temple_large(cls, ts):
        """Large rectangular temple with columned portico (e.g. Temple of Saturn)."""
        w, h = 6 * ts, 10 * ts
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        
        # Base platform (crepidoma) — 3 steps
        for step in range(3):
            margin = step * 2
            step_color = tuple(min(255, c + step * 5) for c in COLORS["travertine"])
            pygame.draw.rect(surf, step_color,
                             (margin, margin, w - margin * 2, h - margin * 2))
        
        # Inner cella
        cella_margin = ts
        pygame.draw.rect(surf, COLORS["marble_white"],
                         (cella_margin, cella_margin * 2,
                          w - cella_margin * 2, h - cella_margin * 3))
        pygame.draw.rect(surf, COLORS["marble_cream"],
                         (cella_margin, cella_margin * 2,
                          w - cella_margin * 2, h - cella_margin * 3), 1)
        
        # Columns (front row — hexastyle)
        col_count = 6
        for i in range(col_count):
            cx = int(cella_margin + i * (w - cella_margin * 2) / (col_count - 1))
            pygame.draw.circle(surf, COLORS["marble_white"], (cx, ts), ts // 3)
            pygame.draw.circle(surf, COLORS["shadow"], (cx, ts), ts // 3, 1)
            # Column fluting hint
            pygame.draw.circle(surf, COLORS["marble_cream"], (cx, ts), ts // 5)
        
        # Side columns (peripteral)
        for i in range(1, 8):
            cy = int(ts + i * (h - ts * 2) / 8)
            pygame.draw.circle(surf, COLORS["marble_cream"], (6, cy), ts // 4)
            pygame.draw.circle(surf, COLORS["shadow"], (6, cy), ts // 4, 1)
            pygame.draw.circle(surf, COLORS["marble_cream"], (w - 6, cy), ts // 4)
            pygame.draw.circle(surf, COLORS["shadow"], (w - 6, cy), ts // 4, 1)
        
        # Back columns
        for i in range(col_count):
            cx = int(cella_margin + i * (w - cella_margin * 2) / (col_count - 1))
            pygame.draw.circle(surf, COLORS["marble_cream"], (cx, h - ts), ts // 4)
        
        # Pediment accent line
        pygame.draw.rect(surf, COLORS["pompeii_red"], (2, 0, w - 4, 3))
        
        # Cella interior detail
        inner_x = cella_margin + 4
        inner_y = cella_margin * 2 + 4
        inner_w = w - cella_margin * 2 - 8
        inner_h = h - cella_margin * 3 - 8
        pygame.draw.rect(surf, (245, 238, 225), (inner_x, inner_y, inner_w, inner_h))
        
        # Cult statue suggestion
        pygame.draw.rect(surf, COLORS["pompeii_yellow"],
                         (w // 2 - 3, h - ts * 3, 6, 8))
        
        cls._cache["temple_large"] = surf
    
    @classmethod
    def _gen_temple_round(cls, ts):
        """Circular temple (Temple of Vesta)."""
        size = 4 * ts
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        
        cx, cy = size // 2, size // 2
        r = size // 2 - 2
        
        # Base circle (stepped platform)
        pygame.draw.circle(surf, COLORS["travertine"], (cx, cy), r)
        pygame.draw.circle(surf, (225, 215, 198), (cx, cy), r - 3)
        pygame.draw.circle(surf, COLORS["marble_white"], (cx, cy), r - 6)
        
        # Inner sanctum
        pygame.draw.circle(surf, COLORS["marble_cream"], (cx, cy), r // 2)
        pygame.draw.circle(surf, (240, 235, 225), (cx, cy), r // 2 - 2)
        
        # Fire at center (eternal flame)
        pygame.draw.circle(surf, COLORS["fire_core"], (cx, cy), 4)
        pygame.draw.circle(surf, COLORS["fire_mid"], (cx, cy), 6, 1)
        pygame.draw.circle(surf, COLORS["fire_outer"], (cx, cy), 8, 1)
        
        # Peristyle columns (20 columns)
        for angle in range(0, 360, 18):
            rad = math.radians(angle)
            col_x = int(cx + (r - 7) * math.cos(rad))
            col_y = int(cy + (r - 7) * math.sin(rad))
            pygame.draw.circle(surf, COLORS["marble_white"], (col_x, col_y), 3)
            pygame.draw.circle(surf, COLORS["shadow"], (col_x, col_y), 3, 1)
        
        cls._cache["temple_round"] = surf
    
    @classmethod
    def _gen_temple_medium(cls, ts):
        """Medium rectangular temple (e.g. Antoninus & Faustina, Divus Julius)."""
        w, h = 5 * ts, 7 * ts
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        
        # Platform
        pygame.draw.rect(surf, COLORS["travertine"], (0, 0, w, h))
        pygame.draw.rect(surf, COLORS["marble_cream"], (3, 3, w - 6, h - 6))
        
        # Cella
        cella_m = ts
        pygame.draw.rect(surf, COLORS["marble_white"],
                         (cella_m, cella_m, w - cella_m * 2, h - cella_m * 2))
        
        # Front columns (4)
        for i in range(4):
            cx = int(8 + i * (w - 16) / 3)
            pygame.draw.circle(surf, COLORS["marble_white"], (cx, ts // 2 + 2), ts // 3)
            pygame.draw.circle(surf, COLORS["shadow"], (cx, ts // 2 + 2), ts // 3, 1)
        
        # Side columns
        for i in range(1, 6):
            cy = int(ts + i * (h - ts * 2) / 6)
            pygame.draw.circle(surf, COLORS["marble_cream"], (5, cy), ts // 4)
            pygame.draw.circle(surf, COLORS["marble_cream"], (w - 5, cy), ts // 4)
        
        # Steps at front
        pygame.draw.rect(surf, COLORS["steps"], (2, 0, w - 4, 4))
        
        cls._cache["temple_medium"] = surf
    
    @classmethod
    def _gen_temple_podium(cls, ts):
        """Temple on high podium (e.g. Temple of Castor & Pollux — 3 surviving columns)."""
        w, h = 4 * ts, 8 * ts
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        
        # High podium
        pygame.draw.rect(surf, COLORS["concrete_roman"], (0, 0, w, h))
        pygame.draw.rect(surf, COLORS["marble_cream"], (2, 2, w - 4, h - 4))
        
        # Only 3 famous standing columns
        positions = [w // 4, w // 2, w * 3 // 4]
        for cx in positions:
            pygame.draw.circle(surf, COLORS["marble_white"], (cx, ts), ts // 3 + 1)
            pygame.draw.circle(surf, COLORS["shadow"], (cx, ts), ts // 3 + 1, 1)
            # Tall column shaft
            pygame.draw.rect(surf, COLORS["marble_white"],
                             (cx - 2, ts, 4, ts * 2))
        
        # Entablature fragment on top of columns
        pygame.draw.rect(surf, COLORS["marble_white"],
                         (positions[0] - 4, ts // 2, positions[-1] - positions[0] + 8, 4))
        
        # Ruined cella outline
        pygame.draw.rect(surf, COLORS["travertine"],
                         (4, ts * 3, w - 8, h - ts * 4), 1)
        
        cls._cache["temple_podium"] = surf
    
    @classmethod
    def _gen_basilica(cls, ts):
        """Basilica Julia — long rectangular basilica on south side of Forum."""
        w, h = 16 * ts, 6 * ts
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        
        # Main structure
        pygame.draw.rect(surf, COLORS["travertine"], (0, 0, w, h))
        pygame.draw.rect(surf, COLORS["marble_cream"], (2, 2, w - 4, h - 4))
        
        # Central nave
        nave_w = w // 3
        pygame.draw.rect(surf, COLORS["marble_white"],
                         (w // 2 - nave_w // 2, 6, nave_w, h - 12))
        
        # Four aisles (column rows creating 5 aisles)
        for row_idx, row_frac in enumerate([0.2, 0.35, 0.65, 0.8]):
            row_y = int(h * row_frac)
            for i in range(14):
                cx = int(8 + i * (w - 16) / 13)
                pygame.draw.circle(surf, COLORS["marble_white"], (cx, row_y), 2)
                pygame.draw.circle(surf, COLORS["shadow"], (cx, row_y), 2, 1)
        
        # Steps along the front (north side)
        pygame.draw.rect(surf, COLORS["steps"], (0, 0, w, 3))
        
        # Border
        pygame.draw.rect(surf, COLORS["shadow"], (0, 0, w, h), 1)
        
        cls._cache["basilica"] = surf
    
    @classmethod
    def _gen_basilica_aemilia(cls, ts):
        """Basilica Aemilia — on the north side of the Forum."""
        w, h = 14 * ts, 5 * ts
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        
        # Main structure
        pygame.draw.rect(surf, COLORS["brick_roman"], (0, 0, w, h))
        pygame.draw.rect(surf, COLORS["marble_cream"], (2, 2, w - 4, h - 4))
        
        # Tabernae along the front (shops)
        for i in range(10):
            tx = 4 + i * (w - 8) // 10
            tw = (w - 8) // 10 - 2
            pygame.draw.rect(surf, COLORS["shadow"], (tx, h - 12, tw, 10))
            pygame.draw.rect(surf, COLORS["travertine"], (tx, h - 12, tw, 10), 1)
        
        # Column rows
        for i in range(12):
            cx = int(6 + i * (w - 12) / 11)
            pygame.draw.circle(surf, COLORS["marble_white"], (cx, h // 3), 2)
            pygame.draw.circle(surf, COLORS["shadow"], (cx, h // 3), 2, 1)
            pygame.draw.circle(surf, COLORS["marble_white"], (cx, h * 2 // 3), 2)
            pygame.draw.circle(surf, COLORS["shadow"], (cx, h * 2 // 3), 2, 1)
        
        # Front portico columns
        for i in range(12):
            cx = int(6 + i * (w - 12) / 11)
            pygame.draw.circle(surf, COLORS["marble_cream"], (cx, h - 3), 2)
        
        pygame.draw.rect(surf, COLORS["shadow"], (0, 0, w, h), 1)
        
        cls._cache["basilica_aemilia"] = surf
    
    @classmethod
    def _gen_rostra(cls, ts):
        """Raised speaker's platform with ship-prow decorations."""
        w, h = 5 * ts, 3 * ts
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        
        # Platform
        pygame.draw.rect(surf, COLORS["travertine"], (0, h // 4, w, h * 3 // 4))
        pygame.draw.rect(surf, COLORS["marble_cream"], (2, h // 4 + 2, w - 4, h * 3 // 4 - 4))
        
        # Ship prow decorations (the rostra — pointed bronze beaks)
        for i in range(4):
            px = int(6 + i * (w - 12) / 3)
            pygame.draw.polygon(surf, COLORS["pompeii_yellow"],
                                [(px, h - 4), (px - 4, h), (px + 4, h)])
            pygame.draw.polygon(surf, COLORS["legionary_gold"],
                                [(px, h - 4), (px - 4, h), (px + 4, h)], 1)
        
        # Railing/balustrade on top
        pygame.draw.rect(surf, COLORS["marble_white"], (2, h // 4, w - 4, 3))
        
        cls._cache["rostra"] = surf
    
    @classmethod
    def _gen_curia(cls, ts):
        """Curia Julia — Senate House, tall rectangular building."""
        w, h = 4 * ts, 5 * ts
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        
        # Tall brick walls
        pygame.draw.rect(surf, COLORS["brick_roman"], (0, 0, w, h))
        pygame.draw.rect(surf, COLORS["plaster_ochre"], (3, 3, w - 6, h - 6))
        
        # Main entrance (large bronze doors)
        door_w = w // 3
        pygame.draw.rect(surf, COLORS["wood_dark"],
                         (w // 2 - door_w // 2, 0, door_w, ts))
        pygame.draw.rect(surf, COLORS["pompeii_yellow"],
                         (w // 2 - door_w // 2, 0, door_w, ts), 1)
        
        # Interior seating (tiered benches along walls)
        pygame.draw.rect(surf, COLORS["marble_cream"],
                         (5, ts + 2, w - 10, h - ts - 6))
        # Bench rows
        for i in range(4):
            by = ts + 6 + i * (h - ts - 12) // 4
            pygame.draw.rect(surf, COLORS["travertine"],
                             (6, by, 6, (h - ts - 12) // 4 - 2))
            pygame.draw.rect(surf, COLORS["travertine"],
                             (w - 12, by, 6, (h - ts - 12) // 4 - 2))
        
        # Apex/ridge hint
        pygame.draw.rect(surf, COLORS["terracotta_roof"], (0, 0, w, 2))
        
        cls._cache["curia"] = surf
    
    @classmethod
    def _gen_tabularium(cls, ts):
        """Tabularium — state archive on the slope of the Capitoline, arcaded facade."""
        w, h = 12 * ts, 4 * ts
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        
        # Main structure (high substructure)
        pygame.draw.rect(surf, COLORS["concrete_roman"], (0, 0, w, h))
        pygame.draw.rect(surf, COLORS["travertine"], (2, 2, w - 4, h - 4))
        
        # Arcade of arches (11 arches)
        arch_w = (w - 8) // 11
        for i in range(11):
            ax = 4 + i * arch_w
            # Arch opening
            pygame.draw.rect(surf, COLORS["shadow"],
                             (ax + 2, h // 3, arch_w - 4, h * 2 // 3 - 4))
            # Arch top (semi-circular hint)
            pygame.draw.circle(surf, COLORS["shadow"],
                               (ax + arch_w // 2, h // 3), (arch_w - 4) // 2)
            # Pilaster between arches
            pygame.draw.rect(surf, COLORS["marble_cream"],
                             (ax, 2, 3, h - 4))
        
        # Cornice
        pygame.draw.rect(surf, COLORS["marble_white"], (0, 0, w, 3))
        
        cls._cache["tabularium"] = surf
    
    @classmethod
    def _gen_palace(cls, ts):
        """Domus Tiberiana — Imperial Palace on the Palatine."""
        w, h = 14 * ts, 10 * ts
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        
        # Main block
        pygame.draw.rect(surf, COLORS["brick_roman"], (0, 0, w, h))
        pygame.draw.rect(surf, COLORS["plaster_ochre"], (3, 3, w - 6, h - 6))
        
        # Central courtyard (peristyle)
        court_x = w // 4
        court_y = h // 4
        court_w = w // 2
        court_h = h // 2
        pygame.draw.rect(surf, COLORS["garden"], (court_x, court_y, court_w, court_h))
        pygame.draw.rect(surf, COLORS["marble_cream"],
                         (court_x, court_y, court_w, court_h), 2)
        
        # Courtyard columns
        for i in range(6):
            cx = int(court_x + 4 + i * (court_w - 8) / 5)
            pygame.draw.circle(surf, COLORS["marble_white"], (cx, court_y + 3), 2)
            pygame.draw.circle(surf, COLORS["marble_white"], (cx, court_y + court_h - 3), 2)
        for i in range(4):
            cy = int(court_y + 4 + i * (court_h - 8) / 3)
            pygame.draw.circle(surf, COLORS["marble_white"], (court_x + 3, cy), 2)
            pygame.draw.circle(surf, COLORS["marble_white"], (court_x + court_w - 3, cy), 2)
        
        # Fountain in courtyard center
        pygame.draw.circle(surf, COLORS["water"], (w // 2, h // 2), 5)
        pygame.draw.circle(surf, COLORS["water_shallow"], (w // 2, h // 2), 7, 1)
        
        # Room divisions
        for rx in [w // 4, w * 3 // 4]:
            pygame.draw.line(surf, COLORS["shadow"], (rx, 3), (rx, court_y), 1)
            pygame.draw.line(surf, COLORS["shadow"], (rx, court_y + court_h), (rx, h - 3), 1)
        for ry_frac in [0.15, 0.85]:
            ry = int(h * ry_frac)
            pygame.draw.line(surf, COLORS["shadow"], (3, ry), (court_x, ry), 1)
            pygame.draw.line(surf, COLORS["shadow"], (court_x + court_w, ry), (w - 3, ry), 1)
        
        # Entrance portico
        pygame.draw.rect(surf, COLORS["marble_cream"], (w // 2 - 8, 0, 16, 4))
        
        cls._cache["palace"] = surf
    
    @classmethod
    def _gen_domus_augustana(cls, ts):
        """Domus Augustana — official imperial residence, larger complex."""
        w, h = 18 * ts, 16 * ts
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        
        # Main block
        pygame.draw.rect(surf, COLORS["brick_roman"], (0, 0, w, h))
        pygame.draw.rect(surf, COLORS["plaster_white"], (3, 3, w - 6, h - 6))
        
        # Upper level peristyle (north)
        court1_x, court1_y = w // 6, h // 8
        court1_w, court1_h = w * 2 // 3, h // 3
        pygame.draw.rect(surf, COLORS["garden"],
                         (court1_x, court1_y, court1_w, court1_h))
        pygame.draw.rect(surf, COLORS["marble_cream"],
                         (court1_x, court1_y, court1_w, court1_h), 2)
        # Pool in upper court
        pygame.draw.rect(surf, COLORS["water"],
                         (court1_x + court1_w // 4, court1_y + court1_h // 3,
                          court1_w // 2, court1_h // 3))
        
        # Lower level peristyle (south)
        court2_x, court2_y = w // 5, h * 3 // 5
        court2_w, court2_h = w * 3 // 5, h * 2 // 7
        pygame.draw.rect(surf, COLORS["garden"],
                         (court2_x, court2_y, court2_w, court2_h))
        pygame.draw.rect(surf, COLORS["marble_cream"],
                         (court2_x, court2_y, court2_w, court2_h), 2)
        
        # Columns around courtyards
        for court_data in [(court1_x, court1_y, court1_w, court1_h),
                           (court2_x, court2_y, court2_w, court2_h)]:
            cx, cy, cw, ch = court_data
            for i in range(8):
                px = int(cx + 4 + i * (cw - 8) / 7)
                pygame.draw.circle(surf, COLORS["marble_white"], (px, cy + 3), 2)
                pygame.draw.circle(surf, COLORS["marble_white"], (px, cy + ch - 3), 2)
        
        # Room divisions (creating triclinium, tablinum, etc.)
        for dx in range(3):
            rx = w // 4 + dx * w // 4
            pygame.draw.line(surf, COLORS["shadow"],
                             (rx, 3), (rx, court1_y - 2), 1)
        
        # Throne room (large central room between courts)
        throne_y = court1_y + court1_h + 4
        throne_h = court2_y - throne_y - 4
        pygame.draw.rect(surf, COLORS["marble_white"],
                         (w // 3, throne_y, w // 3, throne_h))
        pygame.draw.rect(surf, COLORS["pompeii_red"],
                         (w // 3, throne_y, w // 3, throne_h), 1)
        
        # Outer wall detail
        pygame.draw.rect(surf, COLORS["brick_dark"], (0, 0, w, h), 2)
        
        cls._cache["domus_augustana"] = surf
    
    @classmethod
    def _gen_stadium(cls, ts):
        """Stadium of Domitian on the Palatine — hippodrome-shaped garden."""
        w, h = 5 * ts, 18 * ts
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        
        # Outer wall
        pygame.draw.rect(surf, COLORS["brick_roman"], (0, 0, w, h))
        
        # Rounded ends
        pygame.draw.ellipse(surf, COLORS["brick_roman"], (0, -ts, w, ts * 2))
        pygame.draw.ellipse(surf, COLORS["brick_roman"], (0, h - ts, w, ts * 2))
        
        # Inner garden area
        pygame.draw.rect(surf, COLORS["garden"], (4, ts, w - 8, h - ts * 2))
        pygame.draw.ellipse(surf, COLORS["garden"], (4, 0, w - 8, ts * 2))
        pygame.draw.ellipse(surf, COLORS["garden"], (4, h - ts * 2, w - 8, ts * 2))
        
        # Central spine (like a circus spina)
        pygame.draw.rect(surf, COLORS["travertine"],
                         (w // 2 - 2, ts * 3, 4, h - ts * 6))
        
        # Perimeter seats/columns
        for i in range(12):
            sy = int(ts + i * (h - ts * 2) / 11)
            pygame.draw.circle(surf, COLORS["marble_cream"], (6, sy), 2)
            pygame.draw.circle(surf, COLORS["marble_cream"], (w - 6, sy), 2)
        
        # Niche at south end
        pygame.draw.rect(surf, COLORS["marble_white"],
                         (w // 2 - 4, h - ts - 2, 8, ts))
        
        cls._cache["stadium"] = surf
    
    @classmethod
    def _gen_triumphal_arch(cls, ts):
        """Single-bay triumphal arch (Arch of Titus)."""
        w, h = 3 * ts, 2 * ts
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        
        # Main structure
        pygame.draw.rect(surf, COLORS["marble_cream"], (0, 0, w, h))
        
        # Central passage
        pw = w // 3
        pygame.draw.rect(surf, COLORS["shadow"], (w // 2 - pw // 2, 3, pw, h - 3))
        
        # Engaged columns on sides
        pygame.draw.rect(surf, COLORS["marble_white"], (2, 0, 5, h))
        pygame.draw.rect(surf, COLORS["marble_white"], (w - 7, 0, 5, h))
        
        # Attic (top section with inscription)
        pygame.draw.rect(surf, COLORS["marble_white"], (0, 0, w, 4))
        pygame.draw.rect(surf, COLORS["pompeii_yellow"], (4, 1, w - 8, 2))
        
        # Relief panels
        pygame.draw.rect(surf, COLORS["travertine"],
                         (3, h // 3, 3, h // 3))
        pygame.draw.rect(surf, COLORS["travertine"],
                         (w - 6, h // 3, 3, h // 3))
        
        cls._cache["triumphal_arch"] = surf
    
    @classmethod
    def _gen_arch_large(cls, ts):
        """Triple-bay arch (Arch of Constantine / Arch of Septimius Severus)."""
        w, h = 5 * ts, 3 * ts
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        
        # Main structure
        pygame.draw.rect(surf, COLORS["marble_cream"], (0, 0, w, h))
        
        # Three passages
        pw_center = w // 5
        pw_side = w // 7
        # Center passage
        pygame.draw.rect(surf, COLORS["shadow"],
                         (w // 2 - pw_center // 2, 5, pw_center, h - 5))
        # Side passages
        pygame.draw.rect(surf, COLORS["shadow"],
                         (4, 8, pw_side, h - 8))
        pygame.draw.rect(surf, COLORS["shadow"],
                         (w - 4 - pw_side, 8, pw_side, h - 8))
        
        # Columns between passages
        col_positions = [4 + pw_side + 2, w // 2 - pw_center // 2 - 4,
                         w // 2 + pw_center // 2 + 1, w - 4 - pw_side - 5]
        for cx in col_positions:
            pygame.draw.rect(surf, COLORS["marble_white"], (cx, 3, 3, h - 3))
        
        # Attic
        pygame.draw.rect(surf, COLORS["marble_white"], (0, 0, w, 5))
        pygame.draw.rect(surf, COLORS["pompeii_yellow"], (6, 1, w - 12, 3))
        
        cls._cache["arch_large"] = surf
    
    @classmethod
    def _gen_temple_venus_roma(cls, ts):
        """Temple of Venus and Roma — double temple, back to back."""
        w, h = 8 * ts, 14 * ts
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        
        # Huge platform
        pygame.draw.rect(surf, COLORS["travertine"], (0, 0, w, h))
        pygame.draw.rect(surf, COLORS["marble_cream"], (3, 3, w - 6, h - 6))
        
        # Two back-to-back cellas
        cella_h = h // 2 - 4
        # North cella (Temple of Roma)
        pygame.draw.rect(surf, COLORS["marble_white"],
                         (ts, 4, w - ts * 2, cella_h))
        pygame.draw.rect(surf, COLORS["pompeii_red"],
                         (ts, 4, w - ts * 2, cella_h), 1)
        # Apse
        pygame.draw.circle(surf, COLORS["marble_white"],
                           (w // 2, 4 + cella_h - 2), (w - ts * 2) // 3)
        
        # South cella (Temple of Venus)
        pygame.draw.rect(surf, COLORS["marble_white"],
                         (ts, h // 2 + 4, w - ts * 2, cella_h))
        pygame.draw.rect(surf, COLORS["pompeii_red"],
                         (ts, h // 2 + 4, w - ts * 2, cella_h), 1)
        # Apse
        pygame.draw.circle(surf, COLORS["marble_white"],
                           (w // 2, h // 2 + 4 + 2), (w - ts * 2) // 3)
        
        # Peristyle columns all around
        for i in range(10):
            cy = int(6 + i * (h - 12) / 9)
            pygame.draw.circle(surf, COLORS["marble_cream"], (4, cy), 2)
            pygame.draw.circle(surf, COLORS["marble_cream"], (w - 4, cy), 2)
        for i in range(6):
            cx = int(6 + i * (w - 12) / 5)
            pygame.draw.circle(surf, COLORS["marble_cream"], (cx, 4), 2)
            pygame.draw.circle(surf, COLORS["marble_cream"], (cx, h - 4), 2)
        
        cls._cache["temple_venus_roma"] = surf
    
    @classmethod
    def _gen_circus_maximus(cls, ts):
        """Circus Maximus — long chariot racing track."""
        w, h = 40 * ts, 8 * ts
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        
        # Outer structure (seating)
        pygame.draw.rect(surf, COLORS["travertine"], (0, 0, w, h))
        # Rounded east end
        pygame.draw.ellipse(surf, COLORS["travertine"],
                            (w - h, 0, h, h))
        
        # Track (sand)
        margin = ts
        pygame.draw.rect(surf, COLORS["circus_sand"],
                         (margin, margin, w - margin * 2 - h // 2, h - margin * 2))
        pygame.draw.ellipse(surf, COLORS["circus_sand"],
                            (w - h + margin // 2, margin, h - margin, h - margin * 2))
        
        # Spina (central divider)
        spina_x = ts * 6
        spina_w = w - ts * 16
        spina_y = h // 2 - 2
        pygame.draw.rect(surf, COLORS["circus_spina"],
                         (spina_x, spina_y, spina_w, 4))
        
        # Meta (turning posts)
        pygame.draw.circle(surf, COLORS["marble_white"],
                           (spina_x, h // 2), 4)
        pygame.draw.circle(surf, COLORS["marble_white"],
                           (spina_x + spina_w, h // 2), 4)
        
        # Obelisk in center of spina
        pygame.draw.rect(surf, COLORS["pompeii_red"],
                         (w // 2 - 2, spina_y - 2, 4, 8))
        
        # Starting gates (carceres) at west end
        pygame.draw.rect(surf, COLORS["marble_cream"], (0, 0, ts * 2, h))
        for i in range(6):
            gy = 4 + i * (h - 8) // 6
            pygame.draw.rect(surf, COLORS["shadow"],
                             (2, gy, ts * 2 - 4, (h - 8) // 6 - 2))
        
        # Seating tier lines
        for offset in [margin // 2, margin + 2]:
            pygame.draw.rect(surf, COLORS["shadow"],
                             (0, offset, w - h // 2, 1))
            pygame.draw.rect(surf, COLORS["shadow"],
                             (0, h - offset, w - h // 2, 1))
        
        cls._cache["circus_maximus"] = surf
    
    @classmethod
    def _gen_forum_imperiale(cls, ts):
        """Generic Imperial Forum enclosure (Forum of Augustus, Trajan, etc.)."""
        w, h = 8 * ts, 10 * ts
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        
        # Enclosure walls
        pygame.draw.rect(surf, COLORS["concrete_roman"], (0, 0, w, h))
        pygame.draw.rect(surf, COLORS["marble_cream"], (3, 3, w - 6, h - 6))
        
        # Central open plaza
        pygame.draw.rect(surf, COLORS["forum_floor"],
                         (ts, ts, w - ts * 2, h - ts * 2))
        
        # Temple at the back
        temple_w = w * 2 // 3
        pygame.draw.rect(surf, COLORS["marble_white"],
                         (w // 2 - temple_w // 2, 4, temple_w, ts * 3))
        # Temple columns
        for i in range(5):
            cx = int(w // 2 - temple_w // 2 + 4 + i * (temple_w - 8) / 4)
            pygame.draw.circle(surf, COLORS["marble_white"],
                               (cx, ts * 3 + 2), 2)
        
        # Portico columns along sides
        for i in range(6):
            cy = int(ts * 2 + i * (h - ts * 4) / 5)
            pygame.draw.circle(surf, COLORS["marble_cream"], (ts + 2, cy), 2)
            pygame.draw.circle(surf, COLORS["marble_cream"], (w - ts - 2, cy), 2)
        
        # Exedrae (semicircular niches in walls)
        pygame.draw.arc(surf, COLORS["shadow"],
                        (-ts, h // 3, ts * 2, ts * 2), -1.57, 1.57, 2)
        pygame.draw.arc(surf, COLORS["shadow"],
                        (w - ts, h // 3, ts * 2, ts * 2), 1.57, 4.71, 2)
        
        # Equestrian statue in center
        pygame.draw.circle(surf, COLORS["pompeii_yellow"],
                           (w // 2, h // 2), 3)
        
        cls._cache["forum_imperiale"] = surf
    
    @classmethod
    def _gen_markets_trajan(cls, ts):
        """Markets of Trajan — semicircular multi-level market complex."""
        w, h = 10 * ts, 8 * ts
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        
        # Semicircular shape (exedra)
        pygame.draw.ellipse(surf, COLORS["brick_roman"],
                            (-w // 2, 0, w * 3 // 2, h * 2))
        pygame.draw.ellipse(surf, COLORS["plaster_ochre"],
                            (-w // 2 + 3, 3, w * 3 // 2 - 6, h * 2 - 6))
        
        # Cut off the bottom half (we only want top semicircle)
        pygame.draw.rect(surf, (0, 0, 0, 0), (0, h, w, h),
                         )
        
        # Multiple levels of tabernae (shops)
        for level in range(3):
            ly = 6 + level * (h // 3)
            for i in range(6 - level):
                sx = int(ts + level * ts // 2 + i * (w - ts * 2 - level * ts) / max(1, 6 - level - 1))
                sw = max(4, (w - ts * 3) // 7)
                pygame.draw.rect(surf, COLORS["shadow"],
                                 (sx, ly, sw - 2, h // 3 - 4))
                pygame.draw.rect(surf, COLORS["travertine"],
                                 (sx, ly, sw - 2, h // 3 - 4), 1)
        
        # Great hall
        pygame.draw.rect(surf, COLORS["marble_cream"],
                         (w // 3, h // 4, w // 3, h // 2))
        pygame.draw.rect(surf, COLORS["shadow"],
                         (w // 3, h // 4, w // 3, h // 2), 1)
        
        cls._cache["markets_trajan"] = surf
    
    @classmethod
    def _gen_regia(cls, ts):
        """Regia — ancient royal/religious building, small and trapezoidal."""
        w, h = 3 * ts, 3 * ts
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        
        # Irregular trapezoidal shape
        points = [(2, 2), (w - 4, 0), (w - 2, h - 2), (0, h - 4)]
        pygame.draw.polygon(surf, COLORS["travertine"], points)
        
        inset = [(6, 6), (w - 8, 4), (w - 6, h - 6), (4, h - 8)]
        pygame.draw.polygon(surf, COLORS["marble_cream"], inset)
        
        # Internal divisions
        pygame.draw.line(surf, COLORS["shadow"],
                         (w // 3, 4), (w // 3, h - 4), 1)
        
        cls._cache["regia"] = surf
    
    # ----------------------------------------------------------------
    # Residential & Commercial
    # ----------------------------------------------------------------
    
    @classmethod
    def _gen_insula(cls, ts):
        """Multi-story tenement block."""
        w, h = 3 * ts, 3 * ts
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        
        # Walls
        pygame.draw.rect(surf, COLORS["brick_roman"], (0, 0, w, h))
        pygame.draw.rect(surf, COLORS["plaster_ochre"], (2, 2, w - 4, h - 4))
        
        # Windows (grid pattern showing multiple floors)
        for row in range(3):
            for col in range(2):
                wx = 5 + col * (w - 14)
                wy = 4 + row * (h - 10) // 2
                pygame.draw.rect(surf, COLORS["shadow"], (wx, wy, 4, 4))
                pygame.draw.rect(surf, COLORS["pompeii_yellow"], (wx, wy, 4, 4), 1)
        
        # Door
        pygame.draw.rect(surf, COLORS["wood_dark"], (w // 2 - 3, h - 8, 6, 8))
        
        # Clotheslines (characteristic detail)
        pygame.draw.line(surf, COLORS["plaster_white"],
                         (2, h // 2), (w - 2, h // 2), 1)
        
        cls._cache["insula"] = surf
    
    @classmethod
    def _gen_domus(cls, ts):
        """Wealthy Roman townhouse with atrium."""
        w, h = 4 * ts, 3 * ts
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        
        # Outer walls
        pygame.draw.rect(surf, COLORS["brick_roman"], (0, 0, w, h))
        pygame.draw.rect(surf, COLORS["plaster_white"], (2, 2, w - 4, h - 4))
        
        # Atrium (central open area)
        atrium_x = w // 3
        atrium_w = w // 3
        atrium_y = h // 4
        atrium_h = h // 2
        pygame.draw.rect(surf, COLORS["garden"],
                         (atrium_x, atrium_y, atrium_w, atrium_h))
        
        # Impluvium (rain pool in atrium)
        pool_cx = atrium_x + atrium_w // 2
        pool_cy = atrium_y + atrium_h // 2
        pygame.draw.rect(surf, COLORS["water"],
                         (pool_cx - 3, pool_cy - 2, 6, 4))
        
        # Entrance
        pygame.draw.rect(surf, COLORS["wood_dark"], (w // 2 - 3, 0, 6, 3))
        
        # Terracotta roof hint
        pygame.draw.rect(surf, COLORS["terracotta_roof"], (0, 0, w, 2))
        pygame.draw.rect(surf, COLORS["terracotta_roof"], (0, h - 2, w, 2))
        
        cls._cache["domus"] = surf
    
    @classmethod
    def _gen_house(cls, ts):
        """Simple small house."""
        w, h = 2 * ts, 2 * ts
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        
        pygame.draw.rect(surf, COLORS["brick_roman"], (0, 0, w, h))
        pygame.draw.rect(surf, COLORS["plaster_ochre"], (2, 2, w - 4, h - 4))
        pygame.draw.rect(surf, COLORS["terracotta_roof"], (0, 0, w, 3))
        pygame.draw.rect(surf, COLORS["wood_dark"], (w // 2 - 2, h - 5, 4, 5))
        
        cls._cache["house_simple"] = surf
    
    @classmethod
    def _gen_taberna(cls, ts):
        """Roman shop / tavern."""
        w, h = 2 * ts, 2 * ts
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        
        pygame.draw.rect(surf, COLORS["brick_dark"], (0, 0, w, h))
        pygame.draw.rect(surf, COLORS["plaster_ochre"], (2, 2, w - 4, h - 4))
        
        # Wide shop front opening
        pygame.draw.rect(surf, COLORS["shadow"], (3, 0, w - 6, h // 2))
        
        # Counter
        pygame.draw.rect(surf, COLORS["travertine"], (3, h // 2 - 2, w - 6, 3))
        
        # Awning
        pygame.draw.rect(surf, COLORS["pompeii_red"], (0, 0, w, 3))
        
        cls._cache["taberna"] = surf
    
    @classmethod
    def _gen_market_stall(cls, ts):
        """Open-air market stall."""
        w, h = 3 * ts, 2 * ts
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        
        # Wooden frame
        pygame.draw.rect(surf, COLORS["wood_beam"], (0, 0, w, 2))
        pygame.draw.rect(surf, COLORS["wood_beam"], (0, 0, 2, h))
        pygame.draw.rect(surf, COLORS["wood_beam"], (w - 2, 0, 2, h))
        
        # Canopy
        for i in range(0, w, 6):
            c = COLORS["pompeii_red"] if (i // 6) % 2 == 0 else COLORS["pompeii_yellow"]
            pygame.draw.rect(surf, c, (i, 0, 6, 4))
        
        # Goods on counter
        pygame.draw.rect(surf, COLORS["wood_beam"], (2, h // 2, w - 4, 2))
        colors = [COLORS["pompeii_red"], COLORS["pompeii_yellow"], COLORS["pompeii_green"]]
        for i in range(4):
            c = colors[i % len(colors)]
            pygame.draw.circle(surf, c, (6 + i * 8, h // 2 + 5), 2)
        
        cls._cache["market_stall"] = surf
    
    @classmethod
    def _gen_bathhouse(cls, ts):
        """Public baths."""
        w, h = 6 * ts, 5 * ts
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        
        # Outer walls
        pygame.draw.rect(surf, COLORS["brick_roman"], (0, 0, w, h))
        pygame.draw.rect(surf, COLORS["plaster_white"], (3, 3, w - 6, h - 6))
        
        # Caldarium (hot pool)
        pool_w = w // 2
        pool_h = h // 2
        pygame.draw.rect(surf, COLORS["water"],
                         (w // 2 - pool_w // 2, h // 2 - pool_h // 2,
                          pool_w, pool_h))
        pygame.draw.rect(surf, COLORS["marble_cream"],
                         (w // 2 - pool_w // 2, h // 2 - pool_h // 2,
                          pool_w, pool_h), 2)
        
        # Frigidarium (cold pool)
        pygame.draw.rect(surf, COLORS["water_shallow"],
                         (w - 18, 6, 12, 10))
        pygame.draw.rect(surf, COLORS["marble_cream"],
                         (w - 18, 6, 12, 10), 1)
        
        # Tepidarium
        pygame.draw.rect(surf, COLORS["water_shallow"],
                         (6, 6, 12, 10))
        
        cls._cache["bathhouse"] = surf
    
    @classmethod
    def _gen_ludus(cls, ts):
        """Gladiator training school (Ludus Magnus)."""
        w, h = 10 * ts, 10 * ts
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        
        # Outer walls
        pygame.draw.rect(surf, COLORS["brick_dark"], (0, 0, w, h))
        pygame.draw.rect(surf, COLORS["plaster_ochre"], (3, 3, w - 6, h - 6))
        
        # Central elliptical training arena (miniature amphitheatre)
        cx, cy = w // 2, h // 2
        rx, ry = w // 3, h // 3
        # Seating
        pygame.draw.ellipse(surf, COLORS["travertine"],
                            (cx - rx - 6, cy - ry - 6, (rx + 6) * 2, (ry + 6) * 2))
        # Arena floor
        pygame.draw.ellipse(surf, COLORS["sand_arena"],
                            (cx - rx, cy - ry, rx * 2, ry * 2))
        pygame.draw.ellipse(surf, COLORS["brick_dark"],
                            (cx - rx, cy - ry, rx * 2, ry * 2), 2)
        
        # Cell blocks (barracks) around edges
        for i in range(3):
            # Left cells
            ry_cell = 8 + i * (h - 16) // 3
            pygame.draw.rect(surf, COLORS["shadow"],
                             (4, ry_cell, ts * 2, (h - 20) // 3))
            pygame.draw.rect(surf, COLORS["brick_roman"],
                             (4, ry_cell, ts * 2, (h - 20) // 3), 1)
            # Right cells
            pygame.draw.rect(surf, COLORS["shadow"],
                             (w - 4 - ts * 2, ry_cell, ts * 2, (h - 20) // 3))
            pygame.draw.rect(surf, COLORS["brick_roman"],
                             (w - 4 - ts * 2, ry_cell, ts * 2, (h - 20) // 3), 1)
        
        # Connecting tunnel (to Colosseum)
        pygame.draw.rect(surf, COLORS["shadow"], (0, cy - 3, 4, 6))
        
        cls._cache["ludus"] = surf
    
    @classmethod
    def _gen_porticus(cls, ts):
        """Covered colonnade/portico."""
        w, h = 8 * ts, 2 * ts
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        
        # Roof
        pygame.draw.rect(surf, COLORS["terracotta_roof"], (0, 0, w, 3))
        
        # Columns
        for i in range(10):
            cx = int(4 + i * (w - 8) / 9)
            pygame.draw.circle(surf, COLORS["marble_cream"], (cx, h // 2), ts // 4)
            pygame.draw.circle(surf, COLORS["shadow"], (cx, h // 2), ts // 4, 1)
        
        # Base
        pygame.draw.rect(surf, COLORS["travertine"], (0, h - 3, w, 3))
        
        cls._cache["porticus"] = surf
    
    @classmethod
    def _gen_theatre(cls, ts):
        """Theatre of Marcellus — semicircular theatre."""
        w, h = 10 * ts, 6 * ts
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        
        # Semicircular cavea
        pygame.draw.ellipse(surf, COLORS["travertine"],
                            (0, 0, w, h * 2))
        pygame.draw.ellipse(surf, COLORS["marble_cream"],
                            (3, 3, w - 6, h * 2 - 6))
        
        # Orchestra (semicircular floor)
        orch_r = w // 4
        pygame.draw.ellipse(surf, COLORS["forum_floor"],
                            (w // 2 - orch_r, h // 4, orch_r * 2, orch_r))
        
        # Scaenae frons (stage building)
        pygame.draw.rect(surf, COLORS["marble_white"],
                         (w // 6, 0, w * 2 // 3, ts))
        
        # Seating tier lines
        for ring in range(3):
            r = w // 3 + ring * ts
            pygame.draw.ellipse(surf, COLORS["shadow"],
                                (w // 2 - r, h // 2 - r // 2, r * 2, r), 1)
        
        # Outer arches
        for angle in range(0, 180, 12):
            rad = math.radians(angle)
            ax = int(w // 2 + (w // 2 - 4) * math.cos(rad))
            ay = int(h + (h - 4) * math.sin(rad) * -1)
            if 0 < ay < h:
                pygame.draw.circle(surf, COLORS["shadow"], (ax, ay), 2)
        
        cls._cache["theatre"] = surf
    
    # ----------------------------------------------------------------
    # Infrastructure
    # ----------------------------------------------------------------
    
    @classmethod
    def _gen_fountain(cls, ts):
        """Simple public fountain."""
        surf = pygame.Surface((ts, ts), pygame.SRCALPHA)
        cx, cy = ts // 2, ts // 2
        
        # Basin
        pygame.draw.circle(surf, COLORS["travertine"], (cx, cy), ts // 3)
        pygame.draw.circle(surf, COLORS["water"], (cx, cy), ts // 4)
        
        # Center spout
        pygame.draw.circle(surf, COLORS["marble_white"], (cx, cy), 2)
        
        cls._cache["fountain"] = surf
    
    @classmethod
    def _gen_fountain_large(cls, ts):
        """Meta Sudans — large conical fountain near the Colosseum."""
        size = 3 * ts
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        cx, cy = size // 2, size // 2
        
        # Large basin
        pygame.draw.circle(surf, COLORS["travertine"], (cx, cy), size // 2 - 2)
        pygame.draw.circle(surf, COLORS["water"], (cx, cy), size // 3)
        
        # Central cone (tall conical structure)
        pygame.draw.circle(surf, COLORS["concrete_roman"], (cx, cy), size // 5)
        pygame.draw.circle(surf, COLORS["marble_cream"], (cx, cy), size // 7)
        pygame.draw.circle(surf, COLORS["marble_white"], (cx, cy), size // 10)
        
        # Water ripples
        for r in range(3):
            radius = size // 4 + r * 4
            pygame.draw.circle(surf, COLORS["water_shallow"], (cx, cy), radius, 1)
        
        cls._cache["fountain_large"] = surf
    
    @classmethod
    def _gen_column(cls, ts):
        """Single standing column."""
        surf = pygame.Surface((ts, ts), pygame.SRCALPHA)
        cx, cy = ts // 2, ts // 2
        
        # Column shadow
        pygame.draw.circle(surf, COLORS["shadow"], (cx + 1, cy + 1), ts // 4)
        # Column
        pygame.draw.circle(surf, COLORS["marble_white"], (cx, cy), ts // 4)
        pygame.draw.circle(surf, COLORS["marble_cream"], (cx, cy), ts // 4, 1)
        
        cls._cache["column"] = surf
    
    @classmethod
    def _gen_statue(cls, ts):
        """Roman statue on pedestal."""
        surf = pygame.Surface((ts, ts), pygame.SRCALPHA)
        cx, cy = ts // 2, ts // 2
        
        # Pedestal
        pygame.draw.rect(surf, COLORS["travertine"], (cx - 4, cy + 1, 8, 6))
        
        # Figure (simple)
        pygame.draw.rect(surf, COLORS["marble_white"], (cx - 2, cy - 4, 4, 6))
        pygame.draw.circle(surf, COLORS["marble_white"], (cx, cy - 5), 2)
        
        cls._cache["statue"] = surf
    
    @classmethod
    def _gen_statue_equestrian(cls, ts):
        """Equestrian statue (like Marcus Aurelius)."""
        size = 2 * ts
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        cx, cy = size // 2, size // 2
        
        # Pedestal
        pygame.draw.rect(surf, COLORS["travertine"],
                         (cx - 6, cy + 4, 12, 6))
        
        # Horse body (ellipse)
        pygame.draw.ellipse(surf, COLORS["pompeii_yellow"],
                            (cx - 6, cy - 4, 12, 8))
        
        # Rider
        pygame.draw.rect(surf, COLORS["pompeii_yellow"],
                         (cx - 2, cy - 8, 4, 5))
        pygame.draw.circle(surf, COLORS["pompeii_yellow"], (cx, cy - 9), 2)
        
        cls._cache["statue_equestrian"] = surf
    
    @classmethod
    def _gen_obelisk(cls, ts):
        """Egyptian obelisk (several in Rome)."""
        surf = pygame.Surface((ts, ts * 2), pygame.SRCALPHA)
        cx = ts // 2
        
        # Base
        pygame.draw.rect(surf, COLORS["travertine"],
                         (cx - 5, ts * 2 - 6, 10, 6))
        
        # Obelisk shaft (tapers upward)
        points = [
            (cx - 3, ts * 2 - 6),
            (cx + 3, ts * 2 - 6),
            (cx + 1, 4),
            (cx - 1, 4),
        ]
        pygame.draw.polygon(surf, COLORS["pompeii_red"], points)
        
        # Pyramidion (tip)
        pygame.draw.polygon(surf, COLORS["pompeii_yellow"],
                            [(cx, 0), (cx - 2, 4), (cx + 2, 4)])
        
        cls._cache["obelisk"] = surf
    
    @classmethod
    def _gen_cloaca(cls, ts):
        """Cloaca Maxima entrance — Roman sewer."""
        surf = pygame.Surface((ts, ts), pygame.SRCALPHA)
        
        # Arch opening
        pygame.draw.rect(surf, COLORS["shadow"],
                         (2, ts // 3, ts - 4, ts * 2 // 3))
        pygame.draw.arc(surf, COLORS["travertine"],
                        (2, ts // 6, ts - 4, ts // 2), 0, math.pi, 2)
        
        # Stone frame
        pygame.draw.rect(surf, COLORS["travertine"],
                         (0, ts // 3, 3, ts * 2 // 3))
        pygame.draw.rect(surf, COLORS["travertine"],
                         (ts - 3, ts // 3, 3, ts * 2 // 3))
        
        cls._cache["cloaca"] = surf
    
    @classmethod
    def _gen_aqueduct(cls, ts):
        """Aqueduct arch section."""
        w, h = ts, ts
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        
        # Pillars
        pygame.draw.rect(surf, COLORS["travertine"], (0, 0, 3, h))
        pygame.draw.rect(surf, COLORS["travertine"], (w - 3, 0, 3, h))
        
        # Arch
        pygame.draw.rect(surf, COLORS["travertine"], (0, 0, w, 4))
        
        # Water channel on top
        pygame.draw.rect(surf, COLORS["water"], (2, 1, w - 4, 2))
        
        # Arch opening
        pygame.draw.rect(surf, COLORS["shadow"], (3, 4, w - 6, h - 4))
        
        cls._cache["aqueduct"] = surf
    
    @classmethod
    def _gen_torch(cls, ts):
        """Wall torch."""
        surf = pygame.Surface((ts, ts), pygame.SRCALPHA)
        cx = ts // 2
        
        # Bracket
        pygame.draw.rect(surf, COLORS["wood_dark"], (cx - 1, ts // 3, 2, ts // 2))
        
        # Flame
        pygame.draw.circle(surf, COLORS["fire_core"], (cx, ts // 3), 3)
        pygame.draw.circle(surf, COLORS["fire_mid"], (cx, ts // 3), 4, 1)
        
        cls._cache["torch"] = surf
    
    # ----------------------------------------------------------------
    # Vegetation
    # ----------------------------------------------------------------
    
    @classmethod
    def _gen_cypress(cls, ts):
        """Tall, narrow Italian cypress tree."""
        surf = pygame.Surface((ts, ts * 2), pygame.SRCALPHA)
        cx = ts // 2
        
        # Trunk
        pygame.draw.rect(surf, COLORS["olive_trunk"], (cx - 1, ts, 2, ts))
        
        # Foliage — tall narrow ellipse
        points = []
        for i in range(20):
            t = i / 19
            x = cx + int(3 * math.sin(t * math.pi))
            y = int(ts * 1.8 * (1 - t))
            points.append((x, y))
        for i in range(19, -1, -1):
            t = i / 19
            x = cx - int(3 * math.sin(t * math.pi))
            y = int(ts * 1.8 * (1 - t))
            points.append((x, y))
        
        if len(points) >= 3:
            pygame.draw.polygon(surf, COLORS["cypress_dark"], points)
            pygame.draw.line(surf, COLORS["cypress_mid"],
                             (cx, 4), (cx, int(ts * 1.5)), 2)
        
        cls._cache["cypress"] = surf
    
    @classmethod
    def _gen_olive_tree(cls, ts):
        """Gnarled olive tree with spreading canopy."""
        surf = pygame.Surface((ts * 2, ts * 2), pygame.SRCALPHA)
        cx, cy = ts, ts
        
        # Trunk (gnarled)
        pygame.draw.line(surf, COLORS["olive_trunk"],
                         (cx, cy + ts // 2), (cx - 2, cy), 3)
        pygame.draw.line(surf, COLORS["olive_trunk"],
                         (cx - 2, cy), (cx + 3, cy - 4), 2)
        
        # Canopy (irregular blob)
        random.seed(42)  # deterministic
        for _ in range(8):
            ox = cx + random.randint(-ts // 2, ts // 2)
            oy = cy - ts // 4 + random.randint(-ts // 3, ts // 3)
            r = random.randint(3, 6)
            pygame.draw.circle(surf, COLORS["olive_leaf"], (ox, oy), r)
        
        cls._cache["olive_tree"] = surf
    
    @classmethod
    def _gen_pine_tree(cls, ts):
        """Italian Stone Pine (Pinus pinea) — umbrella-shaped canopy."""
        surf = pygame.Surface((ts * 2, ts * 2), pygame.SRCALPHA)
        cx, cy = ts, ts
        
        # Tall trunk
        pygame.draw.rect(surf, COLORS["olive_trunk"],
                         (cx - 1, cy, 2, ts))
        
        # Umbrella canopy (flat-topped ellipse)
        pygame.draw.ellipse(surf, COLORS["cypress_dark"],
                            (cx - ts // 2, cy // 2 - ts // 4, ts, ts // 2))
        pygame.draw.ellipse(surf, COLORS["cypress_mid"],
                            (cx - ts // 3, cy // 2 - ts // 5, ts * 2 // 3, ts // 3))
        
        cls._cache["pine_tree"] = surf
    
    @classmethod
    def _gen_shrub(cls, ts):
        """Low Mediterranean shrub."""
        surf = pygame.Surface((ts, ts), pygame.SRCALPHA)
        cx, cy = ts // 2, ts * 2 // 3
        
        pygame.draw.ellipse(surf, COLORS["shrub_green"],
                            (cx - ts // 3, cy - ts // 4, ts * 2 // 3, ts // 2))
        pygame.draw.ellipse(surf, COLORS["cypress_light"],
                            (cx - ts // 5, cy - ts // 5, ts // 3, ts // 4))
        
        cls._cache["shrub"] = surf
    
    @classmethod
    def _gen_flowers(cls, ts):
        """Decorative flower bed."""
        surf = pygame.Surface((ts, ts), pygame.SRCALPHA)
        
        # Green base
        pygame.draw.rect(surf, COLORS["garden"], (1, 1, ts - 2, ts - 2))
        
        # Scattered flowers
        random.seed(99)
        flower_colors = [COLORS["flower_red"], COLORS["flower_yellow"],
                         COLORS["flower_purple"]]
        for _ in range(5):
            fx = random.randint(2, ts - 3)
            fy = random.randint(2, ts - 3)
            fc = random.choice(flower_colors)
            pygame.draw.circle(surf, fc, (fx, fy), 1)
        
        cls._cache["flowers"] = surf
    
    # ----------------------------------------------------------------
    # Ground Decorations
    # ----------------------------------------------------------------
    
    @classmethod
    def _gen_ground_decorations(cls, ts):
        """Generate small overlay decorations for ground tiles."""
        
        # Mosaic pattern
        surf = pygame.Surface((ts, ts), pygame.SRCALPHA)
        for i in range(0, ts, 4):
            for j in range(0, ts, 4):
                if (i + j) % 8 == 0:
                    pygame.draw.rect(surf, (*COLORS["pompeii_red"], 80), (i, j, 3, 3))
                else:
                    pygame.draw.rect(surf, (*COLORS["pompeii_yellow"], 60), (i, j, 3, 3))
        cls._cache["mosaic_simple"] = surf
        
        # Drain grate
        surf = pygame.Surface((ts, ts), pygame.SRCALPHA)
        pygame.draw.rect(surf, (*COLORS["shadow"], 120),
                         (ts // 4, ts // 4, ts // 2, ts // 2))
        for i in range(3):
            y = ts // 4 + 2 + i * (ts // 2 - 4) // 2
            pygame.draw.line(surf, (*COLORS["marble_cream"], 150),
                             (ts // 4 + 1, y), (ts * 3 // 4 - 1, y), 1)
        cls._cache["drain_grate"] = surf
        
        # Inscription
        surf = pygame.Surface((ts, ts), pygame.SRCALPHA)
        pygame.draw.rect(surf, (*COLORS["marble_cream"], 60), (2, 2, ts - 4, ts - 4))
        for i in range(3):
            y = 4 + i * 3
            pygame.draw.line(surf, (*COLORS["shadow"], 100),
                             (4, y), (ts - 4, y), 1)
        cls._cache["inscription"] = surf
        
        # Mosaic border (for Via Sacra)
        surf = pygame.Surface((ts, ts), pygame.SRCALPHA)
        pygame.draw.rect(surf, (*COLORS["pompeii_red"], 40), (0, 0, ts, 2))
        pygame.draw.rect(surf, (*COLORS["pompeii_red"], 40), (0, ts - 2, ts, 2))
        cls._cache["mosaic_border"] = surf
        
        # Cobble worn
        surf = pygame.Surface((ts, ts), pygame.SRCALPHA)
        random.seed(77)
        for _ in range(3):
            cx = random.randint(2, ts - 3)
            cy = random.randint(2, ts - 3)
            pygame.draw.circle(surf, (*COLORS["shadow"], 30), (cx, cy), 2)
        cls._cache["cobble_worn"] = surf
        
        # Pebbles on dirt
        surf = pygame.Surface((ts, ts), pygame.SRCALPHA)
        random.seed(88)
        for _ in range(4):
            px = random.randint(1, ts - 2)
            py = random.randint(1, ts - 2)
            pygame.draw.circle(surf, (*COLORS["hill"], 60), (px, py), 1)
        cls._cache["pebbles"] = surf
        
        # Arena sand texture
        surf = pygame.Surface((ts, ts), pygame.SRCALPHA)
        random.seed(55)
        for _ in range(3):
            sx = random.randint(1, ts - 2)
            sy = random.randint(1, ts - 2)
            pygame.draw.circle(surf, (*COLORS["sand_arena"], 40), (sx, sy), 2)
        cls._cache["arena_sand"] = surf
        
        # Travertine paving
        surf = pygame.Surface((ts, ts), pygame.SRCALPHA)
        pygame.draw.rect(surf, (*COLORS["travertine"], 30), (0, 0, ts, ts))
        pygame.draw.rect(surf, (*COLORS["shadow"], 20), (0, 0, ts, ts), 1)
        cls._cache["travertine"] = surf


# ============================================================
# PARTICLE EFFECTS
# ============================================================

class Particle:
    """Simple particle for visual effects."""
    __slots__ = ['x', 'y', 'vx', 'vy', 'life', 'max_life', 'color', 'size']
    
    def __init__(self, x, y, vx, vy, life, color, size=2):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size
    
    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0
    
    def draw(self, surface, camera):
        if self.life <= 0:
            return
        alpha = int(255 * (self.life / self.max_life))
        sx, sy = camera.apply(self.x, self.y)
        size = max(1, int(self.size * camera.zoom))
        
        ps = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        color_with_alpha = (*self.color[:3], min(255, alpha))
        pygame.draw.circle(ps, color_with_alpha, (size, size), size)
        surface.blit(ps, (sx - size, sy - size))


class ParticleSystem:
    """Manages all active particles."""
    
    def __init__(self):
        self.particles = []
    
    def emit_fire(self, x, y, intensity=1.0):
        for _ in range(int(2 * intensity)):
            self.particles.append(Particle(
                x + random.uniform(-0.3, 0.3),
                y + random.uniform(-0.3, 0.3),
                random.uniform(-0.5, 0.5),
                random.uniform(-2.0, -0.5),
                random.uniform(0.3, 0.8),
                random.choice([COLORS["fire_core"], COLORS["fire_mid"],
                               COLORS["fire_outer"]]),
                size=random.randint(1, 3)
            ))
    
    def emit_smoke(self, x, y):
        self.particles.append(Particle(
            x + random.uniform(-0.2, 0.2),
            y,
            random.uniform(-0.3, 0.3),
            random.uniform(-1.0, -0.3),
            random.uniform(1.0, 2.5),
            COLORS["smoke"],
            size=random.randint(2, 4)
        ))
    
    def emit_water_splash(self, x, y):
        for _ in range(2):
            self.particles.append(Particle(
                x, y,
                random.uniform(-0.8, 0.8),
                random.uniform(-1.5, -0.3),
                random.uniform(0.3, 0.7),
                COLORS["water"],
                size=1
            ))
    
    def emit_dust(self, x, y):
        self.particles.append(Particle(
            x + random.uniform(-0.5, 0.5),
            y + random.uniform(-0.2, 0.2),
            random.uniform(-0.3, 0.3),
            random.uniform(-0.5, 0.1),
            random.uniform(0.5, 1.5),
            COLORS["dirt_dark"],
            size=1
        ))
    
    def update(self, dt):
        self.particles = [p for p in self.particles if p.update(dt)]
        if len(self.particles) > 500:
            self.particles = self.particles[-500:]
    
    def draw(self, surface, camera):
        for p in self.particles:
            p.draw(surface, camera)
