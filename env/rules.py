# rules.py
import random
from collections import Counter

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


REQUESTABLE_CARD_IDS = [
    card_id
    for name, card_id in CARD_TYPES.items()
    if name != "EXPLODING_KITTEN"
]


def apply_action(game_state: dict, action: int, player_idx: int | None = None) -> str:
    """
    Apply one action to the game state.

    Main phase:
        Only current_player can act.

    Reaction phase:
        Only reaction_player can act.
        They may pass or play Nope.

    Nope rule:
        Odd number of Nopes cancels the original action.
        Even number of Nopes allows the original action to resolve.
    """
    if game_state.get("terminated", False):
        return "game_already_terminated"

    if player_idx is None:
        if game_state.get("phase") == "reaction":
            player_idx = game_state.get("reaction_player")
        else:
            player_idx = game_state["current_player"]

    game_state["turn_count"] = game_state.get("turn_count", 0) + 1

    if game_state.get("phase") == "reaction":
        return _handle_reaction_action(game_state, action, player_idx)

    if player_idx != game_state["current_player"]:
        return "not_current_player"

    if not game_state["alive_players"][player_idx]:
        return "player_not_alive"

    # If the player just drew an Exploding Kitten,
    # they must play Defuse or be eliminated.
    if game_state.get("kitten_just_drawn", False):
        if action == 3:
            event = _play_defuse(game_state, player_idx)
        else:
            event = _eliminate_player(
                game_state,
                player_idx,
                reason="exploded_no_defuse",
            )

        _update_winner(game_state)
        return event

    if action == 0:
        event = _draw_card(game_state, player_idx)

    elif action == 3:
        event = "defuse_played_illegally"

    elif action == 4:
        event = "nope_played_illegally"

    elif action in NOPEABLE_ACTIONS:
        event = _start_nopeable_action(game_state, action, player_idx)

    else:
        event = "no_op"

    _update_winner(game_state)
    return event


def _start_nopeable_action(game_state: dict, action: int, player_idx: int) -> str:
    """
    Spend the action card first, then wait for Nope reactions.

    If nobody can Nope, resolve immediately.
    """
    spend_event = _spend_nopeable_action_cards(game_state, action, player_idx)

    if spend_event != "spent_nopeable_action":
        return spend_event

    pending_action = {
        "action": action,
        "player_idx": player_idx,
        "nope_count": 0,
        "pass_count": 0,
        "last_nope_player": player_idx,
    }

    game_state["pending_action"] = pending_action

    # If nobody else can Nope, resolve immediately.
    if not _any_player_can_nope(game_state, exclude_player=player_idx):
        return _finish_nope_chain(game_state)

    game_state["phase"] = "reaction"
    game_state["reaction_player"] = _find_next_reaction_player(
        game_state,
        start_idx=player_idx,
        exclude_player=player_idx,
    )

    return f"awaiting_nope_{ACTION_EVENT_NAMES.get(action, 'action')}"


def _handle_reaction_action(game_state: dict, action: int, player_idx: int) -> str:
    """
    Handle pass_nope or play_nope during reaction phase.
    """
    pending = game_state.get("pending_action")

    if pending is None:
        game_state["phase"] = "main"
        game_state["reaction_player"] = None
        return "reaction_without_pending_action"

    if player_idx != game_state.get("reaction_player"):
        return "not_reaction_player"

    if action == PASS_NOPE_ACTION:
        pending["pass_count"] += 1

        # If everyone except the most recent Nope player has passed,
        # the Nope chain ends.
        if pending["pass_count"] >= max(0, _alive_count(game_state) - 1):
            return _finish_nope_chain(game_state)

        next_player = _find_next_reaction_player(
            game_state,
            start_idx=player_idx,
            exclude_player=pending.get("last_nope_player"),
        )

        if next_player is None:
            return _finish_nope_chain(game_state)

        # If no remaining eligible player has a Nope, finish automatically.
        if not _any_player_can_nope(
            game_state,
            exclude_player=pending.get("last_nope_player"),
        ):
            return _finish_nope_chain(game_state)

        game_state["reaction_player"] = next_player
        return "passed_nope"

    if action == 4:
        hand = game_state["players"][player_idx]

        if CARD_TYPES["NOPE"] not in hand:
            return "nope_failed_no_card"

        hand.remove(CARD_TYPES["NOPE"])
        game_state["discard"].append(CARD_TYPES["NOPE"])

        pending["nope_count"] += 1
        pending["pass_count"] = 0
        pending["last_nope_player"] = player_idx

        if not _any_player_can_nope(game_state, exclude_player=player_idx):
            return _finish_nope_chain(game_state)

        game_state["reaction_player"] = _find_next_reaction_player(
            game_state,
            start_idx=player_idx,
            exclude_player=player_idx,
        )

        return "played_nope"

    return "illegal_reaction_action"


