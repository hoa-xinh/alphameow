# state.py
import numpy as np
from gymnasium import spaces

# State vector indices — document these clearly for Team Brain
STATE_INDICES = {
    "defuse_in_hand":       0,
    "skip_in_hand":         1,
    "attack_in_hand":       2,
    "nope_in_hand":         3,
    "shuffle_in_hand":      4,
    "see_future_in_hand":   5,
    "favor_in_hand":        6,
    "cat_pairs_in_hand":    7,   # number of usable cat pairs
    "cards_in_deck":        8,
    "exploding_kittens_in_deck": 9,
    "opponents_alive":      10,
    "attacks_pending":      11,  # how many extra draws are forced on you
    "is_nope_possible":     12,  # 1 if any opponent has cards (can nope)
}

STATE_SIZE = len(STATE_INDICES)
STATE_HIGH = np.array([6, 5, 5, 5, 5, 5, 5, 4, 56, 3, 3, 4, 1], dtype=np.float32)
STATE_LOW  = np.zeros(STATE_SIZE, dtype=np.float32)

def get_observation_space():
    return spaces.Box(low=STATE_LOW, high=STATE_HIGH, dtype=np.float32)

def encode_state(game_state: dict) -> np.ndarray:
    """
    Convert a game_state dict into a fixed-length numpy array for the agent.
    game_state keys: hand (list of card ints), deck (list), 
                     opponents (list of hands), attacks_pending (int)
    """
    from collections import Counter
    from .cards import CARD_TYPES

    hand = Counter(game_state["hand"])
    obs = np.zeros(STATE_SIZE, dtype=np.float32)

    obs[0] = hand[CARD_TYPES["DEFUSE"]]
    obs[1] = hand[CARD_TYPES["SKIP"]]
    obs[2] = hand[CARD_TYPES["ATTACK"]]
    obs[3] = hand[CARD_TYPES["NOPE"]]
    obs[4] = hand[CARD_TYPES["SHUFFLE"]]
    obs[5] = hand[CARD_TYPES["SEE_THE_FUTURE"]]
    obs[6] = hand[CARD_TYPES["FAVOR"]]

    # Count usable cat pairs
    cat_ids = [8, 9, 10, 11, 12]
    cat_pairs = sum(hand[c] // 2 for c in cat_ids)
    obs[7] = cat_pairs

    deck = game_state["deck"]
    obs[8] = len(deck)
    obs[9] = deck.count(CARD_TYPES["EXPLODING_KITTEN"])
    obs[10] = len(game_state["opponents"])
    obs[11] = game_state.get("attacks_pending", 0)
    obs[12] = 1.0 if any(len(o) > 0 for o in game_state["opponents"]) else 0.0

    return obs