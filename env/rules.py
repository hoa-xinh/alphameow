# rules.py
import random
from .cards import CARD_TYPES
from .action_space import NOPEABLE_ACTIONS, PASS_NOPE_ACTION


ACTION_EVENT_NAMES = {
    1: "skip",
    2: "attack",
    5: "shuffle",
    6: "see_future",
    7: "favor",
    8: "cat_pair",
    9: "cat_triple",
    10: "five_diff",
}


CARD_FOR_ACTION = {
    1: CARD_TYPES["SKIP"],
    2: CARD_TYPES["ATTACK"],
    5: CARD_TYPES["SHUFFLE"],
    6: CARD_TYPES["SEE_THE_FUTURE"],
    7: CARD_TYPES["FAVOR"],
}


CAT_IDS = [
    CARD_TYPES["CAT_TACO"],
    CARD_TYPES["CAT_WATERMELON"],
    CARD_TYPES["CAT_POTATO"],
    CARD_TYPES["CAT_BEARD"],
    CARD_TYPES["CAT_RAINBOW"],
]


def apply_action(game_state: dict, action: int, player_idx: int | None = None) -> str:
    if player_idx is None:
        player_idx = game_state["current_player"]

    if game_state.get("terminated", False):
        return "game_already_terminated"

    # If we are in Nope reaction phase, only Nope/pass actions are handled.
    if game_state.get("phase") == "reaction":
        event = _handle_reaction_action(game_state, action, player_idx)
        _update_winner(game_state)
        return event

    # During the main phase, only the current player can act.
    if player_idx != game_state["current_player"]:
        return "no_op"

    game_state["turn_count"] += 1

    if action == 0:
        event = _draw_card(game_state, player_idx)
    elif action == 3:
        event = _play_defuse(game_state, player_idx)
    elif action in NOPEABLE_ACTIONS:
        event = _start_nopeable_action(game_state, action, player_idx)
    elif action == 4:
        event = "nope_illegal_without_pending_action"
    elif action == PASS_NOPE_ACTION:
        event = "pass_illegal_without_pending_action"
    else:
        event = "no_op"

    _update_winner(game_state)
    return event


# ============================================================
# Nope reaction system
# ============================================================

def _start_nopeable_action(game_state, action, player_idx):
    spend_event = _spend_nopeable_action_cards(game_state, action, player_idx)

    if (
        spend_event.endswith("failed")
        or spend_event.endswith("no_target")
        or spend_event.endswith("empty_discard")
    ):
        return spend_event

    game_state["pending_action"] = {
        "action": action,
        "source_player": player_idx,
        "nope_count": 0,
        "last_actor": player_idx,
        "passes": 0,
    }

    # If nobody else has Nope, resolve immediately.
    if not _any_player_can_nope(game_state, excluded_player=player_idx):
        return _finish_nope_chain(game_state)

    game_state["phase"] = "reaction"

    next_responder = _find_next_reaction_player(
        game_state,
        start_idx=player_idx,
        excluded_player=player_idx,
    )

    if next_responder is None:
        return _finish_nope_chain(game_state)

    game_state["current_player"] = next_responder
    return f"pending_{ACTION_EVENT_NAMES[action]}_awaiting_nope"


def _handle_reaction_action(game_state, action, player_idx):
    if player_idx != game_state["current_player"]:
        return "reaction_wrong_player"

    if not game_state["alive_players"][player_idx]:
        return "reaction_dead_player"

    pending = game_state.get("pending_action")

    if pending is None:
        game_state["phase"] = "main"
        return "reaction_without_pending_action"

    game_state["turn_count"] += 1

    # Pass during Nope reaction.
    if action == PASS_NOPE_ACTION:
        pending["passes"] += 1

        # Everyone except the last actor has passed.
        if pending["passes"] >= max(0, _alive_count(game_state) - 1):
            return _finish_nope_chain(game_state)

        nxt = _find_next_reaction_player(
            game_state,
            start_idx=player_idx,
            excluded_player=pending["last_actor"],
        )

        if nxt is None:
            return _finish_nope_chain(game_state)

        game_state["current_player"] = nxt
        return "passed_nope"

    # Play Nope.
    if action == 4:
        if CARD_TYPES["NOPE"] not in game_state["players"][player_idx]:
            return "nope_failed_no_card"

        game_state["players"][player_idx].remove(CARD_TYPES["NOPE"])
        game_state["discard"].append(CARD_TYPES["NOPE"])

        pending["nope_count"] += 1
        pending["last_actor"] = player_idx
        pending["passes"] = 0

        # If nobody else can Nope this Nope, finish immediately.
        if not _any_player_can_nope(game_state, excluded_player=player_idx):
            return _finish_nope_chain(game_state)

        nxt = _find_next_reaction_player(
            game_state,
            start_idx=player_idx,
            excluded_player=player_idx,
        )

        if nxt is None:
            return _finish_nope_chain(game_state)

        game_state["current_player"] = nxt
        return "played_nope"

    return "reaction_illegal_action"


