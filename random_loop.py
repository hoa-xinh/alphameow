# random_loop.py
import sys, os
# ✅ FIX 7: Make sure Python can find the env/ package
sys.path.insert(0, os.path.dirname(__file__))

import random
from env import ExplodingKittensEnv
from env.action_space import get_legal_actions

def run_random_games(n=10_000):
    env = ExplodingKittensEnv(num_players=4)
    wins = crashes = 0

    for i in range(n):
        try:
            obs, info = env.reset()
            done = False
            while not done:
                legal = info.get("legal_actions", [0])
                action = random.choice(legal)
                obs, reward, terminated, truncated, info = env.step(action)
                done = terminated or truncated
            wins += 1
        except Exception as e:
            crashes += 1
            print(f"Game {i} crashed: {e}")

    print(f"\n✅ {wins} games completed | ❌ {crashes} crashes")
    print(f"Crash rate: {crashes/n*100:.2f}%")

if __name__ == "__main__":
    run_random_games()