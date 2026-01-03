import pytest
import sys
import os

# Add source directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'source'))

from goal import (
    GoalAAA_BBB, GoalAA_BB_CC, GoalAllUnique,
    GoalAAAA_BB, GoalAA_BB_C_D, GoalAAA_BB_C,
    create_default_goals, create_random_goals, ALL_GOAL_CLASSES
)
from hex_grid import HexGrid
from tile import Tile, Color, Pattern
from game_state import TurnPhase


def complete_goal_selection(game):
    """Helper to complete goal selection phase and transition to tile placement."""
    if game.turn_phase == TurnPhase.GOAL_SELECTION:
        actions = game.get_legal_actions()
        game.apply_action(actions[0])
    return game


class TestGoalAAA_BBB:
    """Test the AAA-BBB goal (3 of one type, 3 of another)."""

    def setup_method(self):
        self.grid = HexGrid()
        self.goal = GoalAAA_BBB((-2, 1, 1))

    def get_neighbor_positions(self):
        """Get the 6 neighbors of the goal position."""
        return self.grid.get_neighbors(-2, 1, 1)

    def test_no_neighbors_scores_zero(self):
        # Empty grid
        assert self.goal.score(self.grid) == 0

    def test_partial_neighbors_scores_zero(self):
        # Only fill 3 neighbors
        neighbors = self.get_neighbor_positions()
        for i, pos in enumerate(neighbors[:3]):
            self.grid.set_tile(*pos, Tile(Color.BLUE, Pattern.DOTS))
        assert self.goal.score(self.grid) == 0

    def test_color_3_3_scores_8(self):
        # 3 blue, 3 pink - satisfies color condition only
        neighbors = self.get_neighbor_positions()
        for i, pos in enumerate(neighbors):
            color = Color.BLUE if i < 3 else Color.PINK
            pattern = Pattern(i + 1)  # All different patterns
            self.grid.set_tile(*pos, Tile(color, pattern))
        assert self.goal.score(self.grid) == 8

    def test_pattern_3_3_scores_8(self):
        # All different colors, but 3 dots and 3 leaves
        neighbors = self.get_neighbor_positions()
        colors = list(Color)[:6]
        for i, pos in enumerate(neighbors):
            pattern = Pattern.DOTS if i < 3 else Pattern.LEAVES
            self.grid.set_tile(*pos, Tile(colors[i], pattern))
        assert self.goal.score(self.grid) == 8

    def test_both_conditions_scores_13(self):
        # 3 blue dots, 3 pink leaves
        neighbors = self.get_neighbor_positions()
        for i, pos in enumerate(neighbors):
            if i < 3:
                self.grid.set_tile(*pos, Tile(Color.BLUE, Pattern.DOTS))
            else:
                self.grid.set_tile(*pos, Tile(Color.PINK, Pattern.LEAVES))
        assert self.goal.score(self.grid) == 13

    def test_wrong_distribution_scores_zero(self):
        # 4-2 split doesn't count
        neighbors = self.get_neighbor_positions()
        for i, pos in enumerate(neighbors):
            color = Color.BLUE if i < 4 else Color.PINK
            self.grid.set_tile(*pos, Tile(color, Pattern(i + 1)))
        assert self.goal.score(self.grid) == 0


