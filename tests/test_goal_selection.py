"""Tests for goal selection feature."""
import pytest
from game_state import Action, TurnPhase
from goal import (
    create_goal_options,
    create_goals_from_selection,
    ALL_GOAL_CLASSES,
)
from simulation_mode import SimulationMode
from board_configurations import BOARD_1, GOAL_POSITIONS


class TestCreateGoalOptions:
    def test_returns_four_goals(self):
        classes = create_goal_options()
        assert len(classes) == 4

    def test_goals_are_goal_classes(self):
        classes = create_goal_options()
        for cls in classes:
            assert cls in ALL_GOAL_CLASSES

    def test_goals_are_unique(self):
        for _ in range(20):
            classes = create_goal_options()
            assert len(set(classes)) == 4


class TestCreateGoalsFromSelection:
    def test_creates_three_goals(self):
        classes = create_goal_options()
        selected = (0, 1, 2)
        positions = list(GOAL_POSITIONS)

        goals = create_goals_from_selection(classes, selected, positions)

        assert len(goals) == 3

    def test_goals_at_correct_positions(self):
        classes = create_goal_options()
        selected = (0, 1, 2)
        positions = list(GOAL_POSITIONS)

        goals = create_goals_from_selection(classes, selected, positions)

        for i, goal in enumerate(goals):
            assert goal.position == positions[i]

    def test_correct_goal_types_selected(self):
        classes = create_goal_options()
        selected = (3, 1, 0)  # Pick goals in specific order
        positions = list(GOAL_POSITIONS)

        goals = create_goals_from_selection(classes, selected, positions)

        assert type(goals[0]) == classes[3]
        assert type(goals[1]) == classes[1]
        assert type(goals[2]) == classes[0]


class TestGoalSelectionPhase:
    def test_game_starts_in_goal_selection(self):
        game = SimulationMode(BOARD_1)
        assert game.turn_phase == TurnPhase.GOAL_SELECTION

    def test_four_goal_options_available(self):
        game = SimulationMode(BOARD_1)
        assert len(game.goal_options) == 4

    def test_no_goals_before_selection(self):
        game = SimulationMode(BOARD_1)
        assert len(game.goals) == 0

    def test_no_tiles_before_selection(self):
        game = SimulationMode(BOARD_1)
        assert len(game.player.tiles) == 0

    def test_no_market_before_selection(self):
        game = SimulationMode(BOARD_1)
        assert game.market is None

    def test_legal_actions_returns_24_options(self):
        game = SimulationMode(BOARD_1)
        actions = game.get_legal_actions()
        assert len(actions) == 24
        assert all(a.action_type == "select_goals" for a in actions)

    def test_each_action_has_unique_selection(self):
        game = SimulationMode(BOARD_1)
        actions = game.get_legal_actions()

        selections = set()
        for a in actions:
            selections.add(a.selected_goal_indices)

        assert len(selections) == 24

    def test_apply_selection_transitions_to_place_tile(self):
        game = SimulationMode(BOARD_1)
        actions = game.get_legal_actions()
        game.apply_action(actions[0])
        assert game.turn_phase == TurnPhase.PLACE_TILE

    def test_tiles_drawn_after_selection(self):
        game = SimulationMode(BOARD_1)
        actions = game.get_legal_actions()
        game.apply_action(actions[0])
        assert len(game.player.tiles) == 2

    def test_market_initialized_after_selection(self):
        game = SimulationMode(BOARD_1)
        actions = game.get_legal_actions()
        game.apply_action(actions[0])
        assert game.market is not None
        assert len(game.market.tiles) == 3

    def test_goals_created_from_selection(self):
        game = SimulationMode(BOARD_1)
        actions = game.get_legal_actions()
        game.apply_action(actions[0])
        assert len(game.goals) == 3

    def test_selected_goals_match_action(self):
        game = SimulationMode(BOARD_1)
        action = game.get_legal_actions()[5]  # Pick a specific action
        selected_classes = [game.goal_options[i] for i in action.selected_goal_indices]

        game.apply_action(action)

        for i, goal in enumerate(game.goals):
            assert type(goal) == selected_classes[i]


class TestGoalSelectionCopy:
    def test_copy_during_goal_selection(self):
        game = SimulationMode(BOARD_1)
        game_copy = game.copy()

        assert game_copy.turn_phase == TurnPhase.GOAL_SELECTION
        assert len(game_copy.goal_options) == 4
        assert len(game_copy.goals) == 0

    def test_copy_shares_goal_options(self):
        game = SimulationMode(BOARD_1)
        game_copy = game.copy()

        # Goal options list is shared (immutable classes)
        assert game_copy.goal_options is game.goal_options

    def test_copy_is_independent(self):
        game = SimulationMode(BOARD_1)
        game_copy = game.copy()

        # Modify original
        actions = game.get_legal_actions()
        game.apply_action(actions[0])

        # Copy should be unchanged
        assert game_copy.turn_phase == TurnPhase.GOAL_SELECTION
        assert len(game_copy.goals) == 0

    def test_copy_after_selection(self):
        game = SimulationMode(BOARD_1)
        game.apply_action(game.get_legal_actions()[0])

        game_copy = game.copy()

        assert game_copy.turn_phase == TurnPhase.PLACE_TILE
        assert len(game_copy.goals) == 3
        assert len(game_copy.player.tiles) == 2
        assert game_copy.market is not None


class TestGoalSelectionActionHistory:
    def test_selection_recorded_in_history(self):
        game = SimulationMode(BOARD_1)
        action = game.get_legal_actions()[0]
        game.apply_action(action)

        history = game.get_action_history()
        assert len(history) == 1
        assert history[0].action_type == "select_goals"

    def test_full_game_includes_selection(self):
        game = SimulationMode(BOARD_1)
        game.play_random_game()

        history = game.get_action_history()
        assert history[0].action_type == "select_goals"


class TestPlayRandomGameWithGoalSelection:
    def test_random_game_completes(self):
        game = SimulationMode(BOARD_1)
        score = game.play_random_game()

        assert game.is_game_over()
        assert game.turn_phase == TurnPhase.GAME_OVER
        assert score >= 0

    def test_random_game_selects_goals_first(self):
        game = SimulationMode(BOARD_1)
        game.play_random_game()

        # First action should be goal selection
        history = game.get_action_history()
        assert history[0].action_type == "select_goals"
