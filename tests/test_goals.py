import pytest
from source.goal import GoalAAA_BBB, GoalAA_BB_CC, GoalAllUnique, create_default_goals
from source.hex_grid import HexGrid
from source.tile import Tile, Color, Pattern


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

    def test_color_3_3_scores_7(self):
        # 3 blue, 3 pink - satisfies color condition only
        neighbors = self.get_neighbor_positions()
        for i, pos in enumerate(neighbors):
            color = Color.BLUE if i < 3 else Color.PINK
            pattern = Pattern(i + 1)  # All different patterns
            self.grid.set_tile(*pos, Tile(color, pattern))
        assert self.goal.score(self.grid) == 7

    def test_pattern_3_3_scores_7(self):
        # All different colors, but 3 dots and 3 leaves
        neighbors = self.get_neighbor_positions()
        colors = list(Color)[:6]
        for i, pos in enumerate(neighbors):
            pattern = Pattern.DOTS if i < 3 else Pattern.LEAVES
            self.grid.set_tile(*pos, Tile(colors[i], pattern))
        assert self.goal.score(self.grid) == 7

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


class TestGameModeGoalIntegration:
    """Test goals integrate correctly with game modes."""

    def test_simulation_mode_has_goals(self):
        from source.simulation_mode import SimulationMode
        from source.board_configurations import BOARD_1

        game = SimulationMode(BOARD_1)
        assert len(game.goals) == 3

    def test_play_mode_has_goals(self):
        from source.play_mode import PlayMode
        from source.board_configurations import BOARD_1

        game = PlayMode(BOARD_1)
        assert len(game.goals) == 3

    def test_final_score_includes_goals(self):
        from source.simulation_mode import SimulationMode
        from source.board_configurations import BOARD_1

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
        from source.simulation_mode import SimulationMode
        from source.board_configurations import BOARD_1

        game = SimulationMode(BOARD_1)
        empty_positions = game.player.grid.get_empty_positions()

        # Should be 22 empty spaces (25 - 3 goals)
        # Note: BOARD_1 has 22 pre-filled tiles, total grid ~47 positions
        # So empty should be 47 - 22 - 3 = 22
        assert len(empty_positions) == 22
