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
                            self.selected_agent = None  # Close window instead of quitting
                        else:
                            running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if self.selected_agent:
                        # Handle scrolling when window is open
                        if event.button == 4: # Scroll Up
                            self.agent_window_scroll = max(0, self.agent_window_scroll - 40)
                        elif event.button == 5: # Scroll Down
                            self.agent_window_scroll += 40
                        elif event.button == 1: # Left Click
                            # Close window if clicking outside of it
                            win_rect = pygame.Rect(100, 50, SCREEN_WIDTH - 200, SCREEN_HEIGHT - 100)
                            if not win_rect.collidepoint(event.pos):
                                self.selected_agent = None
                    else:
                        # If clicking on an agent, open the window
                        if event.button == 1 and hasattr(self.hovered_entity, 'role'):
                            self.selected_agent = self.hovered_entity
                            self.agent_window_scroll = 0

                # Only pass events to the camera if the UI window isn't open
                if not self.selected_agent:
                    self.camera.handle_event(event)

            self.camera.update(dt)
            self.engine.update(dt)
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
        
        n = len(self.engine.agents)
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
        
        if self.engine.agents:
            hero = self.engine.agents[0]
            
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
        """Draws a large scrollable window showing the exact LLM Context Prompt."""
        # Generate the exact prompt the LLM evaluates
        from ..llm.prompts import build_prompt
        prompt_text = build_prompt(
            self.selected_agent, 
            self.engine.world, 
            self.engine.agents, 
            self.engine.weather
        )

        win_rect = pygame.Rect(100, 50, SCREEN_WIDTH - 200, SCREEN_HEIGHT - 100)
        
        # Dim the background
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        # Window Background & Border
        pygame.draw.rect(self.screen, (*COLORS["ui_bg"], 250), win_rect, border_radius=8)
        pygame.draw.rect(self.screen, COLORS["ui_border_gold"], win_rect, 2, border_radius=8)
        
        # Header
        header_text = self.font_title.render(f"Agent Core Inspection: {self.selected_agent.name}", True, COLORS["ui_text_accent"])
        self.screen.blit(header_text, (win_rect.x + 20, win_rect.y + 20))
        pygame.draw.line(self.screen, COLORS["ui_border"], 
                         (win_rect.x + 20, win_rect.y + 45), 
                         (win_rect.right - 20, win_rect.y + 45))

        # Close button hint
        close_text = self.font_small.render("[ Click outside or press ESC to close ]", True, COLORS["ui_text_dim"])
        self.screen.blit(close_text, (win_rect.right - 230, win_rect.y + 25))

        # Text area setup
        text_rect = pygame.Rect(win_rect.x + 20, win_rect.y + 55, win_rect.width - 40, win_rect.height - 75)
        wrapped_lines = self._wrap_text(prompt_text, self.font_body, text_rect.width - 20)
        
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
