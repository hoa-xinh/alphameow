# state.py
import numpy as np
from .spaces_compat import spaces

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
    "opponent_hand_size_0": 13,
    "opponent_hand_size_1": 14,
    "opponent_hand_size_2": 15,
}

STATE_SIZE = len(STATE_INDICES)
STATE_HIGH = np.array([6, 5, 5, 5, 5, 5, 5, 4, 56, 3, 3, 4, 1, 12, 12, 12], dtype=np.float32)
STATE_LOW  = np.zeros(STATE_SIZE, dtype=np.float32)

def get_observation_space():
    return spaces.Box(low=STATE_LOW, high=STATE_HIGH, dtype=np.float32)

def encode_state(game_state: dict) -> np.ndarray:
    return encode_state_for_player(game_state, game_state["current_player"])

def encode_state_for_player(game_state: dict, player_idx: int) -> np.ndarray:
    """
    Convert a game_state dict into a fixed-length numpy array for a player.
    """
    from collections import Counter
    from .cards import CARD_TYPES

    hand = Counter(game_state["players"][player_idx])
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
    alive_players = game_state["alive_players"]
    obs[10] = sum(1 for idx, alive in enumerate(alive_players) if alive and idx != player_idx)

    if game_state["current_player"] == player_idx:
        obs[11] = max(0, game_state.get("current_turn_draws_remaining", 1) - 1)
    else:
        obs[11] = game_state["pending_extra_draws"][player_idx]

    obs[12] = 1.0 if any(
        alive and idx != player_idx and len(game_state["players"][idx]) > 0
        for idx, alive in enumerate(alive_players)
    ) else 0.0

    opponent_indices = [
        idx for idx in range(len(alive_players))
        if idx != player_idx
    ]
    for slot, opp_idx in enumerate(opponent_indices[:3]):
        obs[13 + slot] = len(game_state["players"][opp_idx])

    obs = obs / STATE_HIGH
    return obs
