"""All Pygame drawing: the board, the fog, the percept icons and the side panel.

Nothing in this file changes the game. It only looks at a `Game` and draws it.
"""
import math
import random

import pygame

from game import DIR_NAMES, DIRS, DEAD_PIT, DEAD_WUMPUS, LEFT_EMPTY, WON
from sprites import blit_sprite

# --- colours: two themes (dark dungeon / light parchment) ----------------------
THEMES = {
    "dark": dict(
        bg1=(10, 10, 22), bg2=(22, 18, 40), panel=(24, 24, 38), panel_edge=(70, 66, 110),
        box=(14, 14, 24), box_edge=(50, 48, 80), frame=(30, 28, 44), frame_edge=(90, 80, 130),
        fog=(20, 20, 30), fog_mark=(50, 50, 70), tile=(58, 54, 74),
        btn=(34, 34, 54), btn_hover=(48, 46, 78), btn_sel=(70, 64, 120),
        btn_edge=(74, 70, 110), btn_edge_hover=(120, 112, 180),
        btn_off=(26, 26, 40), btn_off_edge=(50, 48, 70), btn_off_text=(95, 98, 118), btn_off_sub=(75, 78, 98),
        track=(60, 58, 92), glow=100,
        text=(240, 240, 255), muted=(150, 155, 185), gold=(255, 200, 90),
        breeze=(120, 210, 255), stench=(140, 220, 90), green=(80, 220, 140), red=(240, 90, 80),
        bump=(255, 170, 90), scream=(230, 130, 255), warn=(255, 170, 70), info=(150, 220, 255)),
    "light": dict(
        bg1=(238, 234, 248), bg2=(214, 208, 234), panel=(250, 248, 255), panel_edge=(170, 160, 205),
        box=(238, 235, 248), box_edge=(185, 178, 215), frame=(226, 222, 240), frame_edge=(150, 140, 190),
        fog=(176, 172, 196), fog_mark=(214, 210, 230), tile=(246, 240, 226),
        btn=(240, 238, 250), btn_hover=(226, 222, 244), btn_sel=(205, 196, 240),
        btn_edge=(170, 162, 205), btn_edge_hover=(120, 108, 180),
        btn_off=(232, 230, 240), btn_off_edge=(206, 202, 220), btn_off_text=(165, 165, 185), btn_off_sub=(180, 180, 198),
        track=(200, 196, 222), glow=45,
        text=(36, 32, 60), muted=(104, 100, 132), gold=(176, 104, 0),
        breeze=(30, 130, 200), stench=(70, 150, 20), green=(20, 140, 80), red=(200, 50, 50),
        bump=(210, 110, 20), scream=(150, 60, 190), warn=(200, 110, 0), info=(10, 110, 170)),
}
T = THEMES["dark"]
GOLD = MUTED = WHITE = BREEZE = STENCH = GREEN = RED = BUMP = SCREAM = (0, 0, 0)


def set_theme(name):
    """Switch every colour used by the drawing code to the 'dark' or 'light' theme."""
    global T, GOLD, MUTED, WHITE, BREEZE, STENCH, GREEN, RED, BUMP, SCREAM
    T = THEMES[name]
    GOLD, MUTED, WHITE = T["gold"], T["muted"], T["text"]
    BREEZE, STENCH, GREEN, RED = T["breeze"], T["stench"], T["green"], T["red"]
    BUMP, SCREAM = T["bump"], T["scream"]
    _tile_cache.clear()                  # tiles were drawn in the old colours


WIDTH, HEIGHT = 1100, 680
BOARD_ORIGIN = (40, 110)
BOARD_PX = 520          # the board is always this big; cells shrink on bigger grids
PANEL = pygame.Rect(640, 40, 420, 600)
GRIP = pygame.Rect(1056, 636, 44, 44)      # the corner you drag with the mouse to resize the window


def make_fonts():
    return {
        "title": pygame.font.Font(None, 44),
        "head": pygame.font.Font(None, 26),
        "body": pygame.font.Font(None, 22),
    }


