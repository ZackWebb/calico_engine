from abc import ABC, abstractmethod
from typing import List, Tuple, Optional
import random

from tile_bag import TileBag
from market import Market
from player import Player
from cat import initialize_game_cats
from board_configurations import GOAL_POSITIONS, get_random_board, get_board_name
from game_state import GameState, Action, TurnPhase
from goal import create_goal_options, create_goals_from_selection
from button import score_buttons, get_button_details


class GameMode(ABC):
    """Abstract base class for game modes."""

    def __init__(self, board_config=None):
        # Select random board if none provided
        if board_config is None:
            board_config, self.board_name = get_random_board()
        else:
            self.board_name = get_board_name(board_config)

        self.board_config = board_config
        self.tile_bag = TileBag()
        self.cats, _ = initialize_game_cats()

        # Goal selection: 4 options, player chooses 3
        self.goal_options: List[type] = create_goal_options()  # 4 goal classes
        self.goal_positions: List[Tuple[int, int, int]] = list(GOAL_POSITIONS)
        self.goals: List = []  # Empty until goal selection complete

        # Game starts in goal selection phase
        self.turn_number = 0
        self.turn_phase = TurnPhase.GOAL_SELECTION

        # Create player with empty hand (tiles drawn after goal selection)
        self.player = Player.__new__(Player)
        self.player.name = "Player1"
        self.player.grid = __import__('hex_grid', fromlist=['HexGrid']).HexGrid()
        self.player.tiles = []  # No tiles yet

        # Market not initialized until goal selection complete
        self.market: Optional[Market] = None
        self._tiles_initialized = False

        # Initialize player grid with board configuration and goal positions
        self.player.grid.initialize_from_config(board_config)
        self.player.grid.set_goal_positions(GOAL_POSITIONS)

    # --- State Query Methods ---

    def get_game_state(self) -> GameState:
        """Get current game state snapshot."""
        return GameState(
            player_hand=list(self.player.tiles),
            market_tiles=list(self.market.tiles) if self.market else [],
            empty_positions=self.player.grid.get_empty_positions(),
            turn_number=self.turn_number,
            turn_phase=self.turn_phase,
            tiles_remaining_in_bag=self.tile_bag.tiles_remaining()
        )

    def get_legal_actions(self) -> List[Action]:
        """Get list of legal actions for current phase."""
        actions = []

        if self.turn_phase == TurnPhase.GOAL_SELECTION:
            actions = self._enumerate_goal_selection_actions()

        elif self.turn_phase == TurnPhase.PLACE_TILE:
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

    def _enumerate_goal_selection_actions(self) -> List[Action]:
        """
        Enumerate all 24 possible goal selection arrangements.

        Player chooses 3 of 4 goals and assigns them to 3 positions.
        P(4,3) = 4 * 3 * 2 = 24 arrangements.
        """
        from itertools import permutations

        actions = []
        # Each permutation is a way to select 3 from 4 in a specific order
        for perm in permutations(range(4), 3):
            actions.append(Action(
                action_type="select_goals",
                selected_goal_indices=perm
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
        if action.action_type == "select_goals":
            return self._do_select_goals(action)
        elif action.action_type == "place_tile":
            return self._do_place_tile(action.position, action.hand_index)
        elif action.action_type == "choose_market":
            return self._do_choose_market(action.market_index)
        elif action.action_type == "place_and_choose":
            return self._do_place_and_choose(action)
        return False

    def _do_select_goals(self, action: Action) -> bool:
        """Execute goal selection and initialize tiles."""
        if self.turn_phase != TurnPhase.GOAL_SELECTION:
            return False

        # Create goal instances from selection
        self.goals = create_goals_from_selection(
            self.goal_options,
            action.selected_goal_indices,
            self.goal_positions
        )

        # Now initialize tiles (player hand and market)
        self._initialize_tiles()

        # Transition to tile placement phase
        self.turn_phase = TurnPhase.PLACE_TILE
        return True

    def _initialize_tiles(self):
        """Initialize player hand and market after goal selection."""
        if not self._tiles_initialized:
            # Draw 2 tiles for player hand
            self.player.tiles = [
                self.tile_bag.draw_tile(),
                self.tile_bag.draw_tile()
            ]
            # Initialize market with 3 tiles
            self.market = Market(self.tile_bag)
            self._tiles_initialized = True

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
