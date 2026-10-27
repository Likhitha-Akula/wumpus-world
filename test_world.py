import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from world import SIZES, START, World


@pytest.mark.parametrize("size", SIZES)
def test_world_has_the_right_things(size):
    for seed in range(300):
        w = World.random(size, seed)
        everything = [w.wumpus, w.gold, *w.pits]
        assert len(set(everything)) == len(everything)        # no two things share a cell
        assert START not in everything                          # the start cell is always safe
        assert all(w.in_bounds(c) for c in everything)
        assert len(w.pits) >= 2


@pytest.mark.parametrize("size", SIZES)
def test_every_random_world_is_solvable(size):
    assert all(World.random(size, seed).is_solvable() for seed in range(300))


def test_same_seed_gives_the_same_world():
    a, b = World.random(5, 42), World.random(5, 42)
    assert (a.wumpus, a.pits, a.gold) == (b.wumpus, b.pits, b.gold)


def test_percepts_in_a_hand_made_world():
    w = World(4, wumpus=(1, 2), pits=[(2, 0)], gold=(3, 3))
    assert w.percepts((1, 0)) == {"breeze": True, "stench": False, "glitter": False}
    assert w.percepts((1, 1)) == {"breeze": False, "stench": True, "glitter": False}
    assert w.percepts((3, 3))["glitter"] is True
    assert w.percepts(START) == {"breeze": False, "stench": False, "glitter": False}


def test_neighbours_at_corner_and_middle():
    w = World(4, wumpus=(1, 2), pits=[(2, 0)], gold=(3, 3))
    assert sorted(w.neighbours((0, 0))) == [(0, 1), (1, 0)]
    assert len(w.neighbours((1, 1))) == 4


def test_unsolvable_world_is_detected():
    # gold sealed in the corner behind two pits
    w = World(4, wumpus=(2, 2), pits=[(2, 3), (3, 2)], gold=(3, 3))
    assert not w.is_solvable()