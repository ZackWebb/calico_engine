"""
Tests for button scoring.
"""
import pytest
from source.hex_grid import HexGrid, Color, Pattern
from source.tile import Tile
from source.button import (
    find_color_groups, count_buttons_by_color, score_buttons,
    get_button_details, BUTTON_POINTS, RAINBOW_BUTTON_POINTS
)


class TestBasicButtonScoring:
    """Test basic button group detection."""

    def test_3_adjacent_same_color_scores_button(self):
        """3 adjacent tiles of same color should score 1 button."""
        grid = HexGrid()

        # Triangle of 3 BLUE tiles
        grid.set_tile(0, 0, 0, Tile(Color.BLUE, Pattern.DOTS))
        grid.set_tile(1, 0, -1, Tile(Color.BLUE, Pattern.LEAVES))
        grid.set_tile(0, 1, -1, Tile(Color.BLUE, Pattern.FLOWERS))

        groups = find_color_groups(grid, Color.BLUE, set())
        assert len(groups) == 1
        assert score_buttons(grid) == BUTTON_POINTS

    def test_2_adjacent_same_color_no_button(self):
        """Only 2 adjacent tiles should not score."""
        grid = HexGrid()

        grid.set_tile(0, 0, 0, Tile(Color.BLUE, Pattern.DOTS))
        grid.set_tile(1, 0, -1, Tile(Color.BLUE, Pattern.LEAVES))

        groups = find_color_groups(grid, Color.BLUE, set())
        assert len(groups) == 0
        assert score_buttons(grid) == 0

    def test_3_non_adjacent_same_color_no_button(self):
        """3 tiles of same color that don't touch should not score."""
        grid = HexGrid()

        grid.set_tile(0, 0, 0, Tile(Color.BLUE, Pattern.DOTS))
        grid.set_tile(2, 0, -2, Tile(Color.BLUE, Pattern.LEAVES))
        grid.set_tile(-2, 0, 2, Tile(Color.BLUE, Pattern.FLOWERS))

        groups = find_color_groups(grid, Color.BLUE, set())
        assert len(groups) == 0

    def test_mixed_colors_no_button(self):
        """3 adjacent tiles of different colors should not score."""
        grid = HexGrid()

        grid.set_tile(0, 0, 0, Tile(Color.BLUE, Pattern.DOTS))
        grid.set_tile(1, 0, -1, Tile(Color.PINK, Pattern.LEAVES))
        grid.set_tile(0, 1, -1, Tile(Color.GREEN, Pattern.FLOWERS))

        assert score_buttons(grid) == 0