class TestGoalAA_BB_CC:
    """Test the AA-BB-CC goal (2 each of 3 types)."""

    def setup_method(self):
        self.grid = HexGrid()
        self.goal = GoalAA_BB_CC((1, -1, 0))

    def get_neighbor_positions(self):
        return self.grid.get_neighbors(1, -1, 0)

    def test_no_neighbors_scores_zero(self):
        assert self.goal.score(self.grid) == 0

    def test_color_2_2_2_scores_7(self):
        # 2 blue, 2 pink, 2 green
        neighbors = self.get_neighbor_positions()
        colors = [Color.BLUE, Color.BLUE, Color.PINK, Color.PINK, Color.GREEN, Color.GREEN]
        for i, pos in enumerate(neighbors):
            pattern = Pattern(i + 1)  # All different patterns
            self.grid.set_tile(*pos, Tile(colors[i], pattern))
        assert self.goal.score(self.grid) == 7

    def test_pattern_2_2_2_scores_7(self):
        # All different colors, 2 dots, 2 leaves, 2 flowers
        neighbors = self.get_neighbor_positions()
        colors = list(Color)[:6]
        patterns = [Pattern.DOTS, Pattern.DOTS, Pattern.LEAVES, Pattern.LEAVES,
                   Pattern.FLOWERS, Pattern.FLOWERS]
        for i, pos in enumerate(neighbors):
            self.grid.set_tile(*pos, Tile(colors[i], patterns[i]))
        assert self.goal.score(self.grid) == 7

    def test_both_conditions_scores_11(self):
        # 2 blue dots, 2 pink leaves, 2 green flowers
        neighbors = self.get_neighbor_positions()
        tiles = [
            (Color.BLUE, Pattern.DOTS), (Color.BLUE, Pattern.DOTS),
            (Color.PINK, Pattern.LEAVES), (Color.PINK, Pattern.LEAVES),
            (Color.GREEN, Pattern.FLOWERS), (Color.GREEN, Pattern.FLOWERS),
        ]
        for i, pos in enumerate(neighbors):
            self.grid.set_tile(*pos, Tile(*tiles[i]))
        assert self.goal.score(self.grid) == 11

    def test_wrong_distribution_scores_zero(self):
        # 3-2-1 split doesn't count
        neighbors = self.get_neighbor_positions()
        colors = [Color.BLUE, Color.BLUE, Color.BLUE, Color.PINK, Color.PINK, Color.GREEN]
        for i, pos in enumerate(neighbors):
            self.grid.set_tile(*pos, Tile(colors[i], Pattern(i + 1)))
        assert self.goal.score(self.grid) == 0


class TestGoalAllUnique:
    """Test the All Unique goal (6 different colors or patterns)."""

    def setup_method(self):
        self.grid = HexGrid()
        self.goal = GoalAllUnique((0, 1, -1))

    def get_neighbor_positions(self):
        return self.grid.get_neighbors(0, 1, -1)

    def test_no_neighbors_scores_zero(self):
        assert self.goal.score(self.grid) == 0

    def test_unique_colors_scores_10(self):
        # 6 different colors, same pattern
        neighbors = self.get_neighbor_positions()
        colors = list(Color)[:6]
        for i, pos in enumerate(neighbors):
            self.grid.set_tile(*pos, Tile(colors[i], Pattern.DOTS))
        assert self.goal.score(self.grid) == 10

    def test_unique_patterns_scores_10(self):
        # Same color, 6 different patterns
        neighbors = self.get_neighbor_positions()
        patterns = list(Pattern)[:6]
        for i, pos in enumerate(neighbors):
            self.grid.set_tile(*pos, Tile(Color.BLUE, patterns[i]))
        assert self.goal.score(self.grid) == 10

    def test_both_unique_scores_15(self):
        # 6 different colors AND 6 different patterns
        neighbors = self.get_neighbor_positions()
        colors = list(Color)[:6]
        patterns = list(Pattern)[:6]
        for i, pos in enumerate(neighbors):
            self.grid.set_tile(*pos, Tile(colors[i], patterns[i]))
        assert self.goal.score(self.grid) == 15

    def test_duplicate_color_with_unique_pattern_scores_10(self):
        # 5 different colors (one duplicate), 6 different patterns
        neighbors = self.get_neighbor_positions()
        colors = [Color.BLUE, Color.PINK, Color.GREEN, Color.YELLOW, Color.PURPLE, Color.BLUE]
        patterns = list(Pattern)[:6]
        for i, pos in enumerate(neighbors):
            self.grid.set_tile(*pos, Tile(colors[i], patterns[i]))
        assert self.goal.score(self.grid) == 10  # Only pattern condition met

    def test_all_same_scores_zero(self):
        # All same color and pattern
        neighbors = self.get_neighbor_positions()
        for pos in neighbors:
            self.grid.set_tile(*pos, Tile(Color.BLUE, Pattern.DOTS))
        assert self.goal.score(self.grid) == 0


