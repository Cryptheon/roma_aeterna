"""
World Generator — Historically Faithful Central Rome c. 161 AD
================================================================

Based on the archaeological plan of Rome's monumental center.
Map orientation: North is UP. The map covers roughly 1km x 0.75km.

Layout matches the reference map:

    Y=0   ┌──────────────────────────────────────────────────────────┐
          │ Subura / Vicus Sandaliarius (residential, NE)            │
    Y=10  │                                                          │
          │   ┌─Markets of Trajan─┐                                  │
    Y=15  │   │  (semicircular)   │                                  │
          │   └───────────────────┘     Colossus                     │
    Y=20  │ ┌─Forum──┐ ┌─Forum──────┐   ●        ┌──────────────┐  │
          │ │Traiani  │ │ Augusti    │            │              │  │
          │ │ Column  │ └────────────┘   T.Venus  │  COLOSSEUM   │  │
    Y=30  │ └────────┘ ┌─F.Nervae─┐    et Roma   │  (Amphith.   │  │
          │            │          │ ┌──────────┐  │   Flavium)   │  │
          │            └──────────┘ │          │  │              │  │
    Y=40  │  ┌──Curia──┐           │          │  └──────────────┘  │
          │  │  Julia   │ Basilica │ T.Venus   │                    │
          │  └──────────┘ Aemilia  │ et Roma   │  Meta    Arch of   │
    Y=45  │                        └──────────┘  Sudans  Constantine│
          │  Arch of S.S.                                           │
    Y=50  │  ┌─────────FORUM ROMANUM──────────────┐                 │
          │  │ Rostra     Via Sacra →              │ Arch of Titus  │
          │  │ T.Saturn   T.Divus Julius  T.Vesta  │                │
    Y=60  │  │            T.Castor                 │                │
          │  │ Basilica Julia                      │                │
    Y=65  │  └─────────────────────────────────────┘                │
          │                                                          │
    Y=70  │  Tabularium (on Capitoline slope)                       │
          │                                                          │
    Y=75  │  ┌──CAPITOLINE HILL──┐  ┌─PALATINE HILL─────────────┐  │
          │  │ T. Jovis O.M.     │  │ Domus Tiberiana            │  │
          │  │ (Temple Jupiter)  │  │                            │  │
    Y=85  │  └───────────────────┘  │ T.Victoria  T.Magna Mater │  │
          │                         │                            │  │
    Y=90  │  Velabrum               │ Domus Liviae               │  │
          │  (valley)               │                   Stadium  │  │
    Y=95  │                         │ Domus Augustana   ┌──────┐ │  │
          │                         │ (Palace)          │      │ │  │
    Y=100 │ Forum Holitorium/       │                   │      │ │  │
          │ Forum Boarium           │                   └──────┘ │  │
    Y=110 │                         └────────────────────────────┘  │
          │                                                          │
    Y=115 │ Theatre of Marcellus    ┌──CIRCUS MAXIMUS──────────────┐│
          │                         │  (chariot racing)             ││
    Y=125 │                         └──────────────────────────────┘│
          │                                                          │
    Y=130 │ Porticus / T.Apollinis    Aqueduct (Aqua Claudia)       │
    Y=140 │                                                          │
    Y=150 └──────────────────────────────────────────────────────────┘
            X=0                                                  X=200
"""

import random
import math
from .map import GameMap, TERRAIN_TYPES
from .objects import create_prefab
from ..config import GRID_WIDTH, GRID_HEIGHT, RANDOM_SEED


