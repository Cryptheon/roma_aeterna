import pygame
from ..config import *
from .camera import Camera
from .assets import COLORS

class Renderer:
    def __init__(self, engine):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Rome: Aeterna")
        
        self.engine = engine
        self.clock = pygame.time.Clock()
        self.camera = Camera(GRID_WIDTH*TILE_SIZE, GRID_HEIGHT*TILE_SIZE)
        self.font = pygame.font.SysFont("Arial", 14)

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            
            # 1. Inputs (Standard Pygame)
            mx, my = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEWHEEL:
                    self.camera.change_zoom(event.y * 0.1, (mx, my))

            keys = pygame.key.get_pressed()
            move_speed = CAMERA_SPEED / self.camera.zoom # Adjust speed by zoom
            if keys[pygame.K_w]: self.camera.move(0, -move_speed)
            if keys[pygame.K_s]: self.camera.move(0, move_speed)
            if keys[pygame.K_a]: self.camera.move(-move_speed, 0)
            if keys[pygame.K_d]: self.camera.move(move_speed, 0)

            # 2. Logic Update
            self.engine.update(dt)

            # 3. Render
            self.screen.fill((20, 20, 20))
            
            # --- CRITICAL: LOCK THE STATE FOR RENDERING ---
            # This prevents the simulation thread from changing lists while we draw
            with self.engine.lock:
                self._render_world()
                self._render_agents()
            # ---------------------------------------------

            self._draw_ui(mx, my) # UI can be drawn outside lock usually
            pygame.display.flip()
        
        pygame.quit()

    def _render_world(self):
        # Optimization: Only calculate loops once
        start_x, start_y = self.camera.unapply(0, 0)
        end_x, end_y = self.camera.unapply(SCREEN_WIDTH, SCREEN_HEIGHT)
        
        start_x = max(0, int(start_x))
        start_y = max(0, int(start_y))
        end_x = min(GRID_WIDTH, int(end_x) + 2)
        end_y = min(GRID_HEIGHT, int(end_y) + 2)

        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                tile = self.engine.world.tiles[y][x]
                
                # Draw Terrain
                color = COLORS.get(tile.terrain_type, (255, 0, 255))
                sx, sy = self.camera.apply(x, y)
                # +1 to size covers grid lines (anti-tearing)
                size = int(TILE_SIZE * self.camera.zoom) + 1 
                
                pygame.draw.rect(self.screen, color, (sx, sy, size, size))
                
                # Draw Building
                if tile.building:
                    # Visual feedback for burning
                    b_color = COLORS["building"]
                    # We can safely check components because we hold the lock
                    if tile.building.components.get(type(enumerate)): # safer check needed in real code
                        pass
                        
                    pygame.draw.rect(self.screen, b_color, (sx+2, sy+2, size-4, size-4))

    def _render_agents(self):
        for agent in self.engine.agents:
            ax, ay = self.camera.apply(agent.x, agent.y)
            size = int(TILE_SIZE * self.camera.zoom)
            
            c = COLORS["agent_senator"] if agent.role == "Senator" else COLORS["agent_pleb"]
            pygame.draw.circle(self.screen, c, (ax+size//2, ay+size//2), size//3)

    def _draw_ui(self, mx, my):
        # Weather
        w_text = f"Weather: {self.engine.weather.current.name}"
        self.screen.blit(self.font.render(w_text, True, (255, 255, 255)), (10, 10))

        # Agent Inspection
        wx, wy = self.camera.unapply(mx, my)
        hovered = None
        
        # We need the lock again briefly to check agents safely
        with self.engine.lock:
            for a in self.engine.agents:
                # Simple distance check for selection
                if abs(a.x - wx) < 0.8 and abs(a.y - wy) < 0.8:
                    hovered = a
                    break
            
            if hovered:
                data = hovered.get_inspection_data()
                # Copy data out of the lock so we can draw it leisurely
                display_data = list(data)
            else:
                display_data = None

        if display_data:
            bg = pygame.Surface((200, 20 + len(display_data)*20))
            bg.set_alpha(200)
            bg.fill((0,0,0))
            self.screen.blit(bg, (mx+10, my))
            
            for i, line in enumerate(display_data):
                txt = self.font.render(line, True, (255, 255, 255))
                self.screen.blit(txt, (mx+15, my+5 + i*20))