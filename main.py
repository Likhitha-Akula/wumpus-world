"""Wumpus World: the window, the buttons, keyboard input and the main loop.

Run with:  python main.py
"""
import pygame

import ui
from agent import Agent
from effects import Effects, Slider
from game import CLIMB, FORWARD, GRAB, SHOOT, TURN_LEFT, TURN_RIGHT, Game
from world import SIZES, World

# keyboard -> game action (only used in User mode)
KEYS = {
    pygame.K_UP: FORWARD, pygame.K_w: FORWARD,
    pygame.K_LEFT: TURN_LEFT, pygame.K_a: TURN_LEFT,
    pygame.K_RIGHT: TURN_RIGHT, pygame.K_d: TURN_RIGHT,
    pygame.K_g: GRAB, pygame.K_SPACE: SHOOT, pygame.K_c: CLIMB,
}

# the six mouse buttons: (action, label, small text under the label)
CONTROLS = [
    (TURN_LEFT, "Turn Left", "-1"),
    (FORWARD, "Forward", "-1"),
    (TURN_RIGHT, "Turn Right", "-1"),
    (GRAB, "Grab", "-1"),
    (SHOOT, "Shoot", "-11"),
    (CLIMB, "Climb Out", "ends game"),
]


class State:
    """Everything the screen needs to know right now."""

    def __init__(self):
        self.size = SIZES[0]
        self.reveal = False
        self.mode = "user"              # "user" or "ai"
        self.auto = False               # Auto-Play on/off (AI mode)
        self.theme = "dark"             # "dark" or "light"
        self.fx = Effects()             # animations and sound
        self._start(Game(World.random(self.size)))
        self._make_buttons()
        self.update_buttons()

    def _make_buttons(self):
        left = ui.PANEL.left + 20
        self.size_buttons = [
            ui.Button((left + i * 88, 56, 84, 36), f"{s} x {s}", lambda s=s: self.set_size(s))
            for i, s in enumerate(SIZES)]
        self.replay_button = ui.Button((left + 264, 56, 116, 36), "Replay", self.replay)
        self.hint_button = ui.Button((left + 286, 402, 94, 28), "Hint", self.hint)
        self.new_button = ui.Button((left, 100, 122, 36), "New World", self.new_world)
        self.reveal_button = ui.Button((left + 129, 100, 122, 36), "Reveal: OFF", self.toggle_reveal)
        self.mode_button = ui.Button((left + 258, 100, 122, 36), "Mode: USER", self.toggle_mode)
        # small icon buttons: sun = light theme, moon = dark theme, speaker = sound on, crossed speaker = mute
        self.sun_button = ui.Button((left + 232, 166, 32, 26), "", lambda: self.set_theme("light"), icon="sun")
        self.moon_button = ui.Button((left + 268, 166, 32, 26), "", lambda: self.set_theme("dark"), icon="moon")
        self.speaker_button = ui.Button((left + 312, 166, 32, 26), "", lambda: self.set_sound(True), icon="speaker")
        self.muted_button = ui.Button((left + 348, 166, 32, 26), "", lambda: self.set_sound(False), icon="muted")
        self.refresh_button = ui.Button((left + 186, 166, 32, 26), "", self.new_world, icon="refresh")
        self.over_button = ui.Button((0, 0, 56, 56), "", self.new_world, icon="refresh")   # shown on the GAME OVER card
        self.close_button = ui.Button((0, 0, 28, 28), "", self.close_card, icon="close")    # the X on the card
        self.reopen_button = ui.Button((0, 0, 220, 32), "GAME OVER", self.open_card)        # shown after the card is closed
        self.icon_buttons = [self.refresh_button, self.sun_button, self.moon_button, self.speaker_button, self.muted_button]
        self.slider = Slider((left + 190, 408, 190, 20), value=0.67)       # AI speed
        self.step_button = ui.Button((left, 428, 186, 38), "Step", self.ai_step)
        self.auto_button = ui.Button((left + 194, 428, 186, 38), "Auto-Play: OFF", self.toggle_auto)
        self.control_buttons = []
        for i, (action, label, sub) in enumerate(CONTROLS):
            rect = (left + (i % 3) * 129, 432 + (i // 3) * 56, 122, 48)
            self.control_buttons.append(ui.Button(rect, label, lambda a=action: self.do(a), sub, tag=action))

    def visible_buttons(self):
        buttons = self.size_buttons + [self.replay_button, self.new_button, self.reveal_button,
                                       self.mode_button] + self.icon_buttons
        if self.game.is_over:
            buttons += [self.over_button, self.close_button] if self.card_open else [self.reopen_button]
        if self.mode == "user":
            buttons += self.control_buttons + [self.hint_button]
        else:
            buttons += [self.step_button, self.auto_button]
        return buttons

    def update_buttons(self):
        """Called every frame: highlight the chosen ones, grey out what can't be used now."""
        for b, size in zip(self.size_buttons, SIZES):
            b.selected = (size == self.size)
        self.reveal_button.label = "Reveal: ON" if self.reveal else "Reveal: OFF"
        self.reveal_button.selected = self.reveal
        self.mode_button.label = "Mode: USER" if self.mode == "user" else "Mode: AI"
        self.mode_button.selected = (self.mode == "ai")
        for b in self.control_buttons:
            b.enabled = self.mode == "user" and self.game.can(b.tag)
        self.hint_button.enabled = self.mode == "user" and not self.game.is_over
        if self.game.is_over:
            self.auto = False
        self.step_button.enabled = self.mode == "ai" and not self.game.is_over
        self.auto_button.enabled = self.mode == "ai" and not self.game.is_over
        self.auto_button.label = "Pause" if self.auto else "Auto-Play"
        self.auto_button.selected = self.auto
        self.sun_button.selected = self.theme == "light"
        self.moon_button.selected = self.theme == "dark"
        on = self.fx.sound.enabled and self.fx.sound.available
        self.speaker_button.selected = on
        self.muted_button.selected = not on
        self.speaker_button.enabled = self.fx.sound.available       # no sound card: nothing to switch on

    # ---- actions
    def set_size(self, size):
        self.size = size
        self.new_world()

    def _start(self, game):
        """Begin playing `game`, with a fresh agent that watches it from the first percept."""
        self.game = game
        self.agent = Agent(game.world.size, game.percepts())
        self.fx.reset()
        self.log = [("info", "Find the gold, then climb out at the start.")]
        self.steps = 0
        self.trail = [game.pos]          # the cells walked so far, drawn as a dotted path
        self.card_open = True            # the GAME OVER card is shown when the game ends

    def close_card(self):
        self.card_open = False

    def open_card(self):
        self.card_open = True

    def new_world(self):
        self._start(Game(World.random(self.size)))

    def replay(self):
        """Play the very same world again: same pits, Wumpus and gold, but a fresh game."""
        self._start(Game(self.game.world))

    def toggle_reveal(self):
        self.reveal = not self.reveal

    def toggle_mode(self):
        self.mode = "ai" if self.mode == "user" else "user"
        self.auto = False

    def toggle_auto(self):
        self.auto = not self.auto

    def set_sound(self, on):
        self.fx.sound.enabled = on

    def toggle_sound(self):
        self.set_sound(not self.fx.sound.enabled)

    def set_theme(self, name):
        self.theme = name
        ui.set_theme(name)

    def toggle_theme(self):
        self.set_theme("light" if self.theme == "dark" else "dark")

    @property
    def ai_delay(self):
        """Milliseconds between AI moves, from the speed slider (right = faster)."""
        return int(1200 - self.slider.value * 1050)

    def _perform(self, action):
        """Do an action in the game, and let the agent observe what happened."""
        if self.game.can(action):
            before = self.game.pos
            message = self.game.act(action)
            self.fx.pace = self.ai_delay if self.auto else 600
            self.fx.on_action(action, before, self.game)
            if not self.game.is_over:           # a dead or finished hero has nothing more to sense
                self.agent.observe(action, self.game.percepts())
            if self.game.pos != self.trail[-1]:
                self.trail.append(self.game.pos)
            self.steps += 1
            self.log.append(("act", f"{self.steps}. {message}"))

    def do(self, action):
        if self.mode == "user":
            self._perform(action)

    def hint(self):
        """Ask the AI what it would do now. Free: it costs no points and changes nothing."""
        if self.mode == "user" and not self.game.is_over:
            action = self.agent.decide()
            name = {a: label for a, label, _ in CONTROLS}[action]
            self.log.append(("hint", f"Hint: {name}. {self.agent.thoughts[1]}"))

    def ai_step(self):
        """The AI picks one action from what it knows (percepts only) and does it."""
        if self.mode == "ai" and not self.game.is_over:
            self._perform(self.agent.decide())


def fit(window, canvas=(ui.WIDTH, ui.HEIGHT)):
    """How to place the fixed-size game picture inside the window without stretching it:
    returns (scale, (left, top), (width, height))."""
    scale = min(window[0] / canvas[0], window[1] / canvas[1])
    size = (max(1, int(canvas[0] * scale)), max(1, int(canvas[1] * scale)))
    return scale, ((window[0] - size[0]) // 2, (window[1] - size[1]) // 2), size


def to_game(pos, window):
    """Convert a mouse position in the window into a position on the 1100x680 game picture."""
    scale, (left, top), _ = fit(window)
    return (int((pos[0] - left) / scale), int((pos[1] - top) / scale))

def current_window(fullscreen):
    """The window's drawing surface. If the window was resized (you dragged its edge) and the surface
    still has the old size, make it again at the new size: that is what stops the picture being cut off."""
    window = pygame.display.get_surface()
    real = pygame.display.get_window_size()
    if real != window.get_size() and not fullscreen:
        window = pygame.display.set_mode(real, pygame.RESIZABLE)
    return window


def run():
    pygame.init()
    # start with a window that fits this screen (a small laptop screen gets a smaller window)
    desktop = pygame.display.get_desktop_sizes()[0]
    start = min(1.0, desktop[0] * 0.92 / ui.WIDTH, desktop[1] * 0.85 / ui.HEIGHT)
    window = pygame.display.set_mode((int(ui.WIDTH * start), int(ui.HEIGHT * start)), pygame.RESIZABLE)
    pygame.display.set_caption("Wumpus World")
    canvas = pygame.Surface((ui.WIDTH, ui.HEIGHT))           # the game is always drawn here, then scaled
    fonts = ui.make_fonts()
    clock = pygame.time.Clock()
    state = State()
    last_ai_move = 0
    fullscreen, windowed_size = False, window.get_size()
    dragging, hand = False, False        # dragging the resize grip in the bottom-right corner

    running = True
    while running:
        window = current_window(fullscreen)
        for event in pygame.event.get():
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
                raw = event.pos                         # the position in the window itself
                # give the rest of the code a position on the game picture, not on the window
                event = pygame.event.Event(event.type, {**event.dict, "pos": to_game(raw, window.get_size())})
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and ui.GRIP.collidepoint(event.pos) and not fullscreen:
                    dragging = True                     # grabbed the corner: the window follows the mouse
                    continue
                if event.type == pygame.MOUSEBUTTONUP:
                    dragging = False
                if event.type == pygame.MOUSEMOTION and dragging:
                    w = max(raw[0] / (1080 / ui.WIDTH), raw[1] / (660 / ui.HEIGHT) * ui.WIDTH / ui.HEIGHT)
                    w = max(550, min(w, desktop[0], (desktop[1] - 80) * ui.WIDTH / ui.HEIGHT))
                    pygame.display.set_mode((int(w), int(w * ui.HEIGHT / ui.WIDTH)), pygame.RESIZABLE)
                    window = pygame.display.get_surface()
                    continue
            if state.mode == "ai" and state.slider.handle(event):
                continue                                  # the speed slider used this mouse event
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE and not fullscreen:
                    running = False
                elif event.key in (pygame.K_F11, pygame.K_ESCAPE):          # full screen on / off
                    fullscreen = not fullscreen
                    if fullscreen:
                        windowed_size = window.get_size()
                        pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                    else:
                        pygame.display.set_mode(windowed_size, pygame.RESIZABLE)
                elif event.key in (pygame.K_MINUS, pygame.K_EQUALS, pygame.K_KP_MINUS, pygame.K_KP_PLUS) and not fullscreen:
                    grow = 1.1 if event.key in (pygame.K_EQUALS, pygame.K_KP_PLUS) else 1 / 1.1    # window smaller / bigger
                    w, h = window.get_size()
                    pygame.display.set_mode((max(550, int(w * grow)), max(340, int(h * grow))), pygame.RESIZABLE)
                elif event.key in (pygame.K_4, pygame.K_5, pygame.K_6):
                    state.set_size(event.key - pygame.K_0)
                elif event.key == pygame.K_n:
                    state.new_world()
                elif event.key == pygame.K_p:
                    state.replay()
                elif event.key == pygame.K_h:
                    state.hint()
                elif event.key == pygame.K_m:
                    state.toggle_sound()
                elif event.key == pygame.K_t:
                    state.toggle_theme()
                elif event.key == pygame.K_r:
                    state.toggle_reveal()
                elif event.key == pygame.K_TAB:
                    state.toggle_mode()
                elif event.key == pygame.K_SPACE and state.mode == "ai":
                    state.ai_step()
                elif event.key in KEYS:
                    state.do(KEYS[event.key])
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for button in state.visible_buttons():
                    if button.enabled and button.rect.collidepoint(event.pos):
                        button.action()
                        break

        now = pygame.time.get_ticks()
        if state.auto and now - last_ai_move >= state.ai_delay:
            state.ai_step()
            last_ai_move = now

        window = current_window(fullscreen)
        over_grip = (dragging or ui.GRIP.collidepoint(to_game(pygame.mouse.get_pos(), window.get_size()))) and not fullscreen
        if over_grip != hand:                           # a diagonal two-headed arrow over the corner
            hand = over_grip
            try:
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZENWSE if hand else pygame.SYSTEM_CURSOR_ARROW)
            except pygame.error:
                pass                                    # no cursor support here: the grip still works
        ui.set_mouse(to_game(pygame.mouse.get_pos(), window.get_size()))     # for the hover highlight
        state.update_buttons()
        ui.draw_frame(canvas, fonts, state)
        scale, offset, size = fit(window.get_size())
        window.fill((0, 0, 0))
        window.blit(canvas if size == canvas.get_size() else pygame.transform.smoothscale(canvas, size), offset)
        pygame.display.flip()
        clock.tick(60)
    pygame.quit()


if __name__ == "__main__":
    run()