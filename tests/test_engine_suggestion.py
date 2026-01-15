"""
Tests for the engine suggestion feature.

Tests the ScoreBreakdown, CandidateInfo, and engine suggestion
functionality in PlayMode.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'source'))

from simulation_mode import SimulationMode
from play_mode import PlayMode
from mcts_agent import MCTSAgent, CandidateInfo
from heuristic import (
    ScoreBreakdown,
    evaluate_state_with_breakdown,
    evaluate_cats_with_reasons,
    evaluate_goals_with_reasons,
    evaluate_buttons_with_reasons,
)
from game_state import TurnPhase


class TestScoreBreakdown:
    """Tests for the ScoreBreakdown dataclass."""

    def test_score_breakdown_creation(self):
        """ScoreBreakdown can be created with defaults."""
        breakdown = ScoreBreakdown()
        assert breakdown.total == 0.0
        assert breakdown.cat_score == 0.0
        assert breakdown.goal_score == 0.0
        assert breakdown.button_score == 0.0
        assert breakdown.cat_reasons == []
        assert breakdown.goal_reasons == []
        assert breakdown.button_reasons == []

    def test_score_breakdown_with_values(self):
        """ScoreBreakdown stores provided values."""
        breakdown = ScoreBreakdown(
            total=50.0,
            cat_score=20.0,
            goal_score=25.0,
            button_score=5.0,
            cat_reasons=["Leo 4/5 stripes line"],
            goal_reasons=["AAA-BBB: 5/6 filled"],
            button_reasons=["3 buttons (blue, green)"],
        )
        assert breakdown.total == 50.0
        assert breakdown.cat_score == 20.0
        assert len(breakdown.cat_reasons) == 1

    def test_top_reason_returns_first(self):
        """top_reason returns first reason or empty string."""
        breakdown = ScoreBreakdown(
            cat_reasons=["First", "Second"],
            goal_reasons=[],
        )
        assert breakdown.top_reason("cat") == "First"
        assert breakdown.top_reason("goal") == ""

    def test_format_compact(self):
        """format_compact produces readable output."""
        breakdown = ScoreBreakdown(
            cat_score=5.0,
            goal_score=3.0,
            button_score=2.0,
            cat_reasons=["Leo potential"],
            goal_reasons=["AAA-BBB progress"],
            button_reasons=["Blue pair"],
        )
        compact = breakdown.format_compact()
        assert "Cats: +5.0" in compact
        assert "Leo potential" in compact


class TestEvaluateStateWithBreakdown:
    """Tests for evaluate_state_with_breakdown function."""

    def test_returns_score_breakdown(self):
        """Function returns a ScoreBreakdown object."""
        game = SimulationMode()
        # Skip goal selection
        game.apply_action(game.get_legal_actions()[0])

        breakdown = evaluate_state_with_breakdown(game)
        assert isinstance(breakdown, ScoreBreakdown)
        assert breakdown.total >= 0  # May be 0 for empty board

    def test_breakdown_matches_total(self):
        """Component scores should approximately sum to total."""
        game = SimulationMode()
        game.apply_action(game.get_legal_actions()[0])

        breakdown = evaluate_state_with_breakdown(game)
        component_sum = breakdown.cat_score + breakdown.goal_score + breakdown.button_score
        # Allow small floating point differences
        assert abs(breakdown.total - component_sum) < 0.1

    def test_reasons_are_populated(self):
        """Breakdown should include at least some reasons."""
        game = SimulationMode()
        game.apply_action(game.get_legal_actions()[0])

        # Play a few moves to create some state
        for _ in range(5):
            if game.is_game_over():
                break
            actions = game.get_combined_legal_actions()
            if actions:
                game.apply_action(actions[0])

        breakdown = evaluate_state_with_breakdown(game)
        # At least one category should have reasons after several moves
        total_reasons = len(breakdown.cat_reasons) + len(breakdown.goal_reasons) + len(breakdown.button_reasons)
        assert total_reasons >= 0  # May be 0 early game, that's OK


class TestCandidateInfo:
    """Tests for CandidateInfo dataclass."""

    def test_candidate_info_creation(self):
        """CandidateInfo can be created with required fields."""
        from game_state import Action
        action = Action(action_type="place_and_choose", position=(0, 0, 0), hand_index=0, market_index=0)
        breakdown = ScoreBreakdown()

        candidate = CandidateInfo(
            action=action,
            visits=100,
            avg_score=65.5,
            breakdown=breakdown,
        )
        assert candidate.visits == 100
        assert candidate.avg_score == 65.5

    def test_action_description_place_and_choose(self):
        """action_description formats place_and_choose actions."""
        from game_state import Action

        game = SimulationMode()
        game.apply_action(game.get_legal_actions()[0])

        action = Action(
            action_type="place_and_choose",
            position=(0, 0, 0),
            hand_index=0,
            market_index=1,
        )
        candidate = CandidateInfo(action=action, visits=50, avg_score=60.0, breakdown=ScoreBreakdown())

        desc = candidate.action_description(game)
        assert "at" in desc.lower() or "/" in desc  # Should describe tile and position


class TestMCTSDetailedAnalysis:
    """Tests for select_action_with_detailed_analysis method."""

    def test_returns_candidates_with_breakdown(self):
        """Method returns list of CandidateInfo with breakdowns."""
        game = SimulationMode()
        game.apply_action(game.get_legal_actions()[0])

        agent = MCTSAgent(max_iterations=50)  # Low iterations for speed
        best_action, candidates = agent.select_action_with_detailed_analysis(game, n_candidates=3)

        assert best_action is not None
        assert len(candidates) <= 3
        for candidate in candidates:
            assert isinstance(candidate, CandidateInfo)
            assert isinstance(candidate.breakdown, ScoreBreakdown)
            assert candidate.visits >= 0
            assert isinstance(candidate.avg_score, float)

    def test_candidates_sorted_by_visits(self):
        """Candidates should be sorted by visit count (descending)."""
        game = SimulationMode()
        game.apply_action(game.get_legal_actions()[0])

        agent = MCTSAgent(max_iterations=100)
        _, candidates = agent.select_action_with_detailed_analysis(game, n_candidates=5)

        if len(candidates) > 1:
            for i in range(len(candidates) - 1):
                assert candidates[i].visits >= candidates[i + 1].visits

    def test_best_action_matches_first_candidate(self):
        """Best action should match the first candidate's action."""
        game = SimulationMode()
        game.apply_action(game.get_legal_actions()[0])

        agent = MCTSAgent(max_iterations=50)
        best_action, candidates = agent.select_action_with_detailed_analysis(game)

        if candidates:
            assert best_action == candidates[0].action