def _finish_nope_chain(game_state):
    pending = game_state.pop("pending_action", None)
    game_state["phase"] = "main"

    if pending is None:
        return "reaction_without_pending_action"

    source_player = pending["source_player"]
    action = pending["action"]
    action_name = ACTION_EVENT_NAMES[action]

    game_state["current_player"] = source_player

    # Odd number of Nopes cancels the action.
    # Even number of Nopes allows the action.
    if pending["nope_count"] % 2 == 1:
        return f"noped_{action_name}"

    return _resolve_already_spent_action(game_state, action, source_player)


# ============================================================
# Draw / Defuse
# ============================================================

def _draw_card(game_state, player_idx):
    if not game_state["deck"]:
        game_state["terminated"] = True
        game_state["winner"] = _only_alive_player(game_state)
        return "deck_empty_draw_death"

    card = game_state["deck"].pop()

    game_state["current_turn_draws_remaining"] = max(
        0,
        game_state["current_turn_draws_remaining"] - 1,
    )

    if card == CARD_TYPES["EXPLODING_KITTEN"]:
        game_state["kitten_just_drawn"] = True

        if CARD_TYPES["DEFUSE"] not in game_state["players"][player_idx]:
            _eliminate_player(game_state, player_idx)
            return "exploded_no_defuse"

        return "drew_exploding_kitten"

    game_state["players"][player_idx].append(card)

    if game_state["current_turn_draws_remaining"] <= 0:
        _advance_turn(game_state)

    return "drew_safe_card"


def _play_defuse(game_state, player_idx):
    if not game_state["kitten_just_drawn"]:
        return "defuse_played_illegally"

    if CARD_TYPES["DEFUSE"] not in game_state["players"][player_idx]:
        _eliminate_player(game_state, player_idx)
        return "exploded_no_defuse"

    game_state["players"][player_idx].remove(CARD_TYPES["DEFUSE"])
    game_state["discard"].append(CARD_TYPES["DEFUSE"])

    insert_pos = random.randint(0, len(game_state["deck"]))
    game_state["deck"].insert(insert_pos, CARD_TYPES["EXPLODING_KITTEN"])

    game_state["kitten_just_drawn"] = False

    if game_state["current_turn_draws_remaining"] <= 0:
        _advance_turn(game_state)

    return "defused_kitten"


# ============================================================
# Spending cards before Nope resolution
# ============================================================

def _spend_nopeable_action_cards(game_state, action, player_idx):
    if action in CARD_FOR_ACTION:
        card = CARD_FOR_ACTION[action]

        if card not in game_state["players"][player_idx]:
            return f"{ACTION_EVENT_NAMES[action]}_failed"

        game_state["players"][player_idx].remove(card)
        game_state["discard"].append(card)
        return f"spent_{ACTION_EVENT_NAMES[action]}"

    if action == 8:
        return _spend_cat_pair(game_state, player_idx)

    if action == 9:
        return _spend_cat_triple(game_state, player_idx)

    if action == 10:
        return _spend_five_diff(game_state, player_idx)

    return "unknown_action_failed"


def _spend_cat_pair(game_state, player_idx):
    from collections import Counter

    hand_counts = Counter(game_state["players"][player_idx])

    for cat in CAT_IDS:
        if hand_counts[cat] >= 2:
            game_state["players"][player_idx].remove(cat)
            game_state["players"][player_idx].remove(cat)
            game_state["discard"].extend([cat, cat])
            return "spent_cat_pair"

    return "cat_pair_failed"


def _spend_cat_triple(game_state, player_idx):
    from collections import Counter

    hand_counts = Counter(game_state["players"][player_idx])

    for cat in CAT_IDS:
        if hand_counts[cat] >= 3:
            for _ in range(3):
                game_state["players"][player_idx].remove(cat)

            game_state["discard"].extend([cat] * 3)
            return "spent_cat_triple"

    return "cat_triple_failed"


def _spend_five_diff(game_state, player_idx):
    hand = game_state["players"][player_idx]
    unique_cards = []

    for card in list(hand):
        if card not in unique_cards:
            unique_cards.append(card)

        if len(unique_cards) == 5:
            break

    if len(unique_cards) < 5:
        return "five_diff_failed"

    if not game_state.get("discard"):
        return "five_diff_empty_discard"

    for card in unique_cards:
        hand.remove(card)
        game_state["discard"].append(card)

    return "spent_five_diff"


# ============================================================
# Resolving action effects after Nope chain
# ============================================================

def _resolve_already_spent_action(game_state, action, player_idx):
    if action == 1:
        return _resolve_skip(game_state, player_idx)

    if action == 2:
        return _resolve_attack(game_state, player_idx)

    if action == 5:
        return _resolve_shuffle(game_state, player_idx)

    if action == 6:
        return _resolve_see_future(game_state, player_idx)

    if action == 7:
        return _resolve_favor(game_state, player_idx)

    if action == 8:
        return _resolve_cat_pair(game_state, player_idx)

    if action == 9:
        return _resolve_cat_triple(game_state, player_idx)

    if action == 10:
        return _resolve_five_diff(game_state, player_idx)

    return "no_op"