class TestMultipleButtons:
    """Test multiple button group scoring."""

    def test_two_separate_groups_same_color(self):
        """Two separate groups of same color should score 2 buttons."""
        grid = HexGrid()

        # Cluster 1: BLUE around (0,0,0)
        grid.set_tile(0, 0, 0, Tile(Color.BLUE, Pattern.DOTS))
        grid.set_tile(1, 0, -1, Tile(Color.BLUE, Pattern.LEAVES))
        grid.set_tile(0, 1, -1, Tile(Color.BLUE, Pattern.FLOWERS))

        # Cluster 2: BLUE far away (not adjacent)
        grid.set_tile(3, -3, 0, Tile(Color.BLUE, Pattern.STRIPES))
        grid.set_tile(3, -2, -1, Tile(Color.BLUE, Pattern.CLUBS))
        grid.set_tile(2, -2, 0, Tile(Color.BLUE, Pattern.SWIRLS))

        groups = find_color_groups(grid, Color.BLUE, set())
        assert len(groups) == 2
        assert score_buttons(grid) == BUTTON_POINTS * 2

    def test_adjacent_groups_same_color_scores_once(self):
        """6 touching tiles of same color (2 groups without separation) scores only once."""
        grid = HexGrid()

        # 6 BLUE tiles touching each other
        grid.set_tile(0, 0, 0, Tile(Color.BLUE, Pattern.DOTS))
        grid.set_tile(1, 0, -1, Tile(Color.BLUE, Pattern.LEAVES))
        grid.set_tile(0, 1, -1, Tile(Color.BLUE, Pattern.FLOWERS))
        grid.set_tile(1, 1, -2, Tile(Color.BLUE, Pattern.STRIPES))
        grid.set_tile(-1, 1, 0, Tile(Color.BLUE, Pattern.CLUBS))
        grid.set_tile(0, 2, -2, Tile(Color.BLUE, Pattern.SWIRLS))

        groups = find_color_groups(grid, Color.BLUE, set())
        # Should only find 1 group because second group would be adjacent
        assert len(groups) == 1
        assert score_buttons(grid) == BUTTON_POINTS

    def test_different_colors_can_touch(self):
        """Groups of different colors can be adjacent."""
        grid = HexGrid()

        # 3 BLUE tiles
        grid.set_tile(0, 0, 0, Tile(Color.BLUE, Pattern.DOTS))
        grid.set_tile(1, 0, -1, Tile(Color.BLUE, Pattern.LEAVES))
        grid.set_tile(0, 1, -1, Tile(Color.BLUE, Pattern.FLOWERS))

        # 3 PINK tiles adjacent to the blue group
        grid.set_tile(-1, 0, 1, Tile(Color.PINK, Pattern.DOTS))
        grid.set_tile(-1, 1, 0, Tile(Color.PINK, Pattern.LEAVES))
        grid.set_tile(-2, 1, 1, Tile(Color.PINK, Pattern.FLOWERS))

        button_counts = count_buttons_by_color(grid)
        assert button_counts[Color.BLUE] == 1
        assert button_counts[Color.PINK] == 1
        assert score_buttons(grid) == BUTTON_POINTS * 2


class TestRainbowButton:
    """Test rainbow button bonus."""

    def test_no_rainbow_with_missing_color(self):
        """No rainbow button if any color is missing."""
        grid = HexGrid()

        # Only set up 5 colors (missing one)
        colors = [Color.BLUE, Color.PINK, Color.GREEN, Color.YELLOW, Color.PURPLE]
        positions = [
            [(0, 0, 0), (1, 0, -1), (0, 1, -1)],
            [(2, 0, -2), (2, 1, -3), (3, 0, -3)],
            [(-2, 0, 2), (-2, 1, 1), (-1, 0, 1)],
            [(0, -2, 2), (1, -2, 1), (0, -1, 1)],
            [(2, -2, 0), (2, -1, -1), (3, -2, -1)],
        ]

        for color, pos_list in zip(colors, positions):
            for pos in pos_list:
                grid.set_tile(*pos, Tile(color, Pattern.DOTS))

        details = get_button_details(grid)
        assert details['has_rainbow'] == False
        assert details['rainbow_score'] == 0

    def test_rainbow_with_all_colors(self):
        """Rainbow button awarded when all 6 colors have at least one button."""
        grid = HexGrid()

        # Set up all 6 colors with button groups
        # Use valid positions that are far enough apart
        colors = list(Color)
        base_positions = [
            [(0, 0, 0), (1, 0, -1), (0, 1, -1)],           # center
            [(2, 0, -2), (2, 1, -3), (3, 0, -3)],          # right
            [(-2, 0, 2), (-2, 1, 1), (-1, 0, 1)],          # left
            [(0, -2, 2), (1, -2, 1), (0, -1, 1)],          # bottom
            [(2, -2, 0), (2, -1, -1), (3, -2, -1)],        # bottom right
            [(-2, 2, 0), (-2, 3, -1), (-1, 2, -1)],        # top left
        ]

        for color, pos_list in zip(colors, base_positions):
            for pos in pos_list:
                grid.set_tile(*pos, Tile(color, Pattern.DOTS))

        details = get_button_details(grid)
        assert details['has_rainbow'] == True
        assert details['rainbow_score'] == RAINBOW_BUTTON_POINTS
        expected_total = 6 * BUTTON_POINTS + RAINBOW_BUTTON_POINTS
        assert details['total_score'] == expected_total


