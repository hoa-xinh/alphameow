# env.py
import gymnasium as gym
import numpy as np
from .state import encode_state, get_observation_space, STATE_SIZE
from .action_space import get_action_space, get_legal_actions, NUM_ACTIONS
from .cards import CARD_TYPES, DECK_COUNTS
from .rules import apply_action      
from .rewards import calculate_reward  

class ExplodingKittensEnv(gym.Env):
    metadata = {"render_modes": ["human"]}

    def __init__(self, num_players=4):
        super().__init__()
        self.num_players = num_players
        self.observation_space = get_observation_space()
        self.action_space = get_action_space()
        self.game_state = None

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.game_state = self._init_game()
        obs = encode_state(self.game_state)
        return obs, {"legal_actions": get_legal_actions(self.game_state)}

    def step(self, action):
        assert self.game_state is not None, "Call reset() first"

        legal = get_legal_actions(self.game_state)
        if action not in legal:
            # Illegal action penalty — return current state unchanged
            obs = encode_state(self.game_state)
            return obs, -1.0, False, False, {"error": "illegal_action"}

        event = apply_action(self.game_state, action)

        reward = calculate_reward(self.game_state, event)
        terminated = self.game_state["terminated"]
        truncated = self.game_state.get("turn_count", 0) > 500

        obs = encode_state(self.game_state)
        info = {
            "legal_actions": get_legal_actions(self.game_state),
            "turns_taken": self.game_state.get("turn_count", 0),
            "event": event,
        }
        return obs, reward, terminated, truncated, info

    def render(self):
        gs = self.game_state
        print(f"Hand: {gs['hand']} | Deck: {len(gs['deck'])} cards | "
              f"Opponents alive: {len(gs['opponents'])}")

    def _init_game(self) -> dict:
        """Build and shuffle the deck, deal hands."""
        import random
        from collections import defaultdict

        deck = []
        for card_name, count in DECK_COUNTS.items():
            card_id = CARD_TYPES[card_name]
            if card_name == "EXPLODING_KITTEN":
                continue  # inserted after dealing
            if card_name == "DEFUSE":
                continue  # 1 per player dealt directly
            deck.extend([card_id] * count)

        random.shuffle(deck)

        # Deal 7 cards + 1 Defuse to each player
        hands = []
        for _ in range(self.num_players):
            hand = [deck.pop() for _ in range(7)]
            hand.append(CARD_TYPES["DEFUSE"])
            hands.append(hand)

        # Insert exploding kittens (num_players - 1)
        for _ in range(self.num_players - 1):
            deck.append(CARD_TYPES["EXPLODING_KITTEN"])
        random.shuffle(deck)

        return {
            "hand": hands[0],             # Agent is always player 0
            "opponents": hands[1:],
            "deck": deck,
            "discard": [],
            "terminated": False,
            "turn_count": 0,
            "attacks_pending": 0,
            "kitten_just_drawn": False,
            "top_three": None,            # from See the Future
        }