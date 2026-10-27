"""Smooth, shaded character sprites for the Wumpus World game.

Every sprite is drawn on a 200x200 logical canvas at 4x resolution and then
scaled down with smoothscale, which gives clean anti-aliased edges.
"""
import math

import pygame

SS = 4  # supersampling factor
OUT = (32, 20, 44)  # outline colour shared by all sprites


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


class Pen:
    def __init__(self, surf):
        self.S = surf

    def _p(self, pts):
        return [(x * SS, y * SS) for x, y in pts]

    def poly(self, pts, fill, outline=OUT, w=3):
        pygame.draw.polygon(self.S, fill, self._p(pts))
        if outline:
            pygame.draw.polygon(self.S, outline, self._p(pts), int(w * SS))

    def ell(self, cx, cy, rx, ry, fill, outline=None, w=3):
        r = pygame.Rect((cx - rx) * SS, (cy - ry) * SS, 2 * rx * SS, 2 * ry * SS)
        pygame.draw.ellipse(self.S, fill, r)
        if outline:
            pygame.draw.ellipse(self.S, outline, r, int(w * SS))

    def shade(self, cx, cy, rx, ry, dark, light, outline=OUT, w=3, steps=22, hl=(-0.45, -0.5)):
        """Ellipse with a soft highlight toward the upper left."""
        self.ell(cx, cy, rx, ry, dark)
        for i in range(steps):
            t = i / (steps - 1)
            sc = 1 - 0.78 * t
            self.ell(cx + hl[0] * rx * (1 - sc), cy + hl[1] * ry * (1 - sc), rx * sc * 0.96, ry * sc * 0.96,
                     lerp(dark, light, t))
        if outline:
            self._ring(cx, cy, rx, ry, outline, w)

    def _ring(self, cx, cy, rx, ry, color, w):
        r = pygame.Rect((cx - rx) * SS, (cy - ry) * SS, 2 * rx * SS, 2 * ry * SS)
        pygame.draw.ellipse(self.S, color, r, int(w * SS))

    def line(self, p1, p2, color, w):
        a = (p1[0] * SS, p1[1] * SS)
        b = (p2[0] * SS, p2[1] * SS)
        pygame.draw.line(self.S, color, a, b, int(w * SS))
        pygame.draw.circle(self.S, color, a, int(w * SS / 2))
        pygame.draw.circle(self.S, color, b, int(w * SS / 2))

    def curve(self, pts, color, w):
        for i in range(len(pts) - 1):
            self.line(pts[i], pts[i + 1], color, w)

    def rrect(self, x, y, w_, h_, fill, outline=OUT, ow=3, radius=8):
        r = pygame.Rect(x * SS, y * SS, w_ * SS, h_ * SS)
        pygame.draw.rect(self.S, fill, r, border_radius=int(radius * SS))
        if outline:
            pygame.draw.rect(self.S, outline, r, int(ow * SS), border_radius=int(radius * SS))

# ------------------------------------------------------------------ hero
# The archer is drawn from three sides (side, front, back), each with the arrow in
# his hand ("armed") or without it ("empty", after the one arrow has been shot).
SKIN_D, SKIN_L = (224, 168, 128), (255, 224, 190)
GREEN_D, GREEN_L = (28, 110, 84), (70, 185, 130)


def _bow(p, cx, cy):
    """A bow standing upright, bulging to the right, with its string."""
    arc = [(cx + 22 * math.cos(t), cy + 56 * math.sin(t))
           for t in [(-math.pi / 2) + i * math.pi / 20 for i in range(21)]]
    p.curve(arc, OUT, 9)
    p.curve(arc, (156, 98, 46), 6)
    p.curve([(x - 1, y - 1) for x, y in arc], (206, 148, 82), 2.2)
    p.line((cx, cy - 56), (cx, cy + 56), (240, 240, 245), 1.6)


def _arrow_vertical(p, x, nock, tip):
    """An arrow held upright, pointing up or down (used for the front and back views)."""
    s = 1 if tip > nock else -1
    p.line((x, nock), (x, tip - s * 14), OUT, 5)
    p.line((x, nock), (x, tip - s * 14), (215, 180, 125), 3)
    p.poly([(x - 9, tip - s * 18), (x, tip), (x + 9, tip - s * 18)], (225, 230, 245))
    p.poly([(x, nock), (x - 11, nock - s * 12), (x, nock + s * 8)], (230, 70, 80), w=2)
    p.poly([(x, nock), (x + 11, nock - s * 12), (x, nock + s * 8)], (240, 240, 245), w=2)


