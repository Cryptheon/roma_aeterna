"""
PauseMenu — Windowed overlay shown when the simulation is paused.

Floats centered on screen with a semi-transparent background so the
world is still faintly visible. Tabs:
  AGENTS  — scrollable roster + per-agent detail (STATE / DECISIONS / LLM CALLS)
  GRAPHS  — action distribution, LIF activity, drive heatmap
  STATS   — session overview and per-agent performance table
  VOLUME  — music volume slider
"""

import pygame
from collections import Counter
from typing import Any, List, Optional

# ── Window geometry ──────────────────────────────────────────────────────────
_MX       = 80          # horizontal margin (left & right)
_MY       = 46          # vertical margin (top & bottom)
_TOP_H    = 50          # top bar height inside window
_SIDE_W   = 155         # left tab sidebar width
_ROSTER_W = 310         # agent roster panel width (AGENTS tab)
_PAD      = 12          # general padding
_ITEM_H   = 58          # height of one roster row
_ROW_H    = 28          # height of one stats table row
_VEIL_A   = 148         # veil alpha (0=invisible, 255=opaque) — slightly dim

# ── Palette ──────────────────────────────────────────────────────────────────
_BG      = (20,  17,  14)
_PANEL   = (32,  28,  24)
_BORDER  = (72,  62,  46)
_SEL     = (62,  52,  30)
_TEXT    = (220, 210, 190)
_DIM     = (130, 120, 100)
_GOLD    = (210, 170,  80)
_GREEN   = ( 80, 190,  90)
_RED     = (210,  70,  60)
_YELLOW  = (220, 190,  50)
_ORANGE  = (220, 140,  50)

_DRIVE_COLORS = {
    "hunger":  _ORANGE,
    "thirst":  (80, 160, 220),
    "energy":  (180, 130, 220),
    "social":  _GREEN,
    "comfort": (160, 200, 160),
}