class TestGoalAAAA_BB:
    """Test the AAAA-BB goal (4 of one type, 2 of another)."""

    def setup_method(self):
        self.grid = HexGrid()
        self.goal = GoalAAAA_BB((-2, 1, 1))

    def get_neighbor_positions(self):
        """Get the 6 neighbors of the goal position."""
        return self.grid.get_neighbors(-2, 1, 1)

    def test_no_neighbors_scores_zero(self):
        # Empty grid
        assert self.goal.score(self.grid) == 0

    def test_partial_neighbors_scores_zero(self):
        # Only fill 4 neighbors
        neighbors = self.get_neighbor_positions()
        for i, pos in enumerate(neighbors[:4]):
            self.grid.set_tile(*pos, Tile(Color.BLUE, Pattern.DOTS))
        assert self.goal.score(self.grid) == 0

    def test_color_4_2_scores_7(self):
        # 4 blue, 2 pink - satisfies color condition only
        neighbors = self.get_neighbor_positions()
        for i, pos in enumerate(neighbors):
            color = Color.BLUE if i < 4 else Color.PINK
            pattern = Pattern(i + 1)  # All different patterns
            self.grid.set_tile(*pos, Tile(color, pattern))
        assert self.goal.score(self.grid) == 7

    def test_pattern_4_2_scores_7(self):
        # All different colors, but 4 dots and 2 leaves
        neighbors = self.get_neighbor_positions()
        colors = list(Color)[:6]
        for i, pos in enumerate(neighbors):
            pattern = Pattern.DOTS if i < 4 else Pattern.LEAVES
            self.grid.set_tile(*pos, Tile(colors[i], pattern))
        assert self.goal.score(self.grid) == 7

    def test_both_conditions_scores_14(self):
        # 4 blue dots, 2 pink leaves
        neighbors = self.get_neighbor_positions()
        for i, pos in enumerate(neighbors):
            if i < 4:
                self.grid.set_tile(*pos, Tile(Color.BLUE, Pattern.DOTS))
            else:
                self.grid.set_tile(*pos, Tile(Color.PINK, Pattern.LEAVES))
        assert self.goal.score(self.grid) == 14

    def test_wrong_distribution_3_3_scores_zero(self):
        # 3-3 split doesn't count for this goal
        neighbors = self.get_neighbor_positions()
        for i, pos in enumerate(neighbors):
            color = Color.BLUE if i < 3 else Color.PINK
            self.grid.set_tile(*pos, Tile(color, Pattern(i + 1)))
        assert self.goal.score(self.grid) == 0

    def test_wrong_distribution_5_1_scores_zero(self):
        # 5-1 split doesn't count
        neighbors = self.get_neighbor_positions()
        for i, pos in enumerate(neighbors):
            color = Color.BLUE if i < 5 else Color.PINK
            self.grid.set_tile(*pos, Tile(color, Pattern(i + 1)))
        assert self.goal.score(self.grid) == 0