def _finish_nope_chain(game_state: dict) -> str:
    """
    End the Nope chain.

    Odd Nope count:
        Original action is canceled.

    Even Nope count:
        Original action resolves.
    """
    pending = game_state.get("pending_action")

    if pending is None:
        game_state["phase"] = "main"
        game_state["reaction_player"] = None
        return "no_pending_action"

    action = pending["action"]
    nope_count = pending.get("nope_count", 0)

    game_state["phase"] = "main"
    game_state["reaction_player"] = None
    game_state["pending_action"] = None

    if nope_count % 2 == 1:
        # Odd number of Nopes cancels the action.
        # The spent cards stay discarded.
        return f"{ACTION_EVENT_NAMES.get(action, 'action')}_noped"

    # Zero Nopes or even Nopes means the original action resolves.
    return _resolve_already_spent_action(game_state, pending)


def _spend_nopeable_action_cards(
    game_state: dict,
    action: int,
    player_idx: int,
) -> str:
    """
    Remove the original action card from hand and put it in discard.

    Important:
    The effect does not happen here.
    The effect only happens later in _resolve_already_spent_action().
    """
    hand = game_state["players"][player_idx]

    if action in CARD_FOR_ACTION:
        card = CARD_FOR_ACTION[action]

        if card not in hand:
            return f"{ACTION_EVENT_NAMES.get(action, 'action')}_failed_no_card"

        hand.remove(card)
        game_state["discard"].append(card)
        return "spent_nopeable_action"

    if action == 8:
        hand_counts = Counter(hand)

        for cat in CAT_IDS:
            if hand_counts[cat] >= 2:
                hand.remove(cat)
                hand.remove(cat)
                game_state["discard"].extend([cat, cat])
                return "spent_nopeable_action"

        return "cat_pair_failed"

    if action == 9:
        hand_counts = Counter(hand)

        for cat in CAT_IDS:
            if hand_counts[cat] >= 3:
                for _ in range(3):
                    hand.remove(cat)

                game_state["discard"].extend([cat] * 3)
                return "spent_nopeable_action"

        return "cat_triple_failed"

    if action == 10:
        used = []

        for card in list(hand):
            if card == CARD_TYPES["EXPLODING_KITTEN"]:
                continue

            if card not in used:
                used.append(card)

            if len(used) == 5:
                break

        if len(used) < 5:
            return "five_diff_failed"

        for card in used:
            hand.remove(card)
            game_state["discard"].append(card)

        return "spent_nopeable_action"

    return "no_op"


def _resolve_already_spent_action(game_state: dict, pending_action: dict) -> str:
    """
    Resolve an action after the Nope chain allows it.
    """
    action = pending_action["action"]
    player_idx = pending_action["player_idx"]

    if not game_state["alive_players"][player_idx]:
        return "actor_not_alive"

    if action == 1:
        return _resolve_skip(game_state, player_idx)

    if action == 2:
        return _resolve_attack(game_state, player_idx)

    if action == 5:
        return _resolve_shuffle(game_state)

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


