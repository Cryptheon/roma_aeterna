"""
Renderer — Layered 2D Rome Visualization
==========================================
Draws the game world with:
  - Terrain tiles with color variation
  - Ground decorations (mosaics, drains)
  - Building sprites from SpriteSheet
  - Elevation shading (pseudo-3D hills)
  - Environmental particles (fire, smoke, dust, water)
  - Dynamic day/night tinting
  - Agent rendering
  - RPG-style UI overlay
"""

import pygame
import math
import random
from ..config import *
from .camera import Camera
from .assets import COLORS, SpriteSheet, ParticleSystem
from ..world.components import (Flammable, Decoration, Elevation,
                                 WaterFeature, Footprint)


class Renderer:
    def __init__(self, engine):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Rome: Aeterna — Forum Romanum et Colosseum")
        
        self.engine = engine
        self.clock = pygame.time.Clock()
        self.camera = Camera(GRID_WIDTH * TILE_SIZE, GRID_HEIGHT * TILE_SIZE)
        
        # Center camera on the Forum area
        self.camera.center_on(90, 55)
        
        # Initialize sprite system
        SpriteSheet.init(TILE_SIZE)
        
        # Particle system
        self.particles = ParticleSystem()
        
        # Fonts
        self.font_title = pygame.font.SysFont("Georgia", 18, bold=True)
        self.font_body = pygame.font.SysFont("Georgia", 14)
        self.font_small = pygame.font.SysFont("Georgia", 11)
        self.font_label = pygame.font.SysFont("Georgia", 10)
        
        # Day/night cycle
        self.time_of_day = 0.35  # Start at morning
        
        # Cached terrain color variations
        self._terrain_noise = {}
        random.seed(RANDOM_SEED + 1)
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                self._terrain_noise[(x, y)] = random.randint(-8, 8)
        
        # Tooltip state
        self.hovered_entity = None
        self.hover_timer = 0.0
        
        # Ambient animation timer
        self.anim_timer = 0.0

        # Tooltip state
        self.hovered_entity = None
        self.hover_timer = 0.0
        
        # --- NEW: Agent Inspection Window State ---
        self.selected_agent = None
        self.agent_window_scroll = 0
        self.agent_window_mode = "prompt"  # "prompt" or "history"
        
        # --- NEW: Right-click context menu ---
        self.context_menu_agent = None     # Agent that was right-clicked
        self.context_menu_pos = (0, 0)     # Screen position of menu
        self.context_menu_visible = False
        
        # --- Tick rate decoupling (sim @ TPS, render @ FPS) ---
        self._sim_accumulator = 0.0
        self._sim_dt = 1.0 / TPS
        
        # Ambient animation timer
        self.anim_timer = 0.0

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            self.anim_timer += dt

            mx, my = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.selected_agent:
                            self.selected_agent = None
                        elif self.context_menu_visible:
                            self.context_menu_visible = False
                        else:
                            running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    # --- Context menu click handling ---
                    if self.context_menu_visible:
                        clicked_option = self._check_context_menu_click(event.pos)
                        if clicked_option == "prompt":
                            self.selected_agent = self.context_menu_agent
                            self.agent_window_mode = "prompt"
                            self.agent_window_scroll = 0
                        elif clicked_option == "history":
                            self.selected_agent = self.context_menu_agent
                            self.agent_window_mode = "history"
                            self.agent_window_scroll = 0
                        self.context_menu_visible = False
                        continue
                    
                    # --- Agent inspection window open ---
                    if self.selected_agent:
                        if event.button == 4:  # Scroll Up
                            self.agent_window_scroll = max(0, self.agent_window_scroll - 40)
                        elif event.button == 5:  # Scroll Down
                            self.agent_window_scroll += 40
                        elif event.button == 1:  # Left Click
                            win_rect = pygame.Rect(100, 50, SCREEN_WIDTH - 200, SCREEN_HEIGHT - 100)
                            if not win_rect.collidepoint(event.pos):
                                self.selected_agent = None
                    else:
                        # Right-click on agent → context menu
                        if event.button == 3 and hasattr(self.hovered_entity, 'role'):
                            self.context_menu_agent = self.hovered_entity
                            self.context_menu_pos = event.pos
                            self.context_menu_visible = True
                        # Left-click still opens prompt directly (backward compatible)
                        elif event.button == 1 and hasattr(self.hovered_entity, 'role'):
                            self.selected_agent = self.hovered_entity
                            self.agent_window_mode = "prompt"
                            self.agent_window_scroll = 0

                # Only pass events to the camera if no UI is open
                if not self.selected_agent and not self.context_menu_visible:
                    self.camera.handle_event(event)

            self.camera.update(dt)
            
            # --- Fixed tick rate: sim runs at TPS, render at FPS ---
            self._sim_accumulator += dt
            while self._sim_accumulator >= self._sim_dt:
                self.engine.update(self._sim_dt)
                self._sim_accumulator -= self._sim_dt
            
            self.time_of_day = (self.time_of_day + dt / DAY_LENGTH_TICKS * TPS) % 1.0
            self._update_particles(dt)
            self._update_hover(mx, my)

            self._draw_frame(mx, my)
            pygame.display.flip()

        pygame.quit()
            
    def _draw_frame(self, mx, my):
        sky_color = self._get_sky_color()
        self.screen.fill(sky_color)
        
        with self.engine.lock:
            min_x, min_y, max_x, max_y = self.camera.get_visible_bounds()
            min_x = max(0, min_x)
            min_y = max(0, min_y)
            max_x = min(GRID_WIDTH, max_x)
            max_y = min(GRID_HEIGHT, max_y)
            
            self._render_terrain(min_x, min_y, max_x, max_y)
            self._render_ground_decorations(min_x, min_y, max_x, max_y)
            self._render_shadows(min_x, min_y, max_x, max_y)
            self._render_objects(min_x, min_y, max_x, max_y)
            self._render_agents()
            self.particles.draw(self.screen, self.camera)
            self._render_lighting()
        
        self._draw_ui(mx, my)

    # ================================================================
    # TERRAIN
    # ================================================================
    
    def _render_terrain(self, min_x, min_y, max_x, max_y):
        tile_px = int(TILE_SIZE * self.camera.zoom)
        if tile_px < 1:
            tile_px = 1
        
        for y in range(min_y, max_y):
            for x in range(min_x, max_x):
                tile = self.engine.world.get_tile(x, y)
                if not tile:
                    continue
                
                sx, sy = self.camera.apply(x, y)
                
                base_color = COLORS.get(tile.terrain_type, COLORS["dirt"])
                noise = self._terrain_noise.get((x, y), 0)
                elev_mod = int(tile.elevation * 5)
                
                color = (
                    max(0, min(255, base_color[0] + noise + elev_mod)),
                    max(0, min(255, base_color[1] + noise + elev_mod)),
                    max(0, min(255, base_color[2] + noise - 2)),
                )
                
                pygame.draw.rect(self.screen, color, (sx, sy, tile_px, tile_px))
                
                # Grid lines at high zoom
                if self.camera.zoom >= 2.5 and tile_px > 4:
                    darker = tuple(max(0, c - 15) for c in color)
                    pygame.draw.rect(self.screen, darker,
                                     (sx, sy, tile_px, tile_px), 1)
                
                # Zone-specific ground patterns
                if tile.zone == "forum" and tile.terrain_type == "forum_floor":
                    if self.camera.zoom >= 1.5 and (x + y) % 3 == 0:
                        lighter = tuple(min(255, c + 8) for c in color)
                        inner = tile_px // 4
                        pygame.draw.rect(self.screen, lighter,
                                         (sx + inner, sy + inner,
                                          tile_px - inner * 2,
                                          tile_px - inner * 2))
                
                # Elevation contour hints
                if tile.elevation > 1.5 and self.camera.zoom >= 1.0:
                    if tile.elevation > 2.5:
                        contour_alpha = 20
                    else:
                        contour_alpha = 10
                    # Subtle darkening on steep sides
                    neighbor = self.engine.world.get_tile(x + 1, y)
                    if neighbor and abs(tile.elevation - neighbor.elevation) > 0.5:
                        edge_surf = pygame.Surface((2, tile_px), pygame.SRCALPHA)
                        edge_surf.fill((0, 0, 0, contour_alpha))
                        self.screen.blit(edge_surf,
                                         (sx + tile_px - 2, sy))

    # ================================================================
    # GROUND DECORATIONS
    # ================================================================
    
    def _render_ground_decorations(self, min_x, min_y, max_x, max_y):
        if self.camera.zoom < 1.0:
            return
        
        tile_px = int(TILE_SIZE * self.camera.zoom)
        
        for y in range(min_y, max_y):
            for x in range(min_x, max_x):
                tile = self.engine.world.get_tile(x, y)
                if not tile or not tile.ground_decoration:
                    continue
                
                sx, sy = self.camera.apply(x, y)
                
                deco_sprite = SpriteSheet.get(tile.ground_decoration)
                if deco_sprite:
                    scaled = pygame.transform.scale(deco_sprite,
                                                    (tile_px, tile_px))
                    self.screen.blit(scaled, (sx, sy))

    # ================================================================
    # SHADOWS
    # ================================================================
    
    def _render_shadows(self, min_x, min_y, max_x, max_y):
        sun_angle = (self.time_of_day - 0.25) * math.pi
        shadow_dx = math.cos(sun_angle) * 0.5
        shadow_dy = 0.3
        
        shadow_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT),
                                        pygame.SRCALPHA)
        
        for obj in self.engine.world.objects:
            if obj.x < min_x - 5 or obj.x > max_x + 5:
                continue
            if obj.y < min_y - 5 or obj.y > max_y + 5:
                continue
            
            elev = obj.get_component(Elevation)
            if not elev or not elev.casts_shadow:
                continue
            
            fp = obj.get_component(Footprint)
            fw = fp.width if fp else 1
            fh = fp.height if fp else 1
            
            sdx = int(shadow_dx * elev.shadow_length * 2)
            sdy = int(shadow_dy * elev.shadow_length * 2)
            
            sx, sy = self.camera.apply(obj.x + sdx, obj.y + sdy)
            sw = int(fw * TILE_SIZE * self.camera.zoom)
            sh = int(fh * TILE_SIZE * self.camera.zoom * 0.6)
            
            pygame.draw.ellipse(shadow_surface, (0, 0, 0, 35),
                                (sx, sy + sh // 2, sw, sh))
        
        self.screen.blit(shadow_surface, (0, 0))

    # ================================================================
    # OBJECTS (Buildings, Vegetation, Infrastructure)
    # ================================================================
    
    def _render_objects(self, min_x, min_y, max_x, max_y):
        visible = []
        for obj in self.engine.world.objects:
            if (min_x - 25 <= obj.x <= max_x + 5
                    and min_y - 25 <= obj.y <= max_y + 5):
                visible.append(obj)
        
        visible.sort(key=lambda o: o.y)
        
        for obj in visible:
            self._draw_object(obj)
    
    def _draw_object(self, obj):
        deco = obj.get_component(Decoration)
        if not deco:
            return
        
        sprite = SpriteSheet.get(deco.sprite_key)
        if not sprite:
            fp = obj.get_component(Footprint)
            fw = fp.width if fp else 1
            fh = fp.height if fp else 1
            sx, sy = self.camera.apply(obj.x, obj.y)
            sw = int(fw * TILE_SIZE * self.camera.zoom)
            sh = int(fh * TILE_SIZE * self.camera.zoom)
            pygame.draw.rect(self.screen,
                             COLORS.get("brick_roman", (150, 100, 80)),
                             (sx, sy, sw, sh))
            return
        
        fp = obj.get_component(Footprint)
        fw = fp.width if fp else 1
        fh = fp.height if fp else 1
        
        sx, sy = self.camera.apply(obj.x, obj.y)
        target_w = int(fw * TILE_SIZE * self.camera.zoom)
        target_h = int(fh * TILE_SIZE * self.camera.zoom)
        
        if target_w > 0 and target_h > 0:
            sprite_w, sprite_h = sprite.get_size()
            scale_w = target_w / max(sprite_w, 1)
            scale_h = target_h / max(sprite_h, 1)
            scale = min(scale_w, scale_h)
            
            final_w = max(1, int(sprite_w * scale))
            final_h = max(1, int(sprite_h * scale))
            
            scaled = pygame.transform.scale(sprite, (final_w, final_h))
            
            offset_x = (target_w - final_w) // 2
            offset_y = (target_h - final_h) // 2
            
            self.screen.blit(scaled, (sx + offset_x, sy + offset_y))
        
        # Fire overlay
        flam = obj.get_component(Flammable)
        if flam and flam.is_burning:
            self._draw_fire_overlay(obj, sx, sy, target_w, target_h)
        
        # Animated effects
        if deco.animation == "fountain":
            self._animate_fountain(obj)
        elif deco.animation == "torch":
            self._animate_torch(obj)
    
    def _draw_fire_overlay(self, obj, sx, sy, w, h):
        fire_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        
        for _ in range(3):
            fx = random.randint(0, max(1, w - 4))
            fy = random.randint(0, max(1, h - 4))
            fw = random.randint(3, min(8, w))
            fh = random.randint(3, min(8, h))
            fc = random.choice([COLORS["fire_core"], COLORS["fire_mid"],
                                COLORS["fire_outer"]])
            pygame.draw.rect(fire_surf, (*fc, 180), (fx, fy, fw, fh))
        
        self.screen.blit(fire_surf, (sx, sy))
    
    def _animate_fountain(self, obj):
        if random.random() < 0.3:
            self.particles.emit_water_splash(
                obj.x + 0.5 + random.uniform(-0.3, 0.3),
                obj.y + 0.5
            )
    
    def _animate_torch(self, obj):
        if random.random() < 0.2:
            self.particles.emit_fire(obj.x + 0.5, obj.y + 0.3, intensity=0.3)

    # ================================================================
    # AGENTS
    # ================================================================
    
    def _render_agents(self):
        tile_px = int(TILE_SIZE * self.camera.zoom)
        
        for agent in self.engine.agents:
            sx, sy = self.camera.apply(agent.x, agent.y)
            size = max(4, tile_px)

            if not agent.is_alive:
                cx = sx + size // 2
                cy = sy + size // 2
                corpse_w = max(4, size * 2 // 3)
                corpse_h = max(2, size // 4)
                pygame.draw.rect(self.screen, (80, 60, 50),
                                 (cx - corpse_w // 2, cy - corpse_h // 2, corpse_w, corpse_h))
                if self.camera.zoom >= 2.0:
                    label = self.font_label.render(f"{agent.name} (dead)", True, (120, 80, 60))
                    self.screen.blit(label, (cx - label.get_width() // 2, cy - 12))
                continue

            if getattr(agent, "is_animal", False):
                self._render_animal(agent, sx, sy, size)
                continue

            # Shadow
            shadow_surf = pygame.Surface((size, size // 3), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow_surf, (0, 0, 0, 50),
                                (0, 0, size, size // 3))
            self.screen.blit(shadow_surf, (sx, sy + size - size // 6))
            
            # Determine colors by role
            body_color = COLORS["tunic_brown"]
            head_detail = COLORS["skin_roman"]
            
            if "Legionary" in agent.role or "Guard" in agent.role:
                body_color = COLORS["legionary_red"]
                head_detail = COLORS["legionary_gold"]
            elif "Senator" in agent.role or "Patrician" in agent.role:
                body_color = COLORS["toga_white"]
                head_detail = COLORS["senator_purple"]
            elif "Merchant" in agent.role or "Trader" in agent.role:
                body_color = COLORS["tunic_brown"]
            elif "Priest" in agent.role:
                body_color = COLORS["toga_white"]
                head_detail = COLORS["pompeii_yellow"]
            elif "Gladiator" in agent.role:
                body_color = COLORS["brick_dark"]
                head_detail = COLORS["legionary_gold"]
            
            # Draw agent (simple pawn shape)
            agent_size = max(3, size // 2)
            cx = sx + size // 2
            cy = sy + size // 2
            
            body_w = max(2, agent_size * 2 // 3)
            body_h = max(2, agent_size)
            pygame.draw.rect(self.screen, body_color,
                             (cx - body_w // 2, cy, body_w, body_h))
            
            head_r = max(2, agent_size // 3)
            pygame.draw.circle(self.screen, COLORS["skin_roman"],
                               (cx, cy - 1), head_r)
            pygame.draw.circle(self.screen, head_detail,
                               (cx, cy - head_r), max(1, head_r // 2))
            
            # Name label at high zoom
            if self.camera.zoom >= 2.0:
                label = self.font_label.render(agent.name, True,
                                               COLORS["ui_text"])
                label_x = sx + size // 2 - label.get_width() // 2
                self.screen.blit(label, (label_x, sy - 12))
            
            # Action indicator
            if agent.action == "MOVING" and self.camera.zoom >= 1.5:
                dot_offset = int(self.anim_timer * 4) % 3
                for d in range(3):
                    if d == dot_offset:
                        continue
                    pygame.draw.circle(self.screen, (*body_color, 150),
                                       (cx - 4 + d * 4, cy + body_h + 3), 1)
            
            if agent.action == "MOVING" and random.random() < 0.1:
                self.particles.emit_dust(agent.x, agent.y + 0.5)

    # Per-species palette: (body, outline, accent)
    _ANIMAL_COLORS = {
        "wolf":  ((35, 190, 175),  (15,  90,  85), (255, 80, 80)),   # teal; red when attacking
        "dog":   ((215, 185,  45), (100, 80,  10), None),             # golden yellow
        "boar":  ((220, 110,  25), (110, 50,   5), None),             # bright orange
        "raven": ((175,  55, 220), ( 80, 20, 110), None),             # violet/magenta
    }

    def _render_animal(self, agent, sx: int, sy: int, size: int) -> None:
        """Draw a species-specific sprite for an Animal."""
        cx = sx + size // 2
        cy = sy + size // 2
        atype = agent.animal_type

        body_c, outline_c, attack_c = self._ANIMAL_COLORS.get(
            atype, ((180, 180, 180), (80, 80, 80), None)
        )

        if atype == "wolf":
            body_color = attack_c if agent.action == "ATTACKING" else body_c
            bw = max(3, size * 3 // 4)
            bh = max(2, size // 3)
            rect = (cx - bw // 2, cy - bh // 2, bw, bh)
            pygame.draw.rect(self.screen, body_color, rect)
            pygame.draw.rect(self.screen, outline_c, rect, 1)
            # Amber eyes at higher zoom
            if size >= 6:
                eye_r = max(1, size // 8)
                pygame.draw.circle(self.screen, (240, 200, 50),
                                   (cx - bw // 4, cy - bh // 4), eye_r)
                pygame.draw.circle(self.screen, (240, 200, 50),
                                   (cx + bw // 4, cy - bh // 4), eye_r)

        elif atype == "dog":
            bw = max(2, size * 2 // 3)
            bh = max(2, size * 3 // 8)
            rect = (cx - bw // 2, cy - bh // 2, bw, bh)
            pygame.draw.rect(self.screen, body_c, rect)
            pygame.draw.rect(self.screen, outline_c, rect, 1)

        elif atype == "boar":
            bw = max(3, size * 4 // 5)
            bh = max(2, size * 2 // 5)
            rect = (cx - bw // 2, cy - bh // 2, bw, bh)
            pygame.draw.rect(self.screen, body_c, rect)
            pygame.draw.rect(self.screen, outline_c, rect, 1)
            # Tusk lines at front-right
            if size >= 6:
                tx = cx + bw // 2
                pygame.draw.line(self.screen, (240, 235, 210),
                                 (tx, cy), (tx + max(1, size // 5), cy - max(1, size // 6)), 1)
                pygame.draw.line(self.screen, (240, 235, 210),
                                 (tx, cy + 1), (tx + max(1, size // 5), cy + max(1, size // 5)), 1)

        elif atype == "raven":
            r = max(2, size // 4)
            pts = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
            pygame.draw.polygon(self.screen, body_c, pts)
            pygame.draw.polygon(self.screen, outline_c, pts, 1)
            # Bright beak dot
            if size >= 5:
                pygame.draw.circle(self.screen, (240, 220, 60),
                                   (cx + r, cy), max(1, size // 8))

        # Health bar at zoom >= 2 if damaged
        if self.camera.zoom >= 2.0 and agent.health < agent.max_health:
            bar_w = max(4, size * 2 // 3)
            bar_h = max(1, size // 8)
            bar_x = cx - bar_w // 2
            bar_y = cy - size // 2 - bar_h - 1
            pygame.draw.rect(self.screen, (80, 20, 20),
                             (bar_x, bar_y, bar_w, bar_h))
            filled = int(bar_w * agent.health / agent.max_health)
            if filled > 0:
                pygame.draw.rect(self.screen, (180, 60, 60),
                                 (bar_x, bar_y, filled, bar_h))

        # Name label at zoom >= 3
        if self.camera.zoom >= 3.0:
            label = self.font_label.render(agent.name, True, (185, 165, 120))
            self.screen.blit(label, (cx - label.get_width() // 2, cy - size // 2 - 14))

    # ================================================================
    # LIGHTING / DAY-NIGHT
    # ================================================================
    
    def _get_sky_color(self):
        t = self.time_of_day
        
        if t < DAWN_START:
            return (15, 12, 25)
        elif t < DAWN_END:
            frac = (t - DAWN_START) / (DAWN_END - DAWN_START)
            return self._lerp_color((15, 12, 25), (135, 160, 200), frac)
        elif t < DUSK_START:
            return (135, 175, 215)
        elif t < DUSK_END:
            frac = (t - DUSK_START) / (DUSK_END - DUSK_START)
            return self._lerp_color((135, 175, 215), (15, 12, 25), frac)
        else:
            return (15, 12, 25)
    
    def _render_lighting(self):
        t = self.time_of_day
        
        if DAWN_END <= t <= DUSK_START:
            darkness = 0
        elif t < DAWN_START or t > DUSK_END:
            darkness = 140
        elif t < DAWN_END:
            frac = (t - DAWN_START) / (DAWN_END - DAWN_START)
            darkness = int(140 * (1 - frac))
        else:
            frac = (t - DUSK_START) / (DUSK_END - DUSK_START)
            darkness = int(140 * frac)
        
        if darkness > 0:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT),
                                     pygame.SRCALPHA)
            overlay.fill((10, 10, 40, darkness))
            
            if darkness > 30:
                for obj in self.engine.world.objects:
                    flam = obj.get_component(Flammable)
                    if flam and flam.is_burning:
                        osx, osy = self.camera.apply(obj.x, obj.y)
                        glow_r = int(3 * TILE_SIZE * self.camera.zoom)
                        glow_surf = pygame.Surface(
                            (glow_r * 2, glow_r * 2), pygame.SRCALPHA)
                        for r in range(glow_r, 0, -2):
                            alpha = int(darkness * (r / glow_r))
                            pygame.draw.circle(glow_surf,
                                               (10, 10, 40, alpha),
                                               (glow_r, glow_r), r)
                        overlay.blit(glow_surf,
                                     (osx - glow_r, osy - glow_r),
                                     special_flags=pygame.BLEND_RGBA_MIN)
            
            self.screen.blit(overlay, (0, 0))
    
    @staticmethod
    def _lerp_color(c1, c2, t):
        t = max(0.0, min(1.0, t))
        return (
            int(c1[0] + (c2[0] - c1[0]) * t),
            int(c1[1] + (c2[1] - c1[1]) * t),
            int(c1[2] + (c2[2] - c1[2]) * t),
        )

    # ================================================================
    # PARTICLES
    # ================================================================
    
    def _update_particles(self, dt):
        self.particles.update(dt)
        
        for obj in self.engine.world.objects:
            flam = obj.get_component(Flammable)
            if flam and flam.is_burning and random.random() < 0.3:
                self.particles.emit_fire(
                    obj.x + random.uniform(0, 1),
                    obj.y + random.uniform(0, 1),
                    flam.fire_intensity / 10.0
                )
                if random.random() < 0.2:
                    self.particles.emit_smoke(obj.x + 0.5, obj.y)

    # ================================================================
    # HOVER / TOOLTIP
    # ================================================================
    
    def _update_hover(self, mx, my):
        wx, wy = self.camera.unapply(mx, my)
        gx, gy = int(wx), int(wy)
        
        self.hovered_entity = None
        
        for agent in self.engine.agents:
            if abs(agent.x - wx) < 0.8 and abs(agent.y - wy) < 0.8:
                self.hovered_entity = agent
                return
        
        tile = self.engine.world.get_tile(gx, gy)
        if tile and tile.building:
            self.hovered_entity = tile.building

    # ================================================================
    # UI
    # ================================================================
    
    def _draw_ui(self, mx, my):
        self._draw_info_bar()
        self._draw_main_textbox()
        self._draw_minimap()
        
        # Draw the window if an agent is selected 
        if self.selected_agent:
            self._draw_agent_window(mx, my)
            self._draw_lif_monitor(self.selected_agent)
        elif self.context_menu_visible:
            self._draw_context_menu()
        elif self.hovered_entity:
            self._draw_tooltip(mx, my)
    
    def _draw_info_bar(self):
        bar_h = 32
        bar_surf = pygame.Surface((SCREEN_WIDTH, bar_h), pygame.SRCALPHA)
        bar_surf.fill((*COLORS["ui_bg"], 200))
        
        pygame.draw.line(bar_surf, COLORS["ui_border_gold"],
                         (0, bar_h - 1), (SCREEN_WIDTH, bar_h - 1), 1)
        
        hour = int(self.time_of_day * 24)
        minute = int((self.time_of_day * 24 - hour) * 60)
        period = ("Dawn" if DAWN_START <= self.time_of_day < DAWN_END else
                  "Day" if DAWN_END <= self.time_of_day < DUSK_START else
                  "Dusk" if DUSK_START <= self.time_of_day < DUSK_END else
                  "Night")
        
        time_text = self.font_body.render(
            f"☀ {hour:02d}:{minute:02d} ({period})", True,
            COLORS["ui_text_accent"])
        bar_surf.blit(time_text, (15, 7))
        
        weather_name = self.engine.weather.current.value
        weather_text = self.font_body.render(
            f"⛅ {weather_name}  Wind: {self.engine.weather.wind_speed:.1f}",
            True, COLORS["ui_text"])
        bar_surf.blit(weather_text, (200, 7))
        
        n = sum(1 for a in self.engine.agents if not getattr(a, "is_animal", False))
        count_text = self.font_body.render(f"Citizens: {n}", True,
                                           COLORS["ui_text_dim"])
        bar_surf.blit(count_text, (SCREEN_WIDTH - 150, 7))
        
        fps_text = self.font_small.render(
            f"FPS: {int(self.clock.get_fps())}", True, COLORS["ui_text_dim"])
        bar_surf.blit(fps_text, (SCREEN_WIDTH - 60, 10))
        
        self.screen.blit(bar_surf, (0, 0))
    
    def _draw_main_textbox(self):
        box_h = 90
        box_y = SCREEN_HEIGHT - box_h - 8
        margin = 15
        box_w = SCREEN_WIDTH - margin * 2
        
        box_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        
        pygame.draw.rect(box_surf, (*COLORS["ui_bg"], 220),
                         (0, 0, box_w, box_h), border_radius=4)
        pygame.draw.rect(box_surf, (*COLORS["ui_border_gold"], 200),
                         (0, 0, box_w, box_h), 2, border_radius=4)
        pygame.draw.rect(box_surf, (*COLORS["ui_border"], 100),
                         (3, 3, box_w - 6, box_h - 6), 1, border_radius=3)
        
        # Pick the first human agent (skip animals which have no drives/thoughts)
        human_agents = [a for a in self.engine.agents if not getattr(a, "is_animal", False)]
        if human_agents:
            hero = human_agents[0]

            name_str = f"⟨ {hero.name} — {hero.role} ⟩"
            name_txt = self.font_title.render(name_str, True,
                                              COLORS["ui_text_accent"])
            box_surf.blit(name_txt, (15, 8))

            thought = hero.current_thought
            if len(thought) > 90:
                thought = thought[:90] + "..."
            thought_txt = self.font_body.render(f'"{thought}"', True,
                                                COLORS["ui_text"])
            box_surf.blit(thought_txt, (15, 35))

            y_drives = 58
            drives_info = [
                ("Hunger", hero.drives["hunger"], COLORS["pompeii_red"]),
                ("Energy", hero.drives["energy"], COLORS["pompeii_blue"]),
                ("Social", hero.drives["social"], COLORS["pompeii_green"]),
            ]
            
            for i, (name, val, color) in enumerate(drives_info):
                bx = 15 + i * 140
                label = self.font_small.render(f"{name}:", True,
                                               COLORS["ui_text_dim"])
                box_surf.blit(label, (bx, y_drives))
                
                bar_w = 80
                bar_x = bx + 50
                pygame.draw.rect(box_surf, (30, 25, 20),
                                 (bar_x, y_drives + 2, bar_w, 10))
                fill_w = int(bar_w * val / 100)
                pygame.draw.rect(box_surf, color,
                                 (bar_x, y_drives + 2, fill_w, 10))
                pygame.draw.rect(box_surf, COLORS["ui_border"],
                                 (bar_x, y_drives + 2, bar_w, 10), 1)
            
            action_txt = self.font_small.render(
                f"Action: {hero.action}", True, COLORS["ui_text_dim"])
            box_surf.blit(action_txt, (box_w - 140, y_drives))
        
        self.screen.blit(box_surf, (margin, box_y))
    
    def _draw_tooltip(self, mx, my):
        entity = self.hovered_entity
        if not entity:
            return
        
        lines = []
        if hasattr(entity, 'get_inspection_data'):
            lines = entity.get_inspection_data()
        elif hasattr(entity, 'name'):
            lines.append(f"◆ {entity.name}")
            
            struct = entity.get_component(
                __import__('roma_aeterna.world.components',
                           fromlist=['Structural']).Structural
            ) if hasattr(entity, 'get_component') else None
            
            if struct:
                lines.append(f"  HP: {int(struct.hp)}/{int(struct.max_hp)}")
                lines.append(f"  Material: {struct.material}")
            
            flam = entity.get_component(
                __import__('roma_aeterna.world.components',
                           fromlist=['Flammable']).Flammable
            ) if hasattr(entity, 'get_component') else None
            
            if flam:
                status = "🔥 BURNING!" if flam.is_burning else "Stable"
                lines.append(f"  Fire: {status}")
        
        if not lines:
            return
        
        padding = 8
        line_h = 16
        max_w = max(self.font_small.size(line)[0] for line in lines) + padding * 2
        total_h = len(lines) * line_h + padding * 2
        
        tip_x = min(mx + 15, SCREEN_WIDTH - max_w - 5)
        tip_y = max(5, my - total_h - 5)
        
        tip_surf = pygame.Surface((max_w, total_h), pygame.SRCALPHA)
        pygame.draw.rect(tip_surf, (*COLORS["ui_bg"], 230),
                         (0, 0, max_w, total_h), border_radius=3)
        pygame.draw.rect(tip_surf, COLORS["ui_border_gold"],
                         (0, 0, max_w, total_h), 1, border_radius=3)
        
        for i, line in enumerate(lines):
            color = COLORS["ui_text_accent"] if i == 0 else COLORS["ui_text"]
            txt = self.font_small.render(line, True, color)
            tip_surf.blit(txt, (padding, padding + i * line_h))
        
        self.screen.blit(tip_surf, (tip_x, tip_y))
    
    def _wrap_text(self, text, font, max_width):
        """Helper to wrap long text into multiple lines for PyGame."""
        lines = []
        for paragraph in text.split('\n'):
            if not paragraph:
                lines.append("")
                continue
            words = paragraph.split(' ')
            current_line = []
            for word in words:
                test_line = ' '.join(current_line + [word])
                if font.size(test_line)[0] <= max_width:
                    current_line.append(word)
                else:
                    lines.append(' '.join(current_line))
                    current_line = [word]
            if current_line:
                lines.append(' '.join(current_line))
        return lines

    def _draw_agent_window(self, mx, my):
        """Draws a large scrollable window showing either the LLM prompt or decision history."""
        agent = self.selected_agent
        if getattr(agent, "is_animal", False):
            display_text = (
                f"Name: {agent.name}\n"
                f"Type: {agent.animal_type}\n"
                f"Health: {agent.health:.1f}/{agent.max_health:.1f}\n"
                f"Action: {agent.action}\n"
                f"Position: ({agent.x:.1f}, {agent.y:.1f})\n"
                f"[Animal — no LLM prompts or decision history]"
            )
            title_label = f"Animal: {agent.name}"
        elif self.agent_window_mode == "prompt":
            from ..llm.prompts import build_prompt
            display_text = build_prompt(
                agent,
                self.engine.world,
                self.engine.agents,
                self.engine.weather
            )
            title_label = f"Agent Prompt: {agent.name}"
        else:
            display_text = agent.get_full_history_text()
            title_label = f"Decision History: {agent.name}"

        win_rect = pygame.Rect(100, 50, SCREEN_WIDTH - 200, SCREEN_HEIGHT - 100)
        
        # Dim the background
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        # Window Background & Border
        pygame.draw.rect(self.screen, (*COLORS["ui_bg"], 250), win_rect, border_radius=8)
        pygame.draw.rect(self.screen, COLORS["ui_border_gold"], win_rect, 2, border_radius=8)
        
        # Header
        header_text = self.font_title.render(title_label, True, COLORS["ui_text_accent"])
        self.screen.blit(header_text, (win_rect.x + 20, win_rect.y + 20))
        pygame.draw.line(self.screen, COLORS["ui_border"], 
                         (win_rect.x + 20, win_rect.y + 45), 
                         (win_rect.right - 20, win_rect.y + 45))

        # Close button hint + mode toggle
        mode_hint = "History" if self.agent_window_mode == "prompt" else "Prompt"
        close_text = self.font_small.render(f"[ ESC to close | Right-click for {mode_hint} ]", True, COLORS["ui_text_dim"])
        self.screen.blit(close_text, (win_rect.right - 280, win_rect.y + 25))

        # Text area setup
        text_rect = pygame.Rect(win_rect.x + 20, win_rect.y + 55, win_rect.width - 40, win_rect.height - 75)
        wrapped_lines = self._wrap_text(display_text, self.font_body, text_rect.width - 20)
        
        line_height = self.font_body.get_height() + 4
        total_text_height = len(wrapped_lines) * line_height
        
        # Clamp scroll position
        max_scroll = max(0, total_text_height - text_rect.height)
        self.agent_window_scroll = min(self.agent_window_scroll, max_scroll)

        # Draw lines clipped to the window boundaries
        old_clip = self.screen.get_clip()
        self.screen.set_clip(text_rect)
        
        y_offset = text_rect.y - self.agent_window_scroll
        for line in wrapped_lines:
            if y_offset + line_height > text_rect.y and y_offset < text_rect.bottom:
                if line:
                    # Highlight ALL CAPS headings in gold
                    color = COLORS["ui_text_accent"] if line.isupper() and len(line) > 3 else COLORS["ui_text"]
                    txt_surf = self.font_body.render(line, True, color)
                    self.screen.blit(txt_surf, (text_rect.x, y_offset))
            y_offset += line_height
            
        self.screen.set_clip(old_clip)

        # Scrollbar
        if max_scroll > 0:
            sb_x = win_rect.right - 10
            sb_y = text_rect.y
            sb_h = text_rect.height
            pygame.draw.rect(self.screen, (60, 50, 40), (sb_x, sb_y, 4, sb_h))
            
            thumb_h = max(30, sb_h * (text_rect.height / total_text_height))
            thumb_y = sb_y + (self.agent_window_scroll / max_scroll) * (sb_h - thumb_h)
            pygame.draw.rect(self.screen, COLORS["ui_border_gold"], (sb_x, thumb_y, 4, thumb_h), border_radius=2)

    def _draw_context_menu(self):
        """Draws a small right-click popup menu with Inspect Prompt / Inspect History."""
        if not self.context_menu_agent:
            return
        
        menu_w = 180
        menu_h = 62
        mx, my = self.context_menu_pos
        
        # Keep menu on screen
        menu_x = min(mx, SCREEN_WIDTH - menu_w - 5)
        menu_y = min(my, SCREEN_HEIGHT - menu_h - 5)
        
        # Background
        menu_surf = pygame.Surface((menu_w, menu_h), pygame.SRCALPHA)
        pygame.draw.rect(menu_surf, (*COLORS["ui_bg"], 240),
                         (0, 0, menu_w, menu_h), border_radius=4)
        pygame.draw.rect(menu_surf, COLORS["ui_border_gold"],
                         (0, 0, menu_w, menu_h), 1, border_radius=4)
        
        # Header (agent name)
        name_txt = self.font_small.render(
            f"◆ {self.context_menu_agent.name}", True, COLORS["ui_text_accent"])
        menu_surf.blit(name_txt, (8, 4))
        
        # Divider
        pygame.draw.line(menu_surf, COLORS["ui_border"],
                         (4, 20), (menu_w - 4, 20))
        
        # Option 1: Inspect Prompt
        mouse_pos = pygame.mouse.get_pos()
        rel_y = mouse_pos[1] - menu_y
        
        opt1_hover = 22 <= rel_y < 40
        opt2_hover = 42 <= rel_y < 60
        
        opt1_color = COLORS["ui_text_accent"] if opt1_hover else COLORS["ui_text"]
        opt2_color = COLORS["ui_text_accent"] if opt2_hover else COLORS["ui_text"]
        
        if opt1_hover:
            pygame.draw.rect(menu_surf, (*COLORS["ui_bg_light"], 200),
                             (2, 22, menu_w - 4, 18))
        if opt2_hover:
            pygame.draw.rect(menu_surf, (*COLORS["ui_bg_light"], 200),
                             (2, 42, menu_w - 4, 18))
        
        txt1 = self.font_small.render("📜  Inspect Prompt", True, opt1_color)
        txt2 = self.font_small.render("📋  Inspect History", True, opt2_color)
        menu_surf.blit(txt1, (10, 24))
        menu_surf.blit(txt2, (10, 44))
        
        self.screen.blit(menu_surf, (menu_x, menu_y))
    
    def _check_context_menu_click(self, click_pos):
        """Check if a click hit one of the context menu options. Returns 'prompt', 'history', or None."""
        if not self.context_menu_visible or not self.context_menu_agent:
            return None
        
        menu_w = 180
        mx, my = self.context_menu_pos
        menu_x = min(mx, SCREEN_WIDTH - menu_w - 5)
        menu_y = min(my, SCREEN_HEIGHT - 62 - 5)
        
        cx, cy = click_pos
        rel_x = cx - menu_x
        rel_y = cy - menu_y
        
        if 0 <= rel_x <= menu_w:
            if 22 <= rel_y < 40:
                return "prompt"
            elif 42 <= rel_y < 60:
                return "history"
        return None
    
    def _draw_lif_monitor(self, agent):
        """Draw a live LIF neuron potential graph in the bottom-right corner."""
        if getattr(agent, "is_animal", False) or agent.brain is None:
            return
        brain = agent.brain
        history = list(brain.potential_history)
        fire_hist = list(brain.fire_history)
        
        if len(history) < 2:
            return
        
        # Layout — bottom-right, above minimap
        graph_w = 180
        graph_h = 80
        padding = 6
        graph_x = SCREEN_WIDTH - graph_w - 10
        graph_y = 155  # Below minimap
        
        # Background panel
        panel = pygame.Surface((graph_w, graph_h + 20), pygame.SRCALPHA)
        pygame.draw.rect(panel, (*COLORS["ui_bg"], 220),
                         (0, 0, graph_w, graph_h + 20), border_radius=4)
        pygame.draw.rect(panel, COLORS["ui_border_gold"],
                         (0, 0, graph_w, graph_h + 20), 1, border_radius=4)
        
        # Title
        title = self.font_label.render("LIF Neuron Monitor", True, COLORS["ui_text_accent"])
        panel.blit(title, (padding, 2))
        
        # Graph area
        gx = padding
        gy = 14
        gw = graph_w - padding * 2
        gh = graph_h - 8
        
        # Graph background
        pygame.draw.rect(panel, (25, 20, 18), (gx, gy, gw, gh))
        
        # Scale — find max for y-axis
        threshold = brain.params.threshold
        max_val = max(threshold * 1.3, max(history) * 1.1) if history else threshold * 1.3
        if max_val < 0.01:
            max_val = 1.0
        
        # Threshold line (dashed)
        thresh_y = gy + gh - int((threshold / max_val) * gh)
        thresh_y = max(gy, min(gy + gh - 1, thresh_y))
        for dash_x in range(gx, gx + gw, 6):
            pygame.draw.line(panel, (195, 168, 92, 150),
                             (dash_x, thresh_y), (min(dash_x + 3, gx + gw), thresh_y), 1)
        
        # Threshold label
        thresh_label = self.font_label.render(f"θ={threshold:.1f}", True, COLORS["ui_text_dim"])
        panel.blit(thresh_label, (gx + gw - 30, thresh_y - 10))
        
        # Plot potential history
        n = len(history)
        step_x = gw / max(n - 1, 1)
        
        points = []
        for i, val in enumerate(history):
            px = gx + int(i * step_x)
            py = gy + gh - int((val / max_val) * gh)
            py = max(gy, min(gy + gh, py))
            points.append((px, py))
        
        # Draw the line
        if len(points) >= 2:
            pygame.draw.lines(panel, (100, 200, 100), False, points, 1)
        
        # Draw fire events as red dots
        for i, fired in enumerate(fire_hist):
            if fired and i < len(points):
                pygame.draw.circle(panel, (255, 60, 60), points[i], 3)
        
        # Current value label
        current_v = history[-1] if history else 0
        refractory = brain.is_refractory
        status_color = (180, 80, 80) if refractory else (100, 200, 100)
        status_text = "REFR" if refractory else f"V={current_v:.1f}"
        val_label = self.font_label.render(status_text, True, status_color)
        panel.blit(val_label, (gx + 2, gy + gh - 10))
        
        # Urgency (input current)
        if brain.input_history:
            urg = brain.input_history[-1]
            urg_label = self.font_label.render(f"I={urg:.1f}", True, COLORS["ui_text_dim"])
            panel.blit(urg_label, (gx + 2, gy + 1))
        
        self.screen.blit(panel, (graph_x, graph_y))
    
    def _draw_minimap(self):
        mm_w, mm_h = 140, 105
        mm_x = SCREEN_WIDTH - mm_w - 10
        mm_y = 42
        
        mm_surf = pygame.Surface((mm_w, mm_h), pygame.SRCALPHA)
        mm_surf.fill((*COLORS["ui_bg"], 180))
        pygame.draw.rect(mm_surf, COLORS["ui_border_gold"],
                         (0, 0, mm_w, mm_h), 1)
        
        sx_scale = mm_w / GRID_WIDTH
        sy_scale = mm_h / GRID_HEIGHT
        
        step = max(1, GRID_WIDTH // mm_w)
        for y in range(0, GRID_HEIGHT, step):
            for x in range(0, GRID_WIDTH, step):
                tile = self.engine.world.get_tile(x, y)
                if not tile:
                    continue
                
                px = int(x * sx_scale)
                py = int(y * sy_scale)
                
                if tile.terrain_type in ("wall", "building_floor"):
                    c = (120, 100, 80)
                elif "road" in tile.terrain_type or "via" in tile.terrain_type:
                    c = (200, 190, 170)
                elif "forum" in tile.terrain_type or tile.terrain_type == "plaza":
                    c = (210, 200, 185)
                elif tile.terrain_type in ("water", "water_shallow"):
                    c = (72, 120, 168)
                elif tile.terrain_type in ("garden",):
                    c = (88, 140, 72)
                elif tile.terrain_type in ("sand_arena", "circus_sand"):
                    c = (210, 190, 150)
                elif tile.elevation > 1.5:
                    c = (140, 128, 100)
                elif tile.terrain_type == "cliff":
                    c = (100, 85, 68)
                else:
                    c = (160, 145, 115)
                
                mm_surf.set_at((min(px, mm_w - 1), min(py, mm_h - 1)), c)
        
        # Camera viewport indicator
        vb = self.camera.get_visible_bounds()
        vx1 = int(max(0, vb[0]) * sx_scale)
        vy1 = int(max(0, vb[1]) * sy_scale)
        vx2 = int(min(GRID_WIDTH, vb[2]) * sx_scale)
        vy2 = int(min(GRID_HEIGHT, vb[3]) * sy_scale)
        pygame.draw.rect(mm_surf, (255, 255, 255, 150),
                         (vx1, vy1, vx2 - vx1, vy2 - vy1), 1)
        
        # Agent dots
        for agent in self.engine.agents:
            ax = int(agent.x * sx_scale)
            ay = int(agent.y * sy_scale)
            if 0 <= ax < mm_w and 0 <= ay < mm_h:
                pygame.draw.circle(mm_surf, (255, 50, 50), (ax, ay), 2)
        
        self.screen.blit(mm_surf, (mm_x, mm_y))