class TestGoalAA_BB_C_D:
    """Test the AA-BB-C-D goal (2-2-1-1 distribution)."""

    def setup_method(self):
        self.grid = HexGrid()
        self.goal = GoalAA_BB_C_D((1, -1, 0))

    def get_neighbor_positions(self):
        return self.grid.get_neighbors(1, -1, 0)

    def test_no_neighbors_scores_zero(self):
        assert self.goal.score(self.grid) == 0

    def test_color_2_2_1_1_scores_5(self):
        # 2 blue, 2 pink, 1 green, 1 yellow
        neighbors = self.get_neighbor_positions()
        colors = [Color.BLUE, Color.BLUE, Color.PINK, Color.PINK, Color.GREEN, Color.YELLOW]
        for i, pos in enumerate(neighbors):
            pattern = Pattern(i + 1)  # All different patterns
            self.grid.set_tile(*pos, Tile(colors[i], pattern))
        assert self.goal.score(self.grid) == 5

    def test_pattern_2_2_1_1_scores_5(self):
        # All different colors, 2 dots, 2 leaves, 1 flowers, 1 stripes
        neighbors = self.get_neighbor_positions()
        colors = list(Color)[:6]
        patterns = [Pattern.DOTS, Pattern.DOTS, Pattern.LEAVES, Pattern.LEAVES,
                    Pattern.FLOWERS, Pattern.STRIPES]
        for i, pos in enumerate(neighbors):
            self.grid.set_tile(*pos, Tile(colors[i], patterns[i]))
        assert self.goal.score(self.grid) == 5

    def test_both_conditions_scores_7(self):
        # 2 blue dots, 2 pink leaves, 1 green flowers, 1 yellow stripes
        neighbors = self.get_neighbor_positions()
        tiles = [
            (Color.BLUE, Pattern.DOTS), (Color.BLUE, Pattern.DOTS),
            (Color.PINK, Pattern.LEAVES), (Color.PINK, Pattern.LEAVES),
            (Color.GREEN, Pattern.FLOWERS), (Color.YELLOW, Pattern.STRIPES),
        ]
        for i, pos in enumerate(neighbors):
            self.grid.set_tile(*pos, Tile(*tiles[i]))
        assert self.goal.score(self.grid) == 7

    def test_wrong_distribution_2_2_2_scores_zero(self):
        # 2-2-2 split doesn't count for this goal
        neighbors = self.get_neighbor_positions()
        colors = [Color.BLUE, Color.BLUE, Color.PINK, Color.PINK, Color.GREEN, Color.GREEN]
        for i, pos in enumerate(neighbors):
            self.grid.set_tile(*pos, Tile(colors[i], Pattern(i + 1)))
        assert self.goal.score(self.grid) == 0

    def test_wrong_distribution_3_2_1_scores_zero(self):
        # 3-2-1 split doesn't count for this goal
        neighbors = self.get_neighbor_positions()
        colors = [Color.BLUE, Color.BLUE, Color.BLUE, Color.PINK, Color.PINK, Color.GREEN]
        for i, pos in enumerate(neighbors):
            self.grid.set_tile(*pos, Tile(colors[i], Pattern(i + 1)))
        assert self.goal.score(self.grid) == 0