def _draw_card(game_state: dict, player_idx: int) -> str:
    """
    Draw one card for player_idx.
    """
    game_state["top_three"] = []
    game_state["sf_player"] = None

    if not game_state["deck"]:
        event = _eliminate_player(
            game_state,
            player_idx,
            reason="deck_empty_draw_death",
        )
        _update_winner(game_state)
        return event

    card = game_state["deck"].pop()

    # Drawing consumes one required draw.
    game_state["current_turn_draws_remaining"] = max(
        0,
        game_state.get("current_turn_draws_remaining", 1) - 1,
    )

    if card == CARD_TYPES["EXPLODING_KITTEN"]:
        game_state["kitten_just_drawn"] = True

        if CARD_TYPES["DEFUSE"] not in game_state["players"][player_idx]:
            return _eliminate_player(
                game_state,
                player_idx,
                reason="exploded_no_defuse",
            )

        return "drew_exploding_kitten"

    game_state["players"][player_idx].append(card)

    if game_state["current_turn_draws_remaining"] <= 0:
        _advance_turn(game_state)

    return "drew_safe_card"


def _play_defuse(game_state: dict, player_idx: int) -> str:
    """
    Play Defuse after drawing an Exploding Kitten.
    """
    if not game_state.get("kitten_just_drawn", False):
        return "defuse_played_illegally"

    hand = game_state["players"][player_idx]

    if CARD_TYPES["DEFUSE"] not in hand:
        return _eliminate_player(
            game_state,
            player_idx,
            reason="exploded_no_defuse",
        )

    hand.remove(CARD_TYPES["DEFUSE"])
    game_state["discard"].append(CARD_TYPES["DEFUSE"])

    insert_pos = random.randint(0, len(game_state["deck"]))
    game_state["deck"].insert(insert_pos, CARD_TYPES["EXPLODING_KITTEN"])

    game_state["kitten_just_drawn"] = False

    if game_state.get("current_turn_draws_remaining", 0) <= 0:
        _advance_turn(game_state)

    return "defused_kitten"


def _resolve_skip(game_state: dict, player_idx: int) -> str:
    """
    Skip removes one required draw from the current player.
    """
    game_state["current_turn_draws_remaining"] = max(
        0,
        game_state.get("current_turn_draws_remaining", 1) - 1,
    )

    if game_state["current_turn_draws_remaining"] <= 0:
        _advance_turn(game_state)

    return "played_skip"


def _resolve_attack(game_state: dict, player_idx: int) -> str:
    """
    Attack ends the current player's turn and makes the next player take
    2 total draws/turns.

    Because _advance_turn() already gives the next player 1 normal draw,
    we only add 1 extra draw.
    """
    next_player = _find_next_alive_player(game_state, player_idx)

    if next_player is None:
        _update_winner(game_state)
        return "played_attack_no_target"

    game_state["pending_extra_draws"][next_player] += 1
    game_state["current_turn_draws_remaining"] = 0

    _advance_turn(game_state)

    return "played_attack"


def _resolve_shuffle(game_state: dict) -> str:
    random.shuffle(game_state["deck"])
    game_state["top_three"] = []
    game_state["sf_player"] = None

    return "played_shuffle"


def _resolve_see_future(game_state: dict, player_idx: int) -> str:
    top3 = (
        game_state["deck"][-3:]
        if len(game_state["deck"]) >= 3
        else game_state["deck"][:]
    )

    game_state["top_three"] = list(reversed(top3))
    game_state["sf_player"] = player_idx

    return "played_see_future"


def _resolve_favor(game_state: dict, player_idx: int) -> str:
    """
    Simplified Favor:
    Random target with cards gives one random card to player.
    """
    target = _choose_target_with_cards(game_state, player_idx)

    if target is None:
        return "favor_no_target"

    stolen = random.choice(game_state["players"][target])
    game_state["players"][target].remove(stolen)
    game_state["players"][player_idx].append(stolen)

    return "played_favor_stole_card"


def _resolve_cat_pair(game_state: dict, player_idx: int) -> str:
    """
    Simplified cat pair:
    Steal one random card from a random target with cards.
    """
    target = _choose_target_with_cards(game_state, player_idx)

    if target is None:
        return "cat_pair_no_target"

    stolen = random.choice(game_state["players"][target])
    game_state["players"][target].remove(stolen)
    game_state["players"][player_idx].append(stolen)

    return "played_cat_pair"


