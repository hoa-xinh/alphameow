# rules.py
import random
from .cards import CARD_TYPES

def apply_action(game_state: dict, action: int) -> str:
    game_state["turn_count"] += 1

    if action == 0:
        event = _draw_card(game_state)
    elif action == 1:
        event = _play_skip(game_state)
    elif action == 2:
        event = _play_attack(game_state)
    elif action == 3:
        event = _play_defuse(game_state)
    elif action == 4:
        event = "no_op"  # Nope is reactive — skipped in Phase 1
    elif action == 5:
        event = _play_shuffle(game_state)
    elif action == 6:
        event = _play_see_future(game_state)
    elif action == 7:
        event = _play_favor(game_state)
    elif action == 8:
        event = _play_cat_pair(game_state)
    elif action == 9:
        event = _play_cat_triple(game_state)
    elif action == 10:
        event = _play_five_diff(game_state)
    else:
        event = "no_op"

    # ✅ FIX 4: Check win condition after every action
    if len(game_state["opponents"]) == 0 and not game_state["terminated"]:
        game_state["terminated"] = True

    return event


def _draw_card(game_state):
    if not game_state["deck"]:
        game_state["terminated"] = True
        return "deck_empty_draw_death"

    card = game_state["deck"].pop()

    if card == CARD_TYPES["EXPLODING_KITTEN"]:
        game_state["kitten_just_drawn"] = True
        if CARD_TYPES["DEFUSE"] not in game_state["hand"]:
            game_state["terminated"] = True
            return "exploded_no_defuse"
        return "drew_exploding_kitten"  # agent must now play defuse
    else:
        game_state["hand"].append(card)
        # ✅ FIX 1: Drawn cards go to hand ONLY — not discard
        # ✅ FIX 2: Decrement attacks first, THEN let opponents move
        if game_state["attacks_pending"] > 0:
            game_state["attacks_pending"] -= 1
        else:
            _opponents_take_turns(game_state)
        return "drew_safe_card"


def _play_skip(game_state):
    game_state["hand"].remove(CARD_TYPES["SKIP"])
    game_state["discard"].append(CARD_TYPES["SKIP"])
    if game_state["attacks_pending"] > 0:
        game_state["attacks_pending"] -= 1
    else:
        _opponents_take_turns(game_state)
    return "played_skip"


def _play_attack(game_state):
    game_state["hand"].remove(CARD_TYPES["ATTACK"])
    game_state["discard"].append(CARD_TYPES["ATTACK"])
    # Force next opponent to take 2 extra draws
    game_state["attacks_pending"] += 2
    _opponents_take_turns(game_state)
    return "played_attack"


def _play_defuse(game_state):
    if not game_state["kitten_just_drawn"]:
        return "defuse_played_illegally"
    game_state["hand"].remove(CARD_TYPES["DEFUSE"])
    game_state["discard"].append(CARD_TYPES["DEFUSE"])
    # Put kitten back at a random position in deck
    insert_pos = random.randint(0, len(game_state["deck"]))
    game_state["deck"].insert(insert_pos, CARD_TYPES["EXPLODING_KITTEN"])
    game_state["kitten_just_drawn"] = False
    # ✅ FIX 3: Turn ends after defusing — opponents now move
    _opponents_take_turns(game_state)
    return "defused_kitten"


def _play_shuffle(game_state):
    game_state["hand"].remove(CARD_TYPES["SHUFFLE"])
    game_state["discard"].append(CARD_TYPES["SHUFFLE"])
    random.shuffle(game_state["deck"])
    game_state["top_three"] = None  # invalidate any See the Future peek
    _opponents_take_turns(game_state)
    return "played_shuffle"


