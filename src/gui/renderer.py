import pygame
from config import *
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
            
            # 1. Inputs
            mx, my = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEWHEEL:
                    self.camera.change_zoom(event.y * 0.1, (mx, my))

            keys = pygame.key.get_pressed()
            if keys[pygame.K_w]: self.camera.move(0, -CAMERA_SPEED)
            if keys[pygame.K_s]: self.camera.move(0, CAMERA_SPEED)
            if keys[pygame.K_a]: self.camera.move(-CAMERA_SPEED, 0)
            if keys[pygame.K_d]: self.camera.move(CAMERA_SPEED, 0)

            # 2. Logic Update
            self.engine.update(dt)

            # 3. Render
            self.screen.fill((20, 20, 20))
            
            # Grid
            start_x, start_y = self.camera.unapply(0, 0)
            end_x, end_y = self.camera.unapply(SCREEN_WIDTH, SCREEN_HEIGHT)
            
            # Clamp
            start_x = max(0, int(start_x))
            start_y = max(0, int(start_y))
            end_x = min(GRID_WIDTH, int(end_x) + 2)
            end_y = min(GRID_HEIGHT, int(end_y) + 2)

            # Draw Tiles
            for y in range(start_y, end_y):
                for x in range(start_x, end_x):
                    tile = self.engine.world.tiles[y][x]
                    color = COLORS.get(tile.terrain_type, (255, 0, 255))
                    
                    sx, sy = self.camera.apply(x, y)
                    size = int(TILE_SIZE * self.camera.zoom) + 1
                    
                    pygame.draw.rect(self.screen, color, (sx, sy, size, size))
                    
                    if tile.building:
                        pygame.draw.rect(self.screen, COLORS["building"], (sx+2, sy+2, size-4, size-4))

            # Draw Agents
            for agent in self.engine.agents:
                ax, ay = self.camera.apply(agent.x, agent.y)
                size = int(TILE_SIZE * self.camera.zoom)
                
                c = COLORS["agent_senator"] if agent.role == "Senator" else COLORS["agent_pleb"]
                pygame.draw.circle(self.screen, c, (ax+size//2, ay+size//2), size//3)

            # UI / Inspection
            self._draw_ui(mx, my)

            pygame.display.flip()
        
        pygame.quit()

    def _draw_ui(self, mx, my):
        # Weather
        w_text = f"Weather: {self.engine.weather.current.name}"
        self.screen.blit(self.font.render(w_text, True, (255, 255, 255)), (10, 10))

        # Agent Inspection
        wx, wy = self.camera.unapply(mx, my)
        hovered = None
        for a in self.engine.agents:
            if int(a.x) == int(wx) and int(a.y) == int(wy):
                hovered = a
                break
        
        if hovered:
            data = hovered.get_inspection_data()
            bg = pygame.Surface((200, 20 + len(data)*20))
            bg.set_alpha(200)
            bg.fill((0,0,0))
            self.screen.blit(bg, (mx+10, my))
            
            for i, line in enumerate(data):
                txt = self.font.render(line, True, (255, 255, 255))
                self.screen.blit(txt, (mx+15, my+5 + i*20))
