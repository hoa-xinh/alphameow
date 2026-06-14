import pytest
from env import ExplodingKittensEnv
from env.rewards import calculate_reward
from env.state import STATE_SIZE, encode_state_for_player

def test_reset_returns_valid_obs():
    env = ExplodingKittensEnv(num_players=3)
    obs, info = env.reset()
    assert obs.shape == (STATE_SIZE,)
    assert "legal_actions" in info
    assert "all_observations" in info
    assert len(info["all_observations"]) == 3
    assert info["current_player"] == 0

def test_draw_card_action_always_legal():
    env = ExplodingKittensEnv()
    _, info = env.reset()
    assert 0 in info["legal_actions"]  # draw always legal

def test_defuse_illegal_without_kitten():
    env = ExplodingKittensEnv()
    _, info = env.reset()
    assert 3 not in info["legal_actions"]  # no kitten drawn yet

def test_illegal_action_penalty_is_small():
    env = ExplodingKittensEnv()
    _, _ = env.reset()
    _, reward, terminated, truncated, info = env.step(3)
    assert reward == -0.05
    assert not terminated
    assert not truncated
    assert info["error"] == "illegal_action"

def test_turn_advances_after_safe_draw():
    env = ExplodingKittensEnv(num_players=2)
    _, info = env.reset()
    first_player = info["current_player"]
    obs, reward, terminated, truncated, info = env.step(0)
    if not terminated and not truncated and info["event"] == "drew_safe_card":
        assert info["current_player"] != first_player

def test_10_games_no_crash():
    env = ExplodingKittensEnv(num_players=4)
    import random
    for _ in range(10):
        obs, info = env.reset()
        done = False
        while not done:
            action = random.choice(info["legal_actions"])
            obs, r, terminated, truncated, info = env.step(action)
            done = terminated or truncated

def test_rewards_are_bounded_to_normalized_scale():
    base_state = {"terminated": False, "winner": None}

    assert calculate_reward(base_state, "drew_safe_card", acting_player=0) == 0.01
    assert calculate_reward(base_state, "played_attack", acting_player=0) == 0.02
    assert calculate_reward(base_state, "defused_kitten", acting_player=0) == 0.2
    assert calculate_reward(base_state, "cat_pair_failed", acting_player=0) == -0.02
    assert calculate_reward(base_state, "unknown_event", acting_player=0) == 0.001

    terminal_win = {"terminated": True, "winner": 1}
    terminal_loss = {"terminated": False, "winner": None}
    assert calculate_reward(terminal_win, "anything", acting_player=1) == 1.0
    assert calculate_reward(terminal_loss, "exploded_no_defuse", acting_player=0) == -1.0


def test_observation_includes_relative_opponent_hand_sizes():
    env = ExplodingKittensEnv(num_players=4)
    env.reset()

    game_state = env.game_state
    game_state["players"] = [
        [1, 2],
        [3, 4, 5, 6],
        [7],
        [8, 9, 10],
    ]
    game_state["alive_players"] = [True, True, True, True]

    obs = encode_state_for_player(game_state, 0)

    assert obs[13] == pytest.approx(4 / 12)
    assert obs[14] == pytest.approx(1 / 12)
    assert obs[15] == pytest.approx(3 / 12)
