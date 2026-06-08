# rules.py
import random
from .cards import CARD_TYPES

def apply_action(game_state: dict, action: int, player_idx: int | None = None) -> str:
    if player_idx is None:
        player_idx = game_state["current_player"]

    if player_idx != game_state["current_player"]:
        return "no_op"

    game_state["turn_count"] += 1

    if action == 0:
        event = _draw_card(game_state, player_idx)
    elif action == 1:
        event = _play_skip(game_state, player_idx)
    elif action == 2:
        event = _play_attack(game_state, player_idx)
    elif action == 3:
        event = _play_defuse(game_state, player_idx)
    elif action == 4:
        event = "no_op"  # Nope is reactive — skipped in Phase 1
    elif action == 5:
        event = _play_shuffle(game_state, player_idx)
    elif action == 6:
        event = _play_see_future(game_state, player_idx)
    elif action == 7:
        event = _play_favor(game_state, player_idx)
    elif action == 8:
        event = _play_cat_pair(game_state, player_idx)
    elif action == 9:
        event = _play_cat_triple(game_state, player_idx)
    elif action == 10:
        event = _play_five_diff(game_state, player_idx)
    else:
        event = "no_op"

    _update_winner(game_state)

    return event


def _draw_card(game_state, player_idx):
    if not game_state["deck"]:
        game_state["terminated"] = True
        game_state["winner"] = _only_alive_player(game_state)
        return "deck_empty_draw_death"

    card = game_state["deck"].pop()
    game_state["current_turn_draws_remaining"] = max(
        0, game_state["current_turn_draws_remaining"] - 1
    )

    if card == CARD_TYPES["EXPLODING_KITTEN"]:
        game_state["kitten_just_drawn"] = True
        if CARD_TYPES["DEFUSE"] not in game_state["players"][player_idx]:
            _eliminate_player(game_state, player_idx)
            return "exploded_no_defuse"
        return "drew_exploding_kitten"  # agent must now play defuse
    else:
        game_state["players"][player_idx].append(card)
        if game_state["current_turn_draws_remaining"] <= 0:
            _advance_turn(game_state)
        return "drew_safe_card"


def _play_skip(game_state, player_idx):
    game_state["players"][player_idx].remove(CARD_TYPES["SKIP"])
    game_state["discard"].append(CARD_TYPES["SKIP"])
    game_state["current_turn_draws_remaining"] = max(
        0, game_state["current_turn_draws_remaining"] - 1
    )
    if game_state["current_turn_draws_remaining"] <= 0:
        _advance_turn(game_state)
    return "played_skip"


def _play_attack(game_state, player_idx):
    game_state["players"][player_idx].remove(CARD_TYPES["ATTACK"])
    game_state["discard"].append(CARD_TYPES["ATTACK"])
    next_player = _find_next_alive_player(game_state, player_idx)
    if next_player is not None:
        game_state["pending_extra_draws"][next_player] += 2
    game_state["current_turn_draws_remaining"] = 0
    _advance_turn(game_state)
    return "played_attack"


def _play_defuse(game_state, player_idx):
    if not game_state["kitten_just_drawn"]:
        return "defuse_played_illegally"
    game_state["players"][player_idx].remove(CARD_TYPES["DEFUSE"])
    game_state["discard"].append(CARD_TYPES["DEFUSE"])
    # Put kitten back at a random position in deck
    insert_pos = random.randint(0, len(game_state["deck"]))
    game_state["deck"].insert(insert_pos, CARD_TYPES["EXPLODING_KITTEN"])
    game_state["kitten_just_drawn"] = False
    if game_state["current_turn_draws_remaining"] <= 0:
        _advance_turn(game_state)
    return "defused_kitten"


def _play_shuffle(game_state, player_idx):
    game_state["players"][player_idx].remove(CARD_TYPES["SHUFFLE"])
    game_state["discard"].append(CARD_TYPES["SHUFFLE"])
    random.shuffle(game_state["deck"])
    game_state["top_three"] = None  # invalidate any See the Future peek
    return "played_shuffle"


def _play_see_future(game_state, player_idx):
    game_state["players"][player_idx].remove(CARD_TYPES["SEE_THE_FUTURE"])
    game_state["discard"].append(CARD_TYPES["SEE_THE_FUTURE"])
    top3 = game_state["deck"][-3:] if len(game_state["deck"]) >= 3 else game_state["deck"][:]
    game_state["top_three"] = list(reversed(top3))  # index 0 = next draw
    # See the Future does NOT end your turn — no opponent move here
    return "played_see_future"