_TABS = ["AGENTS", "GRAPHS", "STATS", "VOLUME"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _bar(surface, x, y, w, h, frac, fg, bg=(50, 44, 38)):
    pygame.draw.rect(surface, bg, (x, y, w, h))
    fw = max(0, int(w * max(0.0, min(1.0, frac))))
    if fw:
        pygame.draw.rect(surface, fg, (x, y, fw, h))
    pygame.draw.rect(surface, _BORDER, (x, y, w, h), 1)


def _panel(surface, rect):
    pygame.draw.rect(surface, _PANEL, rect)
    pygame.draw.rect(surface, _BORDER, rect, 1)


def _clip(surface, clip, fn):
    prev = surface.get_clip()
    surface.set_clip(clip)
    fn()
    surface.set_clip(prev)


def _hbar_chart(surface, rect, items, font, max_val=None):
    """Draw a simple labeled horizontal bar chart inside rect.
    items = [(label, value, color), ...]"""
    if not items:
        return
    max_v = max_val or max(v for _, v, _ in items) or 1
    row_h = max(14, rect.h // max(len(items), 1))
    label_w = 130
    for i, (label, val, col) in enumerate(items):
        y = rect.y + i * row_h
        if y + row_h > rect.bottom:
            break
        lbl = font.render(label[:20], True, _DIM)
        surface.blit(lbl, (rect.x, y + (row_h - lbl.get_height()) // 2))
        bx = rect.x + label_w
        bw = rect.w - label_w - 40
        _bar(surface, bx, y + 4, bw, row_h - 8, val / max_v, col)
        cnt = font.render(str(val), True, _TEXT)
        surface.blit(cnt, (bx + bw + 4, y + (row_h - cnt.get_height()) // 2))


# ── Main class ────────────────────────────────────────────────────────────────

class PauseMenu:
    """Windowed pause overlay rendered over the frozen game world."""

    def __init__(self, renderer: Any) -> None:
        self._r = renderer
        self._engine = renderer.engine
        self._screen = renderer.screen

        self._tab: str = "AGENTS"
        self._agent_idx: int = 0
        self._dtab: str = "STATE"
        self._roster_scroll: int = 0
        self._detail_scroll: int = 0
        self._vol_dragging: bool = False
        self._vol_btns: list = []

        # Fonts (reuse renderer's)
        self._ft = renderer.font_title   # 18 bold
        self._fb = renderer.font_body    # 14
        self._fs = renderer.font_small   # 11
        self._fl = renderer.font_label   # 10

        self._W: int = 0
        self._H: int = 0

    # ================================================================
    # PUBLIC API
    # ================================================================

    def draw(self) -> None:
        screen = self._screen
        W, H = screen.get_size()
        self._W, self._H = W, H

        # Semi-transparent full-screen veil — low enough to glimpse the world
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((0, 0, 0, _VEIL_A))
        screen.blit(veil, (0, 0))

        # Floating window panel
        win = self._win()
        pygame.draw.rect(screen, _BG, win, border_radius=6)
        pygame.draw.rect(screen, _BORDER, win, 2, border_radius=6)

        self._draw_topbar(win)
        self._draw_sidebar(win)
        self._draw_content(win)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._engine.paused = False
            elif event.key == pygame.K_TAB:
                idx = _TABS.index(self._tab)
                self._tab = _TABS[(idx + 1) % len(_TABS)]

        elif event.type == pygame.MOUSEWHEEL:
            if self._tab in ("AGENTS", "STATS"):
                mx, my = pygame.mouse.get_pos()
                if self._tab == "AGENTS":
                    if self._roster_rect().collidepoint(mx, my):
                        self._roster_scroll = max(0, self._roster_scroll - event.y * _ITEM_H)
                    elif self._detail_rect().collidepoint(mx, my):
                        self._detail_scroll = max(0, self._detail_scroll - event.y * 20)
                else:
                    self._roster_scroll = max(0, self._roster_scroll - event.y * _ROW_H)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._on_click(event.pos)

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._vol_dragging = False

        elif event.type == pygame.MOUSEMOTION:
            if self._vol_dragging and self._tab == "VOLUME":
                self._drag_volume(event.pos[0])

    # ================================================================
    # LAYOUT
    # ================================================================

    def _win(self) -> pygame.Rect:
        return pygame.Rect(_MX, _MY, self._W - 2 * _MX, self._H - 2 * _MY)

    def _content_rect(self) -> pygame.Rect:
        win = self._win()
        return pygame.Rect(win.x + _SIDE_W, win.y + _TOP_H,
                           win.w - _SIDE_W, win.h - _TOP_H)

    def _roster_rect(self) -> pygame.Rect:
        cr = self._content_rect()
        return pygame.Rect(cr.x, cr.y, _ROSTER_W, cr.h)

    def _detail_rect(self) -> pygame.Rect:
        cr = self._content_rect()
        return pygame.Rect(cr.x + _ROSTER_W, cr.y, cr.w - _ROSTER_W, cr.h)

    def _agents(self) -> List[Any]:
        return [a for a in self._engine.agents
                if not getattr(a, "is_animal", False)]

    def _current_agent(self) -> Optional[Any]:
        agents = self._agents()
        if not agents:
            return None
        return agents[min(self._agent_idx, len(agents) - 1)]

    # ================================================================
    # TOP BAR
    # ================================================================

    def _draw_topbar(self, win: pygame.Rect) -> None:
        bar = pygame.Rect(win.x, win.y, win.w, _TOP_H)
        pygame.draw.rect(self._screen, _PANEL, bar, border_top_left_radius=6, border_top_right_radius=6)
        pygame.draw.line(self._screen, _BORDER,
                         (win.x, win.y + _TOP_H - 1), (win.right, win.y + _TOP_H - 1))

        title = self._ft.render("⏸  PAUSED", True, _GOLD)
        self._screen.blit(title, (win.x + _SIDE_W + _PAD, win.y + (_TOP_H - title.get_height()) // 2))

        hint = self._fs.render("SPACE / ESC to resume  ·  TAB cycles tabs", True, _DIM)
        self._screen.blit(hint, (win.right - hint.get_width() - _PAD,
                                 win.y + (_TOP_H - hint.get_height()) // 2))

        from roma_aeterna.config import TPS
        tick = self._engine.tick_count
        secs = tick // TPS
        info = self._fb.render(f"Tick {tick:,}  ·  {secs // 60:02d}:{secs % 60:02d}", True, _TEXT)
        self._screen.blit(info, (win.x + win.w // 2 - info.get_width() // 2,
                                 win.y + (_TOP_H - info.get_height()) // 2))

    # ================================================================
    # SIDEBAR
    # ================================================================

    def _draw_sidebar(self, win: pygame.Rect) -> None:
        side = pygame.Rect(win.x, win.y + _TOP_H, _SIDE_W, win.h - _TOP_H)
        pygame.draw.rect(self._screen, _PANEL, side, border_bottom_left_radius=6)
        pygame.draw.line(self._screen, _BORDER,
                         (win.x + _SIDE_W - 1, win.y + _TOP_H),
                         (win.x + _SIDE_W - 1, win.bottom))

        for i, tab in enumerate(_TABS):
            y = win.y + _TOP_H + _PAD + i * 46
            rect = pygame.Rect(win.x + 6, y, _SIDE_W - 12, 38)
            bg = _SEL if tab == self._tab else _PANEL
            pygame.draw.rect(self._screen, bg, rect, border_radius=4)
            pygame.draw.rect(self._screen, _BORDER, rect, 1, border_radius=4)
            lbl = self._fb.render(tab, True, _GOLD if tab == self._tab else _TEXT)
            self._screen.blit(lbl, (rect.x + (rect.w - lbl.get_width()) // 2,
                                    rect.y + (rect.h - lbl.get_height()) // 2))

    # ================================================================
    # CONTENT DISPATCH
    # ================================================================

    def _draw_content(self, win: pygame.Rect) -> None:
        cr = self._content_rect()
        if self._tab == "AGENTS":
            self._draw_agents_tab(cr)
        elif self._tab == "GRAPHS":
            self._draw_graphs_tab(cr)
        elif self._tab == "STATS":
            self._draw_stats_tab(cr)
        elif self._tab == "VOLUME":
            self._draw_volume_tab(cr)

    # ================================================================
    # AGENTS TAB
    # ================================================================

    def _draw_agents_tab(self, cr: pygame.Rect) -> None:
        self._draw_roster()
        self._draw_detail()

    def _draw_roster(self) -> None:
        rect = self._roster_rect()
        _panel(self._screen, rect)
        agents = self._agents()
        inner = pygame.Rect(rect.x + 1, rect.y + 1, rect.w - 2, rect.h - 2)

        def _draw():
            y = inner.y - self._roster_scroll
            for i, agent in enumerate(agents):
                ir = pygame.Rect(inner.x, y, inner.w, _ITEM_H)
                if ir.bottom >= inner.y and ir.top <= inner.bottom:
                    bg = _SEL if i == self._agent_idx else _PANEL
                    pygame.draw.rect(self._screen, bg, ir)
                    pygame.draw.line(self._screen, _BORDER,
                                     (ir.x, ir.bottom - 1), (ir.right, ir.bottom - 1))

                    name_s = self._fb.render(agent.name, True,
                                             _GOLD if i == self._agent_idx else _TEXT)
                    self._screen.blit(name_s, (ir.x + _PAD, ir.y + 4))
                    role_s = self._fs.render(agent.role, True, _DIM)
                    self._screen.blit(role_s, (ir.x + _PAD, ir.y + 22))
                    action = getattr(agent, "action", "IDLE")
                    act_col = _GREEN if action not in ("IDLE", "REST", "SLEEP") else _DIM
                    self._screen.blit(self._fs.render(action, True, act_col),
                                      (ir.x + _PAD, ir.y + 38))

                    hp = max(0.0, min(1.0, agent.health / 100.0))
                    hp_col = _GREEN if hp > 0.5 else (_YELLOW if hp > 0.25 else _RED)
                    bx = ir.right - 72 - _PAD
                    _bar(self._screen, bx, ir.y + 8, 68, 8, hp, hp_col)
                    self._screen.blit(self._fl.render(f"HP {agent.health:.0f}", True, _DIM),
                                      (bx, ir.y + 20))
                y += _ITEM_H

        _clip(self._screen, inner, _draw)

    def _draw_detail(self) -> None:
        rect = self._detail_rect()
        _panel(self._screen, rect)
        agent = self._current_agent()
        if agent is None:
            self._screen.blit(self._fb.render("No agents", True, _DIM),
                               (rect.x + _PAD, rect.y + _PAD))
            return

        dtabs = ["STATE", "DECISIONS", "LLM CALLS"]
        tab_h = 30
        tab_w = rect.w // len(dtabs)
        for i, dt in enumerate(dtabs):
            tr = pygame.Rect(rect.x + i * tab_w, rect.y, tab_w, tab_h)
            pygame.draw.rect(self._screen, _SEL if dt == self._dtab else _PANEL, tr)
            pygame.draw.rect(self._screen, _BORDER, tr, 1)
            s = self._fs.render(dt, True, _GOLD if dt == self._dtab else _TEXT)
            self._screen.blit(s, (tr.x + (tr.w - s.get_width()) // 2,
                                  tr.y + (tr.h - s.get_height()) // 2))

        content = pygame.Rect(rect.x, rect.y + tab_h, rect.w, rect.h - tab_h)
        if self._dtab == "STATE":
            self._draw_state(agent, content)
        elif self._dtab == "DECISIONS":
            self._draw_decisions(agent, content)
        elif self._dtab == "LLM CALLS":
            self._draw_llm(agent, content)

    def _draw_state(self, agent: Any, rect: pygame.Rect) -> None:
        x, y = rect.x + _PAD, rect.y + _PAD
        self._screen.blit(self._fs.render(
            f"Position: ({int(agent.x)}, {int(agent.y)})", True, _DIM), (x, y)); y += 18

        drives = getattr(agent, "drives", {})
        self._screen.blit(self._fb.render("Drives", True, _GOLD), (x, y)); y += 20
        for drive, val in drives.items():
            col = _DRIVE_COLORS.get(drive, _TEXT)
            self._screen.blit(self._fs.render(f"{drive.capitalize():8s} {val:5.1f}", True, _TEXT), (x, y))
            _bar(self._screen, x + 130, y + 2, rect.w - 152 - _PAD, 10, val / 100.0, col)
            y += 18
        y += 6

        brain = getattr(agent, "brain", None)
        if brain:
            pot = brain.potential
            thr = getattr(brain, "threshold", None) or getattr(
                getattr(brain, "params", None), "threshold", 18.0)
            self._screen.blit(self._fb.render("LIF Neuron", True, _GOLD), (x, y)); y += 20
            self._screen.blit(self._fs.render(f"Potential {pot:.2f} / {thr:.2f}", True, _TEXT), (x, y))
            _bar(self._screen, x + 155, y + 2, rect.w - 177 - _PAD, 10, pot / max(thr, 1.0), _YELLOW)
            y += 24

        items = getattr(agent, "inventory", []) or []
        self._screen.blit(self._fb.render(f"Inventory ({len(items)} items)", True, _GOLD), (x, y)); y += 20
        for item in items[:8]:
            self._screen.blit(self._fs.render(f"  · {getattr(item, 'name', str(item))}", True, _TEXT), (x, y))
            y += 16
        if len(items) > 8:
            self._screen.blit(self._fs.render(f"  … +{len(items)-8} more", True, _DIM), (x, y))

    def _draw_decisions(self, agent: Any, rect: pygame.Rect) -> None:
        history = agent.decision_history or []
        inner = pygame.Rect(rect.x + 1, rect.y + 1, rect.w - 2, rect.h - 2)

        def _draw():
            y = inner.y + _PAD - self._detail_scroll
            for d in reversed(history):
                src = "AUTO" if d.get("source") == "autopilot" else "LLM"
                col = _DIM if src == "AUTO" else _GOLD
                header = f"[{d.get('tick', 0):,}] {src}  {d.get('action','?')}"
                if d.get("target"):
                    header += f" → {d['target']}"
                if inner.y <= y <= inner.bottom:
                    self._screen.blit(self._fs.render(header, True, col), (inner.x + _PAD, y))
                y += 16
                for line in self._wrap(d.get("thought", ""), inner.w - _PAD * 2, self._fl):
                    if inner.y <= y <= inner.bottom:
                        self._screen.blit(self._fl.render(line, True, _TEXT), (inner.x + _PAD * 2, y))
                    y += 14
                if d.get("speech"):
                    sp = f'"{d["speech"][:80]}"'
                    if inner.y <= y <= inner.bottom:
                        self._screen.blit(self._fl.render(sp, True, _GREEN), (inner.x + _PAD * 2, y))
                    y += 14
                if inner.y <= y <= inner.bottom:
                    pygame.draw.line(self._screen, _BORDER,
                                     (inner.x + _PAD, y + 2), (inner.right - _PAD, y + 2))
                y += 8

        _clip(self._screen, inner, _draw)

    def _draw_llm(self, agent: Any, rect: pygame.Rect) -> None:
        log = agent.llm_response_log or []
        inner = pygame.Rect(rect.x + 1, rect.y + 1, rect.w - 2, rect.h - 2)
        if not log:
            self._screen.blit(self._fs.render("No LLM calls recorded yet.", True, _DIM),
                               (inner.x + _PAD, inner.y + _PAD))
            return

        def _draw():
            y = inner.y + _PAD - self._detail_scroll
            for entry in reversed(log):
                err = entry.get("error", "")
                hdr = f"[{entry.get('tick', 0):,}]  {'ERROR' if err else 'OK'}"
                hdr_col = _RED if err else _GOLD
                if inner.y <= y <= inner.bottom:
                    self._screen.blit(self._fs.render(hdr, True, hdr_col), (inner.x + _PAD, y))
                y += 16
                body = err or entry.get("parsed", "") or ""
                for line in self._wrap(body[:300], inner.w - _PAD * 2, self._fl):
                    if inner.y <= y <= inner.bottom:
                        self._screen.blit(
                            self._fl.render(line, True, _RED if err else _TEXT),
                            (inner.x + _PAD * 2, y))
                    y += 13
                if entry.get("raw"):
                    if inner.y <= y <= inner.bottom:
                        self._screen.blit(self._fl.render("raw ▾", True, _DIM), (inner.x + _PAD * 2, y))
                    y += 13
                    for line in self._wrap(entry["raw"][:300], inner.w - _PAD * 2, self._fl):
                        if inner.y <= y <= inner.bottom:
                            self._screen.blit(self._fl.render(line, True, _DIM), (inner.x + _PAD * 2, y))
                        y += 13
                if inner.y <= y <= inner.bottom:
                    pygame.draw.line(self._screen, _BORDER,
                                     (inner.x + _PAD, y + 2), (inner.right - _PAD, y + 2))
                y += 8

        _clip(self._screen, inner, _draw)

    # ================================================================
    # GRAPHS TAB
    # ================================================================

    def _draw_graphs_tab(self, cr: pygame.Rect) -> None:
        _panel(self._screen, cr)
        agents = self._agents()
        x0, y0 = cr.x + _PAD, cr.y + _PAD
        half_w = (cr.w - _PAD * 3) // 2
        half_h = (cr.h - _PAD * 3) // 2

        panels = [
            pygame.Rect(x0,                  y0,                  half_w, half_h),
            pygame.Rect(x0 + half_w + _PAD,  y0,                  half_w, half_h),
            pygame.Rect(x0,                  y0 + half_h + _PAD,  half_w, half_h),
            pygame.Rect(x0 + half_w + _PAD,  y0 + half_h + _PAD,  half_w, half_h),
        ]
        for p in panels:
            pygame.draw.rect(self._screen, _PANEL, p, border_radius=4)
            pygame.draw.rect(self._screen, _BORDER, p, 1, border_radius=4)

        self._graph_action_dist(panels[0], agents)
        self._graph_llm_vs_auto(panels[1], agents)
        self._graph_drive_heatmap(panels[2], agents)
        self._graph_llm_timeline(panels[3])

    def _graph_action_dist(self, rect: pygame.Rect, agents: List[Any]) -> None:
        """Top-8 action types across all agents (horizontal bar chart)."""
        title = self._fs.render("Action Distribution (all agents)", True, _GOLD)
        self._screen.blit(title, (rect.x + _PAD, rect.y + _PAD))

        counts: Counter = Counter()
        for a in agents:
            for d in a.decision_history:
                counts[d.get("action", "IDLE")] += 1
        top = counts.most_common(8)
        if not top:
            self._screen.blit(self._fl.render("No decisions yet.", True, _DIM),
                               (rect.x + _PAD, rect.y + 36))
            return

        max_v = top[0][1]
        chart = pygame.Rect(rect.x + _PAD, rect.y + 34, rect.w - _PAD * 2, rect.h - 42)
        row_h = chart.h // len(top)
        label_w = 90
        for i, (action, count) in enumerate(top):
            y = chart.y + i * row_h
            col = _GOLD if action not in ("IDLE", "MOVE") else _DIM
            if action == "TALK":
                col = _GREEN
            elif action in ("ATTACK", "FLEE"):
                col = _RED
            elif action == "BUY":
                col = (80, 200, 220)
            lbl = self._fl.render(action[:14], True, _DIM)
            self._screen.blit(lbl, (chart.x, y + (row_h - lbl.get_height()) // 2))
            bx = chart.x + label_w
            bw = chart.w - label_w - 36
            bh = max(6, row_h - 6)
            _bar(self._screen, bx, y + 3, bw, bh, count / max_v, col)
            cnt_s = self._fl.render(str(count), True, _TEXT)
            self._screen.blit(cnt_s, (bx + bw + 4, y + (row_h - cnt_s.get_height()) // 2))

    def _graph_llm_vs_auto(self, rect: pygame.Rect, agents: List[Any]) -> None:
        """Per-agent stacked bar: autopilot vs LLM decisions."""
        title = self._fs.render("Autopilot vs LLM per Agent", True, _GOLD)
        self._screen.blit(title, (rect.x + _PAD, rect.y + _PAD))

        if not agents:
            return
        chart = pygame.Rect(rect.x + _PAD, rect.y + 34, rect.w - _PAD * 2, rect.h - 42)
        row_h = max(12, chart.h // max(len(agents), 1))
        label_w = 80

        for i, agent in enumerate(agents):
            y = chart.y + i * row_h
            if y + row_h > chart.bottom:
                break
            auto = sum(1 for d in agent.decision_history if d.get("source") == "autopilot")
            llm  = sum(1 for d in agent.decision_history if d.get("source") != "autopilot")
            total = auto + llm or 1

            name_s = self._fl.render(agent.name[:12], True, _DIM)
            self._screen.blit(name_s, (chart.x, y + (row_h - name_s.get_height()) // 2))

            bx = chart.x + label_w
            bw = chart.w - label_w - _PAD
            bh = max(6, row_h - 6)

            # Background
            pygame.draw.rect(self._screen, (50, 44, 38), (bx, y + 3, bw, bh))
            # Autopilot portion
            aw = int(bw * auto / total)
            if aw:
                pygame.draw.rect(self._screen, _DIM, (bx, y + 3, aw, bh))
            # LLM portion
            if llm:
                lw = int(bw * llm / total)
                pygame.draw.rect(self._screen, _GOLD, (bx + aw, y + 3, lw, bh))
            pygame.draw.rect(self._screen, _BORDER, (bx, y + 3, bw, bh), 1)

            # Counts
            tag = self._fl.render(f"A:{auto} L:{llm}", True, _TEXT)
            self._screen.blit(tag, (bx + bw + 2, y + (row_h - tag.get_height()) // 2))

        # Legend
        ly = chart.bottom - 14
        pygame.draw.rect(self._screen, _DIM,  (chart.x, ly, 12, 10))
        self._screen.blit(self._fl.render("Autopilot", True, _DIM), (chart.x + 16, ly))
        pygame.draw.rect(self._screen, _GOLD, (chart.x + 80, ly, 12, 10))
        self._screen.blit(self._fl.render("LLM", True, _GOLD), (chart.x + 96, ly))

    def _graph_drive_heatmap(self, rect: pygame.Rect, agents: List[Any]) -> None:
        """Drive-level heatmap: rows = agents, columns = drives."""
        title = self._fs.render("Drive Health Heatmap  (green = low/ok · red = critical)", True, _GOLD)
        self._screen.blit(title, (rect.x + _PAD, rect.y + _PAD))

        drives = ["hunger", "thirst", "energy", "social", "comfort"]
        if not agents:
            return

        header_h = 34
        chart = pygame.Rect(rect.x + _PAD, rect.y + header_h, rect.w - _PAD * 2, rect.h - header_h - _PAD)
        name_w = 88
        cell_w = (chart.w - name_w) // len(drives)
        row_h  = max(10, chart.h // max(len(agents), 1))

        # Column headers
        for j, drv in enumerate(drives):
            hx = chart.x + name_w + j * cell_w
            hs = self._fl.render(drv[:7].capitalize(), True, _DIM)
            self._screen.blit(hs, (hx + (cell_w - hs.get_width()) // 2, chart.y - 14))

        for i, agent in enumerate(agents):
            y = chart.y + i * row_h
            if y + row_h > chart.bottom:
                break
            # Agent name
            ns = self._fl.render(agent.name[:12], True, _TEXT)
            self._screen.blit(ns, (chart.x, y + (row_h - ns.get_height()) // 2))

            drv_vals = getattr(agent, "drives", {})
            for j, drv in enumerate(drives):
                val = drv_vals.get(drv, 0) / 100.0
                # Colour: green at 0, yellow at 0.5, red at 1.0
                r = int(min(255, val * 2 * 210))
                g = int(min(255, (1 - val) * 2 * 190))
                col = (r, g, 40)
                cx_ = chart.x + name_w + j * cell_w + 2
                cw_ = cell_w - 4
                ch_ = max(6, row_h - 4)
                pygame.draw.rect(self._screen, col, (cx_, y + 2, cw_, ch_), border_radius=2)
                pct = self._fl.render(f"{val*100:.0f}", True, (220, 220, 220))
                self._screen.blit(pct, (cx_ + (cw_ - pct.get_width()) // 2,
                                        y + (row_h - pct.get_height()) // 2))

    def _graph_llm_timeline(self, rect: pygame.Rect) -> None:
        """Bar chart of LLM calls bucketed over simulation time."""
        title = self._fs.render("LLM Calls Over Time", True, _GOLD)
        self._screen.blit(title, (rect.x + _PAD, rect.y + _PAD))

        ticks_data = list(self._engine.llm_call_ticks)
        if not ticks_data:
            self._screen.blit(self._fl.render("No LLM calls recorded yet.", True, _DIM),
                               (rect.x + _PAD, rect.y + 36))
            return

        chart = pygame.Rect(rect.x + _PAD, rect.y + 34,
                            rect.w - _PAD * 2, rect.h - 50)

        n_buckets = 24
        t_min, t_max = ticks_data[0], ticks_data[-1]
        span = max(t_max - t_min, 1)
        bucket_size = span / n_buckets

        counts = [0] * n_buckets
        for t in ticks_data:
            idx = min(int((t - t_min) / bucket_size), n_buckets - 1)
            counts[idx] += 1
        max_count = max(counts) or 1

        bar_w = max(2, chart.w // n_buckets - 1)
        gap = (chart.w - bar_w * n_buckets) // max(n_buckets - 1, 1)

        for i, count in enumerate(counts):
            bh = max(0, int(chart.h * count / max_count))
            bx = chart.x + i * (bar_w + gap)
            by = chart.bottom - bh
            # Colour by density: low = teal, high = gold
            ratio = count / max_count
            col = (
                int(80  + ratio * 130),
                int(180 - ratio * 80),
                int(220 - ratio * 160),
            )
            if bh:
                pygame.draw.rect(self._screen, col, (bx, by, bar_w, bh), border_radius=2)

        # Baseline
        pygame.draw.line(self._screen, _BORDER,
                         (chart.x, chart.bottom), (chart.right, chart.bottom))

        # Y-axis label (max)
        self._screen.blit(self._fl.render(str(max_count), True, _DIM),
                           (rect.x + _PAD, chart.y))

        # X-axis labels: start and end tick
        from roma_aeterna.config import TPS
        def _fmt(t):
            s = t // TPS
            return f"{s//60}m{s%60:02d}s"

        start_lbl = self._fl.render(_fmt(t_min), True, _DIM)
        end_lbl   = self._fl.render(_fmt(t_max), True, _DIM)
        self._screen.blit(start_lbl, (chart.x, chart.bottom + 3))
        self._screen.blit(end_lbl,   (chart.right - end_lbl.get_width(), chart.bottom + 3))

        total_lbl = self._fl.render(f"Total: {len(ticks_data)}", True, _TEXT)
        self._screen.blit(total_lbl, (rect.x + rect.w - total_lbl.get_width() - _PAD, rect.y + _PAD))

    # ================================================================
    # STATS TAB
    # ================================================================

    def _draw_stats_tab(self, cr: pygame.Rect) -> None:
        _panel(self._screen, cr)
        from roma_aeterna.config import TPS
        x, y = cr.x + _PAD, cr.y + _PAD

        tick = self._engine.tick_count
        secs = tick // TPS
        self._screen.blit(self._fb.render("Session Overview", True, _GOLD), (x, y)); y += 22
        for label, value in [
            ("Simulation tick",  f"{tick:,}"),
            ("Sim time elapsed", f"{secs // 60}m {secs % 60}s"),
            ("Human agents",     str(len(self._agents()))),
            ("Animals",          str(len([a for a in self._engine.agents
                                          if getattr(a, "is_animal", False)]))),
        ]:
            self._screen.blit(self._fs.render(f"{label}:", True, _DIM), (x + 10, y))
            self._screen.blit(self._fs.render(value, True, _TEXT), (x + 200, y))
            y += 18
        y += 10

        self._screen.blit(self._fb.render("Agent Performance", True, _GOLD), (x, y)); y += 22
        cols = [("Name", 0), ("Role", 155), ("Dec.", 295), ("LLM", 340),
                ("Err", 385), ("HP", 430), ("Hunger", 470), ("Thirst", 530)]
        for hdr, hx in cols:
            self._screen.blit(self._fl.render(hdr, True, _GOLD), (x + hx, y))
        y += 16
        pygame.draw.line(self._screen, _BORDER, (x, y), (cr.right - _PAD, y)); y += 4

        inner = pygame.Rect(cr.x, y, cr.w, cr.bottom - y)

        def _draw_table():
            ty = inner.y - self._roster_scroll
            for agent in self._agents():
                if ty + _ROW_H >= inner.y and ty <= inner.bottom:
                    dec = len(agent.decision_history)
                    llm = len(agent.llm_response_log)
                    err = sum(1 for e in agent.llm_response_log if e.get("error"))
                    hp  = agent.health
                    hun = agent.drives.get("hunger", 0)
                    thr = agent.drives.get("thirst", 0)
                    row = [
                        (agent.name[:18], 0,   _TEXT),
                        (agent.role[:12], 155,  _DIM),
                        (str(dec),        295,  _TEXT),
                        (str(llm),        340,  _GOLD if llm else _DIM),
                        (str(err),        385,  _RED  if err else _DIM),
                        (f"{hp:.0f}",     430,  _GREEN if hp > 50 else (_YELLOW if hp > 25 else _RED)),
                        (f"{hun:.0f}",    470,  _RED if hun > 70 else _TEXT),
                        (f"{thr:.0f}",    530,  _RED if thr > 70 else _TEXT),
                    ]
                    for text, tx, col in row:
                        self._screen.blit(self._fl.render(text, True, col), (x + tx, ty + 7))
                ty += _ROW_H

        _clip(self._screen, inner, _draw_table)

    # ================================================================
    # VOLUME TAB
    # ================================================================

    def _draw_volume_tab(self, cr: pygame.Rect) -> None:
        _panel(self._screen, cr)
        cx = cr.x + cr.w // 2
        cy = cr.y + cr.h // 2 - 50

        self._screen.blit(self._fb.render("Music Volume", True, _GOLD),
                          (cx - 56, cy - 38))

        try:
            vol = pygame.mixer.music.get_volume()
        except Exception:
            vol = 0.5

        sx, sw, sh = cx - 150, 300, 8
        sy = cy

        pygame.draw.rect(self._screen, _BORDER, (sx, sy, sw, sh), border_radius=4)
        fw = int(sw * vol)
        if fw:
            pygame.draw.rect(self._screen, _GOLD, (sx, sy, fw, sh), border_radius=4)
        kx = sx + fw
        pygame.draw.circle(self._screen, _GOLD,   (kx, sy + sh // 2), 10)
        pygame.draw.circle(self._screen, _BORDER, (kx, sy + sh // 2), 10, 2)

        self._slider_rect = pygame.Rect(sx - 12, sy - 12, sw + 24, sh + 24)
        self._slider_x, self._slider_w = sx, sw

        pct = self._fb.render(f"{vol * 100:.0f}%", True, _TEXT)
        self._screen.blit(pct, (cx - pct.get_width() // 2, sy + 18))

        self._vol_btns = []
        for label, bvol, bx in [("Mute", 0.0, cx - 95), ("50%", 0.5, cx - 30), ("Max", 1.0, cx + 38)]:
            br = pygame.Rect(bx, sy + 46, 58, 26)
            pygame.draw.rect(self._screen, _SEL, br, border_radius=4)
            pygame.draw.rect(self._screen, _BORDER, br, 1, border_radius=4)
            ls = self._fs.render(label, True, _TEXT)
            self._screen.blit(ls, (br.x + (br.w - ls.get_width()) // 2,
                                   br.y + (br.h - ls.get_height()) // 2))
            self._vol_btns.append((br, bvol))

        hint = self._fs.render("Drag slider  ·  or click a preset", True, _DIM)
        self._screen.blit(hint, (cx - hint.get_width() // 2, sy + 82))

    # ================================================================
    # CLICK HANDLING
    # ================================================================

    def _on_click(self, pos) -> None:
        mx, my = pos
        win = self._win()

        # Sidebar tabs
        for i, tab in enumerate(_TABS):
            y = win.y + _TOP_H + _PAD + i * 46
            rect = pygame.Rect(win.x + 6, y, _SIDE_W - 12, 38)
            if rect.collidepoint(pos):
                self._tab = tab
                self._roster_scroll = 0
                self._detail_scroll = 0
                return

        if self._tab == "AGENTS":
            roster = self._roster_rect()
            if roster.collidepoint(pos):
                rel_y = my - roster.y + self._roster_scroll
                idx = rel_y // _ITEM_H
                agents = self._agents()
                if 0 <= idx < len(agents):
                    self._agent_idx = idx
                    self._detail_scroll = 0
                return

            detail = self._detail_rect()
            dtabs = ["STATE", "DECISIONS", "LLM CALLS"]
            tab_h, tab_w = 30, detail.w // 3
            if detail.y <= my <= detail.y + tab_h:
                idx = (mx - detail.x) // tab_w
                if 0 <= idx < len(dtabs):
                    self._dtab = dtabs[idx]
                    self._detail_scroll = 0
                return

        elif self._tab == "VOLUME":
            for br, bvol in self._vol_btns:
                if br.collidepoint(pos):
                    self._set_volume(bvol)
                    return
            if hasattr(self, "_slider_rect") and self._slider_rect.collidepoint(pos):
                self._vol_dragging = True
                self._drag_volume(mx)

    def _drag_volume(self, mouse_x: int) -> None:
        if not hasattr(self, "_slider_x"):
            return
        vol = max(0.0, min(1.0, (mouse_x - self._slider_x) / max(1, self._slider_w)))
        self._set_volume(vol)

    def _set_volume(self, vol: float) -> None:
        try:
            pygame.mixer.music.set_volume(vol)
        except Exception:
            pass

    # ================================================================
    # UTILITIES
    # ================================================================

    def _wrap(self, text: str, max_w: int, font: pygame.font.Font) -> List[str]:
        if not text:
            return []
        lines, current = [], ""
        for word in text.split():
            test = (current + " " + word).strip()
            if font.size(test)[0] <= max_w:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines
