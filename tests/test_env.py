import pytest
from env import ExplodingKittensEnv
from env.cards import CARD_TYPES

def test_reset_returns_valid_obs():
    env = ExplodingKittensEnv()
    obs, info = env.reset()
    assert obs.shape == (13,)
    assert "legal_actions" in info

def test_draw_card_action_always_legal():
    env = ExplodingKittensEnv()
    _, info = env.reset()
    assert 0 in info["legal_actions"]  # draw always legal

def test_defuse_illegal_without_kitten():
    env = ExplodingKittensEnv()
    obs, info = env.reset()
    assert 3 not in info["legal_actions"]  # no kitten drawn yet

def test_10_games_no_crash():
    env = ExplodingKittensEnv()
    import random
    for _ in range(10):
        obs, info = env.reset()
        done = False
        while not done:
            action = random.choice(info["legal_actions"])
            obs, r, terminated, truncated, info = env.step(action)
            done = terminated or truncated