class TestEdgeTiles:
    """Test that edge tiles count toward button scoring."""

    def test_edge_tiles_contribute_to_buttons(self):
        """Pre-placed edge tiles should count toward button groups."""
        grid = HexGrid()

        # From BOARD_1, position (-1, 4, -3) has YELLOW STRIPES
        # Place 2 more YELLOW tiles adjacent to it
        grid.set_tile(-1, 4, -3, Tile(Color.YELLOW, Pattern.STRIPES))
        grid.set_tile(-2, 4, -2, Tile(Color.YELLOW, Pattern.DOTS))
        grid.set_tile(0, 3, -3, Tile(Color.YELLOW, Pattern.LEAVES))

        groups = find_color_groups(grid, Color.YELLOW, set())
        assert len(groups) == 1


class TestButtonDetails:
    """Test the get_button_details function."""

    def test_details_structure(self):
        """Test that details dict has all expected keys."""
        grid = HexGrid()

        grid.set_tile(0, 0, 0, Tile(Color.BLUE, Pattern.DOTS))
        grid.set_tile(1, 0, -1, Tile(Color.BLUE, Pattern.LEAVES))
        grid.set_tile(0, 1, -1, Tile(Color.BLUE, Pattern.FLOWERS))

        details = get_button_details(grid)

        assert 'buttons_by_color' in details
        assert 'total_buttons' in details
        assert 'button_score' in details
        assert 'has_rainbow' in details
        assert 'rainbow_score' in details
        assert 'total_score' in details

        assert details['total_buttons'] == 1
        assert details['button_score'] == BUTTON_POINTS
        assert details['buttons_by_color'][Color.BLUE] == 1

    def test_empty_grid_details(self):
        """Test details for empty grid."""
        grid = HexGrid()

        details = get_button_details(grid)
        assert details['total_buttons'] == 0
        assert details['button_score'] == 0
        assert details['has_rainbow'] == False
        assert details['total_score'] == 0


class TestButtonScoringVerbose:
    """Verbose tests for manual verification."""

    def test_complex_board_scoring(self):
        """Test a complex board with multiple color groups."""
        grid = HexGrid()

        # 2 BLUE button groups (separated)
        grid.set_tile(0, 0, 0, Tile(Color.BLUE, Pattern.DOTS))
        grid.set_tile(1, 0, -1, Tile(Color.BLUE, Pattern.LEAVES))
        grid.set_tile(0, 1, -1, Tile(Color.BLUE, Pattern.FLOWERS))

        grid.set_tile(3, -3, 0, Tile(Color.BLUE, Pattern.STRIPES))
        grid.set_tile(3, -2, -1, Tile(Color.BLUE, Pattern.CLUBS))
        grid.set_tile(2, -2, 0, Tile(Color.BLUE, Pattern.SWIRLS))

        # 1 PINK button group
        grid.set_tile(-2, 0, 2, Tile(Color.PINK, Pattern.DOTS))
        grid.set_tile(-2, 1, 1, Tile(Color.PINK, Pattern.LEAVES))
        grid.set_tile(-1, 0, 1, Tile(Color.PINK, Pattern.FLOWERS))

        details = get_button_details(grid)

        print(f"\nComplex board button scoring:")
        print(f"  BLUE buttons: {details['buttons_by_color'][Color.BLUE]}")
        print(f"  PINK buttons: {details['buttons_by_color'][Color.PINK]}")
        print(f"  Total buttons: {details['total_buttons']}")
        print(f"  Button score: {details['button_score']}")
        print(f"  Has rainbow: {details['has_rainbow']}")
        print(f"  Total score: {details['total_score']}")

        assert details['buttons_by_color'][Color.BLUE] == 2
        assert details['buttons_by_color'][Color.PINK] == 1
        assert details['total_buttons'] == 3
        assert details['total_score'] == 9  # 3 buttons * 3 pts each