class TestGoalAAA_BB_C:
    """Test the AAA-BB-C goal (3-2-1 distribution)."""

    def setup_method(self):
        self.grid = HexGrid()
        self.goal = GoalAAA_BB_C((0, 1, -1))

    def get_neighbor_positions(self):
        return self.grid.get_neighbors(0, 1, -1)

    def test_no_neighbors_scores_zero(self):
        assert self.goal.score(self.grid) == 0

    def test_color_3_2_1_scores_7(self):
        # 3 blue, 2 pink, 1 green
        neighbors = self.get_neighbor_positions()
        colors = [Color.BLUE, Color.BLUE, Color.BLUE, Color.PINK, Color.PINK, Color.GREEN]
        for i, pos in enumerate(neighbors):
            pattern = Pattern(i + 1)  # All different patterns
            self.grid.set_tile(*pos, Tile(colors[i], pattern))
        assert self.goal.score(self.grid) == 7

    def test_pattern_3_2_1_scores_7(self):
        # All different colors, 3 dots, 2 leaves, 1 flowers
        neighbors = self.get_neighbor_positions()
        colors = list(Color)[:6]
        patterns = [Pattern.DOTS, Pattern.DOTS, Pattern.DOTS,
                    Pattern.LEAVES, Pattern.LEAVES, Pattern.FLOWERS]
        for i, pos in enumerate(neighbors):
            self.grid.set_tile(*pos, Tile(colors[i], patterns[i]))
        assert self.goal.score(self.grid) == 7

    def test_both_conditions_scores_11(self):
        # 3 blue dots, 2 pink leaves, 1 green flowers
        neighbors = self.get_neighbor_positions()
        tiles = [
            (Color.BLUE, Pattern.DOTS), (Color.BLUE, Pattern.DOTS), (Color.BLUE, Pattern.DOTS),
            (Color.PINK, Pattern.LEAVES), (Color.PINK, Pattern.LEAVES),
            (Color.GREEN, Pattern.FLOWERS),
        ]
        for i, pos in enumerate(neighbors):
            self.grid.set_tile(*pos, Tile(*tiles[i]))
        assert self.goal.score(self.grid) == 11

    def test_wrong_distribution_3_3_scores_zero(self):
        # 3-3 split doesn't count for this goal
        neighbors = self.get_neighbor_positions()
        colors = [Color.BLUE, Color.BLUE, Color.BLUE, Color.PINK, Color.PINK, Color.PINK]
        for i, pos in enumerate(neighbors):
            self.grid.set_tile(*pos, Tile(colors[i], Pattern(i + 1)))
        assert self.goal.score(self.grid) == 0

    def test_wrong_distribution_4_2_scores_zero(self):
        # 4-2 split doesn't count for this goal
        neighbors = self.get_neighbor_positions()
        colors = [Color.BLUE, Color.BLUE, Color.BLUE, Color.BLUE, Color.PINK, Color.PINK]
        for i, pos in enumerate(neighbors):
            self.grid.set_tile(*pos, Tile(colors[i], Pattern(i + 1)))
        assert self.goal.score(self.grid) == 0

    def test_wrong_distribution_2_2_2_scores_zero(self):
        # 2-2-2 split doesn't count for this goal
        neighbors = self.get_neighbor_positions()
        colors = [Color.BLUE, Color.BLUE, Color.PINK, Color.PINK, Color.GREEN, Color.GREEN]
        for i, pos in enumerate(neighbors):
            self.grid.set_tile(*pos, Tile(colors[i], Pattern(i + 1)))
        assert self.goal.score(self.grid) == 0


class TestGoalPositions:
    """Test that goal positions are handled correctly."""

    def test_goal_positions_removed_from_grid(self):
        from source.board_configurations import GOAL_POSITIONS
        grid = HexGrid()
        grid.set_goal_positions(GOAL_POSITIONS)

        # Goal positions should not be in the grid
        for pos in GOAL_POSITIONS:
            assert pos not in grid.grid

    def test_goal_positions_not_in_empty_positions(self):
        from source.board_configurations import GOAL_POSITIONS
        grid = HexGrid()
        grid.set_goal_positions(GOAL_POSITIONS)

        empty = grid.get_empty_positions()
        for pos in GOAL_POSITIONS:
            assert pos not in empty

    def test_is_goal_position(self):
        from source.board_configurations import GOAL_POSITIONS
        grid = HexGrid()
        grid.set_goal_positions(GOAL_POSITIONS)

        for pos in GOAL_POSITIONS:
            assert grid.is_goal_position(*pos)

        # Non-goal position
        assert not grid.is_goal_position(0, 0, 0)


class TestCreateDefaultGoals:
    """Test the default goal factory function."""

    def test_creates_three_goals(self):
        goals = create_default_goals()
        assert len(goals) == 3

    def test_correct_goal_types(self):
        goals = create_default_goals()
        types = [type(g).__name__ for g in goals]
        assert "GoalAAA_BBB" in types
        assert "GoalAA_BB_CC" in types
        assert "GoalAllUnique" in types

    def test_correct_positions(self):
        goals = create_default_goals()
        positions = {g.position for g in goals}
        assert (-2, 1, 1) in positions
        assert (1, -1, 0) in positions
        assert (0, 1, -1) in positions


