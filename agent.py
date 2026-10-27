"""The AI agent. It sees ONLY percepts (never the World) and decides one action at a time.

observe()  - called after every action: updates where the agent thinks it is, and its KB.
decide()   - picks the next action and writes down WHY (self.thoughts).

Priority of decisions:
  1. glitter here            -> GRAB
  2. carrying the gold       -> walk home over known-safe cells, then CLIMB
  3. a safe cell not visited -> walk to the nearest one (BFS)
  4. stuck, arrow, suspects  -> go to the best shooting spot and SHOOT
  5. stuck                   -> take the least risky step, or give up if too risky
"""
from collections import deque

from game import (CLIMB, DIRS, FORWARD, GRAB, SHOOT, TURN_LEFT, TURN_RIGHT)
from kb import KnowledgeBase
from world import START

MAX_RISK = 0.5          # never walk into a cell that is more likely deadly than this


class Agent:
    def __init__(self, size, percepts):
        self.size = size
        self.pos = START                 # the agent keeps track of its own position
        self.facing = 0                  # ... and direction (dead reckoning)
        self.has_arrow = True
        self.has_gold = False
        self.kb = KnowledgeBase(size)
        self.thoughts = ["Starting at (0, 0)."]
        self.observe(None, percepts)

    # ------------------------------------------------------------ learning
    def observe(self, action, percepts):
        if action == TURN_LEFT:
            self.facing = (self.facing + 1) % 4
        elif action == TURN_RIGHT:
            self.facing = (self.facing - 1) % 4
        elif action == FORWARD and not percepts["bump"]:
            dx, dy = DIRS[self.facing]
            self.pos = (self.pos[0] + dx, self.pos[1] + dy)
        elif action == GRAB:
            self.has_gold = True
        elif action == SHOOT:
            self.has_arrow = False
            if not percepts["scream"]:
                self.kb.rule_out(self._line(self.pos, self.facing))
        self.kb.tell(self.pos, percepts)

    def _line(self, cell, facing):
        """Cells an arrow would cross when shot from `cell` towards `facing`."""
        dx, dy = DIRS[facing]
        out, c = [], (cell[0] + dx, cell[1] + dy)
        while 0 <= c[0] < self.size and 0 <= c[1] < self.size:
            out.append(c)
            c = (c[0] + dx, c[1] + dy)
        return out

    # ------------------------------------------------------------ deciding
    def decide(self):
        kb, here = self.kb, self.pos
        sense = self._describe_senses()

        if kb.gold_seen == here and not self.has_gold:
            return self._say(sense, "Glitter! Grab the gold.", GRAB)

        if self.has_gold:
            if here == START:
                return self._say(sense, "I have the gold and I am home. Climb out.", CLIMB)
            return self._walk(sense, "I have the gold, so I head home over safe cells.", {START})

        safe_new = {c for c in kb.safe if c not in kb.visited}
        if safe_new:
            return self._walk(sense, f"{len(safe_new)} safe cell(s) not visited yet. Going to the nearest.", safe_new)

        # stuck: nothing safe is left to explore
        if self.has_arrow and kb.maybe_wumpus and not kb.wumpus_dead and any(kb.stench.values()):
            spot = self._best_shot()
            if spot:
                cell, facing, hits = spot
                why = ("The Wumpus must be at %s." % (kb.wumpus,) if kb.wumpus
                       else f"The Wumpus could be in {len(kb.maybe_wumpus)} cells.")
                if (here, self.facing) == (cell, facing):
                    return self._say(sense, f"{why} Shooting along this line (covers {hits}).", SHOOT)
                if here == cell:
                    return self._say(sense, f"{why} Turning to shoot.", self._turn_towards(facing))
                return self._walk(sense, f"No safe cell left. {why} Going to a shooting spot.", {cell})

        options = [c for c in kb.risk if c not in kb.pits and self._path(here, {c})]
        if options:
            best = min(options, key=lambda c: (kb.risk[c], len(self._path(here, {c}))))
            if kb.risk[best] <= MAX_RISK:
                return self._walk(sense, f"Stuck. Taking the least risky step: {best}.", {best})
        if here == START:
            return self._say(sense, "Too risky to go on. I give up and climb out.", CLIMB)
        return self._walk(sense, "Too risky to go on. Heading home to climb out.", {START})

    # ------------------------------------------------------------ helpers
    def _say(self, sense, plan, action):
        self.thoughts = [sense, plan]
        return action

    def _describe_senses(self):
        kb = self.kb
        felt = [name for name, d in (("a breeze", kb.breeze), ("a stench", kb.stench)) if d.get(self.pos)]
        return f"At {self.pos}: " + (" and ".join(felt) if felt else "nothing special") + "."

    def _turn_towards(self, facing):
        return TURN_LEFT if (facing - self.facing) % 4 in (1, 2) else TURN_RIGHT

    def _passable(self):
        return self.kb.visited | self.kb.safe

    def _path(self, start, goals):
        """Breadth-first search over cells known to be safe. Returns the list of cells to walk."""
        passable = self._passable()
        queue, came = deque([start]), {start: None}
        while queue:
            cell = queue.popleft()
            if cell in goals and cell != start:
                path = []
                while cell != start:
                    path.append(cell)
                    cell = came[cell]
                return path[::-1]
            for dx, dy in DIRS:
                n = (cell[0] + dx, cell[1] + dy)
                if n in came or not (0 <= n[0] < self.size and 0 <= n[1] < self.size):
                    continue
                if n in passable or n in goals:
                    came[n] = cell
                    if n in goals:
                        queue.appendleft(n)       # reached a goal: finish at once
                    else:
                        queue.append(n)
        return None

    def _walk(self, sense, plan, goals):
        path = self._path(self.pos, goals)
        if not path:                              # nothing reachable: go home as a last resort
            if self.pos == START:
                return self._say(sense, "Nowhere left to go. Climb out.", CLIMB)
            return self._walk(sense, "Nowhere left to go. Heading home.", {START})
        step = path[0]
        want = DIRS.index((step[0] - self.pos[0], step[1] - self.pos[1]))
        action = FORWARD if want == self.facing else self._turn_towards(want)
        return self._say(sense, plan, action)

    def _best_shot(self):
        """The (cell, facing) from which an arrow would cross the most suspect cells."""
        best = None
        for cell in self._passable():
            for facing in range(4):
                hits = len(set(self._line(cell, facing)) & self.kb.maybe_wumpus)
                if not hits:
                    continue
                if cell == self.pos:
                    dist = 0
                else:
                    path = self._path(self.pos, {cell})
                    if path is None:
                        continue
                    dist = len(path)
                key = (-hits, dist)
                if best is None or key < best[0]:
                    best = (key, cell, facing, hits)
        return None if best is None else best[1:]