def _resolve_skip(game_state, player_idx):
    game_state["current_turn_draws_remaining"] = max(
        0,
        game_state["current_turn_draws_remaining"] - 1,
    )

    if game_state["current_turn_draws_remaining"] <= 0:
        _advance_turn(game_state)

    return "played_skip"


def _resolve_attack(game_state, player_idx):
    next_player = _find_next_alive_player(game_state, player_idx)

    if next_player is not None:
        # Normal Attack gives next player 2 total turns/draws.
        # If the attacker was already under Attack, pass remaining turns forward + 2.
        if game_state.get("current_turn_draws_remaining", 1) > 1:
            turns_to_give = game_state["current_turn_draws_remaining"] + 2
        else:
            turns_to_give = 2

        game_state["pending_extra_draws"][next_player] += max(0, turns_to_give - 1)

    game_state["current_turn_draws_remaining"] = 0
    _advance_turn(game_state)

    return "played_attack"


def _resolve_shuffle(game_state, player_idx):
    random.shuffle(game_state["deck"])
    game_state["top_three"] = None
    return "played_shuffle"


def _resolve_see_future(game_state, player_idx):
    top3 = (
        game_state["deck"][-3:]
        if len(game_state["deck"]) >= 3
        else game_state["deck"][:]
    )

    # Because the top of the deck is drawn using pop(),
    # the top card is the last element.
    game_state["top_three"] = list(reversed(top3))

    return "played_see_future"


def _resolve_favor(game_state, player_idx):
    target = _choose_target_with_cards(game_state, player_idx)

    if target is None:
        return "favor_no_target"

    # Simplified rule:
    # Officially target chooses which card to give.
    # Here we randomly choose one card from target.
    given = random.choice(game_state["players"][target])
    game_state["players"][target].remove(given)
    game_state["players"][player_idx].append(given)

    return "played_favor_received_card"


def _resolve_cat_pair(game_state, player_idx):
    target = _choose_target_with_cards(game_state, player_idx)

    if target is None:
        return "cat_pair_no_target"

    stolen = random.choice(game_state["players"][target])
    game_state["players"][target].remove(stolen)
    game_state["players"][player_idx].append(stolen)

    return "played_cat_pair"


def _resolve_cat_triple(game_state, player_idx):
    target = _choose_target_with_cards(game_state, player_idx)

    if target is None:
        return "cat_triple_no_target"

    possible_named_cards = [
        card
        for card in CARD_TYPES.values()
        if card != CARD_TYPES["EXPLODING_KITTEN"]
    ]

    # Simplified rule:
    # Officially player chooses the named card.
    # Here the requested card is random.
    requested = random.choice(possible_named_cards)
    game_state["last_requested_card"] = requested

    if requested in game_state["players"][target]:
        game_state["players"][target].remove(requested)
        game_state["players"][player_idx].append(requested)
        return "played_cat_triple_hit"

    return "played_cat_triple_miss"


def _resolve_five_diff(game_state, player_idx):
    if not game_state["discard"]:
        return "five_diff_empty_discard"

    # Simplified rule:
    # Officially player chooses one card from discard.
    # Here the picked card is random.
    picked = random.choice(game_state["discard"])
    game_state["discard"].remove(picked)
    game_state["players"][player_idx].append(picked)

    return "played_five_diff"


# ============================================================
# Helper functions
# ============================================================

def _choose_target_with_cards(game_state, player_idx):
    for idx, alive in enumerate(game_state["alive_players"]):
        if alive and idx != player_idx and game_state["players"][idx]:
            return idx

    return None


def _any_player_can_nope(game_state, excluded_player):
    return any(
        alive
        and idx != excluded_player
        and CARD_TYPES["NOPE"] in game_state["players"][idx]
        for idx, alive in enumerate(game_state["alive_players"])
    )


def _find_next_reaction_player(
    game_state: dict,
    start_idx: int,
    excluded_player: int,
) -> int | None:
    num_players = len(game_state["players"])

    for offset in range(1, num_players + 1):
        idx = (start_idx + offset) % num_players

        if idx == excluded_player:
            continue

        if game_state["alive_players"][idx]:
            return idx

    return None


def _alive_count(game_state):
    return sum(1 for alive in game_state["alive_players"] if alive)


def _find_next_alive_player(game_state: dict, start_idx: int) -> int | None:
    num_players = len(game_state["players"])

    for offset in range(1, num_players + 1):
        idx = (start_idx + offset) % num_players

        if game_state["alive_players"][idx]:
            return idx

    return None


def _only_alive_player(game_state: dict) -> int | None:
    alive = [
        idx
        for idx, is_alive in enumerate(game_state["alive_players"])
        if is_alive
    ]

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

    next_player = _find_next_alive_player(
        game_state,
        game_state["current_player"],
    )

    if next_player is None:
        _update_winner(game_state)
        return

    game_state["current_player"] = next_player

    game_state["current_turn_draws_remaining"] = (
        1 + game_state["pending_extra_draws"][next_player]
    )

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