class WorldGenerator:
    
    @staticmethod
    def generate_rome() -> GameMap:
        random.seed(RANDOM_SEED)
        world = GameMap(GRID_WIDTH, GRID_HEIGHT)
        
        # === Phase 1: Base Terrain ===
        WorldGenerator._paint_base_terrain(world)
        
        # === Phase 2: Elevation (Hills) ===
        WorldGenerator._sculpt_hills(world)
        
        # === Phase 3: Road Network ===
        WorldGenerator._lay_roads(world)
        
        # === Phase 4: Forum Romanum ===
        WorldGenerator._build_forum(world)
        
        # === Phase 5: Imperial Fora (north of Forum Romanum) ===
        WorldGenerator._build_imperial_fora(world)
        
        # === Phase 6: Colosseum Complex ===
        WorldGenerator._build_colosseum(world)
        
        # === Phase 7: Palatine Hill ===
        WorldGenerator._build_palatine(world)
        
        # === Phase 8: Capitoline Hill ===
        WorldGenerator._build_capitoline(world)
        
        # === Phase 9: Circus Maximus ===
        WorldGenerator._build_circus_maximus(world)
        
        # === Phase 10: Subura District (residential NE) ===
        WorldGenerator._build_subura(world)
        
        # === Phase 11: Velabrum & Forum Boarium (SW valley) ===
        WorldGenerator._build_velabrum(world)
        
        # === Phase 12: Theatre of Marcellus area (W) ===
        WorldGenerator._build_theatre_area(world)
        
        # === Phase 13: Infrastructure (Aqueducts, Fountains, Sewers) ===
        WorldGenerator._place_infrastructure(world)
        
        # === Phase 14: Vegetation & Decorations ===
        WorldGenerator._scatter_vegetation(world)
        WorldGenerator._place_decorations(world)
        
        return world

    # ----------------------------------------------------------------
    # Phase 1: Base Terrain
    # ----------------------------------------------------------------
    @staticmethod
    def _paint_base_terrain(world):
        """Fill the entire map with base Mediterranean terrain."""
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                r = random.random()
                if r < 0.55:
                    world.set_tile(x, y, "dirt", elevation=0.0, moisture=0.2)
                elif r < 0.80:
                    world.set_tile(x, y, "grass", elevation=0.0, moisture=0.4)
                elif r < 0.92:
                    world.set_tile(x, y, "grass_dry", elevation=0.0, moisture=0.15)
                else:
                    world.set_tile(x, y, "dirt", elevation=0.0, moisture=0.1,
                                   decoration="pebbles")

    # ----------------------------------------------------------------
    # Phase 2: Hills
    # ----------------------------------------------------------------
    @staticmethod
    def _sculpt_hills(world):
        """Create the Seven Hills topography around the monumental center."""
        
        # Palatine Hill — south-center, between Forum and Circus Maximus
        WorldGenerator._raise_hill(world, cx=110, cy=92, rx=25, ry=18,
                                   max_elevation=3.5, terrain="hill",
                                   zone="palatine")
        
        # Capitoline Hill — west of Forum (two summits: Arx and Capitolium)
        # Northern summit (Arx)
        WorldGenerator._raise_hill(world, cx=40, cy=72, rx=12, ry=8,
                                   max_elevation=3.0, terrain="hill",
                                   zone="capitoline")
        # Southern summit (Capitolium)
        WorldGenerator._raise_hill(world, cx=38, cy=82, rx=14, ry=10,
                                   max_elevation=3.5, terrain="hill",
                                   zone="capitoline")
        
        # Velia ridge — connecting Palatine to Esquiline, between Forum and Colosseum
        WorldGenerator._raise_hill(world, cx=135, cy=40, rx=10, ry=8,
                                   max_elevation=2.0, terrain="hill",
                                   zone="velia")
        
        # Esquiline Hill — northeast
        WorldGenerator._raise_hill(world, cx=100, cy=8, rx=30, ry=8,
                                   max_elevation=2.0, terrain="hill",
                                   zone="esquiline")
        
        # Caelian Hill — southeast
        WorldGenerator._raise_hill(world, cx=175, cy=75, rx=15, ry=12,
                                   max_elevation=1.5, terrain="hill",
                                   zone="caelian")
        
        # Aventine Hill — south of Circus Maximus
        WorldGenerator._raise_hill(world, cx=60, cy=130, rx=20, ry=12,
                                   max_elevation=2.5, terrain="hill",
                                   zone="aventine")

    @staticmethod
    def _raise_hill(world, cx, cy, rx, ry, max_elevation, terrain, zone):
        for y in range(max(0, cy - ry - 2), min(GRID_HEIGHT, cy + ry + 3)):
            for x in range(max(0, cx - rx - 2), min(GRID_WIDTH, cx + rx + 3)):
                dx = (x - cx) / max(rx, 1)
                dy = (y - cy) / max(ry, 1)
                dist_sq = dx * dx + dy * dy
                
                if dist_sq <= 1.0:
                    dist = math.sqrt(dist_sq)
                    elev = max_elevation * (0.5 + 0.5 * math.cos(dist * math.pi))
                    
                    tile = world.get_tile(x, y)
                    if tile:
                        tile.elevation = max(tile.elevation, elev)
                        tile.zone = zone
                        if elev > max_elevation * 0.7:
                            tile.terrain_type = "hill_steep" if elev > max_elevation * 0.9 else terrain
                            tile.movement_cost = TERRAIN_TYPES.get(
                                tile.terrain_type, {}).get("cost", 3.0)

    # ----------------------------------------------------------------
    # Phase 3: Roads
    # ----------------------------------------------------------------
    @staticmethod
    def _lay_roads(world):
        """Lay the major Roman road network matching the historical map."""
        
        # === VIA SACRA === (THE main processional road)
        # Runs from NW Forum through Forum Romanum, curves SE to Colosseum
        # Section 1: Through Forum (west to east)
        world.draw_road(50, 55, 130, 55, width=3, terrain_type="via_sacra",
                        zone="forum", decoration="mosaic_border")
        
        # Section 2: Past Temple of Venus & Roma, curving to Colosseum
        for i in range(25):
            t = i / 25
            rx = int(130 + t * 25)
            ry = int(55 - t * 15)  # Curves northeast to Colosseum
            hw = 1
            for oy in range(-hw, hw + 1):
                for ox in range(-hw, hw + 1):
                    world.set_tile(rx + ox, ry + oy, "via_sacra",
                                   zone="via_sacra", decoration="mosaic_border")
        
        # === VIA NOVA === (Parallel south of Forum, along Palatine slope)
        world.draw_road(50, 66, 130, 66, width=2, terrain_type="road_paved",
                        zone="forum")
        
        # === ARGILETUM / CLIVUS ARGENTARIUS === (North from Forum to Subura)
        world.draw_road(80, 10, 80, 48, width=2, terrain_type="road_cobble",
                        zone="subura")
        
        # === VICUS TUSCUS === (SW from Forum into Velabrum)
        world.draw_road(50, 58, 35, 75, width=2, terrain_type="road_cobble",
                        zone="velabrum")
        
        # === VICUS JUGARIUS === (W from Forum, south of Capitoline)
        world.draw_road(50, 62, 30, 80, width=2, terrain_type="road_cobble")
        
        # === Road around Colosseum === (Elliptical plaza)
        cx_col, cy_col = 170, 32
        for angle in range(0, 360, 2):
            rad = math.radians(angle)
            px = int(cx_col + 16 * math.cos(rad))
            py = int(cy_col + 14 * math.sin(rad))
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    if 0 <= px + dx < GRID_WIDTH and 0 <= py + dy < GRID_HEIGHT:
                        world.set_tile(px + dx, py + dy, "plaza",
                                       zone="colosseum_plaza")
        
        # === CLIVUS PALATINUS === (Road ascending Palatine from Forum)
        world.draw_road(65, 62, 75, 78, width=2, terrain_type="steps",
                        zone="palatine")
        
        # === SCALAE GEMONIAE === (Steps on Capitoline slope)
        world.draw_road(48, 48, 42, 68, width=1, terrain_type="steps",
                        zone="capitoline")
        
        # === Subura grid streets ===
        for street_x in range(55, 120, 10):
            world.draw_road(street_x, 2, street_x, 40, width=1,
                            terrain_type="road_cobble", zone="subura")
        for street_y in range(5, 35, 7):
            world.draw_road(55, street_y, 120, street_y, width=1,
                            terrain_type="road_cobble", zone="subura")
        
        # === VICUS SANDALIARIUS === (East, near Colosseum)
        world.draw_road(130, 5, 155, 15, width=2, terrain_type="road_cobble",
                        zone="subura")
        
        # === Road south: Forum to Circus Maximus ===
        world.draw_road(55, 66, 60, 115, width=2, terrain_type="road_paved")
        
        # === Roads on Palatine ===
        world.draw_road(85, 85, 120, 85, width=1, terrain_type="road_paved",
                        zone="palatine")
        world.draw_road(100, 78, 100, 108, width=1, terrain_type="road_paved",
                        zone="palatine")

    # ----------------------------------------------------------------
    # Phase 4: Forum Romanum
    # ----------------------------------------------------------------
    @staticmethod
    def _build_forum(world):
        """Construct the Forum Romanum — matching historical layout."""
        
        # Clear the forum floor (open rectangular plaza)
        world.fill_rect(50, 48, 130, 65, "forum_floor",
                        zone="forum", elevation=0.2, decoration="travertine")
        
        # --- West end of Forum ---
        
        # Arch of Septimius Severus (NW corner of Forum)
        arch_ss = create_prefab("ArchOfSeptimiusSeverus", 52, 47)
        world.register_landmark("Arch of Septimius Severus", arch_ss)
        WorldGenerator._stamp_footprint(world, arch_ss, "road_paved", zone="forum")
        
        # Rostra (speaker's platform, west side)
        rostra = create_prefab("Rostra", 55, 52)
        world.register_landmark("Rostra", rostra)
        WorldGenerator._stamp_footprint(world, rostra, "building_floor", zone="forum")
        
        # Curia Julia (Senate House, NW of Forum)
        curia = create_prefab("CuriaJulia", 55, 42)
        world.register_landmark("Curia Julia", curia)
        WorldGenerator._stamp_footprint(world, curia, "wall", zone="forum")
        
        # Temple of Saturn (SW corner of Forum, elevated on podium)
        temple_saturn = create_prefab("TempleOfSaturn", 52, 55)
        world.register_landmark("Temple of Saturn", temple_saturn)
        WorldGenerator._stamp_footprint(world, temple_saturn, "wall", zone="forum")
        for x in range(51, 59):
            world.set_tile(x, 64, "steps", zone="forum", elevation=0.3)
        
        # Temple of Concord (above Saturn, at the foot of Capitoline)
        temple_concord = create_prefab("TempleOfConcord", 50, 46)
        world.register_landmark("Temple of Concord", temple_concord)
        WorldGenerator._stamp_footprint(world, temple_concord, "wall", zone="forum")
        
        # --- North side of Forum ---
        
        # Basilica Aemilia (long building along north side)
        basilica_aemilia = create_prefab("BasilicaAemilia", 68, 43)
        world.register_landmark("Basilica Aemilia", basilica_aemilia)
        WorldGenerator._stamp_footprint(world, basilica_aemilia, "wall", zone="forum")
        
        # --- Center of Forum ---
        
        # Temple of Divus Julius (at east end of open Forum)
        temple_julius = create_prefab("TempleOfDivusJulius", 100, 48)
        world.register_landmark("Temple of Divus Julius", temple_julius)
        WorldGenerator._stamp_footprint(world, temple_julius, "wall", zone="forum")
        
        # --- South side of Forum ---
        
        # Basilica Julia (long building along south side, opposite Basilica Aemilia)
        basilica_julia = create_prefab("BasilicaJulia", 64, 59)
        world.register_landmark("Basilica Julia", basilica_julia)
        WorldGenerator._stamp_footprint(world, basilica_julia, "wall", zone="forum")
        
        # Temple of Castor and Pollux (south side, famous 3 columns)
        temple_castor = create_prefab("TempleOfCastor", 90, 57)
        world.register_landmark("Temple of Castor & Pollux", temple_castor)
        WorldGenerator._stamp_footprint(world, temple_castor, "wall", zone="forum")
        
        # --- East end of Forum ---
        
        # Temple of Vesta (circular, SE corner)
        temple_vesta = create_prefab("TempleOfVesta", 110, 56)
        world.register_landmark("Temple of Vesta", temple_vesta)
        WorldGenerator._stamp_footprint(world, temple_vesta, "wall", zone="forum")
        
        # Regia (ancient royal building, near Temple of Vesta)
        regia = create_prefab("Regia", 106, 53)
        world.register_landmark("Regia", regia)
        WorldGenerator._stamp_footprint(world, regia, "wall", zone="forum")
        
        # Temple of Antoninus and Faustina (north side, east of Basilica Aemilia)
        temple_antoninus = create_prefab("TempleOfAntoninus", 95, 42)
        world.register_landmark("Temple of Antoninus & Faustina", temple_antoninus)
        WorldGenerator._stamp_footprint(world, temple_antoninus, "wall", zone="forum")
        
        # --- Columns lining the Forum edges ---
        for x in range(62, 108, 4):
            col = create_prefab("Column", x, 48)
            world.add_object(col)
            col_s = create_prefab("Column", x, 64)
            world.add_object(col_s)

    # ----------------------------------------------------------------
    # Phase 5: Imperial Fora
    # ----------------------------------------------------------------
    @staticmethod
    def _build_imperial_fora(world):
        """Build the Imperial Fora complex north of Forum Romanum."""
        
        # Forum of Trajan (westmost, largest)
        # Clear area
        world.fill_rect(30, 15, 50, 35, "forum_floor", zone="forum_traiani",
                        elevation=0.3)
        forum_trajan = create_prefab("ForumOfTrajan", 32, 18)
        world.register_landmark("Forum of Trajan", forum_trajan)
        WorldGenerator._stamp_footprint(world, forum_trajan, "building_floor",
                                        zone="forum_traiani")
        
        # Column of Trajan
        col_trajan = create_prefab("ColumnaTraiani", 37, 16)
        world.register_landmark("Column of Trajan", col_trajan)
        
        # Markets of Trajan (semicircular, east of Forum of Trajan)
        markets = create_prefab("MarketsOfTrajan", 42, 12)
        world.register_landmark("Markets of Trajan", markets)
        WorldGenerator._stamp_footprint(world, markets, "building_floor",
                                        zone="forum_traiani")
        
        # Forum of Augustus (east of Trajan)
        world.fill_rect(52, 18, 65, 35, "forum_floor", zone="forum_augusti",
                        elevation=0.3)
        forum_augustus = create_prefab("ForumOfAugustus", 53, 20)
        world.register_landmark("Forum of Augustus", forum_augustus)
        WorldGenerator._stamp_footprint(world, forum_augustus, "building_floor",
                                        zone="forum_augusti")
        
        # Forum Transitorium / Forum of Nerva (narrow connecting forum)
        world.fill_rect(65, 22, 72, 40, "forum_floor", zone="forum_nervae",
                        elevation=0.2)
        forum_nerva = create_prefab("ForumOfNerva", 66, 24)
        world.register_landmark("Forum of Nerva", forum_nerva)
        WorldGenerator._stamp_footprint(world, forum_nerva, "building_floor",
                                        zone="forum_nervae")
        
        # Forum of Vespasian / Templum Pacis (east of Nerva)
        world.fill_rect(76, 18, 92, 35, "forum_floor",
                        zone="forum_vespasiani", elevation=0.2)
        forum_vesp = create_prefab("ForumOfVespasian", 78, 20)
        world.register_landmark("Forum of Vespasian / Templum Pacis",
                                forum_vesp)
        WorldGenerator._stamp_footprint(world, forum_vesp, "building_floor",
                                        zone="forum_vespasiani")
        
        # Gardens within Templum Pacis
        world.fill_rect(80, 22, 88, 26, "garden", zone="forum_vespasiani",
                        moisture=0.7)

    # ----------------------------------------------------------------
    # Phase 6: Colosseum Complex
    # ----------------------------------------------------------------
    @staticmethod
    def _build_colosseum(world):
        """Build the Flavian Amphitheatre and surrounding structures."""
        
        # Colosseum center position (upper right of map, matching reference)
        cx, cy = 170, 32
        rx_outer, ry_outer = 12, 10
        rx_inner, ry_inner = 7, 5
        
        # Build the structural footprint
        for y in range(cy - ry_outer - 1, cy + ry_outer + 2):
            for x in range(cx - rx_outer - 1, cx + rx_outer + 2):
                if x < 0 or x >= GRID_WIDTH or y < 0 or y >= GRID_HEIGHT:
                    continue
                dx_o = (x - cx) / rx_outer
                dy_o = (y - cy) / ry_outer
                dist_outer = dx_o * dx_o + dy_o * dy_o
                
                dx_i = (x - cx) / rx_inner
                dy_i = (y - cy) / ry_inner
                dist_inner = dx_i * dx_i + dy_i * dy_i
                
                if dist_outer <= 1.0:
                    if dist_inner <= 1.0:
                        world.set_tile(x, y, "sand_arena",
                                       zone="colosseum", elevation=0.0,
                                       decoration="arena_sand")
                    elif dist_outer <= 0.85:
                        ring_elev = 2.0 + (dist_outer - 0.5) * 4.0
                        world.set_tile(x, y, "wall",
                                       zone="colosseum", elevation=ring_elev,
                                       walkable=False)
                    else:
                        world.set_tile(x, y, "wall",
                                       zone="colosseum", elevation=3.5,
                                       walkable=False)
        
        # Place the Colosseum sprite object
        colosseum = create_prefab("Colosseum", cx - 12, cy - 10)
        world.register_landmark("Colosseum", colosseum)
        
        # Colossus of Nero (giant bronze statue, west of Colosseum)
        colossus = create_prefab("Colossus", 153, 28)
        world.register_landmark("Colossus of Nero", colossus)
        
        # Meta Sudans fountain (SW of Colosseum)
        meta_sudans = create_prefab("MetaSudans", 155, 38)
        world.register_landmark("Meta Sudans", meta_sudans)
        world.fill_ellipse(156, 39, 2, 2, "water_shallow",
                           zone="colosseum_plaza")
        
        # Arch of Constantine (south of Colosseum)
        arch_constantine = create_prefab("ArchOfConstantine", 162, 48)
        world.register_landmark("Arch of Constantine", arch_constantine)
        WorldGenerator._stamp_footprint(world, arch_constantine, "road_paved",
                                        zone="colosseum_plaza")
        
        # Temple of Venus and Roma (between Forum and Colosseum, on Velia)
        temple_vr = create_prefab("TempleOfVenusRoma", 135, 35)
        world.register_landmark("Temple of Venus and Roma", temple_vr)
        WorldGenerator._stamp_footprint(world, temple_vr, "wall", zone="velia")
        
        # Platform for Temple of Venus and Roma
        world.fill_rect(133, 33, 145, 51, "plaza", zone="velia", elevation=1.5)
        
        # Arch of Titus (on the Via Sacra, at the summit of Velia)
        arch_titus = create_prefab("ArchOfTitus", 130, 52)
        world.register_landmark("Arch of Titus", arch_titus)
        WorldGenerator._stamp_footprint(world, arch_titus, "via_sacra",
                                        zone="via_sacra")
        
        # Ludus Magnus (gladiator school, east of Colosseum)
        ludus = create_prefab("LudusMagnus", 185, 38)
        world.register_landmark("Ludus Magnus", ludus)
        WorldGenerator._stamp_footprint(world, ludus, "building_floor",
                                        zone="ludus")
        # Training yard within
        world.fill_rect(188, 42, 193, 46, "sand_arena", zone="ludus")

    # ----------------------------------------------------------------
    # Phase 7: Palatine Hill
    # ----------------------------------------------------------------
    @staticmethod
    def _build_palatine(world):
        """Build the Imperial residences on the Palatine Hill."""
        
        # Domus Tiberiana (NW corner of Palatine, overlooking Forum)
        domus_tib = create_prefab("DomusTiberiana", 70, 72)
        world.register_landmark("Domus Tiberiana", domus_tib)
        WorldGenerator._stamp_footprint(world, domus_tib, "wall",
                                        zone="palatine")
        
        # Domus Augustana / Domus Flavia (center of Palatine, main palace)
        domus_aug = create_prefab("DomusAugustana", 100, 85)
        world.register_landmark("Domus Augustana", domus_aug)
        WorldGenerator._stamp_footprint(world, domus_aug, "wall",
                                        zone="palatine")
        
        # Stadium of Domitian (east edge of Palatine)
        stadium = create_prefab("Stadium", 122, 82)
        world.register_landmark("Stadium of Domitian", stadium)
        WorldGenerator._stamp_footprint(world, stadium, "building_floor",
                                        zone="palatine")
        
        # Temple of Victoria (on Palatine slope)
        temple_vic = create_prefab("TempleOfVictoria", 82, 80)
        world.register_landmark("Temple of Victoria", temple_vic)
        WorldGenerator._stamp_footprint(world, temple_vic, "wall",
                                        zone="palatine")
        
        # Temple of Magna Mater / Cybele
        temple_mm = create_prefab("TempleOfMagnaMater", 90, 78)
        world.register_landmark("Temple of Magna Mater", temple_mm)
        WorldGenerator._stamp_footprint(world, temple_mm, "wall",
                                        zone="palatine")
        
        # Domus Liviae (House of Livia, historical residence)
        domus_liviae = create_prefab("DomusLiviae", 95, 88)
        world.register_landmark("Domus Liviae", domus_liviae)
        WorldGenerator._stamp_footprint(world, domus_liviae, "building_floor",
                                        zone="palatine")
        
        # Palace gardens (south-facing terraces)
        world.fill_rect(88, 104, 120, 112, "garden", zone="palatine",
                        elevation=2.5, moisture=0.7)
        
        # Terrace edge (cliff on north side facing Forum)
        for y in range(68, 78):
            for x in range(65, 85):
                tile = world.get_tile(x, y)
                if tile and tile.elevation < 2.0:
                    world.set_tile(x, y, "cliff", zone="palatine",
                                   elevation=3.0)
        
        # Arch of Domitian / passage to Forum
        world.draw_road(70, 68, 65, 62, width=1, terrain_type="steps",
                        zone="palatine")

    # ----------------------------------------------------------------
    # Phase 8: Capitoline Hill
    # ----------------------------------------------------------------
    @staticmethod
    def _build_capitoline(world):
        """Build the Capitoline Hill — religious and political center."""
        
        # Tabularium (state archive, on the slope facing Forum)
        tabularium = create_prefab("Tabularium", 38, 65)
        world.register_landmark("Tabularium", tabularium)
        WorldGenerator._stamp_footprint(world, tabularium, "wall",
                                        zone="capitoline")
        
        # Temple of Jupiter Optimus Maximus (summit of Capitoline)
        temple_jovis = create_prefab("TempleOfJovisOM", 30, 76)
        world.register_landmark("Temple of Jupiter Optimus Maximus",
                                temple_jovis)
        WorldGenerator._stamp_footprint(world, temple_jovis, "wall",
                                        zone="capitoline")
        
        # Area Capitolina (open area on top)
        world.fill_rect(28, 73, 45, 90, "forum_floor", zone="capitoline",
                        elevation=3.0)
        
        # Cliffs on the east face (Tarpeian Rock area)
        for y in range(70, 88):
            for x in range(45, 50):
                world.set_tile(x, y, "cliff", zone="capitoline", elevation=3.0)

    # ----------------------------------------------------------------
    # Phase 9: Circus Maximus
    # ----------------------------------------------------------------
    @staticmethod
    def _build_circus_maximus(world):
        """Build the Circus Maximus in the valley between Palatine and Aventine."""
        
        # Valley floor
        world.fill_rect(58, 115, 145, 128, "circus_sand", zone="circus",
                        elevation=0.0)
        
        # Place the Circus Maximus
        circus = create_prefab("CircusMaximus", 60, 117)
        world.register_landmark("Circus Maximus", circus)
        WorldGenerator._stamp_footprint(world, circus, "building_floor",
                                        zone="circus")
        
        # Obelisk in spina
        obelisk = create_prefab("Obelisk", 90, 121)
        world.add_object(obelisk)

    # ----------------------------------------------------------------
    # Phase 10: Subura District
    # ----------------------------------------------------------------
    @staticmethod
    def _build_subura(world):
        """Build the crowded Subura tenement district NE of Forum."""
        
        # Dense insulae (apartment blocks)
        for block_y in range(4, 38, 7):
            for block_x in range(56, 120, 9):
                tile = world.get_tile(block_x, block_y)
                if tile and tile.terrain_type in ("road_cobble", "road_paved",
                                                  "forum_floor"):
                    continue
                if tile and tile.zone in ("forum_traiani", "forum_augusti",
                                          "forum_nervae", "forum_vespasiani"):
                    continue
                
                stories = random.choice([3, 4, 4, 5, 5, 6])
                insula = create_prefab("Insula", block_x, block_y,
                                       stories=stories)
                world.add_object(insula)
                WorldGenerator._stamp_footprint(world, insula,
                                                "building_floor", zone="subura")
        
        # Tabernae (shops) along main Subura streets
        for tx in range(57, 115, 12):
            if random.random() < 0.7:
                tab = create_prefab("Taberna", tx, 40)
                world.add_object(tab)
                WorldGenerator._stamp_footprint(world, tab, "building_floor",
                                                zone="subura")
        
        # Market stalls along Argiletum
        for ty in range(12, 38, 6):
            stall = create_prefab("Market", 82, ty)
            world.add_object(stall)

    # ----------------------------------------------------------------
    # Phase 11: Velabrum & Forum Boarium
    # ----------------------------------------------------------------
    @staticmethod
    def _build_velabrum(world):
        """Build the Velabrum valley and Forum Boarium (cattle market)."""
        
        # Velabrum valley floor (between Capitoline and Palatine)
        world.fill_rect(30, 88, 60, 108, "dirt", zone="velabrum",
                        elevation=0.2, moisture=0.3)
        
        # Forum Boarium (open market area)
        world.fill_rect(25, 100, 50, 112, "plaza", zone="forum_boarium",
                        elevation=0.1)
        
        # Forum Holitorium (vegetable market)
        world.fill_rect(20, 108, 40, 118, "plaza", zone="forum_holitorium",
                        elevation=0.1)
        
        # Cloaca Maxima outlet (great sewer, drains into Tiber)
        cloaca = create_prefab("Cloaca", 18, 105)
        world.register_landmark("Cloaca Maxima", cloaca)
        
        # Small temples in Forum Boarium
        for i, pos in enumerate([(30, 102), (38, 104)]):
            temple = create_prefab("Domus", pos[0], pos[1])
            temple.name = f"Temple (Forum Boarium {i+1})"
            world.add_object(temple)
            WorldGenerator._stamp_footprint(world, temple, "wall",
                                            zone="forum_boarium")

    # ----------------------------------------------------------------
    # Phase 12: Theatre of Marcellus Area
    # ----------------------------------------------------------------
    @staticmethod
    def _build_theatre_area(world):
        """Build Theatre of Marcellus and surrounding structures."""
        
        # Theatre of Marcellus
        theatre = create_prefab("TheatreOfMarcellus", 15, 112)
        world.register_landmark("Theatre of Marcellus", theatre)
        WorldGenerator._stamp_footprint(world, theatre, "wall",
                                        zone="theatre_area")
        
        # Porticus Octaviae (nearby colonnade)
        porticus = create_prefab("Porticus", 12, 125)
        world.register_landmark("Porticus Octaviae", porticus)
        WorldGenerator._stamp_footprint(world, porticus, "building_floor",
                                        zone="theatre_area")
        
        # Temple of Apollo Sosianus
        temple_apollo = create_prefab("TempleOfAntoninus", 8, 128)
        temple_apollo.name = "Temple of Apollo Sosianus"
        world.add_object(temple_apollo)
        WorldGenerator._stamp_footprint(world, temple_apollo, "wall",
                                        zone="theatre_area")

    # ----------------------------------------------------------------
    # Phase 13: Infrastructure
    # ----------------------------------------------------------------
    @staticmethod
    def _place_infrastructure(world):
        """Place aqueducts, fountains, and public utilities."""
        
        # Aqueduct — Aqua Claudia running along the east side
        for y in range(0, GRID_HEIGHT, 4):
            if 195 <= 198:
                aq = create_prefab("Aqueduct", 195, y)
                world.add_object(aq)
                world.set_tile(195, y, "wall", elevation=3.0,
                               zone="infrastructure")
                world.set_tile(196, y, "aqueduct_channel",
                               zone="infrastructure")
        
        # Public fountains at key intersections
        fountain_spots = [
            (80, 42),    # Argiletum / Subura entrance
            (65, 55),    # Forum, near Rostra
            (105, 55),   # Forum east
            (55, 66),    # Via Nova / Forum SW
            (155, 35),   # Colosseum approach
            (100, 92),   # Palatine (palace area)
            (35, 95),    # Velabrum
            (90, 120),   # Near Circus Maximus
        ]
        for fx, fy in fountain_spots:
            fountain = create_prefab("Fountain", fx, fy)
            world.add_object(fountain)
        
        # Torches along Via Sacra
        for tx in range(52, 130, 5):
            torch = create_prefab("Torch", tx, 53)
            world.add_object(torch)
            torch2 = create_prefab("Torch", tx, 57)
            world.add_object(torch2)
        
        # Torches around Colosseum
        cx_col, cy_col = 170, 32
        for angle in range(0, 360, 20):
            rad = math.radians(angle)
            tx = int(cx_col + 15 * math.cos(rad))
            ty = int(cy_col + 13 * math.sin(rad))
            if 0 <= tx < GRID_WIDTH and 0 <= ty < GRID_HEIGHT:
                torch = create_prefab("Torch", tx, ty)
                world.add_object(torch)
        
        # Torches on Palatine approaches
        for ty in range(70, 100, 5):
            torch = create_prefab("Torch", 68, ty)
            world.add_object(torch)
        
        # Bathhouse near the Forum
        bath = create_prefab("Bathhouse", 120, 15)
        world.register_landmark("Baths near Subura", bath)
        WorldGenerator._stamp_footprint(world, bath, "building_floor",
                                        zone="subura")

    # ----------------------------------------------------------------
    # Phase 14: Vegetation & Decorations
    # ----------------------------------------------------------------
    @staticmethod
    def _scatter_vegetation(world):
        """Add Mediterranean vegetation — cypress, olive, pine, shrubs."""
        
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                tile = world.get_tile(x, y)
                if not tile:
                    continue
                
                if tile.terrain_type not in ("grass", "grass_dry", "garden",
                                             "hill", "dirt"):
                    continue
                if tile.building is not None:
                    continue
                
                r = random.random()
                
                # Palatine gardens: more dense vegetation
                if tile.zone == "palatine" and tile.terrain_type == "garden":
                    if r < 0.06:
                        cypress = create_prefab("Cypress", x, y)
                        world.add_object(cypress)
                    elif r < 0.10:
                        flowers = create_prefab("FlowerBed", x, y)
                        world.add_object(flowers)
                    elif r < 0.13:
                        pine = create_prefab("PineTree", x, y)
                        world.add_object(pine)
                elif tile.zone == "palatine" and r < 0.03:
                    cypress = create_prefab("Cypress", x, y)
                    world.add_object(cypress)
                
                # Esquiline / Caelian: suburban gardens
                elif tile.zone in ("esquiline", "caelian"):
                    if r < 0.04:
                        choice = random.random()
                        if choice < 0.35:
                            tree = create_prefab("Cypress", x, y)
                        elif choice < 0.65:
                            tree = create_prefab("OliveTree", x, y)
                        else:
                            tree = create_prefab("PineTree", x, y)
                        world.add_object(tree)
                    elif r < 0.06 and tile.terrain_type == "garden":
                        flowers = create_prefab("FlowerBed", x, y)
                        world.add_object(flowers)
                
                # Aventine: some vegetation
                elif tile.zone == "aventine" and r < 0.03:
                    tree = create_prefab("OliveTree", x, y)
                    world.add_object(tree)
                
                # General terrain
                elif tile.terrain_type == "garden" and r < 0.08:
                    flowers = create_prefab("FlowerBed", x, y)
                    world.add_object(flowers)
                elif tile.terrain_type in ("grass", "grass_dry") and r < 0.015:
                    shrub = create_prefab("Shrub", x, y)
                    world.add_object(shrub)

    @staticmethod
    def _place_decorations(world):
        """Place statues, inscriptions, and decorative elements."""
        
        # Statues in the Forum
        statue_spots = [
            (60, 52), (75, 50), (88, 50), (98, 52), (105, 50)
        ]
        for sx, sy in statue_spots:
            statue = create_prefab("Statue", sx, sy)
            world.add_object(statue)
        
        # Equestrian statues in Imperial Fora
        eq_spots = [(40, 28), (60, 28)]
        for sx, sy in eq_spots:
            eq = create_prefab("StatueEquestrian", sx, sy)
            world.add_object(eq)
        
        # Ground decorations — mosaics on forum floor
        for y in range(48, 65):
            for x in range(52, 128):
                tile = world.get_tile(x, y)
                if (tile and tile.terrain_type == "forum_floor"
                        and random.random() < 0.08):
                    tile.ground_decoration = random.choice([
                        "mosaic_simple", "drain_grate", "inscription"
                    ])
        
        # Mosaics in Imperial Fora
        for y in range(18, 35):
            for x in range(30, 92):
                tile = world.get_tile(x, y)
                if (tile and tile.terrain_type == "forum_floor"
                        and random.random() < 0.05):
                    tile.ground_decoration = random.choice([
                        "mosaic_simple", "inscription"
                    ])
        
        # Drain grates along Via Sacra
        for x in range(50, 130, 8):
            tile = world.get_tile(x, 55)
            if tile and tile.terrain_type == "via_sacra":
                tile.ground_decoration = "drain_grate"

    # ----------------------------------------------------------------
    # Utility
    # ----------------------------------------------------------------
    @staticmethod
    def _stamp_footprint(world, obj, terrain_type, zone=""):
        """Mark tiles under a building's footprint as unwalkable."""
        from .components import Footprint
        fp = obj.get_component(Footprint)
        if not fp:
            t = world.get_tile(obj.x, obj.y)
            if t:
                t.terrain_type = terrain_type
                t.is_walkable = False
                t.movement_cost = 999
                t.building = obj
            return
        
        for dy in range(fp.height):
            for dx in range(fp.width):
                tx, ty = obj.x + dx, obj.y + dy
                t = world.get_tile(tx, ty)
                if t:
                    t.terrain_type = terrain_type
                    t.is_walkable = False
                    t.movement_cost = 999
                    t.building = obj
                    t.zone = zone if zone else t.zone