def text(screen, s, font, color, pos, center=False):
    surf = font.render(s, True, color)
    rect = surf.get_rect()
    if center:
        rect.center = pos
    else:
        rect.topleft = pos
    screen.blit(surf, rect)


def wrap(s, font, width):
    """Split a sentence into lines that fit in `width` pixels."""
    lines, line = [], ""
    for word in s.split():
        trial = (line + " " + word).strip()
        if font.size(trial)[0] <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return lines

_mouse = [(0, 0)]


def set_mouse(pos):
    """main.py tells us where the mouse is on the game picture (for the hover highlight)."""
    _mouse[0] = pos

# --- small cached helpers ----------------------------------------------------
_glow_cache, _tile_cache = {}, {}
set_theme("dark")


def glow(screen, center, radius, color, alpha):
    key = (radius, color, alpha)
    if key not in _glow_cache:
        g = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        for r in range(radius, 0, -3):
            a = int(alpha * (1 - r / radius) ** 1.6)
            pygame.draw.circle(g, (*color, a), (radius, radius), r)
        _glow_cache[key] = g
    screen.blit(_glow_cache[key], (center[0] - radius, center[1] - radius))


def stone_tile(size):
    """A speckled stone square for a visited cell (built once per size)."""
    if size not in _tile_cache:
        rng = random.Random(3)
        tile = pygame.Surface((size, size), pygame.SRCALPHA)
        base = T["tile"]
        pygame.draw.rect(tile, base, tile.get_rect(), border_radius=10)
        for _ in range(size // 3):
            x, y = rng.randint(4, size - 5), rng.randint(4, size - 5)
            shade = rng.randint(-10, 10)
            pygame.draw.circle(tile, tuple(max(0, min(255, c + shade)) for c in base), (x, y), 2)
        _tile_cache[size] = tile
    return _tile_cache[size]


def draw_breeze(screen, x, y, scale=1.0):
    for k in range(3):
        pts = [(x + i * 3.6 * scale, y + k * 8 * scale + math.sin(i * 0.9 + k) * 3 * scale) for i in range(11)]
        pygame.draw.lines(screen, BREEZE, False, pts, 2)


def draw_stench(screen, x, y, scale=1.0):
    for k in range(3):
        pts = [(x + k * 9 * scale + math.sin(i * 0.8 + k) * 3 * scale, y + i * 2.8 * scale) for i in range(9)]
        pygame.draw.lines(screen, STENCH, False, pts, 2)


# --- buttons -----------------------------------------------------------------
def draw_icon(screen, name, center, color, back):
    """Small icons drawn with shapes: sun, moon, speaker, muted. `back` is the button's own colour."""
    x, y = center
    if name == "sun":
        pygame.draw.circle(screen, color, (x, y), 5)
        for k in range(8):
            a = k * math.pi / 4
            pygame.draw.line(screen, color, (x + math.cos(a) * 8, y + math.sin(a) * 8),
                             (x + math.cos(a) * 11, y + math.sin(a) * 11), 2)
    elif name == "moon":
        pygame.draw.circle(screen, color, (x, y), 8)
        pygame.draw.circle(screen, back, (x + 5, y - 3), 7)          # bite out of the circle = half moon
    elif name == "close":                                              # an X
        pygame.draw.line(screen, color, (x - 5, y - 5), (x + 5, y + 5), 2)
        pygame.draw.line(screen, color, (x - 5, y + 5), (x + 5, y - 5), 2)
    elif name == "refresh":                                            # a circular arrow
        r = 8
        pygame.draw.arc(screen, color, (x - r, y - r, 2 * r, 2 * r), 0.6, 5.7, 2)
        ex, ey = x + r * math.cos(5.7), y - r * math.sin(5.7)          # where the arc ends
        tx, ty = -math.sin(5.7), -math.cos(5.7)                        # direction of travel there
        px, py = -ty, tx
        pygame.draw.polygon(screen, color, [(ex + tx * 5, ey + ty * 5), (ex + px * 4, ey + py * 4), (ex - px * 4, ey - py * 4)])
    else:                                                              # "speaker" or "muted"
        pygame.draw.rect(screen, color, (x - 9, y - 3, 4, 6))
        pygame.draw.polygon(screen, color, [(x - 5, y - 3), (x + 1, y - 8), (x + 1, y + 8), (x - 5, y + 3)])
        if name == "speaker":
            for r in (5, 9):                                           # two sound waves
                pygame.draw.arc(screen, color, (x + 1 - r, y - r, 2 * r, 2 * r), -0.9, 0.9, 2)
        else:
            pygame.draw.line(screen, T["red"], (x - 10, y + 9), (x + 10, y - 9), 3)   # the slash


class Button:
    def __init__(self, rect, label, action, sub="", tag=None, icon=None):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.sub = sub            # small second line, e.g. the score cost
        self.action = action
        self.tag = tag            # which game action this button stands for (if any)
        self.icon = icon          # "sun", "moon", "speaker", "muted" or "refresh": drawn instead of the label
        self.selected = False
        self.enabled = True

    def draw(self, screen, fonts):
        hover = self.enabled and self.rect.collidepoint(_mouse[0])
        if not self.enabled:
            fill, edge, main, small = T["btn_off"], T["btn_off_edge"], T["btn_off_text"], T["btn_off_sub"]
        else:
            fill = T["btn_sel"] if self.selected else (T["btn_hover"] if hover else T["btn"])
            edge = GOLD if self.selected else (T["btn_edge_hover"] if hover else T["btn_edge"])
            main, small = WHITE, MUTED
        pygame.draw.rect(screen, fill, self.rect, border_radius=10)
        pygame.draw.rect(screen, edge, self.rect, 2, border_radius=10)
        if self.icon:
            color = main if not self.enabled else (GOLD if self.selected else MUTED)
            draw_icon(screen, self.icon, self.rect.center, color, fill)
        elif self.sub:
            text(screen, self.label, fonts["head"], main, (self.rect.centerx, self.rect.centery - 8), center=True)
            text(screen, self.sub, fonts["body"], small, (self.rect.centerx, self.rect.centery + 12), center=True)
        else:
            text(screen, self.label, fonts["head"], main, self.rect.center, center=True)


# --- the board ---------------------------------------------------------------
def cell_rect(world, c, r):
    cell = BOARD_PX // world.size
    return pygame.Rect(BOARD_ORIGIN[0] + c * cell, BOARD_ORIGIN[1] + (world.size - 1 - r) * cell, cell, cell)


def draw_facing_marker(screen, centre, cell, facing):
    """A gold bar on the edge of the agent's cell, on the side it is facing."""
    dx, dy = DIRS[facing]
    long_side, thick = int(cell * 0.5), 7
    edge = cell // 2 - 6                       # just inside the cell's border
    if dx:                                     # facing East or West: a vertical bar
        rect = pygame.Rect(0, 0, thick, long_side)
        rect.center = (centre[0] + dx * edge, centre[1])
    else:                                      # facing North or South: a horizontal bar
        rect = pygame.Rect(0, 0, long_side, thick)
        rect.center = (centre[0], centre[1] - dy * edge)   # screen y grows downward
    pygame.draw.rect(screen, GOLD, rect, border_radius=3)


# which drawing of the archer to use for each facing: 0 East, 1 North, 2 West, 3 South
HERO_VIEW = {0: "side", 1: "back", 2: "side", 3: "front"}


def draw_board(screen, fonts, game, reveal, agent=None, fx=None, trail=None):
    world, n = game.world, game.world.size
    cell = BOARD_PX // n
    show_all = reveal or game.is_over
    frame = pygame.Rect(BOARD_ORIGIN[0] - 10, BOARD_ORIGIN[1] - 10, cell * n + 20, cell * n + 20)
    pygame.draw.rect(screen, T["frame"], frame, border_radius=16)
    pygame.draw.rect(screen, T["frame_edge"], frame, 3, border_radius=16)

    icon = int(cell * 0.9)
    for c in range(n):
        for r in range(n):
            inner = cell_rect(world, c, r).inflate(-6, -6)
            if show_all or (c, r) in game.visited:
                screen.blit(stone_tile(inner.width), inner.topleft)
            else:
                pygame.draw.rect(screen, T["fog"], inner, border_radius=10)
                text(screen, "?", fonts["title"], T["fog_mark"], inner.center, center=True)

    # torch glow follows the agent (kept inside the board frame)
    screen.set_clip(frame)
    glow(screen, cell_rect(world, *game.pos).center, int(cell * 1.45), (255, 170, 60), T["glow"])
    screen.set_clip(None)

    # the path walked so far: a dotted gold trail from cell to cell
    if trail and len(trail) > 1:
        dot = tuple((a + b) // 2 for a, b in zip(GOLD, T["tile"]))
        for a, b in zip(trail, trail[1:]):
            (x1, y1), (x2, y2) = cell_rect(world, *a).center, cell_rect(world, *b).center
            steps = max(1, int(math.hypot(x2 - x1, y2 - y1) // 14))
            for k in range(steps + 1):
                pygame.draw.circle(screen, dot, (x1 + (x2 - x1) * k / steps, y1 + (y2 - y1) * k / steps), 3)

    # breeze / stench icons in the corners of cells the agent has seen
    scale = cell / 130
    for c in range(n):
        for r in range(n):
            if not (show_all or (c, r) in game.visited):
                continue
            if (c, r) in world.pits or (c, r) == world.wumpus:
                continue
            p = world.percepts((c, r))
            rc = cell_rect(world, c, r)
            if p["breeze"]:
                draw_breeze(screen, rc.left + 12 * scale, rc.top + 12 * scale, scale)
            if p["stench"] and game.wumpus_alive:
                draw_stench(screen, rc.right - 40 * scale, rc.top + 12 * scale, scale)
            if p["glitter"] and not game.has_gold and (c, r) in game.visited:
                blit_sprite(screen, "gold", (rc.right - int(cell * 0.2), rc.bottom - int(cell * 0.2)), int(cell * 0.36))

    # hidden things are only drawn when revealed (Reveal button, or the game is over)
    if show_all:
        for pit in world.pits:
            blit_sprite(screen, "pit", cell_rect(world, *pit).center, icon)
        if not game.has_gold:
            blit_sprite(screen, "gold", cell_rect(world, *world.gold).center, icon)
        blit_sprite(screen, "wumpus", cell_rect(world, *world.wumpus).center, icon,
                    alpha=255 if game.wumpus_alive else 90)

    # what the AI believes about cells it has not visited (AI mode only)
    if agent is not None:
        for c in range(n):
            for r in range(n):
                if (c, r) in game.visited:
                    continue
                label = agent.kb.status((c, r))
                if label == "unknown":
                    label = "danger?" if (c, r) in agent.kb.frontier else None
                if label:
                    color = {"safe": GREEN, "pit": RED, "wumpus": RED, "danger?": T["warn"]}[label]
                    rc = cell_rect(world, c, r)
                    text(screen, label, fonts["body"], color, (rc.centerx, rc.top + 14), center=True)

    # the agent (faded if it died), turned to face where it is going
    centre = fx.hero_centre(world, game.pos, cell_rect(world, *game.pos).center) if fx else cell_rect(world, *game.pos).center
    dead = game.status in (DEAD_PIT, DEAD_WUMPUS)
    if not game.is_over:
        draw_facing_marker(screen, centre, cell, game.facing)
    hero = f"hero_{HERO_VIEW[game.facing]}_{'armed' if game.has_arrow else 'empty'}"
    blit_sprite(screen, hero, centre, int(cell * 0.92), flip=(game.facing == 2), alpha=110 if dead else 255)


# --- the side panel ----------------------------------------------------------
def draw_chip(screen, font, x, y, label, color):
    w = font.size(label)[0] + 22
    rect = pygame.Rect(x, y, w, 28)
    pygame.draw.rect(screen, (*color,), rect, 2, border_radius=14)
    text(screen, label, font, color, rect.center, center=True)
    return w


def draw_panel(screen, fonts, state):
    game = state.game
    world = game.world
    pygame.draw.rect(screen, T["panel"], PANEL, border_radius=16)
    pygame.draw.rect(screen, T["panel_edge"], PANEL, 2, border_radius=16)
    x = PANEL.left + 20

    # top buttons: grid size, new world, reveal, mode
    for b in state.size_buttons + [state.replay_button, state.new_button, state.reveal_button, state.mode_button] + state.icon_buttons:
        b.draw(screen, fonts)
    seed = "-" if world.seed is None else world.seed
    text(screen, f"World #{seed}   |   {len(world.pits)} pit(s), 1 Wumpus, 1 gold",
         fonts["body"], MUTED, (x + 2, 146))

    # status
    text(screen, "STATUS", fonts["head"], GOLD, (x, 172))
    score_color = GREEN if game.score > 0 else (RED if game.score < 0 else WHITE)
    rows = [("Score", str(game.score), score_color),
            ("Arrow", "1 left" if game.has_arrow else "used", WHITE),
            ("Gold", "carrying it" if game.has_gold else "not found", GOLD if game.has_gold else MUTED),
            ("Facing", DIR_NAMES[game.facing], WHITE)]
    for i, (label, value, color) in enumerate(rows):
        cx, cy = x + 4 + (i % 2) * 200, 198 + (i // 2) * 24
        text(screen, label, fonts["body"], MUTED, (cx, cy))
        text(screen, value, fonts["head"], color, (cx + 66, cy - 2))

    # percepts
    text(screen, "PERCEPTS NOW", fonts["head"], GOLD, (x, 252))
    p = game.percepts()
    active = [(label, color) for key, label, color in
              (("breeze", "Breeze", BREEZE), ("stench", "Stench", STENCH), ("glitter", "Glitter", GOLD),
               ("bump", "Bump", BUMP), ("scream", "Scream", SCREAM)) if p[key]]
    if not active:
        text(screen, "Nothing special here.", fonts["body"], MUTED, (x + 4, 284))
    cx = x + 4
    for label, color in active:
        cx += draw_chip(screen, fonts["body"], cx, 278, label, color) + 8

    # event log: the latest few things that happened (newest at the bottom)
    box = pygame.Rect(x, 312, 380, 90)
    over_color = {WON: GREEN, LEFT_EMPTY: GOLD, DEAD_PIT: RED, DEAD_WUMPUS: RED}.get(game.status)
    pygame.draw.rect(screen, T["box"], box, border_radius=10)
    pygame.draw.rect(screen, over_color or T["box_edge"], box, 2, border_radius=10)
    rows = []                                          # long entries wrap onto several lines
    for i, (kind, line) in enumerate(state.log[-6:]):
        newest = i == len(state.log[-6:]) - 1
        if kind == "hint":
            color = T["info"]
        elif newest and over_color:
            color = over_color                         # the final result gets the status colour
        else:
            color = WHITE if newest else MUTED
        rows += [(part, color) for part in wrap(line, fonts["body"], box.width - 24)]
    for i, (part, color) in enumerate(rows[-5:]):
        text(screen, part, fonts["body"], color, (box.x + 12, box.y + 6 + i * 16))

    # controls (User mode) or a note (AI mode)
    if state.mode == "user":
        text(screen, "CONTROLS", fonts["head"], GOLD, (x, 410))
        state.hint_button.draw(screen, fonts)
        for b in state.control_buttons:
            b.draw(screen, fonts)
    else:
        text(screen, "AI MODE", fonts["head"], GOLD, (x, 410))
        state.slider.draw(screen, fonts)
        state.step_button.draw(screen, fonts)
        state.auto_button.draw(screen, fonts)
        note = pygame.Rect(x, 474, 380, 66)
        pygame.draw.rect(screen, T["box"], note, border_radius=10)
        pygame.draw.rect(screen, T["box_edge"], note, 2, border_radius=10)
        lines = []
        for t in state.agent.thoughts:
            lines += wrap(t, fonts["body"], note.width - 24)
        for i, line in enumerate(lines[:3]):
            text(screen, line, fonts["body"], WHITE if i else T["info"], (note.x + 12, note.y + 6 + i * 20))
    text(screen, "Keys: arrows/WAD, G grab, Space shoot/step, C climb", fonts["body"], MUTED, (x + 2, 543))
    text(screen, "Tab mode   R reveal   N new world   P replay", fonts["body"], MUTED, (x + 2, 559))
    text(screen, "H hint   M sound   T theme   F11 full screen", fonts["body"], MUTED, (x + 2, 575))
    # legend
    legend = [("hero", "Explorer"), ("wumpus", "Wumpus"), ("pit", "Pit"), ("gold", "Treasure")]
    lx = x + 2
    for name, label in legend:
        blit_sprite(screen, name, (lx + 16, 608), 32)
        text(screen, label, fonts["body"], MUTED, (lx + 36, 601))
        lx += 36 + fonts["body"].size(label)[0] + 8


def draw_game_over(screen, fonts, state):
    """A 'GAME OVER' card on the board (with refresh and close buttons), or a small bar once it is closed."""
    game = state.game
    title, color = {
        WON: ("You escaped with the gold!", GREEN),
        LEFT_EMPTY: ("You left without the gold", GOLD),
        DEAD_PIT: ("You fell into a pit", RED),
        DEAD_WUMPUS: ("The Wumpus got you", RED),
    }[game.status]
    if not state.card_open:                      # closed: a slim bar above the board, click it to reopen
        state.reopen_button.rect.topleft = (BOARD_ORIGIN[0] + BOARD_PX - 220, 62)
        state.reopen_button.label = f"GAME OVER  ({game.score})"
        state.reopen_button.draw(screen, fonts)
        return
    centre = (BOARD_ORIGIN[0] + BOARD_PX // 2, BOARD_ORIGIN[1] + BOARD_PX // 2)
    card = pygame.Rect(0, 0, 400, 112)
    card.center = centre
    shade = pygame.Surface(card.size, pygame.SRCALPHA)
    pygame.draw.rect(shade, (*T["box"], 235), shade.get_rect(), border_radius=16)
    screen.blit(shade, card.topleft)
    pygame.draw.rect(screen, color, card, 3, border_radius=16)
    text(screen, "GAME OVER", fonts["title"], color, (card.left + 150, card.top + 30), center=True)
    text(screen, title, fonts["head"], WHITE, (card.left + 150, card.top + 62), center=True)
    text(screen, f"Final score: {game.score}", fonts["body"], MUTED, (card.left + 150, card.top + 88), center=True)
    state.over_button.rect.center = (card.right - 56, card.centery + 8)
    state.over_button.draw(screen, fonts)
    state.close_button.rect.topright = (card.right - 8, card.top + 8)
    state.close_button.draw(screen, fonts)

def draw_grip(screen):
    """Three little diagonal lines in the bottom-right corner: drag them to resize the whole game."""
    for k in range(3):
        pygame.draw.line(screen, MUTED, (1082 - 8 * k, 668), (1090, 660 - 8 * k), 2)


def draw_frame(screen, fonts, state):
    """Draw one complete frame. `state` needs: game, reveal, buttons."""
    top, bottom = T["bg1"], T["bg2"]
    for y in range(HEIGHT):
        t = y / HEIGHT
        pygame.draw.line(screen, tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)), (0, y), (WIDTH, y))
    text(screen, "WUMPUS WORLD", fonts["title"], GOLD, (40, 28))
    text(screen, "Knowledge-based AI Agent", fonts["body"], MUTED, (42, 66))
    draw_board(screen, fonts, state.game, state.reveal, state.agent if state.mode == "ai" else None, state.fx, state.trail)
    state.fx.draw(screen, fonts, state.game.world)
    draw_panel(screen, fonts, state)
    if state.game.is_over:
        draw_game_over(screen, fonts, state)
    draw_grip(screen)