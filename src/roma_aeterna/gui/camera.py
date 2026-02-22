import math
import random
import pygame
from ..config import TILE_SIZE, MIN_ZOOM, MAX_ZOOM, DEFAULT_ZOOM, SCREEN_WIDTH, SCREEN_HEIGHT


class Camera:
    def __init__(self, map_width_px, map_height_px):
        self.scroll_x = 0.0
        self.scroll_y = 0.0
        self.zoom = DEFAULT_ZOOM
        self.map_w = map_width_px
        self.map_h = map_height_px

        # --- Dragging (middle-mouse or right-mouse) ---
        self.dragging = False
        self.drag_button = 2            # 2 = right-click, 1 = middle-click
        self._drag_start_mouse = (0, 0)
        self._drag_start_scroll = (0.0, 0.0)

        # --- Smooth zoom ---
        self.target_zoom = DEFAULT_ZOOM
        self.zoom_speed = 8.0           # lerp speed (higher = snappier)
        self.zoom_step = 0.1            # per scroll-wheel click

        # --- Edge scrolling ---
        self.edge_scroll_enabled = True
        self.edge_margin = 20           # pixels from screen edge
        self.edge_scroll_speed = 600.0  # pixels/sec at zoom=1

        # --- Keyboard scrolling ---
        self.key_scroll_speed = 800.0   # pixels/sec at zoom=1

        # --- Smooth follow ---
        self._follow_target = None      # (grid_x, grid_y) or callable
        self.follow_lerp = 5.0          # smoothing factor

        # --- Bounds clamping ---
        self.clamp_to_map = True

        # --- Screen shake ---
        self._shake_timer = 0.0
        self._shake_intensity = 0.0
        self._shake_offset = (0.0, 0.0)
        self._shake_decay = 5.0         # how fast shake fades

        # --- Momentum / inertia (after drag release) ---
        self.momentum_enabled = True
        self._velocity_x = 0.0
        self._velocity_y = 0.0
        self._momentum_friction = 5.0   # higher = stops faster
        self._last_drag_dx = 0.0
        self._last_drag_dy = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def center_on(self, grid_x, grid_y, instant=True):
        """Center the camera on a world grid position."""
        target_sx = grid_x * TILE_SIZE * self.zoom - SCREEN_WIDTH / 2
        target_sy = grid_y * TILE_SIZE * self.zoom - SCREEN_HEIGHT / 2
        if instant:
            self.scroll_x = target_sx
            self.scroll_y = target_sy
        else:
            self._follow_target = (grid_x, grid_y)

    def follow(self, target):
        """
        Smoothly follow a target every frame.
        `target` can be:
          - a tuple (grid_x, grid_y)
          - any object with .x and .y attributes (grid coords)
          - a callable returning (grid_x, grid_y)
        """
        self._follow_target = target

    def stop_follow(self):
        self._follow_target = None

    def move(self, dx, dy):
        self.scroll_x += dx
        self.scroll_y += dy

    def change_zoom(self, amount, mouse_pos=None):
        """Queue a smooth zoom change. `amount` is +/- scroll clicks."""
        self.target_zoom = max(MIN_ZOOM, min(self.target_zoom + amount * self.zoom_step, MAX_ZOOM))
        self._zoom_anchor = mouse_pos  # remember where to anchor

    def set_zoom(self, value, mouse_pos=None):
        """Instantly set zoom level."""
        old_zoom = self.zoom
        self.zoom = max(MIN_ZOOM, min(value, MAX_ZOOM))
        self.target_zoom = self.zoom
        self._apply_zoom_anchor(old_zoom, mouse_pos)

    def shake(self, intensity=6.0, duration=0.3):
        """Trigger a screen-shake effect."""
        self._shake_intensity = intensity
        self._shake_timer = duration

    def apply(self, x, y):
        """World Grid → Screen Pixels (with shake offset)."""
        screen_x = (x * TILE_SIZE * self.zoom) - self.scroll_x + self._shake_offset[0]
        screen_y = (y * TILE_SIZE * self.zoom) - self.scroll_y + self._shake_offset[1]
        return int(screen_x), int(screen_y)

    def unapply(self, sx, sy):
        """Screen Pixels → World Grid (ignores shake)."""
        wx = (sx + self.scroll_x) / (TILE_SIZE * self.zoom)
        wy = (sy + self.scroll_y) / (TILE_SIZE * self.zoom)
        return wx, wy

    def get_visible_bounds(self):
        """Returns (min_x, min_y, max_x, max_y) in grid coords."""
        x1, y1 = self.unapply(0, 0)
        x2, y2 = self.unapply(SCREEN_WIDTH, SCREEN_HEIGHT)
        return int(x1) - 1, int(y1) - 1, int(x2) + 2, int(y2) + 2

    def get_tile_size_on_screen(self):
        """Current pixel size of one tile at the active zoom level."""
        return TILE_SIZE * self.zoom

    # ------------------------------------------------------------------
    # Event handling — call from your main event loop
    # ------------------------------------------------------------------

    def handle_event(self, event):
        """
        Feed pygame events here. Returns True if the camera consumed it.
        """
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == self.drag_button:
                self._start_drag(event.pos)
                return True
            # Scroll-wheel zoom
            if event.button == 4:   # wheel up
                self.change_zoom(+1, event.pos)
                return True
            if event.button == 5:   # wheel down
                self.change_zoom(-1, event.pos)
                return True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == self.drag_button and self.dragging:
                self._end_drag()
                return True

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self._update_drag(event.pos)
                return True

        elif event.type == pygame.MOUSEWHEEL:
            # Some pygame versions use MOUSEWHEEL instead of button 4/5
            pos = pygame.mouse.get_pos()
            self.change_zoom(event.y, pos)
            return True

        return False

    # ------------------------------------------------------------------
    # Per-frame update — call once per frame with delta time
    # ------------------------------------------------------------------

    def update(self, dt):
        """
        Call every frame with dt in seconds.
        Handles smooth zoom, edge scroll, keyboard scroll, follow,
        momentum, shake, and clamping.
        """
        self._update_keyboard_scroll(dt)
        self._update_edge_scroll(dt)
        self._update_smooth_zoom(dt)
        self._update_follow(dt)
        self._update_momentum(dt)
        self._update_shake(dt)
        if self.clamp_to_map:
            self._clamp()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    # --- Dragging ---

    def _start_drag(self, mouse_pos):
        self.dragging = True
        self._drag_start_mouse = mouse_pos
        self._drag_start_scroll = (self.scroll_x, self.scroll_y)
        self._velocity_x = 0.0
        self._velocity_y = 0.0
        self._last_drag_dx = 0.0
        self._last_drag_dy = 0.0

    def _update_drag(self, mouse_pos):
        dx = mouse_pos[0] - self._drag_start_mouse[0]
        dy = mouse_pos[1] - self._drag_start_mouse[1]
        new_sx = self._drag_start_scroll[0] - dx
        new_sy = self._drag_start_scroll[1] - dy

        # Track velocity for momentum
        self._last_drag_dx = self.scroll_x - new_sx
        self._last_drag_dy = self.scroll_y - new_sy

        self.scroll_x = new_sx
        self.scroll_y = new_sy

        # Reset the anchor so small movements stay accurate
        self._drag_start_mouse = mouse_pos
        self._drag_start_scroll = (self.scroll_x, self.scroll_y)

    def _end_drag(self):
        self.dragging = False
        if self.momentum_enabled:
            # Kick off momentum from last frame's drag delta
            self._velocity_x = -self._last_drag_dx * 60  # rough px/sec
            self._velocity_y = -self._last_drag_dy * 60

    # --- Momentum ---

    def _update_momentum(self, dt):
        if self.dragging:
            return
        if abs(self._velocity_x) < 0.5 and abs(self._velocity_y) < 0.5:
            self._velocity_x = 0.0
            self._velocity_y = 0.0
            return
        self.scroll_x += self._velocity_x * dt
        self.scroll_y += self._velocity_y * dt
        decay = math.exp(-self._momentum_friction * dt)
        self._velocity_x *= decay
        self._velocity_y *= decay

    # --- Smooth zoom ---

    _zoom_anchor = None

    def _update_smooth_zoom(self, dt):
        if abs(self.zoom - self.target_zoom) < 0.001:
            self.zoom = self.target_zoom
            return

        old_zoom = self.zoom
        t = 1 - math.exp(-self.zoom_speed * dt)
        self.zoom = old_zoom + (self.target_zoom - old_zoom) * t

        self._apply_zoom_anchor(old_zoom, self._zoom_anchor)

    def _apply_zoom_anchor(self, old_zoom, mouse_pos):
        """Keep the world point under `mouse_pos` stationary."""
        if old_zoom == 0:
            return
        anchor = mouse_pos or (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
        mx, my = anchor
        wx = (mx + self.scroll_x) / (TILE_SIZE * old_zoom)
        wy = (my + self.scroll_y) / (TILE_SIZE * old_zoom)
        self.scroll_x = wx * TILE_SIZE * self.zoom - mx
        self.scroll_y = wy * TILE_SIZE * self.zoom - my

    # --- Edge scrolling ---

    def _update_edge_scroll(self, dt):
        if not self.edge_scroll_enabled or self.dragging:
            return
        if not pygame.mouse.get_focused():
            return

        mx, my = pygame.mouse.get_pos()
        speed = self.edge_scroll_speed * dt
        m = self.edge_margin

        if mx < m:
            self.scroll_x -= speed * (1 - mx / m)
        elif mx > SCREEN_WIDTH - m:
            self.scroll_x += speed * (1 - (SCREEN_WIDTH - mx) / m)

        if my < m:
            self.scroll_y -= speed * (1 - my / m)
        elif my > SCREEN_HEIGHT - m:
            self.scroll_y += speed * (1 - (SCREEN_HEIGHT - my) / m)

    # --- Keyboard scrolling ---

    def _update_keyboard_scroll(self, dt):
        if self.dragging:
            return
        keys = pygame.key.get_pressed()
        speed = self.key_scroll_speed * dt

        dx = dy = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += speed
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy -= speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy += speed

        if dx or dy:
            self._velocity_x = 0
            self._velocity_y = 0
            self.scroll_x += dx
            self.scroll_y += dy

    # --- Follow ---

    def _update_follow(self, dt):
        if self._follow_target is None:
            return

        # Resolve target to (gx, gy)
        t = self._follow_target
        if callable(t):
            gx, gy = t()
        elif hasattr(t, 'x') and hasattr(t, 'y'):
            gx, gy = t.x, t.y
        else:
            gx, gy = t

        target_sx = gx * TILE_SIZE * self.zoom - SCREEN_WIDTH / 2
        target_sy = gy * TILE_SIZE * self.zoom - SCREEN_HEIGHT / 2

        lerp = 1 - math.exp(-self.follow_lerp * dt)
        self.scroll_x += (target_sx - self.scroll_x) * lerp
        self.scroll_y += (target_sy - self.scroll_y) * lerp

    # --- Screen shake ---

    def _update_shake(self, dt):
        if self._shake_timer <= 0:
            self._shake_offset = (0.0, 0.0)
            return
        self._shake_timer -= dt
        progress = max(self._shake_timer, 0)
        intensity = self._shake_intensity * progress
        self._shake_offset = (
            random.uniform(-intensity, intensity),
            random.uniform(-intensity, intensity),
        )

    # --- Clamping ---

    def _clamp(self):
        """Prevent the camera from scrolling past the map edges."""
        view_w = SCREEN_WIDTH
        view_h = SCREEN_HEIGHT
        world_w = self.map_w * self.zoom
        world_h = self.map_h * self.zoom

        if world_w <= view_w:
            self.scroll_x = -(view_w - world_w) / 2
        else:
            self.scroll_x = max(0, min(self.scroll_x, world_w - view_w))

        if world_h <= view_h:
            self.scroll_y = -(view_h - world_h) / 2
        else:
            self.scroll_y = max(0, min(self.scroll_y, world_h - view_h))
