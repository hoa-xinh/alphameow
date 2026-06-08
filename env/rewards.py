# rewards.py
# writes calculate_reward()
# It receives game_state (after mutation) and the event string
# Returns a float reward signal

def calculate_reward(game_state: dict, event: str, acting_player: int) -> float:
    """
    Reward shaping for the DQN agent.
    The goal: survive, win, punish death.
    """

    # === TERMINAL EVENTS ===
    if event in ("exploded_no_defuse", "deck_empty_draw_death"):
        return -100.0   # you died

    if game_state["terminated"] and game_state.get("winner") == acting_player:
        return +100.0   # you won! last player standing

    # === SURVIVAL REWARDS ===
    if event == "defused_kitten":
        return +20.0    # great! you survived a kitten draw

    if event == "drew_exploding_kitten":
        return -5.0     # kitten drawn, defuse pending — still dangerous

    if event == "drew_safe_card":
        return +1.0     # survived a draw turn

    # === STRATEGIC ACTIONS ===
    if event == "played_skip":
        return +0.5     # avoided drawing — slightly good

    if event == "played_attack":
        return +2.0     # forced opponent to take risk

    if event == "played_see_future":
        return +1.5     # information is valuable

    if event == "played_shuffle":
        return +1.0     # shuffled away danger

    if event in ("played_favor_stole_card", "played_cat_pair",
                  "played_cat_triple", "played_five_diff"):
        return +3.0     # stole a card — especially good if it's a defuse

    # === ILLEGAL / WASTED ACTIONS ===
    if event in ("defuse_played_illegally", "favor_no_target",
                  "cat_pair_failed", "cat_triple_failed", "five_diff_empty_discard"):
        return -2.0

    # === DEFAULT: still alive ===
    return +0.1