def _quiver_arrows(p, xs, base_y, armed):
    """The little arrows sticking out of the quiver (none once the arrow is used)."""
    if armed:
        for x, col in zip(xs, ((235, 235, 240), (230, 80, 80), (235, 235, 240))):
            p.line((x + 4, base_y), (x - 2, base_y - 18), (200, 170, 120), 2.2)
            p.poly([(x - 5, base_y - 18), (x - 1, base_y - 28), (x + 3, base_y - 16)], col, outline=None)


def _legs(p):
    p.rrect(85, 146, 11, 20, (130, 96, 70), radius=4)
    p.rrect(104, 146, 11, 20, (130, 96, 70), radius=4)
    p.shade(88, 168, 13, 7, (60, 38, 28), (120, 80, 55), w=2.4)
    p.shade(112, 168, 13, 7, (60, 38, 28), (120, 80, 55), w=2.4)


def _cap(p):
    """The green cap with its red feather (looks the same from every side)."""
    p.ell(100, 56, 34, 9, (22, 90, 68), OUT, 2.8)
    p.poly([(74, 56), (104, 12), (126, 56)], (46, 150, 108))
    p.poly([(80, 54), (100, 24), (104, 54)], (84, 200, 146), outline=None)
    p.poly([(112, 34), (138, 16), (134, 40), (122, 46)], (230, 70, 80), w=2.4)
    p.line((116, 38), (132, 24), (255, 170, 170), 1.6)


def _hanging_arm(p):
    """The arm that hangs down at his side (front and back views)."""
    p.line((78, 104), (72, 134), OUT, 13)
    p.line((78, 104), (72, 134), GREEN_L, 9.5)
    p.ell(72, 138, 7, 7, SKIN_L, OUT, 2.4)


def _bow_arm(p, hand_x, hand_y):
    """The arm that reaches out and holds the bow (front and back views)."""
    p.line((122, 104), (hand_x, hand_y), OUT, 12)
    p.line((122, 104), (hand_x, hand_y), GREEN_L, 8.5)
    p.ell(hand_x, hand_y, 7, 7, SKIN_L, OUT, 2.4)


def _tunic(p):
    p.rrect(74, 94, 52, 58, GREEN_D, radius=15)
    p.rrect(80, 98, 40, 50, GREEN_L, outline=None, radius=12)
    p.rrect(74, 126, 52, 9, (130, 84, 42), outline=OUT, ow=2.4, radius=3)


def _ears(p):
    p.ell(77, 76, 7, 12, (112, 70, 40), OUT, 2.4)
    p.ell(123, 76, 7, 12, (112, 70, 40), OUT, 2.4)


