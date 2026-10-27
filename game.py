"""The rules of the game: what each action does to the agent, the arrow and the score.

`Game` owns everything that CHANGES while playing (position, facing, arrow, gold,
score, whether the Wumpus is alive). `World` (world.py) owns what never changes.
Both the human player and the AI will call `game.act(...)`, so the rules are
identical for both.
"""
from world import START

# --- actions -----------------------------------------------------------------
FORWARD, TURN_LEFT, TURN_RIGHT, GRAB, SHOOT, CLIMB = (
    "forward", "turn_left", "turn_right", "grab", "shoot", "climb")
ACTIONS = (FORWARD, TURN_LEFT, TURN_RIGHT, GRAB, SHOOT, CLIMB)

# --- directions: 0 East, 1 North, 2 West, 3 South (turning left adds 1) -------
DIRS = [(1, 0), (0, 1), (-1, 0), (0, -1)]
DIR_NAMES = ["East", "North", "West", "South"]

# --- scoring (standard Russell & Norvig) ---------------------------------------
STEP_COST = -1
ARROW_COST = -10
GOLD_REWARD = 1000
DEATH_PENALTY = -1000

# --- game status ------------------------------------------------------------
PLAYING = "playing"
WON = "won"                      # climbed out with the gold
LEFT_EMPTY = "left_empty"        # climbed out without the gold
DEAD_PIT = "dead_pit"
DEAD_WUMPUS = "dead_wumpus"


class Game:
    def __init__(self, world):
        self.world = world
        self.pos = START
        self.facing = 0                  # start facing East
        self.has_arrow = True
        self.has_gold = False
        self.wumpus_alive = True
        self.score = 0
        self.status = PLAYING
        self.visited = {START}
        self.bump = False                # true only right after walking into a wall
        self.scream = False              # true only right after the Wumpus dies
        self.message = "Find the gold, then climb out at the start."

    # ------------------------------------------------------------ questions
    @property
    def is_over(self):
        return self.status != PLAYING

    def percepts(self):
        """Everything the agent can sense right now. This is ALL the AI may use."""
        p = self.world.percepts(self.pos)
        p["stench"] = p["stench"] and self.wumpus_alive
        p["glitter"] = p["glitter"] and not self.has_gold
        p["bump"] = self.bump
        p["scream"] = self.scream
        return p

    def can(self, action):
        """Is this action allowed right now? Illegal actions are ignored and cost nothing."""
        if self.is_over:
            return False
        if action == GRAB:
            return self.percepts()["glitter"]
        if action == SHOOT:
            return self.has_arrow
        if action == CLIMB:
            return self.pos == START
        return True

    # -------------------------------------------------------------- acting
    def act(self, action):
        """Do one action. Returns the message describing what happened."""
        if self.is_over:
            return self._say("The game is over. Start a new world.")
        if not self.can(action):
            return self._say(self._why_not(action))

        self.bump = False
        self.scream = False
        self.score += STEP_COST

        if action == TURN_LEFT:
            self.facing = (self.facing + 1) % 4
            self._say(f"Turned left, now facing {DIR_NAMES[self.facing]}.")
        elif action == TURN_RIGHT:
            self.facing = (self.facing - 1) % 4
            self._say(f"Turned right, now facing {DIR_NAMES[self.facing]}.")
        elif action == FORWARD:
            self._forward()
        elif action == GRAB:
            self.has_gold = True
            self._say("You grabbed the gold! Now climb out at the start.")
        elif action == SHOOT:
            self._shoot()
        elif action == CLIMB:
            self._climb()
        return self.message

    # ------------------------------------------------------------- helpers
    def _say(self, text):
        self.message = text
        return text

    def _why_not(self, action):
        return {GRAB: "There is no gold here to grab.",
                SHOOT: "You have no arrow left.",
                CLIMB: "You can only climb out at the start cell."}.get(action, "You can't do that.")

    def _forward(self):
        dx, dy = DIRS[self.facing]
        target = (self.pos[0] + dx, self.pos[1] + dy)
        if not self.world.in_bounds(target):
            self.bump = True
            self._say("Bump! There is a wall in front of you.")
            return
        self.pos = target
        self.visited.add(target)
        if target in self.world.pits:
            self.score += DEATH_PENALTY
            self.status = DEAD_PIT
            self._say("You fell into a pit!")
        elif target == self.world.wumpus and self.wumpus_alive:
            self.score += DEATH_PENALTY
            self.status = DEAD_WUMPUS
            self._say("The Wumpus ate you!")
        else:
            self._say(f"Moved to {target}.")

    def _shoot(self):
        self.has_arrow = False
        self.score += ARROW_COST
        dx, dy = DIRS[self.facing]
        cell = (self.pos[0] + dx, self.pos[1] + dy)
        while self.world.in_bounds(cell):             # the arrow flies until it hits a wall
            if self.wumpus_alive and cell == self.world.wumpus:
                self.wumpus_alive = False
                self.scream = True
                self._say("You shot the arrow... a terrible SCREAM! The Wumpus is dead.")
                return
            cell = (cell[0] + dx, cell[1] + dy)
        self._say("You shot the arrow... it hit the wall. Nothing happened.")

    def _climb(self):
        if self.has_gold:
            self.score += GOLD_REWARD
            self.status = WON
            self._say("You climbed out with the gold. YOU WIN!")
        else:
            self.status = LEFT_EMPTY
            self._say("You climbed out without the gold. Game over.")