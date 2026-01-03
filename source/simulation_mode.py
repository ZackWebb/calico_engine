import copy
from typing import List, Optional
import random

from game_mode import GameMode
from game_state import Action, TurnPhase


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
        Create a fast copy of this game for simulation/lookahead.
        Essential for MCTS agent to explore possible futures.

        Uses custom shallow copy that shares immutable objects (Tiles, Cats,
        Goals) while copying mutable state (tile lists, grid positions).

        Implements chance node sampling by shuffling remaining tiles in the
        copied bag. This ensures each simulation explores a different possible
        future, rather than "cheating" by knowing the exact tile order.
        """
        new_game = object.__new__(SimulationMode)

        # Copy tile bag first (needed for chance node sampling)
        new_game.tile_bag = copy.copy(self.tile_bag)

        # Handle player and market based on game phase
        if self.turn_phase == TurnPhase.GOAL_SELECTION:
            # In goal selection: no tiles drawn yet
            # Create player with copied grid but empty hand
            new_game.player = object.__new__(type(self.player))
            new_game.player.name = self.player.name
            new_game.player.grid = copy.copy(self.player.grid)
            new_game.player.tiles = []  # No tiles yet
            new_game.market = None
        else:
            # After goal selection: copy player and market normally
            new_game.player = copy.copy(self.player)
            new_game.market = copy.copy(self.market)
            new_game.market.tile_bag = new_game.tile_bag  # Link market to new bag

        # Share immutable objects (Cats have immutable attributes)
        new_game.cats = self.cats

        # Goal selection state
        new_game.goal_options = self.goal_options  # Share immutable class list
        new_game.goal_positions = self.goal_positions  # Share position list
        new_game.goals = self.goals  # Empty list or instantiated goals
        new_game._tiles_initialized = self._tiles_initialized

        new_game.board_config = self.board_config
        new_game.board_name = self.board_name

        # Copy scalars
        new_game.turn_number = self.turn_number
        new_game.turn_phase = self.turn_phase

        # Copy action history (list of immutable Action dataclasses)
        new_game._action_history = self._action_history.copy()

        # Chance node sampling - shuffle for honest simulation
        # This is important for goal selection: the agent doesn't know
        # which tiles will be drawn after selecting goals
        new_game.tile_bag.shuffle_remaining()

        return new_game

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
            # Goal selection phase uses regular get_legal_actions()
            if self.turn_phase == TurnPhase.GOAL_SELECTION:
                actions = self.get_legal_actions()
            elif use_combined_actions:
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