def _hero_side(p, armed):
    """Seen from the side, facing right (the game flips it for West)."""
    p.ell(100, 176, 40, 7, (0, 0, 0, 80))
    # cape
    p.poly([(78, 94), (62, 156), (96, 146), (122, 94)], (170, 40, 56))
    p.poly([(82, 100), (72, 148), (96, 142), (112, 100)], (205, 70, 80), outline=None)
    # quiver
    p.poly([(66, 84), (80, 76), (94, 122), (80, 130)], (122, 78, 44))
    _quiver_arrows(p, (70, 76, 82), 80, armed)
    _legs(p)
    # tunic and belt buckle
    p.rrect(77, 94, 46, 58, GREEN_D, radius=15)
    p.rrect(81, 98, 28, 50, GREEN_L, outline=None, radius=12)
    p.rrect(77, 126, 46, 9, (130, 84, 42), outline=OUT, ow=2.4, radius=3)
    p.rrect(95, 124, 11, 13, (255, 214, 90), outline=OUT, ow=2.2, radius=3)
    # bow, and the arrow only while he still has it
    _bow(p, 150, 104)
    if armed:
        p.line((110, 104), (180, 104), OUT, 5)
        p.line((110, 104), (180, 104), (215, 180, 125), 3)
        p.poly([(178, 95), (198, 104), (178, 113)], (225, 230, 245))
        p.poly([(110, 104), (98, 93), (118, 104)], (230, 70, 70), w=2)
        p.poly([(110, 104), (98, 115), (118, 104)], (240, 240, 245), w=2)
    # bow arm and hand
    p.line((116, 108), (150, 106), OUT, 12)
    p.line((116, 108), (150, 106), GREEN_L, 8.5)
    p.line((136, 107), (150, 106), SKIN_L, 8.5)
    p.ell(152, 106, 7, 7, SKIN_L, OUT, 2.4)
    # head
    _ears(p)
    p.shade(100, 74, 27, 25, SKIN_D, SKIN_L, w=3)
    for ex in (89, 111):
        p.ell(ex, 76, 6, 7.5, (255, 255, 255), OUT, 1.8)
        p.ell(ex + 1, 77, 3.6, 5, (44, 70, 120))
        p.ell(ex + 1, 78, 2, 3, (10, 10, 20))
        p.ell(ex + 2.4, 74.5, 1.6, 1.6, (255, 255, 255))
    p.ell(81, 86, 5, 3, (255, 150, 150, 150))
    p.ell(119, 86, 5, 3, (255, 150, 150, 150))
    p.curve([(93 + i * 2.8, 88 + math.sin(i / 4 * math.pi) * 2.6) for i in range(5)], (150, 70, 60), 2)
    _cap(p)


def _hero_front(p, armed):
    """Facing the viewer (South). The arrow points down."""
    p.ell(100, 176, 40, 7, (0, 0, 0, 80))
    # cape seen behind the body, quiver peeking over one shoulder
    p.poly([(72, 92), (48, 160), (152, 160), (128, 92)], (170, 40, 56))
    p.poly([(80, 100), (62, 152), (138, 152), (120, 100)], (205, 70, 80), outline=None)
    p.poly([(60, 84), (72, 76), (82, 108), (68, 114)], (122, 78, 44))
    _quiver_arrows(p, (62, 68, 74), 82, armed)
    _legs(p)
    _tunic(p)
    p.rrect(94, 124, 12, 13, (255, 214, 90), outline=OUT, ow=2.2, radius=3)   # buckle in the middle
    _hanging_arm(p)
    # bow in the other hand, arrow pointing down at the viewer
    _bow(p, 158, 108)
    if armed:
        _arrow_vertical(p, 158, 98, 192)
    _bow_arm(p, 158, 108)
    # head: face towards us
    _ears(p)
    p.shade(100, 74, 27, 25, SKIN_D, SKIN_L, w=3)
    for ex in (89, 111):
        p.ell(ex, 76, 6, 7.5, (255, 255, 255), OUT, 1.8)
        p.ell(ex, 77, 3.6, 5, (44, 70, 120))
        p.ell(ex, 78, 2, 3, (10, 10, 20))
        p.ell(ex + 1.6, 74.5, 1.6, 1.6, (255, 255, 255))
    p.ell(81, 86, 5, 3, (255, 150, 150, 150))
    p.ell(119, 86, 5, 3, (255, 150, 150, 150))
    p.curve([(93 + i * 3.5, 88 + math.sin(i / 4 * math.pi) * 2.8) for i in range(5)], (150, 70, 60), 2)
    _cap(p)


def _hero_back(p, armed):
    """Facing away from the viewer (North). The arrow points up."""
    p.ell(100, 176, 40, 7, (0, 0, 0, 80))
    _legs(p)
    _tunic(p)
    # the cape covers his back, with a clasp at the neck
    p.poly([(76, 94), (124, 94), (138, 158), (62, 158)], (170, 40, 56))
    p.poly([(84, 102), (116, 102), (126, 150), (74, 150)], (205, 70, 80), outline=None)
    p.ell(100, 99, 7, 4, (255, 214, 90), OUT, 1.6)
    # quiver on his back, strap across the cape
    p.line((122, 98), (82, 130), (200, 170, 120), 5)
    p.poly([(62, 84), (74, 76), (88, 118), (74, 126)], (122, 78, 44))
    _quiver_arrows(p, (62, 68, 74), 82, armed)
    _hanging_arm(p)
    # bow in the other hand, arrow pointing up (away from us)
    _bow(p, 158, 108)
    if armed:
        _arrow_vertical(p, 158, 118, 6)
    _bow_arm(p, 158, 108)
    # head: the back of it
    _ears(p)
    p.shade(100, 74, 27, 25, (112, 70, 40), (170, 112, 66), w=3)
    for dx in (-12, -4, 4, 12):
        p.line((100 + dx, 62), (100 + dx * 1.3, 90), (96, 58, 32), 2)
    _cap(p)



