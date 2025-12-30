from abc import ABC, abstractmethod
from typing import List, Tuple, Optional
import random

from tile_bag import TileBag
from market import Market
from player import Player
from cat import initialize_game_cats
from board_configurations import BOARD_1, GOAL_POSITIONS
from game_state import GameState, Action, TurnPhase
from goal import create_default_goals
from button import score_buttons, get_button_details


class GameMode(ABC):
    """Abstract base class for game modes."""

    def __init__(self, board_config=None):
        if board_config is None:
            board_config = BOARD_1

        self.tile_bag = TileBag()
        self.player = Player("Player1", self.tile_bag)
        self.market = Market(self.tile_bag)
        self.cats, _ = initialize_game_cats()
        self.goals = create_default_goals()
        self.turn_number = 0
        self.turn_phase = TurnPhase.PLACE_TILE
        self.board_config = board_config

        # Initialize player grid with board configuration and goal positions
        self.player.grid.initialize_from_config(board_config)
        self.player.grid.set_goal_positions(GOAL_POSITIONS)

    # --- State Query Methods ---

    def get_game_state(self) -> GameState:
        """Get current game state snapshot."""
        return GameState(
            player_hand=list(self.player.tiles),
            market_tiles=list(self.market.tiles),
            empty_positions=self.player.grid.get_empty_positions(),
            turn_number=self.turn_number,
            turn_phase=self.turn_phase,
            tiles_remaining_in_bag=self.tile_bag.tiles_remaining()
        )

    def get_legal_actions(self) -> List[Action]:
        """Get list of legal actions for current phase."""
        actions = []

        if self.turn_phase == TurnPhase.PLACE_TILE:
            empty_positions = self.player.grid.get_empty_positions()
            for pos in empty_positions:
                for hand_idx in range(len(self.player.tiles)):
                    actions.append(Action(
                        action_type="place_tile",
                        position=pos,
                        hand_index=hand_idx
                    ))

        elif self.turn_phase == TurnPhase.CHOOSE_MARKET:
            for market_idx in range(len(self.market.tiles)):
                actions.append(Action(
                    action_type="choose_market",
                    market_index=market_idx
                ))

        return actions

    def get_combined_legal_actions(self) -> List[Action]:
        """Get list of combined place_and_choose actions.

        Each action represents a full turn: placing a tile AND choosing from market.
        For the final turn (board fills after placement), market_index will be None.
        """
        actions = []

        # Must be in PLACE_TILE phase to generate combined actions
        if self.turn_phase != TurnPhase.PLACE_TILE:
            return actions

        empty_positions = self.player.grid.get_empty_positions()

        for pos in empty_positions:
            for hand_idx in range(len(self.player.tiles)):
                # Check if placing here would end the game (only 1 empty position left)
                is_final_turn = len(empty_positions) == 1

                if is_final_turn:
                    # Final turn: no market choice after placement
                    actions.append(Action(
                        action_type="place_and_choose",
                        position=pos,
                        hand_index=hand_idx,
                        market_index=None
                    ))
                else:
                    # Normal turn: include all market choices
                    for market_idx in range(len(self.market.tiles)):
                        actions.append(Action(
                            action_type="place_and_choose",
                            position=pos,
                            hand_index=hand_idx,
                            market_index=market_idx
                        ))

        return actions

    def is_game_over(self) -> bool:
        """Check if game has ended (all positions filled)."""
        return len(self.player.grid.get_empty_positions()) == 0

    def get_final_score(self) -> int:
        """Calculate final score using cats, goals, and buttons."""
        total = 0
        for cat in self.cats:
            total += cat.score(self.player.grid)
        for goal in self.goals:
            total += goal.score(self.player.grid)
        total += score_buttons(self.player.grid)
        return total

    def get_cat_scores(self) -> dict:
        """Get breakdown of cat scores."""
        return {cat.name: cat.score(self.player.grid) for cat in self.cats}

    def get_goal_scores(self) -> dict:
        """Get breakdown of goal scores."""
        return {goal.name: goal.score(self.player.grid) for goal in self.goals}

    def get_button_scores(self) -> dict:
        """Get breakdown of button scores."""
        return get_button_details(self.player.grid)

    # --- Action Methods ---

    def apply_action(self, action: Action) -> bool:
        """Apply an action and update game state. Returns success."""
        if action.action_type == "place_tile":
            return self._do_place_tile(action.position, action.hand_index)
        elif action.action_type == "choose_market":
            return self._do_choose_market(action.market_index)
        elif action.action_type == "place_and_choose":
            return self._do_place_and_choose(action)
        return False

    def _do_place_tile(self, position: Tuple[int, int, int], hand_index: int) -> bool:
        """Execute tile placement."""
        if self.turn_phase != TurnPhase.PLACE_TILE:
            return False

        q, r, s = position
        if self.player.place_tile(q, r, s, hand_index):
            # Check if game is over after placement
            if self.is_game_over():
                self.turn_phase = TurnPhase.GAME_OVER
            else:
                self.turn_phase = TurnPhase.CHOOSE_MARKET
            return True
        return False

    def _do_choose_market(self, market_index: int) -> bool:
        """Execute market tile selection."""
        if self.turn_phase != TurnPhase.CHOOSE_MARKET:
            return False

        tile = self.market.choose_tile(market_index)
        if tile:
            self.player.add_tile(tile)
            self.market.refill()
            self._simulate_other_players()
            self._end_turn()
            return True
        return False

    def _do_place_and_choose(self, action: Action) -> bool:
        """Execute combined tile placement and market selection as atomic action."""
        if self.turn_phase != TurnPhase.PLACE_TILE:
            return False

        # Step 1: Place the tile
        q, r, s = action.position
        if not self.player.place_tile(q, r, s, action.hand_index):
            return False

        # Step 2: Check if game is over (board filled after placement)
        if self.is_game_over():
            self.turn_phase = TurnPhase.GAME_OVER
            return True

        # Step 3: Choose from market (if not final turn)
        if action.market_index is not None:
            tile = self.market.choose_tile(action.market_index)
            if tile:
                self.player.add_tile(tile)
                self.market.refill()
                self._simulate_other_players()

        # Step 4: End turn
        self._end_turn()
        return True

    def _simulate_other_players(self):
        """Simulate P2, P3, P4 discarding market tiles."""
        for _ in range(3):  # 3 simulated players
            if self.market.tiles:
                discard_idx = random.randint(0, len(self.market.tiles) - 1)
                self.market.choose_tile(discard_idx)  # Discard
                self.market.refill()

    def _end_turn(self):
        """Advance to next turn or game over."""
        if self.is_game_over():
            self.turn_phase = TurnPhase.GAME_OVER
        else:
            self.turn_number += 1
            self.turn_phase = TurnPhase.PLACE_TILE

    # --- Abstract Methods ---

    @abstractmethod
    def run(self):
        """Run the game loop. Implementation differs by mode."""
        pass