def _resolve_cat_triple(game_state: dict, player_idx: int) -> str:
    """
    Simplified cat triple:
    Randomly request a card type.
    If target has it, steal it.
    Otherwise miss.
    """
    target = _choose_target_with_cards(game_state, player_idx)

    if target is None:
        return "cat_triple_no_target"

    requested_card = random.choice(REQUESTABLE_CARD_IDS)
    game_state["last_requested_card"] = requested_card

    if requested_card in game_state["players"][target]:
        game_state["players"][target].remove(requested_card)
        game_state["players"][player_idx].append(requested_card)
        return "played_cat_triple"

    return "played_cat_triple_missed"


def _resolve_five_diff(game_state: dict, player_idx: int) -> str:
    """
    Simplified five different cards:
    Pick one random card from discard pile.
    """
    if not game_state["discard"]:
        return "five_diff_empty_discard"

    picked = random.choice(game_state["discard"])
    game_state["discard"].remove(picked)
    game_state["players"][player_idx].append(picked)

    return "played_five_diff"


def _choose_target_with_cards(game_state: dict, player_idx: int) -> int | None:
    candidates = [
        idx
        for idx, alive in enumerate(game_state["alive_players"])
        if alive
        and idx != player_idx
        and len(game_state["players"][idx]) > 0
    ]

    if not candidates:
        return None

    return random.choice(candidates)


def _any_player_can_nope(
    game_state: dict,
    exclude_player: int | None = None,
) -> bool:
    return any(
        alive
        and idx != exclude_player
        and CARD_TYPES["NOPE"] in game_state["players"][idx]
        for idx, alive in enumerate(game_state["alive_players"])
    )


def _find_next_reaction_player(
    game_state: dict,
    start_idx: int,
    exclude_player: int | None = None,
) -> int | None:
    player_count = len(game_state["players"])

    for step in range(1, player_count + 1):
        idx = (start_idx + step) % player_count

        if game_state["alive_players"][idx] and idx != exclude_player:
            return idx

    return None


def _alive_count(game_state: dict) -> int:
    return sum(1 for alive in game_state["alive_players"] if alive)


def _find_next_alive_player(game_state: dict, start_idx: int) -> int | None:
    player_count = len(game_state["players"])

    for step in range(1, player_count + 1):
        idx = (start_idx + step) % player_count

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


def _update_winner(game_state: dict) -> None:
    winner = _only_alive_player(game_state)

    if winner is not None:
        game_state["terminated"] = True
        game_state["winner"] = winner


def _advance_turn(game_state: dict) -> None:
    """
    Move to the next alive player and give them their required draws.

    Normal turn:
        current_turn_draws_remaining = 1

    If Attack added pending extra draws:
        current_turn_draws_remaining = 1 + pending_extra_draws[next_player]
    """
    if game_state.get("terminated", False):
        return

    game_state["top_three"] = []
    game_state["sf_player"] = None

    next_player = _find_next_alive_player(
        game_state,
        game_state["current_player"],
    )

    if next_player is None:
        _update_winner(game_state)
        return

    game_state["current_player"] = next_player

    extra_draws = game_state["pending_extra_draws"][next_player]
    game_state["pending_extra_draws"][next_player] = 0

    game_state["current_turn_draws_remaining"] = 1 + extra_draws
    game_state["kitten_just_drawn"] = False


def _eliminate_player(
    game_state: dict,
    player_idx: int,
    reason: str = "player_eliminated",
) -> str:
    game_state["alive_players"][player_idx] = False
    game_state["kitten_just_drawn"] = False
    game_state["pending_extra_draws"][player_idx] = 0
    game_state["current_turn_draws_remaining"] = 0

    _update_winner(game_state)

    if (
        not game_state.get("terminated", False)
        and player_idx == game_state.get("current_player")
    ):
        _advance_turn(game_state)

    return reason
