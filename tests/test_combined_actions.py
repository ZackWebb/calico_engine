"""
Test suite for combined place_and_choose actions.
"""
import pytest
import sys
import os

# Add source directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'source'))

from simulation_mode import SimulationMode
from board_configurations import BOARD_1
from game_state import Action, TurnPhase
from mcts_agent import MCTSNode, MCTSAgent


def complete_goal_selection(game):
    """Helper to complete goal selection phase and transition to tile placement."""
    if game.turn_phase == TurnPhase.GOAL_SELECTION:
        actions = game.get_legal_actions()
        game.apply_action(actions[0])
    return game


class TestCombinedActionGeneration:
    """Tests for get_combined_legal_actions()."""

    def test_combined_actions_count(self):
        """Combined actions should be positions x hand_tiles x market_tiles."""
        game = SimulationMode(BOARD_1)
        complete_goal_selection(game)
        state = game.get_game_state()

        combined = game.get_combined_legal_actions()
        separate = game.get_legal_actions()

        # Combined should be 3x the separate place actions (one for each market choice)
        place_actions = [a for a in separate if a.action_type == "place_tile"]
        expected_combined = len(place_actions) * 3  # 3 market choices

        assert len(combined) == expected_combined

    def test_combined_actions_have_all_fields(self):
        """Combined actions should have position, hand_index, and market_index."""
        game = SimulationMode(BOARD_1)
        complete_goal_selection(game)
        combined = game.get_combined_legal_actions()

        for action in combined:
            assert action.action_type == "place_and_choose"
            assert action.position is not None
            assert action.hand_index is not None
            assert action.market_index is not None  # Not final turn yet

    def test_combined_actions_only_in_place_phase(self):
        """Combined actions should only be generated in PLACE_TILE phase."""
        game = SimulationMode(BOARD_1)
        complete_goal_selection(game)

        # Move to market phase
        actions = game.get_legal_actions()
        game.apply_action(actions[0])
        assert game.turn_phase == TurnPhase.CHOOSE_MARKET

        # Combined actions should be empty
        combined = game.get_combined_legal_actions()
        assert len(combined) == 0

    def test_final_turn_has_no_market_index(self):
        """Final turn combined actions should have market_index=None."""
        game = SimulationMode(BOARD_1)

        # Play until only one empty position
        while len(game.player.grid.get_empty_positions()) > 1:
            actions = game.get_combined_legal_actions()
            if actions:
                game.apply_action(actions[0])
            else:
                break

        # Now check combined actions
        if game.turn_phase == TurnPhase.PLACE_TILE:
            combined = game.get_combined_legal_actions()
            if combined:
                for action in combined:
                    assert action.market_index is None
                    assert action.is_final_turn_action()


class TestCombinedActionExecution:
    """Tests for _do_place_and_choose()."""

    def test_combined_action_places_tile(self):
        """Combined action should place a tile on the board."""
        game = SimulationMode(BOARD_1)
        complete_goal_selection(game)
        initial_empty = len(game.player.grid.get_empty_positions())

        combined = game.get_combined_legal_actions()
        assert len(combined) > 0

        game.apply_action(combined[0])

        # One less empty position
        new_empty = len(game.player.grid.get_empty_positions())
        assert new_empty == initial_empty - 1

    def test_combined_action_takes_market_tile(self):
        """Combined action should take the specified market tile."""
        game = SimulationMode(BOARD_1)
        complete_goal_selection(game)
        initial_hand = list(game.player.tiles)
        market_tile_to_take = game.market.tiles[1]  # Index 1

        # Find a combined action with market_index=1
        combined = game.get_combined_legal_actions()
        action = next(a for a in combined if a.market_index == 1)

        game.apply_action(action)

        # Hand should have the market tile (minus one placed tile)
        assert len(game.player.tiles) == 2
        assert market_tile_to_take in game.player.tiles

    def test_combined_action_advances_turn(self):
        """Combined action should advance to next turn."""
        game = SimulationMode(BOARD_1)
        complete_goal_selection(game)
        assert game.turn_number == 0

        combined = game.get_combined_legal_actions()
        game.apply_action(combined[0])

        # Should be on turn 1 now
        assert game.turn_number == 1
        assert game.turn_phase == TurnPhase.PLACE_TILE

    def test_combined_action_game_completion(self):
        """Game should complete with only combined actions."""
        game = SimulationMode(BOARD_1)
        complete_goal_selection(game)

        while not game.is_game_over():
            combined = game.get_combined_legal_actions()
            if not combined:
                break
            game.apply_action(combined[0])

        assert game.is_game_over()
        score = game.get_final_score()
        assert score >= 0


class TestMCTSWithCombinedActions:
    """Tests for MCTS using combined actions."""

    def test_mcts_returns_combined_action(self):
        """MCTS with combined actions should return place_and_choose."""
        game = SimulationMode(BOARD_1)
        complete_goal_selection(game)
        agent = MCTSAgent(max_iterations=50, use_combined_actions=True)

        action = agent.select_action(game)

        assert action.action_type == "place_and_choose"
        assert action.position is not None
        assert action.hand_index is not None
        assert action.market_index is not None

    def test_mcts_separate_returns_place_tile(self):
        """MCTS with separate actions should return place_tile in place phase."""
        game = SimulationMode(BOARD_1)
        complete_goal_selection(game)
        agent = MCTSAgent(max_iterations=50, use_combined_actions=False)

        action = agent.select_action(game)

        assert action.action_type == "place_tile"
        assert action.position is not None
        assert action.hand_index is not None

    def test_mcts_node_uses_combined_actions(self):
        """MCTSNode should use combined actions when configured."""
        game = SimulationMode(BOARD_1)
        complete_goal_selection(game)
        node = MCTSNode(state=game.copy(), use_combined_actions=True)

        for action in node.untried_actions:
            assert action.action_type == "place_and_choose"

    def test_mcts_node_propagates_flag(self):
        """Expanded children should inherit use_combined_actions flag."""
        game = SimulationMode(BOARD_1)
        complete_goal_selection(game)
        root = MCTSNode(state=game.copy(), use_combined_actions=True)

        child = root.expand()

        assert child.use_combined_actions == True
        for action in child.untried_actions:
            assert action.action_type == "place_and_choose"

    def test_mcts_completes_game_with_combined(self):
        """MCTS should complete a game using only combined actions."""
        game = SimulationMode(BOARD_1)
        complete_goal_selection(game)
        agent = MCTSAgent(max_iterations=50, use_combined_actions=True)

        while not game.is_game_over():
            action = agent.select_action(game)
            assert action.action_type == "place_and_choose"
            game.apply_action(action)

        assert game.is_game_over()
        score = game.get_final_score()
        assert score >= 0


class TestRandomGameWithCombinedActions:
    """Tests for play_random_game with combined actions."""

    def test_random_game_combined(self):
        """Random game with combined actions should complete."""
        game = SimulationMode(BOARD_1)
        score = game.play_random_game(use_combined_actions=True)
        assert score >= 0
        assert game.is_game_over()

    def test_random_game_separate(self):
        """Random game with separate actions should complete."""
        game = SimulationMode(BOARD_1)
        score = game.play_random_game(use_combined_actions=False)
        assert score >= 0
        assert game.is_game_over()

    def test_random_game_default_combined(self):
        """Random game should default to combined actions."""
        game = SimulationMode(BOARD_1)
        score = game.play_random_game()  # Default
        assert score >= 0
        assert game.is_game_over()
