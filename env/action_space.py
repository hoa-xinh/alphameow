# action_space.py
from gymnasium import spaces
import numpy as np

ACTIONS = {
    0:  "draw_card",
    1:  "play_skip",
    2:  "play_attack",
    3:  "play_defuse",
    4:  "play_nope",
    5:  "play_shuffle",
    6:  "play_see_the_future",
    7:  "play_favor",
    8:  "play_cat_pair",
    9:  "play_cat_triple",
    10: "play_five_diff",
}

NUM_ACTIONS = len(ACTIONS)

def get_action_space():
    return spaces.Discrete(NUM_ACTIONS)

def get_legal_actions(game_state: dict) -> list[int]:
    from collections import Counter
    from .cards import CARD_TYPES

    hand = Counter(game_state["hand"])
    legal = []

    kitten_just_drawn = game_state.get("kitten_just_drawn", False)

    if kitten_just_drawn:
        if hand[CARD_TYPES["DEFUSE"]] > 0:
            legal.append(3)  # play_defuse
        # ✅ FIX 6: If no defuse available and kitten drawn, agent is dead —
        # return [0] as a dummy so random.choice() never crashes.
        # env.step will see terminated=True and end the game cleanly.
        if not legal:
            legal.append(0)
        return legal

    # Always can draw to end turn
    legal.append(0)

    if hand[CARD_TYPES["SKIP"]] > 0:           legal.append(1)
    if hand[CARD_TYPES["ATTACK"]] > 0:         legal.append(2)
    if hand[CARD_TYPES["SHUFFLE"]] > 0:        legal.append(5)
    if hand[CARD_TYPES["SEE_THE_FUTURE"]] > 0: legal.append(6)
    if hand[CARD_TYPES["FAVOR"]] > 0 and len(game_state["opponents"]) > 0:
        legal.append(7)

    cat_ids = [8, 9, 10, 11, 12]
    pairs   = [c for c in cat_ids if hand[c] >= 2]
    triples = [c for c in cat_ids if hand[c] >= 3]
    if pairs:   legal.append(8)
    if triples: legal.append(9)

    diff_cats = [c for c in cat_ids if hand[c] >= 1]
    if len(diff_cats) >= 5: legal.append(10)

    return legal