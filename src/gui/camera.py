from config import TILE_SIZE, MIN_ZOOM, MAX_ZOOM

class Camera:
    def __init__(self, map_width_px, map_height_px):
        self.scroll_x = 0
        self.scroll_y = 0
        self.zoom = 1.0
        self.map_w = map_width_px
        self.map_h = map_height_px

    def move(self, dx, dy):
        self.scroll_x += dx
        self.scroll_y += dy

    def change_zoom(self, amount, mouse_pos):
        self.zoom = max(MIN_ZOOM, min(self.zoom + amount, MAX_ZOOM))

    def apply(self, x, y):
        # World Grid -> Screen Pixels
        screen_x = (x * TILE_SIZE * self.zoom) - self.scroll_x
        screen_y = (y * TILE_SIZE * self.zoom) - self.scroll_y
        return int(screen_x), int(screen_y)

    def unapply(self, sx, sy):
        # Screen Pixels -> World Grid
        wx = (sx + self.scroll_x) / (TILE_SIZE * self.zoom)
        wy = (sy + self.scroll_y) / (TILE_SIZE * self.zoom)
        return int(wx), int(wy)
