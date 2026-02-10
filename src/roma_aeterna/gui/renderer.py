import pygame
from ..config import *
from .camera import Camera
from .assets import COLORS
from ..world.components import Flammable

class Renderer:
    def __init__(self, engine):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Rome: Aeterna (RPG Ver.)")
        
        self.engine = engine
        self.clock = pygame.time.Clock()
        self.camera = Camera(GRID_WIDTH*TILE_SIZE, GRID_HEIGHT*TILE_SIZE)
        
        # RPG Fonts
        self.font = pygame.font.SysFont("Courier New", 16, bold=True)
        self.ui_font = pygame.font.SysFont("Verdana", 14)

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            
            # Inputs
            mx, my = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                elif event.type == pygame.MOUSEWHEEL:
                    self.camera.change_zoom(event.y * 0.1, (mx, my))

            keys = pygame.key.get_pressed()
            move_speed = CAMERA_SPEED / self.camera.zoom
            if keys[pygame.K_w]: self.camera.move(0, -move_speed)
            if keys[pygame.K_s]: self.camera.move(0, move_speed)
            if keys[pygame.K_a]: self.camera.move(-move_speed, 0)
            if keys[pygame.K_d]: self.camera.move(move_speed, 0)

            self.engine.update(dt)

            # Draw
            self.screen.fill((20, 20, 20))
            
            with self.engine.lock:
                self._render_map()
                self._render_entities()

            self._draw_rpg_ui()
            pygame.display.flip()
        
        pygame.quit()

    def _render_map(self):
        start_x, start_y = self.camera.unapply(0, 0)
        end_x, end_y = self.camera.unapply(SCREEN_WIDTH, SCREEN_HEIGHT)
        
        start_x, start_y = max(0, int(start_x)), max(0, int(start_y))
        end_x, end_y = min(GRID_WIDTH, int(end_x) + 2), min(GRID_HEIGHT, int(end_y) + 2)

        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                tile = self.engine.world.tiles[y][x]
                sx, sy = self.camera.apply(x, y)
                size = int(TILE_SIZE * self.camera.zoom)
                
                # 1. Draw Tile
                color = COLORS.get(tile.terrain_type, COLORS["grass"])
                pygame.draw.rect(self.screen, color, (sx, sy, size, size))
                
                # 2. Draw Grid (Subtle)
                if self.camera.zoom > 0.8:
                    pygame.draw.rect(self.screen, (0,0,0), (sx, sy, size, size), 1)

                # 3. Draw Objects (Pseudo-3D look)
                if tile.building:
                    self._draw_building(sx, sy, size, tile.building)

    def _draw_building(self, x, y, size, building):
        # Determine Color
        name = building.name
        if "Temple" in name: b_c = COLORS["roof_gym"]
        elif "Market" in name: b_c = COLORS["roof_mart"]
        else: b_c = COLORS["roof_house"]
        
        # Draw "House" shape
        # Base
        wall_h = size * 0.6
        pygame.draw.rect(self.screen, COLORS["wall_white"], (x+2, y + size - wall_h, size-4, wall_h))
        
        # Roof (Triangle)
        poly_points = [
            (x, y + size - wall_h),          # Left Base
            (x + size//2, y),                # Top Peak
            (x + size, y + size - wall_h)    # Right Base
        ]
        pygame.draw.polygon(self.screen, b_c, poly_points)
        
        # Door
        pygame.draw.rect(self.screen, COLORS["door"], (x + size//2 - size//6, y + size - size//3, size//3, size//3))

    def _render_entities(self):
        for agent in self.engine.agents:
            ax, ay = self.camera.apply(agent.x, agent.y)
            size = int(TILE_SIZE * self.camera.zoom)
            
            # Shadow
            pygame.draw.ellipse(self.screen, (50,50,50), (ax+4, ay+size-8, size-8, 6))
            
            # Body (Circle for head, Rect for body? Simplification: Just a colored rounded rect)
            color = COLORS["hero"]
            if "Legionary" in agent.role: color = COLORS["legionary"]
            elif "Senator" in agent.role: color = COLORS["senator"]
            
            # Simple "Pawn" shape
            # Head
            pygame.draw.circle(self.screen, (255, 220, 180), (ax+size//2, ay+size//3), size//3) # Skin tone head
            # Hat/Helmet
            pygame.draw.rect(self.screen, color, (ax+size//4, ay+size//6, size//2, size//6))
            # Body
            pygame.draw.rect(self.screen, color, (ax+size//4, ay+size//2, size//2, size//2))

    def _draw_rpg_ui(self):
        # Bottom Textbox
        box_h = 100
        box_y = SCREEN_HEIGHT - box_h - 10
        margin = 20
        
        # Background
        pygame.draw.rect(self.screen, COLORS["ui_border"], (margin, box_y, SCREEN_WIDTH - margin*2, box_h), border_radius=5)
        pygame.draw.rect(self.screen, COLORS["ui_bg"], (margin+4, box_y+4, SCREEN_WIDTH - margin*2 - 8, box_h-8), border_radius=5)
        
        # Text Content (Display the latest thought of the "Hero" or random agent)
        # Find the hero (First agent usually)
        if self.engine.agents:
            hero = self.engine.agents[0]
            name_txt = self.font.render(f"[{hero.name}]", True, (200, 50, 50))
            self.screen.blit(name_txt, (margin + 20, box_y + 15))
            
            thought = hero.current_thought
            # Simple word wrap (cutoff for demo)
            if len(thought) > 80: thought = thought[:80] + "..."
            
            txt_surf = self.ui_font.render(thought, True, COLORS["ui_text"])
            self.screen.blit(txt_surf, (margin + 20, box_y + 45))
            
            # Action indicator
            act_txt = self.ui_font.render(f"Action: {hero.action}", True, (100, 100, 100))
            self.screen.blit(act_txt, (SCREEN_WIDTH - 200, box_y + 70))