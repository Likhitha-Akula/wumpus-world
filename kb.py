"""The agent's knowledge base: what it has sensed, and what it can logically deduce.

The KB never sees the World. It is only told percepts ("tell"), and it answers
questions about cells ("ask"). All reasoning is propositional logic done by
model checking: list every possible placement of pits that agrees with what was
sensed, then see what is true in ALL of them.
"""
from game import DIRS

PIT_CHANCE = 0.15                          # roughly how many cells hold a pit
RATIO = PIT_CHANCE / (1 - PIT_CHANCE)


class KnowledgeBase:
    def __init__(self, size):
        self.size = size
        self.visited = set()        # cells the agent has stood on (so they are safe)
        self.breeze = {}            # cell -> True/False  (what was sensed there)
        self.stench = {}            # cell -> True/False
        self.wumpus_dead = False
        self.gold_seen = None       # cell where glitter was sensed
        # results of the last inference
        self.safe = set()           # cells proven free of pit AND wumpus
        self.pits = set()           # cells proven to hold a pit
        self.wumpus = None          # cell proven to hold the Wumpus
        self.maybe_pit = set()      # frontier cells that might hold a pit
        self.maybe_wumpus = set()   # cells that might hold the Wumpus
        self.risk = {}              # cell -> chance (0..1) that stepping there kills the agent
        self.ruled_out = set()      # cells an arrow flew through without a scream
        self.frontier = set()       # unvisited cells next to a visited cell

    # ------------------------------------------------------------ geometry
    def neighbours(self, cell):
        c, r = cell
        out = []
        for dc, dr in DIRS:
            n = (c + dc, r + dr)
            if 0 <= n[0] < self.size and 0 <= n[1] < self.size:
                out.append(n)
        return out

    # ------------------------------------------------------------ TELL
    def tell(self, cell, percepts):
        """Record what was sensed at `cell`, then re-run the inference."""
        self.visited.add(cell)
        self.breeze[cell] = percepts["breeze"]
        self.stench[cell] = percepts["stench"]
        if percepts["scream"]:
            self.wumpus_dead = True
        if percepts["glitter"]:
            self.gold_seen = cell
        self._infer()

    def rule_out(self, cells):
        """An arrow flew over these cells and nothing screamed: the Wumpus is not there."""
        self.ruled_out |= set(cells)
        self._infer()

    # ------------------------------------------------------------ ASK
    def status(self, cell):
        """'visited', 'safe', 'pit', 'wumpus' or 'unknown'."""
        if cell in self.visited:
            return "visited"
        if cell in self.pits:
            return "pit"
        if cell == self.wumpus:
            return "wumpus"
        if cell in self.safe:
            return "safe"
        return "unknown"

    # ------------------------------------------------------------ inference
    def _infer(self):
        self._infer_pits()
        self._infer_wumpus()
        # a cell is safe when it can have neither a pit nor the Wumpus
        self.safe = set()
        self.risk = {}
        for c in self._all_cells():
            if c in self.visited:
                continue
            self.risk[c] = min(1.0, self._pit_risk.get(c, 0.2)
                               + (1 / len(self.maybe_wumpus) if c in self.maybe_wumpus else 0))
            no_pit = c not in self.maybe_pit and c not in self.pits
            no_wumpus = c not in self.maybe_wumpus
            if no_pit and no_wumpus:
                self.safe.add(c)

    def _all_cells(self):
        return [(c, r) for c in range(self.size) for r in range(self.size)]

    def _infer_pits(self):
        # Rules:  no breeze at X -> no pit next to X
        #         breeze at X    -> at least one pit next to X
        frontier = sorted({n for v in self.visited for n in self.neighbours(v)} - self.visited)
        constraints = []
        for v in self.visited:
            ns = self.neighbours(v)
            constraints.append((ns, self.breeze[v]))   # (cells, must-contain-a-pit?)

        models = []
        assign = {}

        def ok():
            for ns, must in constraints:
                if all(n in assign or n in self.visited for n in ns):
                    has = any(assign.get(n, False) for n in ns)
                    if has != must:
                        return False
            return True

        def search(i):
            if i == len(frontier):
                models.append(dict(assign))
                return
            for value in (False, True):
                assign[frontier[i]] = value
                if ok():
                    search(i + 1)
            assign.pop(frontier[i], None)

        search(0)
        self.pits, self.maybe_pit, self._pit_risk = set(), set(), {}
        self.frontier = set(frontier)
        # a layout with more pits is less likely: weight each by (p / (1-p)) per pit
        total = sum(RATIO ** sum(m.values()) for m in models)
        if total == 0:          # no layout fits (only after the hero died in a pit): nothing to infer
            return
        for cell in frontier:
            self._pit_risk[cell] = sum(RATIO ** sum(m.values()) for m in models if m[cell]) / total
            values = {m[cell] for m in models}
            if values == {True}:
                self.pits.add(cell)
            elif True in values:
                self.maybe_pit.add(cell)
        # cells with no information at all might hold a pit too
        for c in self._all_cells():
            if c not in self.visited and c not in frontier:
                self.maybe_pit.add(c)

    def _infer_wumpus(self):
        # Rules:  no stench at X -> Wumpus not next to X
        #         stench at X    -> Wumpus is next to X     (exactly one Wumpus)
        if self.wumpus_dead:
            self.wumpus, self.maybe_wumpus = None, set()
            return
        candidates = set()
        for c in self._all_cells():
            if c in self.visited or c in self.ruled_out:
                continue
            fine = True
            for v in self.visited:
                near = c in self.neighbours(v)
                if self.stench[v] != near:
                    fine = False
                    break
            if fine:
                candidates.add(c)
        self.maybe_wumpus = candidates
        self.wumpus = next(iter(candidates)) if len(candidates) == 1 else None
        if self.wumpus:
            self.maybe_wumpus = {self.wumpus}