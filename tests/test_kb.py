import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kb import KnowledgeBase


def senses(breeze=False, stench=False, glitter=False, bump=False, scream=False):
    return {"breeze": breeze, "stench": stench, "glitter": glitter, "bump": bump, "scream": scream}


def test_no_breeze_and_no_stench_make_the_neighbours_safe():
    kb = KnowledgeBase(4)
    kb.tell((0, 0), senses())
    assert kb.status((1, 0)) == "safe" and kb.status((0, 1)) == "safe"
    assert kb.status((0, 0)) == "visited"
    assert kb.status((3, 3)) == "unknown"


def test_a_breeze_alone_proves_nothing():
    kb = KnowledgeBase(4)
    kb.tell((0, 0), senses(breeze=True))
    assert kb.status((1, 0)) == "unknown" and kb.status((0, 1)) == "unknown"
    assert kb.pits == set()                                  # neither is PROVEN to be a pit


def test_breeze_plus_one_safe_neighbour_proves_the_other_is_a_pit():
    kb = KnowledgeBase(4)
    kb.tell((0, 0), senses(breeze=True))
    kb.tell((1, 0), senses())                                # (1,0) turned out safe and calm
    assert kb.status((0, 1)) == "pit"


def test_two_stenches_pin_down_the_wumpus():
    kb = KnowledgeBase(4)
    kb.tell((0, 0), senses())                                # calm start: not next to (0,0)
    kb.tell((1, 0), senses(stench=True))                     # Wumpus is next to (1,0): (2,0) or (1,1)
    assert kb.maybe_wumpus == {(2, 0), (1, 1)}
    kb.tell((0, 1), senses(stench=True))                     # ... and next to (0,1): so it is at (1,1)
    assert kb.wumpus == (1, 1) and kb.status((1, 1)) == "wumpus"


def test_a_scream_means_the_wumpus_is_dead():
    kb = KnowledgeBase(4)
    kb.tell((1, 0), senses(stench=True))
    kb.tell((1, 0), senses(scream=True))
    assert kb.wumpus_dead and kb.maybe_wumpus == set()


def test_an_arrow_that_missed_rules_cells_out():
    kb = KnowledgeBase(4)
    kb.tell((0, 0), senses())
    kb.tell((1, 0), senses(stench=True))
    assert kb.maybe_wumpus == {(2, 0), (1, 1)}
    kb.rule_out([(2, 0), (3, 0)])                            # arrow flew over these, no scream
    assert kb.maybe_wumpus == {(1, 1)}


def test_risk_is_higher_for_a_breezy_neighbour_than_for_a_far_cell():
    kb = KnowledgeBase(5)
    kb.tell((0, 0), senses(breeze=True))
    assert kb.risk[(1, 0)] > 0.4                             # one of the two neighbours holds a pit
    assert kb.risk[(4, 4)] < 0.25                            # a far-away cell is no more risky than average


def test_standing_on_a_pit_does_not_crash_the_knowledge_base():
    # the hero died at (1,0) and a breeze was felt at (0,0): no layout "fits", but nothing may crash
    kb = KnowledgeBase(4)
    kb.tell((0, 0), senses(breeze=True))
    kb.tell((1, 0), senses())
    kb.tell((2, 0), senses(breeze=True))