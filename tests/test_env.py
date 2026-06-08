import pytest
from env import ExplodingKittensEnv

def test_reset_returns_valid_obs():
    env = ExplodingKittensEnv(num_players=3)
    obs, info = env.reset()
    assert obs.shape == (13,)
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