def _play_see_future(game_state):
    game_state["hand"].remove(CARD_TYPES["SEE_THE_FUTURE"])
    game_state["discard"].append(CARD_TYPES["SEE_THE_FUTURE"])
    top3 = game_state["deck"][-3:] if len(game_state["deck"]) >= 3 else game_state["deck"][:]
    game_state["top_three"] = list(reversed(top3))  # index 0 = next draw
    # See the Future does NOT end your turn — no opponent move here
    return "played_see_future"


def _play_favor(game_state):
    game_state["hand"].remove(CARD_TYPES["FAVOR"])
    game_state["discard"].append(CARD_TYPES["FAVOR"])
    if not game_state["opponents"] or not any(game_state["opponents"]):
        return "favor_no_target"
    for opp in game_state["opponents"]:
        if opp:
            stolen = random.choice(opp)
            opp.remove(stolen)
            game_state["hand"].append(stolen)
            # Favor does NOT end your turn
            return "played_favor_stole_card"
    return "favor_no_cards_to_steal"


def _play_cat_pair(game_state):
    cat_ids = [8, 9, 10, 11, 12]
    from collections import Counter
    hand_counts = Counter(game_state["hand"])
    for cat in cat_ids:
        if hand_counts[cat] >= 2:
            game_state["hand"].remove(cat)
            game_state["hand"].remove(cat)
            game_state["discard"].extend([cat, cat])
            for opp in game_state["opponents"]:
                if opp:
                    stolen = random.choice(opp)
                    opp.remove(stolen)
                    game_state["hand"].append(stolen)
                    return "played_cat_pair"
    return "cat_pair_failed"


def _play_cat_triple(game_state):
    cat_ids = [8, 9, 10, 11, 12]
    from collections import Counter
    hand_counts = Counter(game_state["hand"])
    for cat in cat_ids:
        if hand_counts[cat] >= 3:
            for _ in range(3):
                game_state["hand"].remove(cat)
            game_state["discard"].extend([cat] * 3)
            for opp in game_state["opponents"]:
                if opp:
                    if CARD_TYPES["DEFUSE"] in opp:
                        opp.remove(CARD_TYPES["DEFUSE"])
                        game_state["hand"].append(CARD_TYPES["DEFUSE"])
                    else:
                        stolen = random.choice(opp)
                        opp.remove(stolen)
                        game_state["hand"].append(stolen)
                    return "played_cat_triple"
    return "cat_triple_failed"


def _play_five_diff(game_state):
    cat_ids = [8, 9, 10, 11, 12]
    used = []
    for cat in cat_ids:
        if cat in game_state["hand"] and len(used) < 5:
            game_state["hand"].remove(cat)
            game_state["discard"].append(cat)
            used.append(cat)
    if game_state["discard"]:
        if CARD_TYPES["DEFUSE"] in game_state["discard"]:
            picked = CARD_TYPES["DEFUSE"]
        else:
            picked = random.choice(game_state["discard"])
        game_state["discard"].remove(picked)
        game_state["hand"].append(picked)
        return "played_five_diff"
    return "five_diff_empty_discard"


def _opponents_take_turns(game_state: dict):
    """
    Simplified opponent simulation for Phase 1/2.
    Each opponent draws one card. If they explode and have no defuse, they're eliminated.
    """
    alive_opponents = []
    for opp_hand in game_state["opponents"]:
        if not game_state["deck"]:
            alive_opponents.append(opp_hand)
            continue
        drawn = game_state["deck"].pop(0)
        if drawn == CARD_TYPES["EXPLODING_KITTEN"]:
            if CARD_TYPES["DEFUSE"] in opp_hand:
                opp_hand.remove(CARD_TYPES["DEFUSE"])
                insert_pos = random.randint(0, len(game_state["deck"]))
                game_state["deck"].insert(insert_pos, CARD_TYPES["EXPLODING_KITTEN"])
                alive_opponents.append(opp_hand)
            # else: opponent eliminated — not added back
        else:
            opp_hand.append(drawn)
            alive_opponents.append(opp_hand)

    game_state["opponents"] = alive_opponents