# ---------------------------------------------------------------- wumpus
def _wumpus(p):
    tuft = (92, 42, 136)
    p.ell(100, 176, 46, 7, (0, 0, 0, 80))
    # feet
    for fx in (72, 128):
        p.shade(fx, 164, 24, 12, (70, 28, 104), (126, 70, 170), w=3)
        for tx in (-9, 0, 9):
            p.ell(fx + tx, 169, 4, 3, (245, 238, 210), OUT, 1.4)
    # fur tufts all around the body
    for i in range(30):
        a = 2 * math.pi * i / 30
        tip = (100 + 74 * math.cos(a), 104 + 66 * math.sin(a))
        b1 = (100 + 58 * math.cos(a - 0.14), 104 + 52 * math.sin(a - 0.14))
        b2 = (100 + 58 * math.cos(a + 0.14), 104 + 52 * math.sin(a + 0.14))
        p.poly([b1, tip, b2], tuft, outline=None)
    # body and belly
    p.shade(100, 104, 62, 56, (78, 34, 120), (170, 108, 220), w=3.4)
    p.shade(100, 128, 38, 28, (178, 124, 214), (238, 205, 252), outline=None, steps=14)
    # arms with claws
    for sx in (-1, 1):
        ax = 100 + sx * 62
        p.shade(ax, 118, 13, 22, (78, 34, 120), (150, 90, 200), w=2.8, hl=(-0.2, -0.4))
        for k in (-1, 0, 1):
            p.poly([(ax + k * 8 - 3, 134), (ax + k * 8 + sx * 2, 150), (ax + k * 8 + 3, 134)], (250, 244, 222), w=1.8)
    # horns
    p.poly([(60, 58), (40, 8), (86, 44)], (248, 238, 206), w=3)
    p.poly([(62, 54), (47, 18), (74, 46)], (255, 252, 236), outline=None)
    p.poly([(140, 58), (160, 8), (114, 44)], (248, 238, 206), w=3)
    p.poly([(138, 54), (153, 18), (126, 46)], (255, 252, 236), outline=None)
    # eyes
    for ex, sx in ((77, -1), (123, 1)):
        p.ell(ex, 92, 18, 21, (255, 255, 255), OUT, 3)
        p.ell(ex - sx * 2, 96, 10, 12, (232, 40, 56))
        p.ell(ex - sx * 2, 97, 5.5, 7, (20, 6, 16))
        p.ell(ex - sx * 5, 91, 3.6, 3.6, (255, 255, 255))
        p.line((ex + sx * 22, 66), (ex - sx * 18, 80), OUT, 8)  # angry brow
    # nose and mouth
    p.ell(95, 110, 2.6, 3.2, (50, 16, 70))
    p.ell(105, 110, 2.6, 3.2, (50, 16, 70))
    p.ell(100, 128, 34, 21, (54, 10, 40), OUT, 3)
    p.ell(100, 142, 17, 8, (240, 110, 140))
    for dx in (-22, -10, 2, 14):
        p.poly([(100 + dx, 110), (100 + dx + 11, 110), (100 + dx + 5.5, 124)], (255, 255, 255), outline=None)
    p.poly([(82, 146), (92, 146), (87, 133)], (255, 255, 255), outline=None)
    p.poly([(108, 146), (118, 146), (113, 133)], (255, 255, 255), outline=None)  



# ------------------------------------------------------------------- pit
def _pit(p):
    # the original simple pit: dark hole, lavender rim, a few small rocks
    m = 1.3  # scale-up so it fills the cell like the other icons
    cx, cy = 100, 104

    def X(v):
        return cx + v * m

    def Y(v):
        return cy + v * m

    for (dx, dy, r) in [(-40, -10, 8), (-34, 20, 7), (38, 8, 9), (30, -22, 6), (4, 38, 7), (-6, -40, 7)]:
        p.ell(X(dx), Y(dy), r * m, r * m, (88, 80, 105), (60, 54, 78), 2)
    p.ell(cx, cy, 44 * m, 37 * m, (110, 100, 150))  # lavender rim
    for i, col in enumerate([(14, 12, 20), (9, 8, 14), (5, 4, 9), (2, 2, 4)]):
        k = i * 7
        p.ell(cx, cy, (36 - k) * m, (30 - 0.8 * k) * m, col)


