# action_space.py
from collections import Counter

from .spaces_compat import spaces
from .cards import CARD_TYPES


ACTIONS = {
    0: "draw_card",
    1: "play_skip",
    2: "play_attack",
    3: "play_defuse",
    4: "play_nope",
    5: "play_shuffle",
    6: "play_see_the_future",
    7: "play_favor",
    8: "play_cat_pair",
    9: "play_cat_triple",
    10: "play_five_diff",
    11: "pass_nope",
}

NOPEABLE_ACTIONS = {1, 2, 5, 6, 7, 8, 9, 10}
PASS_NOPE_ACTION = 11

NUM_ACTIONS = len(ACTIONS)


def get_action_space():
    return spaces.Discrete(NUM_ACTIONS)


def _default_actor(game_state: dict) -> int:
    """
    Return the player who should act in the current phase.
    """
    if game_state.get("phase") == "reaction":
        return game_state.get(
            "reaction_player",
            game_state.get("current_player", 0),
        )

    return game_state.get("current_player", 0)


def get_legal_actions(game_state: dict, player_idx: int | None = None) -> list[int]:
    """
    Return legal actions for one player.

    Main phase:
        Only current_player can act.

    Reaction phase:
        Only reaction_player can pass or play Nope.
    """
    if game_state.get("terminated", False):
        return []

    if player_idx is None:
        player_idx = _default_actor(game_state)

    alive_players = game_state.get("alive_players", [])

    if player_idx is None:
        return []

    if player_idx < 0 or player_idx >= len(alive_players):
        return []

    if not alive_players[player_idx]:
        return []

    hand = Counter(game_state["players"][player_idx])

    # Reaction phase: only reaction_player can pass or play Nope.
    if game_state.get("phase") == "reaction":
        if player_idx != game_state.get("reaction_player"):
            return []

        legal = [PASS_NOPE_ACTION]

        if hand[CARD_TYPES["NOPE"]] > 0:
            legal.append(4)

        return legal

    # Main phase: only current_player can act.
    if player_idx != game_state.get("current_player"):
        return []

    # If player just drew an Exploding Kitten, they must Defuse if possible.
    if game_state.get("kitten_just_drawn", False):
        if hand[CARD_TYPES["DEFUSE"]] > 0:
            return [3]

        # Dummy legal action. rules.py will eliminate the player.
        return [0]

    legal = [0]  # draw_card

    if hand[CARD_TYPES["SKIP"]] > 0:
        legal.append(1)

    if hand[CARD_TYPES["ATTACK"]] > 0:
        legal.append(2)

    if hand[CARD_TYPES["SHUFFLE"]] > 0:
        legal.append(5)

    if hand[CARD_TYPES["SEE_THE_FUTURE"]] > 0:
        legal.append(6)

    has_target_with_cards = any(
        alive
        and idx != player_idx
        and len(game_state["players"][idx]) > 0
        for idx, alive in enumerate(alive_players)
    )

    if hand[CARD_TYPES["FAVOR"]] > 0 and has_target_with_cards:
        legal.append(7)

    cat_ids = [
        CARD_TYPES["CAT_TACO"],
        CARD_TYPES["CAT_WATERMELON"],
        CARD_TYPES["CAT_POTATO"],
        CARD_TYPES["CAT_BEARD"],
        CARD_TYPES["CAT_RAINBOW"],
    ]

    if any(hand[cat] >= 2 for cat in cat_ids) and has_target_with_cards:
        legal.append(8)

    if any(hand[cat] >= 3 for cat in cat_ids) and has_target_with_cards:
        legal.append(9)

    # Five different cards = five different card titles, not only cat cards.
    distinct_cards = [
        card
        for card, count in hand.items()
        if count > 0 and card != CARD_TYPES["EXPLODING_KITTEN"]
    ]

    if len(distinct_cards) >= 5 and len(game_state.get("discard", [])) > 0:
        legal.append(10)

    return legal