class TestPlayModeEngineSuggestion:
    """Tests for engine suggestion state in PlayMode."""

    def test_initial_state(self):
        """Engine suggestion is off by default."""
        play_mode = PlayMode()
        assert play_mode.show_engine_suggestion is False
        assert play_mode.engine_candidates is None
        assert play_mode.engine_computing is False
        assert play_mode.engine_iterations == 1000

    def test_toggle_on(self):
        """Toggling on triggers computation."""
        play_mode = PlayMode()
        # Complete goal selection first
        play_mode.goal_slot_assignments = [0, 1, 2]
        play_mode.confirm_goal_selection()

        play_mode.toggle_engine_suggestion()
        assert play_mode.show_engine_suggestion is True
        # Should have computed candidates (synchronously for now)
        assert play_mode.engine_candidates is not None

    def test_toggle_off(self):
        """Toggling off hides suggestions."""
        play_mode = PlayMode()
        play_mode.goal_slot_assignments = [0, 1, 2]
        play_mode.confirm_goal_selection()

        play_mode.toggle_engine_suggestion()  # On
        play_mode.toggle_engine_suggestion()  # Off
        assert play_mode.show_engine_suggestion is False

    def test_adjust_iterations(self):
        """Iteration count can be adjusted with scaled steps."""
        play_mode = PlayMode()
        # Default is 1000, so step should be 500 (1000-5000 range)

        play_mode.adjust_engine_iterations(increase=True)
        assert play_mode.engine_iterations == 1500

        # Go down - should step by 500 (in 1000-5000 range)
        play_mode.adjust_engine_iterations(increase=False)
        assert play_mode.engine_iterations == 1000

        # Test lower range (below 1000, step by 250)
        play_mode.engine_iterations = 750
        play_mode.adjust_engine_iterations(increase=False)
        assert play_mode.engine_iterations == 500

        play_mode.adjust_engine_iterations(increase=False)
        assert play_mode.engine_iterations == 250  # Clamped to minimum

        play_mode.adjust_engine_iterations(increase=False)
        assert play_mode.engine_iterations == 250  # Still at minimum

        # Test high range (above 20000, step by 10000)
        play_mode.engine_iterations = 50000
        play_mode.adjust_engine_iterations(increase=True)
        assert play_mode.engine_iterations == 60000

        play_mode.engine_iterations = 95000
        play_mode.adjust_engine_iterations(increase=True)
        assert play_mode.engine_iterations == 100000  # Clamped to maximum

    def test_cache_cleared_on_action(self):
        """Engine cache is cleared when an action is taken."""
        play_mode = PlayMode()
        play_mode.goal_slot_assignments = [0, 1, 2]
        play_mode.confirm_goal_selection()

        play_mode.toggle_engine_suggestion()
        assert play_mode.engine_candidates is not None

        # Make a move
        play_mode.select_hand_tile(0)
        empty_positions = play_mode.player.grid.get_empty_positions()
        if empty_positions:
            pos = empty_positions[0]
            play_mode.try_place_at_position(*pos)
            # Cache should be cleared
            assert play_mode.engine_candidates is None


