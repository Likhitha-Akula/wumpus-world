import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game import (CLIMB, DEAD_PIT, DEAD_WUMPUS, FORWARD, GRAB, LEFT_EMPTY, PLAYING, SHOOT,
                  TURN_LEFT, TURN_RIGHT, WON, Game)
from world import START, World


def make(wumpus=(3, 3), pits=((2, 2),), gold=(1, 0)):
    return Game(World(4, wumpus=wumpus, pits=list(pits), gold=gold))


def test_starts_at_zero_facing_east_with_arrow():
    g = make()
    assert (g.score, g.pos, g.facing, g.has_arrow, g.status) == (0, START, 0, True, PLAYING)


def test_every_action_costs_one():
    g = make()
    g.act(TURN_LEFT)
    g.act(TURN_RIGHT)
    g.act(FORWARD)
    assert g.score == -3


def test_turning_changes_direction():
    g = make()
    g.act(TURN_LEFT)
    assert g.facing == 1            # North
    g.act(TURN_RIGHT)
    g.act(TURN_RIGHT)
    assert g.facing == 3            # South


def test_bump_into_wall_costs_one_and_sets_bump():
    g = make()
    g.act(TURN_RIGHT)               # face South, the wall
    g.act(FORWARD)
    assert g.pos == START and g.percepts()["bump"] is True
    assert g.score == -2
    g.act(TURN_LEFT)
    assert g.percepts()["bump"] is False   # bump only lasts one step


def test_winning_run_scores_994():
    g = make()                      # gold at (1,0), right next to the start
    g.act(FORWARD)
    assert g.percepts()["glitter"] is True
    g.act(GRAB)
    g.act(TURN_LEFT)
    g.act(TURN_LEFT)
    g.act(FORWARD)
    g.act(CLIMB)
    assert g.status == WON and g.score == -1 - 1 - 1 - 1 - 1 - 1 + 1000 == 994


def test_falling_in_a_pit_ends_the_game():
    g = make(pits=((1, 0),))
    g.act(FORWARD)
    assert g.status == DEAD_PIT and g.score == -1 - 1000 + 0
    before = g.score
    g.act(FORWARD)                   # nothing works after the game ends
    assert g.score == before


def test_walking_into_the_wumpus_ends_the_game():
    g = make(wumpus=(1, 0), gold=(3, 0))
    g.act(FORWARD)
    assert g.status == DEAD_WUMPUS and g.score == -1001


def test_arrow_kills_wumpus_in_line_and_costs_eleven_total():
    g = make(wumpus=(3, 0), gold=(1, 3))
    g.act(SHOOT)                     # facing East along row 0
    assert g.wumpus_alive is False and g.percepts()["scream"] is True
    assert g.score == -11
    assert g.has_arrow is False


def test_stench_disappears_after_the_wumpus_dies():
    g = make(wumpus=(2, 0), gold=(1, 3))
    g.act(FORWARD)                   # at (1,0), next to the Wumpus
    assert g.percepts()["stench"] is True
    g.act(SHOOT)
    assert g.wumpus_alive is False
    g.act(TURN_LEFT)                 # scream is gone, stench is gone
    p = g.percepts()
    assert p["stench"] is False and p["scream"] is False


def test_arrow_that_misses_is_still_used_up():
    g = make(wumpus=(3, 3))
    g.act(SHOOT)
    assert g.wumpus_alive and g.has_arrow is False and g.score == -11
    score = g.score
    g.act(SHOOT)                     # no arrow: ignored, costs nothing
    assert g.score == score


def test_illegal_actions_are_ignored_and_free():
    g = make()
    g.act(GRAB)                      # no glitter at the start
    g.act(FORWARD)
    g.act(CLIMB)                     # not at the start any more
    assert g.score == -1 and g.status == PLAYING


def test_climbing_without_gold_ends_the_game():
    g = make()
    g.act(CLIMB)
    assert g.status == LEFT_EMPTY and g.score == -1


def test_percepts_only_use_what_the_agent_can_sense():
    g = make(wumpus=(1, 1), pits=((2, 0),), gold=(3, 3))
    g.act(FORWARD)                   # at (1,0): pit east -> breeze, Wumpus north -> stench
    p = g.percepts()
    assert p["breeze"] and p["stench"] and not p["glitter"]
    assert set(p) == {"breeze", "stench", "glitter", "bump", "scream"}