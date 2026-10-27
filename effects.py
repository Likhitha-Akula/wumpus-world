"""Animations and sound. Nothing here changes the game: it only REACTS to what just happened.

Effects.on_action(...)   is called after every action; it starts the right animation and sound.
Effects.hero_centre(...) makes the archer glide between cells instead of jumping.
Effects.draw(...)        draws the flying arrow, sparkles, rings, score pop-ups and the red flash.
"""
import array
import math
import random

import pygame

import ui
from game import (CLIMB, DEAD_PIT, DEAD_WUMPUS, DIRS, FORWARD, GRAB, LEFT_EMPTY, SHOOT,
                  TURN_LEFT, TURN_RIGHT, WON)


# ----------------------------------------------------------------------------- sound
def _tone(rate, f0, f1, ms, volume=0.35, wave="sine", wobble=0.0):
    """One short sound as a list of samples. The pitch slides from f0 to f1."""
    n = int(rate * ms / 1000)
    out, phase = [], 0.0
    for i in range(n):
        t = i / n
        freq = f0 + (f1 - f0) * t + wobble * math.sin(t * 40)
        phase += 2 * math.pi * freq / rate
        if wave == "square":
            s = 1.0 if math.sin(phase) > 0 else -1.0
        elif wave == "noise":
            s = random.uniform(-1, 1)
        else:
            s = math.sin(phase)
        out.append(s * volume * min(1.0, (1 - t) * 3, t * 40))     # quick fade in and out
    return out


class Sound:
    """Small sound effects made from maths, so the project needs no audio files."""

    def __init__(self):
        self.enabled = True
        self.available = False
        self.sounds = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            rate, fmt, channels = pygame.mixer.get_init()
            if fmt != -16:
                return
            self._build(rate, channels)
            self.available = True
        except pygame.error:
            self.available = False          # no sound card: the game still works, silently

    def _build(self, rate, channels):
        def seq(*parts):
            return [s for p in parts for s in p]

        raw = {
            "step": _tone(rate, 220, 150, 70, 0.30),
            "turn": _tone(rate, 520, 560, 40, 0.18),
            "bump": _tone(rate, 120, 60, 170, 0.45, "square"),
            "shoot": _tone(rate, 1000, 200, 260, 0.30, "noise"),
            "scream": _tone(rate, 700, 300, 700, 0.35, "square", wobble=160),
            "gold": seq(*(_tone(rate, f, f, 90, 0.30) for f in (660, 880, 1100))),
            "win": seq(*(_tone(rate, f, f, 130, 0.32) for f in (523, 659, 784, 1047))),
            "lose": seq(_tone(rate, 330, 330, 150, 0.3), _tone(rate, 247, 247, 250, 0.3)),
            "death": _tone(rate, 420, 50, 650, 0.40, "square"),
        }
        for name, samples in raw.items():
            data = array.array("h")
            for s in samples:
                v = int(32767 * max(-1.0, min(1.0, s)))
                data.extend([v] * channels)                   # same sound on every channel
            self.sounds[name] = pygame.mixer.Sound(buffer=data.tobytes())

    def play(self, name):
        if self.enabled and self.available:
            self.sounds[name].play()