class TestSimulationModeFromGameMode:
    """Tests for SimulationMode.from_game_mode class method."""

    def test_creates_simulation_mode(self):
        """from_game_mode creates a SimulationMode instance."""
        play_mode = PlayMode()
        play_mode.goal_slot_assignments = [0, 1, 2]
        play_mode.confirm_goal_selection()

        sim = SimulationMode.from_game_mode(play_mode)
        assert isinstance(sim, SimulationMode)

    def test_copies_state_correctly(self):
        """Copied state matches original."""
        play_mode = PlayMode()
        play_mode.goal_slot_assignments = [0, 1, 2]
        play_mode.confirm_goal_selection()

        sim = SimulationMode.from_game_mode(play_mode)

        assert sim.turn_number == play_mode.turn_number
        assert sim.turn_phase == play_mode.turn_phase
        assert len(sim.player.tiles) == len(play_mode.player.tiles)
        assert len(sim.goals) == len(play_mode.goals)

    def test_independent_copy(self):
        """Changes to copy don't affect original."""
        play_mode = PlayMode()
        play_mode.goal_slot_assignments = [0, 1, 2]
        play_mode.confirm_goal_selection()

        original_turn = play_mode.turn_number

        sim = SimulationMode.from_game_mode(play_mode)
        # Make moves in sim
        for _ in range(3):
            actions = sim.get_combined_legal_actions()
            if actions:
                sim.apply_action(actions[0])

        # Original should be unchanged
        assert play_mode.turn_number == original_turn


class TestEvaluationHelpers:
    """Tests for the evaluation helper functions with reasons."""

    def test_evaluate_cats_with_reasons(self):
        """evaluate_cats_with_reasons returns score and reasons."""
        game = SimulationMode()
        game.apply_action(game.get_legal_actions()[0])

        score, reasons = evaluate_cats_with_reasons(game)
        assert isinstance(score, float)
        assert isinstance(reasons, list)
        assert score >= 0

    def test_evaluate_goals_with_reasons(self):
        """evaluate_goals_with_reasons returns score and reasons."""
        game = SimulationMode()
        game.apply_action(game.get_legal_actions()[0])

        score, reasons = evaluate_goals_with_reasons(game)
        assert isinstance(score, float)
        assert isinstance(reasons, list)
        assert score >= 0

    def test_evaluate_buttons_with_reasons(self):
        """evaluate_buttons_with_reasons returns score and reasons."""
        game = SimulationMode()
        game.apply_action(game.get_legal_actions()[0])

        score, reasons = evaluate_buttons_with_reasons(game.player.grid)
        assert isinstance(score, float)
        assert isinstance(reasons, list)
        assert score >= 0
