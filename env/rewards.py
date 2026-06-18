# rewards.py
# writes calculate_reward()
# It receives game_state (after mutation) and the event string
# Returns a float reward signal

from .rules import _find_next_alive_player


def _nope_defended_self(game_state: dict, acting_player: int) -> bool:
    """True when acting_player's Nope cancels an attack aimed at them.

    At the played_nope event the original action is still pending (cleared
    only when the chain finishes), so pending_action describes what was noped.
    """
    pending = game_state.get("pending_action")
    if not pending or pending.get("action") != 2:
        return False
    return _find_next_alive_player(game_state, pending["player_idx"]) == acting_player


def calculate_reward(game_state: dict, event: str, acting_player: int) -> float:
    """
    Reward shaping for the DQN agent.
    The goal: survive, win, punish death.
    """

    # === TERMINAL EVENTS ===
    if event in ("exploded_no_defuse", "deck_empty_draw_death"):
        return -1.0   # you died

    if game_state["terminated"] and game_state.get("winner") == acting_player:
        return +1.0   # you won! last player standing

    # === SURVIVAL REWARDS ===
    if event == "defused_kitten":
        return +0.2    # great! you survived a kitten draw

    if event == "drew_exploding_kitten":
        return -0.05     # kitten drawn, defuse pending — still dangerous

    if event == "drew_safe_card":
        return +0.01     # survived a draw turn

    # === STRATEGIC ACTIONS ===
    if event == "played_skip":
        return +0.005     # avoided drawing — slightly good

    if event == "played_attack":
        return +0.02     # forced opponent to take risk

    if event == "played_see_future":
        return +0.015     # information is valuable

    if event == "played_shuffle":
        return +0.01     # shuffled away danger

    if event in ("played_favor_stole_card", "played_cat_pair",
                  "played_cat_triple", "played_five_diff"):
        return +0.03     # stole a card — especially good if it's a defuse

    # === REACTION: defensive Nope ===
    if event == "played_nope" and _nope_defended_self(game_state, acting_player):
        return +0.03     # noped an attack aimed at you — saved your own turn

    # === ILLEGAL / WASTED ACTIONS ===
    if event in ("defuse_played_illegally", "favor_no_target",
                  "cat_pair_failed", "cat_triple_failed", "five_diff_empty_discard"):
        return -0.02

    # === DEFAULT: still alive ===
    return +0.001
