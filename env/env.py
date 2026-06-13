# env.py
from .spaces_compat import gym
from .state import encode_state, encode_state_for_player, get_observation_space
from .action_space import get_action_space, get_legal_actions
from .cards import CARD_TYPES, DECK_COUNTS
from .rules import apply_action
from .rewards import calculate_reward


class ExplodingKittensEnv(gym.Env):
    metadata = {"render_modes": ["human"]}

    def __init__(self, num_players=4):
        super().__init__()

        if not 2 <= num_players <= 4:
            raise ValueError("num_players must be between 2 and 4")

        self.num_players = num_players
        self.observation_space = get_observation_space()
        self.action_space = get_action_space()
        self.game_state = None

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)

        self.game_state = self._init_game()
        obs = encode_state(self.game_state)

        return obs, self._build_info(
            event="reset",
            acting_player=self.game_state["current_player"],
        )

    def step(self, action):
        assert self.game_state is not None, "Call reset() first"

        acting_player = self._acting_player()
        legal = get_legal_actions(self.game_state, acting_player)

        if action not in legal:
            obs = encode_state(self.game_state)
            info = self._build_info(
                event="illegal_action",
                acting_player=acting_player,
            )
            info["error"] = "illegal_action"
            return obs, -0.05, False, False, info

        event = apply_action(self.game_state, action, acting_player)

        reward = calculate_reward(self.game_state, event, acting_player)
        terminated = self.game_state["terminated"]
        truncated = self.game_state.get("turn_count", 0) > 500

        obs = encode_state(self.game_state)
        info = self._build_info(event=event, acting_player=acting_player)

        return obs, reward, terminated, truncated, info

    def render(self):
        gs = self.game_state
        current_player = gs["current_player"]
        reaction_player = gs.get("reaction_player")

        reaction_text = ""
        if gs.get("phase") == "reaction":
            reaction_text = f" | Reaction player: {reaction_player}"

        alive_opponents = sum(gs["alive_players"]) - 1

        print(
            f"Phase: {gs.get('phase', 'main')} | "
            f"Current player: {current_player}"
            f"{reaction_text} | "
            f"Hand: {gs['players'][current_player]} | "
            f"Deck: {len(gs['deck'])} cards | "
            f"Opponents alive: {alive_opponents}"
        )

    def _acting_player(self) -> int:
        """
        In main phase, the current player acts.
        In reaction phase, the reaction player acts.
        """
        if self.game_state.get("phase") == "reaction":
            return self.game_state.get(
                "reaction_player",
                self.game_state["current_player"],
            )

        return self.game_state["current_player"]

    def _build_info(self, event: str, acting_player: int) -> dict:
        return {
            "legal_actions": get_legal_actions(self.game_state),
            "turns_taken": self.game_state.get("turn_count", 0),
            "event": event,
            "acting_player": acting_player,
            "current_player": self.game_state["current_player"],
            "reaction_player": self.game_state.get("reaction_player"),
            "phase": self.game_state.get("phase", "main"),
            "alive_players": list(self.game_state["alive_players"]),
            "all_observations": [
                encode_state_for_player(self.game_state, idx)
                for idx in range(self.num_players)
            ],
        }

    def _init_game(self) -> dict:
        """
        Build and shuffle the deck, then deal 7 cards + 1 Defuse to each player.
        """
        import random

        deck = []

        for card_name, count in DECK_COUNTS.items():
            card_id = CARD_TYPES[card_name]

            if card_name == "EXPLODING_KITTEN":
                continue

            if card_name == "DEFUSE":
                continue

            deck.extend([card_id] * count)

        random.shuffle(deck)

        hands = []

        for _ in range(self.num_players):
            hand = [deck.pop() for _ in range(7)]
            hand.append(CARD_TYPES["DEFUSE"])
            hands.append(hand)

        # Insert enough kittens so all but one player can explode.
        for _ in range(self.num_players - 1):
            deck.append(CARD_TYPES["EXPLODING_KITTEN"])

        random.shuffle(deck)

        return {
            "players": hands,
            "alive_players": [True] * self.num_players,
            "deck": deck,
            "discard": [],
            "terminated": False,
            "turn_count": 0,
            "winner": None,

            # Turn system
            "current_player": 0,
            "pending_extra_draws": [0] * self.num_players,
            "current_turn_draws_remaining": 1,

            # Exploding kitten state
            "kitten_just_drawn": False,

            # See the Future state
            "top_three": None,

            # Nope reaction system
            "phase": "main",
            "pending_action": None,
            "reaction_player": None,

            # Used by simplified cat triple logic
            "last_requested_card": None,
        }
