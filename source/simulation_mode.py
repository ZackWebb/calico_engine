import copy
from typing import List
import random

from game_mode import GameMode
from game_state import Action


class SimulationMode(GameMode):
    """
    Non-visual game mode for MCMC agent and programmatic control.
    Provides complete programmatic interface for:
    - State inspection
    - Legal action enumeration
    - Action application
    - Game state copying for lookahead
    """

    def __init__(self, board_config=None):
        super().__init__(board_config)
        self._action_history: List[Action] = []

    def run(self):
        """
        No-op for simulation mode.
        External code drives the game via apply_action().
        """
        pass

    def copy(self) -> 'SimulationMode':
        """
        Create a deep copy of this game for simulation/lookahead.
        Essential for MCMC agent to explore possible futures.
        """
        return copy.deepcopy(self)

    def get_action_history(self) -> List[Action]:
        """Return history of all actions taken."""
        return list(self._action_history)

    def apply_action(self, action: Action) -> bool:
        """Override to track action history."""
        success = super().apply_action(action)
        if success:
            self._action_history.append(action)
        return success

    # --- Convenience Methods for MCMC Agent ---

    def play_random_game(self, use_combined_actions: bool = True) -> int:
        """
        Play game to completion with random moves.
        Returns final score. Useful for MCMC rollouts.

        Args:
            use_combined_actions: If True, use combined place_and_choose actions
        """
        while not self.is_game_over():
            if use_combined_actions:
                actions = self.get_combined_legal_actions()
            else:
                actions = self.get_legal_actions()
            if not actions:
                break
            action = random.choice(actions)
            self.apply_action(action)
        return self.get_final_score()

    def get_state_hash(self) -> str:
        """
        Return hashable representation of current state.
        Useful for MCMC state deduplication.
        """
        state = self.get_game_state()
        # Create deterministic hash from state
        hand_str = ','.join(f"{t.color.value}{t.pattern.value}" for t in state.player_hand)
        market_str = ','.join(f"{t.color.value}{t.pattern.value}" for t in state.market_tiles)
        grid_str = ','.join(str(pos) for pos in sorted(state.empty_positions))
        return f"{state.turn_phase.value}|{hand_str}|{market_str}|{grid_str}"