def _play_favor(game_state, player_idx):
    game_state["players"][player_idx].remove(CARD_TYPES["FAVOR"])
    game_state["discard"].append(CARD_TYPES["FAVOR"])
    if not any(
        alive and idx != player_idx and game_state["players"][idx]
        for idx, alive in enumerate(game_state["alive_players"])
    ):
        return "favor_no_target"
    for idx, alive in enumerate(game_state["alive_players"]):
        if alive and idx != player_idx and game_state["players"][idx]:
            stolen = random.choice(game_state["players"][idx])
            game_state["players"][idx].remove(stolen)
            game_state["players"][player_idx].append(stolen)
            # Favor does NOT end your turn
            return "played_favor_stole_card"
    return "favor_no_cards_to_steal"


def _play_cat_pair(game_state, player_idx):
    cat_ids = [8, 9, 10, 11, 12]
    from collections import Counter
    hand_counts = Counter(game_state["players"][player_idx])
    for cat in cat_ids:
        if hand_counts[cat] >= 2:
            game_state["players"][player_idx].remove(cat)
            game_state["players"][player_idx].remove(cat)
            game_state["discard"].extend([cat, cat])
            for idx, alive in enumerate(game_state["alive_players"]):
                if alive and idx != player_idx and game_state["players"][idx]:
                    stolen = random.choice(game_state["players"][idx])
                    game_state["players"][idx].remove(stolen)
                    game_state["players"][player_idx].append(stolen)
                    return "played_cat_pair"
    return "cat_pair_failed"


def _play_cat_triple(game_state, player_idx):
    cat_ids = [8, 9, 10, 11, 12]
    from collections import Counter
    hand_counts = Counter(game_state["players"][player_idx])
    for cat in cat_ids:
        if hand_counts[cat] >= 3:
            for _ in range(3):
                game_state["players"][player_idx].remove(cat)
            game_state["discard"].extend([cat] * 3)
            for idx, alive in enumerate(game_state["alive_players"]):
                if alive and idx != player_idx and game_state["players"][idx]:
                    if CARD_TYPES["DEFUSE"] in game_state["players"][idx]:
                        game_state["players"][idx].remove(CARD_TYPES["DEFUSE"])
                        game_state["players"][player_idx].append(CARD_TYPES["DEFUSE"])
                    else:
                        stolen = random.choice(game_state["players"][idx])
                        game_state["players"][idx].remove(stolen)
                        game_state["players"][player_idx].append(stolen)
                    return "played_cat_triple"
    return "cat_triple_failed"


def _play_five_diff(game_state, player_idx):
    cat_ids = [8, 9, 10, 11, 12]
    used = []
    for cat in cat_ids:
        if cat in game_state["players"][player_idx] and len(used) < 5:
            game_state["players"][player_idx].remove(cat)
            game_state["discard"].append(cat)
            used.append(cat)
    if game_state["discard"]:
        if CARD_TYPES["DEFUSE"] in game_state["discard"]:
            picked = CARD_TYPES["DEFUSE"]
        else:
            picked = random.choice(game_state["discard"])
        game_state["discard"].remove(picked)
        game_state["players"][player_idx].append(picked)
        return "played_five_diff"
    return "five_diff_empty_discard"


def _find_next_alive_player(game_state: dict, start_idx: int) -> int | None:
    num_players = len(game_state["players"])
    for offset in range(1, num_players + 1):
        idx = (start_idx + offset) % num_players
        if game_state["alive_players"][idx]:
            return idx
    return None


def _only_alive_player(game_state: dict) -> int | None:
    alive = [idx for idx, is_alive in enumerate(game_state["alive_players"]) if is_alive]
    if len(alive) == 1:
        return alive[0]
    return None


def _update_winner(game_state: dict):
    winner = _only_alive_player(game_state)
    if winner is not None:
        game_state["terminated"] = True
        game_state["winner"] = winner


def _advance_turn(game_state: dict):
    if game_state["terminated"]:
        return

    next_player = _find_next_alive_player(game_state, game_state["current_player"])
    if next_player is None:
        _update_winner(game_state)
        return

    game_state["current_player"] = next_player
    game_state["current_turn_draws_remaining"] = 1 + game_state["pending_extra_draws"][next_player]
    game_state["pending_extra_draws"][next_player] = 0
    game_state["kitten_just_drawn"] = False
    game_state["top_three"] = None


def _eliminate_player(game_state: dict, player_idx: int):
    game_state["alive_players"][player_idx] = False
    game_state["players"][player_idx] = []
    game_state["kitten_just_drawn"] = False
    _update_winner(game_state)
    if not game_state["terminated"]:
        _advance_turn(game_state)
