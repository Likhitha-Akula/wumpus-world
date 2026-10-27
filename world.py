"""The hidden world: where the Wumpus, pits and gold are, and what can be sensed.

Coordinates are (column, row). (0, 0) is the bottom-left start cell.
This file knows nothing about drawing, so it is easy to test and to explain.
"""
import random
from collections import deque

START = (0, 0)
SIZES = (4, 5, 6)


class World:
    def __init__(self, size, wumpus, pits, gold, seed=None):
        self.size = size
        self.wumpus = wumpus
        self.pits = frozenset(pits)
        self.gold = gold
        self.seed = seed

    # ------------------------------------------------------------ creating
    @classmethod
    def random(cls, size=4, seed=None):
        """Make a random world. The same seed always gives the same world."""
        if seed is None:
            seed = random.randrange(1_000_000)
        rng = random.Random(seed)
        cells = [(c, r) for c in range(size) for r in range(size) if (c, r) != START]
        n_pits = max(2, round(0.15 * size * size))  # 4x4 -> 2, 5x5 -> 4, 6x6 -> 5
        while True:
            chosen = rng.sample(cells, n_pits + 2)  # all different cells, never the start
            world = cls(size, wumpus=chosen[n_pits], pits=chosen[:n_pits],
                        gold=chosen[n_pits + 1], seed=seed)
            if world.is_solvable():
                return world  # otherwise re-roll

    # ------------------------------------------------------------- helpers
    def in_bounds(self, cell):
        return 0 <= cell[0] < self.size and 0 <= cell[1] < self.size

    def neighbours(self, cell):
        c, r = cell
        options = [(c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)]
        return [x for x in options if self.in_bounds(x)]

    def is_deadly(self, cell):
        return cell in self.pits or cell == self.wumpus

    # ------------------------------------------------------------- percepts
    def percepts(self, cell):
        """What the agent feels standing in `cell` (bump and scream come in Step 2)."""
        near = self.neighbours(cell)
        return {
            "breeze": any(n in self.pits for n in near),
            "stench": self.wumpus in near,
            "glitter": cell == self.gold,
        }

    # ------------------------------------------------------------ solvable?
    def is_solvable(self):
        """True if a route from the start to the gold exists that avoids every
        pit and the Wumpus. (The AI may still need to reason carefully to find it.)"""
        seen = {START}
        queue = deque([START])
        while queue:
            cell = queue.popleft()
            if cell == self.gold:
                return True
            for n in self.neighbours(cell):
                if n not in seen and not self.is_deadly(n):
                    seen.add(n)
                    queue.append(n)
        return False