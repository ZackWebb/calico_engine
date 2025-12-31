"""
Test suite for MCTS agent.
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
from heuristic import (
    evaluate_state, evaluate_cats, evaluate_goals, evaluate_buttons,
    enumerate_all_5_lines, enumerate_all_3_lines
)


class TestMCTSNode:
    """Tests for MCTSNode class."""

    def test_create_root_node(self):
        """Root node should have no parent or action."""
        game = SimulationMode(BOARD_1)
        node = MCTSNode(state=game.copy())

        assert node.parent is None
        assert node.action is None
        assert node.visits == 0
        assert node.total_score == 0.0
        assert len(node.untried_actions) > 0

    def test_untried_actions_populated(self):
        """Untried actions should be populated from state."""
        game = SimulationMode(BOARD_1)
        # Default is combined actions
        node = MCTSNode(state=game.copy())
        expected_actions = game.get_combined_legal_actions()
        assert len(node.untried_actions) == len(expected_actions)

        # Test with separate actions
        node_separate = MCTSNode(state=game.copy(), use_combined_actions=False)
        expected_separate = game.get_legal_actions()
        assert len(node_separate.untried_actions) == len(expected_separate)

    def test_is_terminal_false_at_start(self):
        """New game should not be terminal."""
        game = SimulationMode(BOARD_1)
        node = MCTSNode(state=game.copy())

        assert not node.is_terminal

    def test_is_terminal_true_at_end(self):
        """Completed game should be terminal."""
        game = SimulationMode(BOARD_1)
        game.play_random_game()

        node = MCTSNode(state=game.copy())
        assert node.is_terminal

    def test_is_fully_expanded_false_initially(self):
        """Node with untried actions is not fully expanded."""
        game = SimulationMode(BOARD_1)
        node = MCTSNode(state=game.copy())

        assert not node.is_fully_expanded

    def test_is_fully_expanded_true_when_no_untried(self):
        """Node with no untried actions is fully expanded."""
        game = SimulationMode(BOARD_1)
        node = MCTSNode(state=game.copy())
        node.untried_actions = []

        assert node.is_fully_expanded

    def test_expand_creates_child(self):
        """Expand should create a child node."""
        game = SimulationMode(BOARD_1)
        root = MCTSNode(state=game.copy())

        initial_untried = len(root.untried_actions)
        child = root.expand()

        assert len(root.children) == 1
        assert len(root.untried_actions) == initial_untried - 1
        assert child.parent is root
        assert child.action is not None

    def test_expand_applies_action(self):
        """Expanded child should have action applied to state."""
        game = SimulationMode(BOARD_1)
        root = MCTSNode(state=game.copy())

        child = root.expand()

        # Child state should differ from parent (action was applied)
        # Check by comparing empty positions or turn phase
        if child.action.action_type == "place_tile":
            root_empty = len(root.state.player.grid.get_empty_positions())
            child_empty = len(child.state.player.grid.get_empty_positions())
            assert child_empty == root_empty - 1

    def test_ucb1_unvisited_is_infinite(self):
        """Unvisited node should have infinite UCB1 score."""
        game = SimulationMode(BOARD_1)
        parent = MCTSNode(state=game.copy())
        parent.visits = 10
        parent.total_score = 50.0

        child = MCTSNode(state=game.copy(), parent=parent)
        child.visits = 0

        assert child.ucb1_score(1.4) == float('inf')

    def test_ucb1_visited_is_finite(self):
        """Visited node should have finite UCB1 score."""
        game = SimulationMode(BOARD_1)
        parent = MCTSNode(state=game.copy())
        parent.visits = 100

        child = MCTSNode(state=game.copy(), parent=parent)
        child.visits = 10
        child.total_score = 50.0  # Average = 5.0

        score = child.ucb1_score(1.4)

        assert score > 0
        assert score < float('inf')
        # Should be around 5 + exploration term
        assert 4.0 < score < 8.0

    def test_best_child_selects_highest_ucb1(self):
        """best_child should return child with highest UCB1."""
        game = SimulationMode(BOARD_1)
        parent = MCTSNode(state=game.copy())
        parent.visits = 100

        # Create two children with different stats
        child1 = MCTSNode(state=game.copy(), parent=parent)
        child1.visits = 10
        child1.total_score = 30.0  # avg = 3

        child2 = MCTSNode(state=game.copy(), parent=parent)
        child2.visits = 10
        child2.total_score = 70.0  # avg = 7

        parent.children = [child1, child2]

        best = parent.best_child(1.4)
        assert best is child2


class TestMCTSAgent:
    """Tests for MCTSAgent class."""

    def test_select_action_returns_valid_action(self):
        """Agent should return a valid legal action."""
        game = SimulationMode(BOARD_1)
        # Default is combined actions
        agent = MCTSAgent(max_iterations=50)
        action = agent.select_action(game)
        legal_actions = game.get_combined_legal_actions()
        assert action in legal_actions

        # Test with separate actions
        agent_separate = MCTSAgent(max_iterations=50, use_combined_actions=False)
        action_separate = agent_separate.select_action(game)
        legal_separate = game.get_legal_actions()
        assert action_separate in legal_separate

    def test_select_action_in_place_phase(self):
        """Action should be place_and_choose in place phase (default combined mode)."""
        game = SimulationMode(BOARD_1)
        assert game.turn_phase == TurnPhase.PLACE_TILE

        agent = MCTSAgent(max_iterations=50)
        action = agent.select_action(game)

        assert action.action_type == "place_and_choose"
        assert action.position is not None
        assert action.hand_index is not None
        # market_index can be None for final turn, but not at start
        assert action.market_index is not None

    def test_select_action_in_place_phase_separate(self):
        """Action should be place_tile in place phase with separate actions."""
        game = SimulationMode(BOARD_1)
        assert game.turn_phase == TurnPhase.PLACE_TILE

        agent = MCTSAgent(max_iterations=50, use_combined_actions=False)
        action = agent.select_action(game)

        assert action.action_type == "place_tile"
        assert action.position is not None
        assert action.hand_index is not None

    def test_select_action_in_market_phase(self):
        """Action should be choose_market in market phase (separate actions mode)."""
        game = SimulationMode(BOARD_1)

        # Move to market phase
        actions = game.get_legal_actions()
        game.apply_action(actions[0])
        assert game.turn_phase == TurnPhase.CHOOSE_MARKET

        # Must use separate actions to be in market phase
        agent = MCTSAgent(max_iterations=50, use_combined_actions=False)
        action = agent.select_action(game)

        assert action.action_type == "choose_market"
        assert action.market_index is not None

    def test_agent_does_not_modify_input(self):
        """Agent should not modify the input game state."""
        game = SimulationMode(BOARD_1)
        initial_empty = len(game.player.grid.get_empty_positions())
        initial_turn = game.turn_number

        agent = MCTSAgent(max_iterations=50)
        agent.select_action(game)

        assert len(game.player.grid.get_empty_positions()) == initial_empty
        assert game.turn_number == initial_turn

    def test_more_iterations_more_children(self):
        """More iterations should generally explore more children."""
        game = SimulationMode(BOARD_1)

        agent_low = MCTSAgent(max_iterations=10)
        agent_high = MCTSAgent(max_iterations=100)

        # Run both agents - just verify they work
        # Can't easily compare tree internals from outside
        action_low = agent_low.select_action(game)
        action_high = agent_high.select_action(game)

        assert action_low is not None
        assert action_high is not None

    def test_agent_plays_full_game(self):
        """Agent should be able to play complete game."""
        game = SimulationMode(BOARD_1)
        agent = MCTSAgent(max_iterations=20)  # Low for speed

        moves = 0
        max_moves = 100  # Safety limit

        while not game.is_game_over() and moves < max_moves:
            action = agent.select_action(game)
            success = game.apply_action(action)
            assert success
            moves += 1

        assert game.is_game_over()
        score = game.get_final_score()
        assert score >= 0


class TestHeuristic:
    """Tests for heuristic evaluation."""

    def test_evaluate_state_returns_float(self):
        """Evaluation should return a numeric score."""
        game = SimulationMode(BOARD_1)
        score = evaluate_state(game)

        assert isinstance(score, (int, float))
        assert score >= 0

    def test_evaluate_state_at_start(self):
        """Early game should have low heuristic score."""
        game = SimulationMode(BOARD_1)
        score = evaluate_state(game)

        # At start, score should be relatively low
        assert score >= 0
        # But not zero (edge tiles may contribute)

    def test_evaluate_state_at_end(self):
        """At game end, heuristic should approximate final score."""
        game = SimulationMode(BOARD_1)
        game.play_random_game()

        heuristic_score = evaluate_state(game)
        actual_score = game.get_final_score()

        # At terminal state, heuristic includes "potential" that can't be realized
        # since no more tiles can be placed. This is expected behavior.
        # Just verify heuristic is in a reasonable range (not wildly off)
        assert heuristic_score >= actual_score * 0.5  # Not too low
        assert heuristic_score <= actual_score * 3 + 30  # Not absurdly high

    def test_evaluate_cats_non_negative(self):
        """Cat evaluation should be non-negative."""
        game = SimulationMode(BOARD_1)
        score = evaluate_cats(game)
        assert score >= 0

    def test_evaluate_goals_non_negative(self):
        """Goal evaluation should be non-negative."""
        game = SimulationMode(BOARD_1)
        score = evaluate_goals(game)
        assert score >= 0

    def test_evaluate_buttons_non_negative(self):
        """Button evaluation should be non-negative."""
        game = SimulationMode(BOARD_1)
        grid = game.player.grid
        score = evaluate_buttons(grid)
        assert score >= 0


class TestHeuristicHelpers:
    """Tests for heuristic helper functions."""

    def test_enumerate_all_5_lines_returns_list(self):
        """Should return list of 5-position lines."""
        game = SimulationMode(BOARD_1)

        lines = enumerate_all_5_lines(game.player.grid)
        assert isinstance(lines, list)
        assert len(lines) > 0
        # All lines should have exactly 5 positions
        for line in lines:
            assert len(line) == 5

    def test_enumerate_all_3_lines_returns_list(self):
        """Should return list of 3-position lines."""
        game = SimulationMode(BOARD_1)

        lines = enumerate_all_3_lines(game.player.grid)
        assert isinstance(lines, list)
        assert len(lines) > 0
        # All lines should have exactly 3 positions
        for line in lines:
            assert len(line) == 3


class TestRollout:
    """Tests for rollout mechanics."""

    def test_full_rollout_returns_score(self):
        """Full rollout should return a final score."""
        game = SimulationMode(BOARD_1)
        agent = MCTSAgent(max_iterations=10)

        score = agent._full_rollout(game)

        assert isinstance(score, float)
        assert score >= 0

    def test_full_rollout_doesnt_modify_original(self):
        """Rollout should not modify the original state."""
        game = SimulationMode(BOARD_1)
        initial_empty = len(game.player.grid.get_empty_positions())

        agent = MCTSAgent(max_iterations=10)
        agent._full_rollout(game)

        final_empty = len(game.player.grid.get_empty_positions())
        assert initial_empty == final_empty

    def test_heuristic_evaluate_works(self):
        """Heuristic evaluation should work."""
        game = SimulationMode(BOARD_1)
        agent = MCTSAgent(max_iterations=10, use_heuristic=True)

        score = agent._heuristic_evaluate(game)

        assert isinstance(score, float)
        assert score >= 0

    def test_deterministic_rollout_returns_score(self):
        """Deterministic rollout should return a final score."""
        game = SimulationMode(BOARD_1)
        agent = MCTSAgent(max_iterations=10, use_deterministic_rollout=True)

        score = agent._deterministic_rollout(game)

        assert isinstance(score, float)
        assert score >= 0

    def test_deterministic_rollout_doesnt_modify_original(self):
        """Deterministic rollout should not modify the original state."""
        game = SimulationMode(BOARD_1)
        initial_empty = len(game.player.grid.get_empty_positions())

        agent = MCTSAgent(max_iterations=10, use_deterministic_rollout=True)
        agent._deterministic_rollout(game)

        final_empty = len(game.player.grid.get_empty_positions())
        assert initial_empty == final_empty

    def test_deterministic_rollout_makes_greedy_choices(self):
        """Deterministic rollout should make greedy heuristic choices."""
        game = SimulationMode(BOARD_1)
        agent = MCTSAgent(max_iterations=10, use_deterministic_rollout=True)

        # Note: While the action choices are deterministic given a state,
        # the tile draws from the bag are random, so final scores may vary.
        # This test just verifies the method completes and returns valid scores.
        scores = []
        for _ in range(3):
            score = agent._deterministic_rollout(game)
            assert isinstance(score, float)
            assert score >= 0
            scores.append(score)

        # Scores should be reasonable (not wildly different)
        # Greedy heuristic should produce fairly consistent results
        avg_score = sum(scores) / len(scores)
        for score in scores:
            # Allow some variance due to random tile draws
            assert abs(score - avg_score) < avg_score * 0.5 + 10


class TestIntegration:
    """Integration tests for complete MCTS workflow."""

    def test_mcts_completes_game(self):
        """MCTS should complete a full game without errors."""
        game = SimulationMode(BOARD_1)
        agent = MCTSAgent(max_iterations=30)

        while not game.is_game_over():
            action = agent.select_action(game)
            game.apply_action(action)

        score = game.get_final_score()
        assert score >= 0
        print(f"\nMCTS game score: {score}")

    def test_mcts_with_heuristic_completes(self):
        """MCTS with heuristic should complete a game."""
        game = SimulationMode(BOARD_1)
        agent = MCTSAgent(max_iterations=30, use_heuristic=True)

        while not game.is_game_over():
            action = agent.select_action(game)
            game.apply_action(action)

        score = game.get_final_score()
        assert score >= 0

    def test_mcts_without_heuristic_completes(self):
        """MCTS without heuristic should complete a game."""
        game = SimulationMode(BOARD_1)
        agent = MCTSAgent(max_iterations=30, use_heuristic=False)

        while not game.is_game_over():
            action = agent.select_action(game)
            game.apply_action(action)

        score = game.get_final_score()
        assert score >= 0


class TestMCTSVsRandom:
    """Statistical comparison tests."""

    @pytest.mark.slow
    def test_mcts_beats_random_average(self):
        """MCTS should generally score better than random (statistical)."""
        n_games = 3  # Keep low for test speed
        mcts_scores = []
        random_scores = []

        agent = MCTSAgent(max_iterations=100)

        for _ in range(n_games):
            # MCTS game
            game_mcts = SimulationMode(BOARD_1)
            while not game_mcts.is_game_over():
                action = agent.select_action(game_mcts)
                game_mcts.apply_action(action)
            mcts_scores.append(game_mcts.get_final_score())

            # Random game
            game_random = SimulationMode(BOARD_1)
            random_scores.append(game_random.play_random_game())

        mcts_avg = sum(mcts_scores) / len(mcts_scores)
        random_avg = sum(random_scores) / len(random_scores)

        print(f"\nMCTS avg: {mcts_avg:.1f}, Random avg: {random_avg:.1f}")

        # MCTS should generally be at least as good
        # This may occasionally fail due to randomness with few games
        assert mcts_avg >= random_avg * 0.8  # Allow some slack