class TestCreateRandomGoals:
    """Test the random goal selection function."""

    def test_creates_three_goals(self):
        goals = create_random_goals()
        assert len(goals) == 3

    def test_goals_are_unique_types(self):
        # Run multiple times to check randomness doesn't repeat types
        for _ in range(10):
            goals = create_random_goals()
            types = [type(g).__name__ for g in goals]
            assert len(types) == len(set(types)), "Goal types should be unique"

    def test_uses_default_positions(self):
        from source.board_configurations import GOAL_POSITIONS
        goals = create_random_goals()
        positions = {g.position for g in goals}
        assert positions == set(GOAL_POSITIONS)

    def test_all_goals_from_valid_classes(self):
        for _ in range(20):  # Multiple runs to check randomness
            goals = create_random_goals()
            for goal in goals:
                assert type(goal) in ALL_GOAL_CLASSES

    def test_randomness_provides_variety_in_types(self):
        # Run many times and verify we see different goal type combinations
        seen_combinations = set()
        for _ in range(50):
            goals = create_random_goals()
            combo = tuple(sorted(type(g).__name__ for g in goals))
            seen_combinations.add(combo)
        # With 6 choose 3 = 20 possible combinations, we should see many different ones
        assert len(seen_combinations) > 5, "Should see variety in random type selections"

    def test_randomness_provides_variety_in_arrangements(self):
        # Run many times and verify we see different position arrangements
        seen_arrangements = set()
        for _ in range(50):
            goals = create_random_goals()
            # Track which goal type is at which position
            arrangement = tuple((type(g).__name__, g.position) for g in goals)
            seen_arrangements.add(arrangement)
        # Should see variety in how goals are arranged on positions
        assert len(seen_arrangements) > 10, "Should see variety in position arrangements"


class TestAllGoalClasses:
    """Test the ALL_GOAL_CLASSES list."""

    def test_contains_all_six_goal_types(self):
        assert len(ALL_GOAL_CLASSES) == 6
        class_names = [c.__name__ for c in ALL_GOAL_CLASSES]
        assert "GoalAAA_BBB" in class_names
        assert "GoalAA_BB_CC" in class_names
        assert "GoalAllUnique" in class_names
        assert "GoalAAAA_BB" in class_names
        assert "GoalAA_BB_C_D" in class_names
        assert "GoalAAA_BB_C" in class_names


class TestGameModeGoalIntegration:
    """Test goals integrate correctly with game modes."""

    def test_simulation_mode_has_goals(self):
        from simulation_mode import SimulationMode
        from board_configurations import BOARD_1

        game = SimulationMode(BOARD_1)
        complete_goal_selection(game)
        assert len(game.goals) == 3

    def test_play_mode_has_goals(self):
        from play_mode import PlayMode
        from board_configurations import BOARD_1

        game = PlayMode(BOARD_1)
        complete_goal_selection(game)
        assert len(game.goals) == 3

    def test_final_score_includes_goals(self):
        from simulation_mode import SimulationMode
        from board_configurations import BOARD_1

        game = SimulationMode(BOARD_1)
        # Play a complete game
        game.play_random_game()

        # Score should include cats, goals, and buttons
        cat_scores = game.get_cat_scores()
        goal_scores = game.get_goal_scores()
        button_scores = game.get_button_scores()
        total = game.get_final_score()

        expected = sum(cat_scores.values()) + sum(goal_scores.values()) + button_scores['total_score']
        assert total == expected

    def test_empty_positions_reduced_by_goals(self):
        from simulation_mode import SimulationMode
        from board_configurations import BOARD_1

        game = SimulationMode(BOARD_1)
        empty_positions = game.player.grid.get_empty_positions()

        # Should be 22 empty spaces (25 - 3 goals)
        # Note: BOARD_1 has 22 pre-filled tiles, total grid ~47 positions
        # So empty should be 47 - 22 - 3 = 22
        assert len(empty_positions) == 22