# ------------------------------------------------------------------ gold
def _spark(p, cx, cy, r, col=(255, 252, 214)):
    pts = [(cx, cy - r), (cx + r * 0.22, cy - r * 0.22), (cx + r, cy), (cx + r * 0.22, cy + r * 0.22),
           (cx, cy + r), (cx - r * 0.22, cy + r * 0.22), (cx - r, cy), (cx - r * 0.22, cy - r * 0.22)]
    p.poly(pts, col, outline=None)


def _coin(p, cx, cy, r=11):
    p.ell(cx, cy, r, r * 0.68, (255, 208, 56), (150, 96, 12), 2.2)
    p.ell(cx, cy, r * 0.62, r * 0.4, (255, 236, 130))
    p.ell(cx - 2, cy - 1.5, r * 0.22, r * 0.14, (255, 255, 235))


def _gold(p):
    p.ell(100, 176, 62, 8, (0, 0, 0, 80))
    # open lid at the back
    p.rrect(48, 62, 104, 54, (120, 74, 38), radius=14)
    p.rrect(54, 68, 92, 42, (150, 98, 52), outline=None, radius=10)
    # coin mound inside
    p.shade(100, 118, 52, 24, (222, 160, 20), (255, 226, 100), w=2.4)
    for (cx, cy) in [(66, 112), (84, 106), (102, 104), (120, 106), (136, 112), (76, 98), (96, 94), (116, 96),
                     (88, 84), (108, 82), (100, 70)]:
        _coin(p, cx, cy, 11)
    # chest front
    p.rrect(46, 118, 108, 56, (138, 86, 44), radius=10)
    for x in (66, 88, 112, 134):
        p.line((x, 124), (x, 170), (104, 62, 30), 2)
    p.rrect(46, 118, 108, 14, (96, 60, 34), outline=OUT, ow=2.6, radius=6)
    for x in (52, 140):
        p.rrect(x, 118, 10, 56, (255, 204, 70), outline=(150, 96, 12), ow=2.2, radius=3)
    p.rrect(90, 134, 20, 24, (255, 214, 80), outline=(150, 96, 12), ow=2.6, radius=5)
    p.ell(100, 144, 3.6, 3.6, (60, 36, 20))
    p.rrect(98.6, 144, 2.8, 8, (60, 36, 20), outline=None, radius=1)
    _spark(p, 46, 50, 11)
    _spark(p, 156, 46, 9)
    _spark(p, 168, 100, 7)
    _spark(p, 34, 100, 6)



SPRITES = {
    "hero": lambda p: _hero_side(p, True),          # used in the legend
    "hero_side_armed": lambda p: _hero_side(p, True),
    "hero_side_empty": lambda p: _hero_side(p, False),
    "hero_front_armed": lambda p: _hero_front(p, True),
    "hero_front_empty": lambda p: _hero_front(p, False),
    "hero_back_armed": lambda p: _hero_back(p, True),
    "hero_back_empty": lambda p: _hero_back(p, False),
    "wumpus": _wumpus,
    "pit": _pit,
    "gold": _gold,
}
_cache = {}


def sprite(name, px):
    key = (name, px)
    if key not in _cache:
        surf = pygame.Surface((200 * SS, 200 * SS), pygame.SRCALPHA)
        SPRITES[name](Pen(surf))
        _cache[key] = pygame.transform.smoothscale(surf, (px, px))
    return _cache[key]


def blit_sprite(target, name, center, px, flip=False, alpha=255):
    """Draw a sprite centred on `center`. flip mirrors it left-right; alpha < 255 fades it."""
    s = sprite(name, px)
    if flip:
        s = pygame.transform.flip(s, True, False)
    if alpha < 255:
        s = s.copy()
        s.set_alpha(alpha)
    target.blit(s, s.get_rect(center=center))       