# ----------------------------------------------------------------------------- slider
class Slider:
    """A horizontal slider (0 = left, 1 = right) used for the AI speed."""

    def __init__(self, rect, value=0.67, label="Speed"):
        self.rect = pygame.Rect(rect)
        self.value = value
        self.label = label
        self.dragging = False

    def _set_from_mouse(self, x):
        self.value = max(0.0, min(1.0, (x - self.rect.left) / self.rect.width))

    def handle(self, event):
        """Returns True if this mouse event belonged to the slider."""
        grab = self.rect.inflate(16, 12)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and grab.collidepoint(event.pos):
            self.dragging = True
            self._set_from_mouse(event.pos[0])
            return True
        if event.type == pygame.MOUSEMOTION and self.dragging:
            self._set_from_mouse(event.pos[0])
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.dragging:
            self.dragging = False
            return True
        return False

    def draw(self, screen, fonts):
        label = fonts["body"].render(self.label, True, ui.MUTED)
        screen.blit(label, (self.rect.left - label.get_width() - 10, self.rect.centery - label.get_height() // 2))
        y = self.rect.centery
        pygame.draw.line(screen, ui.T["track"], (self.rect.left, y), (self.rect.right, y), 6)
        knob_x = self.rect.left + int(self.value * self.rect.width)
        pygame.draw.line(screen, ui.GOLD, (self.rect.left, y), (knob_x, y), 6)
        pygame.draw.circle(screen, ui.WHITE, (knob_x, y), 8)
        pygame.draw.circle(screen, ui.GOLD, (knob_x, y), 8, 2)


# ----------------------------------------------------------------------------- effects
def _ease(p):
    p = max(0.0, min(1.0, p))
    return p * p * (3 - 2 * p)                       # starts and ends gently


class Effects:
    GLIDE_MS = 180

    def __init__(self, now=pygame.time.get_ticks):
        self.now = now                                # a clock we can fake in tests
        self.sound = Sound()
        self.pace = 600                               # ms between moves (the AI speed), keeps glides short
        self.reset()

    def reset(self):
        self.glide = None            # (from_cell, to_cell, start, duration)
        self.shake_until = 0
        self.arrow = None            # (from_cell, to_cell, facing, start, duration)
        self.sparks, self.rings, self.popups = [], [], []
        self.flash = None            # (color, start, duration)
        self.later = []              # sounds that should play a moment from now

    # ---------------------------------------------------------------- reacting to actions
    def on_action(self, action, before_pos, game):
        t = self.now()
        if action in (TURN_LEFT, TURN_RIGHT):
            self.sound.play("turn")
        elif action == FORWARD:
            if game.bump:
                self.shake_until = t + 260
                self.sound.play("bump")
            else:
                self.glide = (before_pos, game.pos, t, min(self.GLIDE_MS, int(self.pace * 0.6)))
                self.sound.play("step")
        elif action == GRAB:
            self.sparks.append((game.pos, t, 14, ui.GOLD))
            self.popups.append(("Gold!", ui.GOLD, game.pos, t))
            self.sound.play("gold")
        elif action == SHOOT:
            self._shoot(game, t)
        elif action == CLIMB and game.status == WON:
            self.sparks.append((game.pos, t, 30, ui.GREEN))
            self.popups.append(("+1000", ui.GREEN, game.pos, t))
            self.sound.play("win")
        elif action == CLIMB:
            self.sound.play("lose")
        if game.status in (DEAD_PIT, DEAD_WUMPUS):
            self.flash = (ui.RED, t, 450)
            self.popups.append(("-1000", ui.RED, game.pos, t))
            self.sound.play("death")

    def _shoot(self, game, t):
        world, facing = game.world, game.facing
        dx, dy = DIRS[facing]
        cell, last = game.pos, game.pos
        while True:
            cell = (cell[0] + dx, cell[1] + dy)
            if not world.in_bounds(cell):
                break
            last = cell
            if game.scream and cell == world.wumpus:
                break
        duration = 120 * max(1, abs(last[0] - game.pos[0]) + abs(last[1] - game.pos[1]))
        self.arrow = (game.pos, last, facing, t, duration)
        self.popups.append(("-10", (255, 170, 90), game.pos, t))
        self.sound.play("shoot")
        if game.scream:
            self.rings.append((last, t + duration, ui.SCREAM))
            self.later.append((t + duration, "scream"))

    # ---------------------------------------------------------------- helpers used by the drawing code
    def hero_centre(self, world, pos, centre):
        """Where to draw the archer right now (gliding between cells, shaking after a bump)."""
        t = self.now()
        if self.glide and self.glide[1] == pos:
            a, b, start, dur = self.glide
            p = (t - start) / max(1, dur)
            if p >= 1:
                self.glide = None
            else:
                ca, cb = ui.cell_rect(world, *a).center, ui.cell_rect(world, *b).center
                e = _ease(p)
                centre = (ca[0] + (cb[0] - ca[0]) * e, ca[1] + (cb[1] - ca[1]) * e)
        if t < self.shake_until:
            centre = (centre[0] + math.sin(t * 0.09) * 5, centre[1])
        return (int(centre[0]), int(centre[1]))

    def draw(self, screen, fonts, world):
        t = self.now()
        for when, name in [x for x in self.later if x[0] <= t]:
            self.sound.play(name)
        self.later = [x for x in self.later if x[0] > t]

        cell = ui.BOARD_PX // world.size
        centre = lambda c: ui.cell_rect(world, *c).center

        # the flying arrow
        if self.arrow:
            a, b, facing, start, dur = self.arrow
            p = (t - start) / dur
            if p >= 1:
                self.arrow = None
            else:
                ca, cb = centre(a), centre(b)
                x = ca[0] + (cb[0] - ca[0]) * p
                y = ca[1] + (cb[1] - ca[1]) * p
                dx, dy = DIRS[facing]
                dx, dy = dx, -dy                                  # screen y grows downwards
                length = cell * 0.42
                tail = (x - dx * length, y - dy * length)
                pygame.draw.line(screen, (215, 180, 125), tail, (x, y), 4)
                px, py = -dy, dx
                head = [(x + dx * 10, y + dy * 10), (x + px * 6, y + py * 6), (x - px * 6, y - py * 6)]
                pygame.draw.polygon(screen, (230, 235, 250), head)
                pygame.draw.line(screen, (230, 70, 80), tail, (tail[0] + px * 5 - dx * 4, tail[1] + py * 5 - dy * 4), 3)
                pygame.draw.line(screen, (230, 70, 80), tail, (tail[0] - px * 5 - dx * 4, tail[1] - py * 5 - dy * 4), 3)

        # sparkles
        alive = []
        for c, start, count, color in self.sparks:
            p = (t - start) / 700
            if p < 1:
                alive.append((c, start, count, color))
                cx, cy = centre(c)
                for i in range(count):
                    ang = i * 2 * math.pi / count + (i % 3) * 0.3
                    dist = cell * (0.25 + 0.55 * _ease(p)) * (0.7 + 0.3 * (i % 4) / 3)
                    pygame.draw.circle(screen, color, (cx + math.cos(ang) * dist, cy + math.sin(ang) * dist),
                                       max(1, int(5 * (1 - p))))
        self.sparks = alive

        # expanding rings (the Wumpus scream)
        alive = []
        for c, start, color in self.rings:
            p = (t - start) / 600
            if p < 1:
                alive.append((c, start, color))
            if 0 <= p < 1:
                pygame.draw.circle(screen, color, centre(c), int(cell * (0.2 + 0.8 * p)), max(1, int(5 * (1 - p))))
        self.rings = alive

        # score pop-ups that float upwards and fade
        alive = []
        for label, color, c, start in self.popups:
            p = (t - start) / 1000
            if p < 1:
                alive.append((label, color, c, start))
                surf = fonts["head"].render(label, True, color)
                surf.set_alpha(int(255 * (1 - p * p)))
                cx, cy = centre(c)
                screen.blit(surf, surf.get_rect(center=(cx, cy - cell * 0.35 - 40 * p)))
        self.popups = alive

        # red flash over the board when the agent dies
        if self.flash:
            color, start, dur = self.flash
            p = (t - start) / dur
            if p >= 1:
                self.flash = None
            else:
                size = cell * world.size
                veil = pygame.Surface((size, size), pygame.SRCALPHA)
                veil.fill((*color, int(110 * (1 - p))))
                screen.blit(veil, ui.BOARD_ORIGIN)