import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from agent import Agent
from game import (CLIMB, FORWARD, GRAB, SHOOT, TURN_LEFT, TURN_RIGHT, WON, Game)
from world import SIZES, World


def play(game, limit=600):
    """Let the AI play a whole game. Returns (game, agent)."""
    agent = Agent(game.world.size, game.percepts())
    for _ in range(limit):
        if game.is_over:
            break
        action = agent.decide()
        game.act(action)
        if not game.is_over:
            agent.observe(action, game.percepts())
    return game, agent


def test_grabs_the_gold_when_it_glitters():
    g = Game(World(4, wumpus=(3, 3), pits=[(2, 2), (3, 1)], gold=(1, 0)))
    a = Agent(4, g.percepts())
    for _ in range(60):
        act = a.decide()
        g.act(act)
        if g.has_gold:
            break
        a.observe(act, g.percepts())
    assert g.has_gold


def test_a_complete_win_in_a_hand_made_world():
    g, _ = play(Game(World(4, wumpus=(3, 3), pits=[(2, 2), (3, 1)], gold=(1, 0))))
    assert g.status == WON and g.score > 900


@pytest.mark.parametrize("size", SIZES)
def test_every_game_ends(size):
    for seed in range(120):
        g, _ = play(Game(World.random(size, seed)))
        assert g.is_over


@pytest.mark.parametrize("size", SIZES)
def test_it_never_walks_into_a_cell_it_has_proven_deadly(size):
    for seed in range(80):
        g = Game(World.random(size, seed))
        a = Agent(size, g.percepts())
        for _ in range(600):
            if g.is_over:
                break
            action = a.decide()
            if action == FORWARD:
                dx, dy = [(1, 0), (0, 1), (-1, 0), (0, -1)][a.facing]
                target = (a.pos[0] + dx, a.pos[1] + dy)
                if 0 <= target[0] < size and 0 <= target[1] < size:
                    assert a.kb.status(target) not in ("pit", "wumpus")
            g.act(action)
            if not g.is_over:
                a.observe(action, g.percepts())


def test_the_ai_cannot_cheat_two_worlds_that_look_the_same_give_the_same_moves():
    # the two worlds differ only in cells the agent never sees before its first move
    w1 = World(5, wumpus=(4, 4), pits=[(3, 3), (4, 2)], gold=(2, 4))
    w2 = World(5, wumpus=(3, 4), pits=[(2, 3), (4, 1)], gold=(1, 4))
    g1, g2 = Game(w1), Game(w2)
    assert g1.percepts() == g2.percepts()
    a1, a2 = Agent(5, g1.percepts()), Agent(5, g2.percepts())
    assert a1.decide() == a2.decide()


def test_it_does_not_shoot_without_a_stench():
    for seed in range(100):
        g = Game(World.random(5, seed))
        a = Agent(5, g.percepts())
        smelled = False
        for _ in range(600):
            if g.is_over:
                break
            smelled = smelled or g.percepts()["stench"]
            action = a.decide()
            if action == SHOOT:
                assert smelled
            g.act(action)
            if not g.is_over:
                a.observe(action, g.percepts())


def test_a_hint_changes_nothing():
    g = Game(World.random(4, 7))
    a = Agent(4, g.percepts())
    score, pos, facing = g.score, g.pos, g.facing
    first = a.decide()
    assert a.decide() == first                                # asking again gives the same answer
    assert (g.score, g.pos, g.facing) == (score, pos, facing)


def test_it_keeps_track_of_a_human_players_moves_too():
    import random
    rng = random.Random(5)
    for seed in range(40):
        g = Game(World.random(4, seed))
        a = Agent(4, g.percepts())
        for _ in range(30):
            if g.is_over:
                break
            action = rng.choice([FORWARD, FORWARD, TURN_LEFT, TURN_RIGHT, GRAB, SHOOT, CLIMB])
            if g.can(action):
                g.act(action)
                if not g.is_over:
                    a.observe(action, g.percepts())
                    assert a.pos == g.pos and a.facing == g.facing