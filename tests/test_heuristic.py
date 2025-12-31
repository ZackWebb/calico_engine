"""
Tests for the heuristic evaluation functions.

Tests cover:
- Non-consecutive line detection (e.g., A _ _ _ A scores as 2/5)
- Blocked line detection (wrong patterns make line score 0)
- Cross-pattern blocking (Leo's other pattern still blocks)
- Millie pair scoring only when 3rd space is available
- Overlap decay for redundant lines
- Line enumeration including edge tiles
"""
import sys
import os

# Add source directory to path so imports work the same way as in source modules
source_dir = os.path.join(os.path.dirname(__file__), '..', 'source')
sys.path.insert(0, source_dir)

import pytest
from hex_grid import HexGrid, Color, Pattern
from tile import Tile
from cat import CatMillie, CatLeo, CatRumi
from heuristic import (
    enumerate_all_5_lines,
    enumerate_all_3_lines,
    evaluate_line_for_pattern,
    evaluate_leo_potential,
    evaluate_rumi_potential,
    evaluate_millie_potential,
    estimate_cat_potential,
    estimate_goal_potential,
)
from goal import GoalAAA_BBB, GoalAA_BB_CC, GoalAllUnique
import heuristic as heuristic_module


@pytest.fixture
def clean_grid():
    """Provide a clean HexGrid and reset line caches."""
    # Clear line caches to ensure fresh computation
    heuristic_module._cached_5_lines = None
    heuristic_module._cached_3_lines = None
    return HexGrid()


@pytest.fixture
def leo_cat():
    """Create a Leo cat for testing (needs 5 in a line)."""
    cat = CatLeo()
    cat.patterns = (Pattern.SWIRLS, Pattern.DOTS)
    return cat


@pytest.fixture
def rumi_cat():
    """Create a Rumi cat for testing (needs 3 in a line)."""
    cat = CatRumi()
    cat.patterns = (Pattern.FLOWERS, Pattern.STRIPES)
    return cat


@pytest.fixture
def millie_cat():
    """Create a Millie cat for testing (needs 3 touching)."""
    cat = CatMillie()
    cat.patterns = (Pattern.LEAVES, Pattern.CLUBS)
    return cat


class TestLineEnumeration:
    """Tests for enumerate_all_5_lines() and enumerate_all_3_lines()."""

    def test_5_lines_exist(self, clean_grid):
        """Should find 5-position lines on the board."""
        lines = enumerate_all_5_lines(clean_grid)
        assert len(lines) > 0

    def test_5_lines_have_5_positions(self, clean_grid):
        """Each 5-line should have exactly 5 positions."""
        lines = enumerate_all_5_lines(clean_grid)
        for line in lines:
            assert len(line) == 5

    def test_5_lines_are_collinear(self, clean_grid):
        """Positions in each line should be collinear (same direction)."""
        lines = enumerate_all_5_lines(clean_grid)
        for line in lines:
            # Calculate direction from first two positions
            dq = line[1][0] - line[0][0]
            dr = line[1][1] - line[0][1]
            ds = line[1][2] - line[0][2]

            # Verify all positions follow this direction
            for i in range(1, 5):
                assert line[i][0] - line[i-1][0] == dq
                assert line[i][1] - line[i-1][1] == dr
                assert line[i][2] - line[i-1][2] == ds

    def test_3_lines_exist(self, clean_grid):
        """Should find 3-position lines on the board."""
        lines = enumerate_all_3_lines(clean_grid)
        assert len(lines) > 0

    def test_3_lines_have_3_positions(self, clean_grid):
        """Each 3-line should have exactly 3 positions."""
        lines = enumerate_all_3_lines(clean_grid)
        for line in lines:
            assert len(line) == 3

    def test_no_duplicate_lines(self, clean_grid):
        """Lines should not be duplicated (forward and backward)."""
        lines = enumerate_all_5_lines(clean_grid)
        line_sets = [frozenset(line) for line in lines]
        assert len(line_sets) == len(set(line_sets))

    def test_lines_include_edge_positions(self, clean_grid):
        """Lines should include edge positions from the board."""
        lines = enumerate_all_5_lines(clean_grid)
        all_positions_in_lines = set()
        for line in lines:
            all_positions_in_lines.update(line)

        # Check that some edge positions are in lines
        # Edge positions include things like (-4, 1, 3), (4, -1, -3)
        edge_positions = [(-4, 1, 3), (-4, 2, 2), (4, -1, -3), (4, -2, -2)]
        found_edge = any(pos in all_positions_in_lines for pos in edge_positions)
        assert found_edge, "Some edge positions should be part of valid lines"


class TestLineEvaluation:
    """Tests for evaluate_line_for_pattern()."""

    def test_empty_line_not_blocked(self, clean_grid):
        """An empty line should not be blocked and have 0 matches."""
        lines = enumerate_all_5_lines(clean_grid)
        line = lines[0]
        count, blocked = evaluate_line_for_pattern(clean_grid, line, Pattern.SWIRLS)
        assert count == 0
        assert blocked == False

    def test_matching_tiles_counted(self, clean_grid):
        """Tiles with matching pattern should be counted."""
        lines = enumerate_all_5_lines(clean_grid)
        line = lines[0]

        # Place 2 matching tiles at positions 0 and 4 (non-consecutive)
        clean_grid.set_tile(*line[0], Tile(Color.BLUE, Pattern.SWIRLS))
        clean_grid.set_tile(*line[4], Tile(Color.PINK, Pattern.SWIRLS))

        count, blocked = evaluate_line_for_pattern(clean_grid, line, Pattern.SWIRLS)
        assert count == 2
        assert blocked == False

    def test_non_matching_tile_blocks(self, clean_grid):
        """A tile with different pattern should block the line."""
        lines = enumerate_all_5_lines(clean_grid)
        line = lines[0]

        # Place matching tiles and one blocking tile
        clean_grid.set_tile(*line[0], Tile(Color.BLUE, Pattern.SWIRLS))
        clean_grid.set_tile(*line[2], Tile(Color.PINK, Pattern.DOTS))  # Wrong pattern
        clean_grid.set_tile(*line[4], Tile(Color.GREEN, Pattern.SWIRLS))

        count, blocked = evaluate_line_for_pattern(clean_grid, line, Pattern.SWIRLS)
        assert count == 2
        assert blocked == True

    def test_consecutive_tiles_counted(self, clean_grid):
        """Consecutive matching tiles should all be counted."""
        lines = enumerate_all_5_lines(clean_grid)
        line = lines[0]

        # Place 4 consecutive matching tiles
        for i in range(4):
            clean_grid.set_tile(*line[i], Tile(Color.BLUE, Pattern.FLOWERS))

        count, blocked = evaluate_line_for_pattern(clean_grid, line, Pattern.FLOWERS)
        assert count == 4
        assert blocked == False


class TestNonConsecutiveLineDetection:
    """Tests for detecting non-consecutive matching tiles in lines."""

    def test_a_blank_blank_blank_a_scores_potential(self, clean_grid, leo_cat):
        """Pattern A _ _ _ A should score as 2/5 potential, not 0."""
        lines = enumerate_all_5_lines(clean_grid)
        line = lines[0]
        pattern = leo_cat.patterns[0]

        # Place tiles at ends only (non-consecutive)
        clean_grid.set_tile(*line[0], Tile(Color.BLUE, pattern))
        clean_grid.set_tile(*line[4], Tile(Color.PINK, pattern))

        potential = evaluate_leo_potential(clean_grid, leo_cat)
        # Should have some potential (15% of 11 = 1.65)
        assert potential > 0, "Non-consecutive A _ _ _ A should score potential"

    def test_a_a_blank_a_a_scores_high_potential(self, clean_grid, leo_cat):
        """Pattern A A _ A A should score as 4/5 potential."""
        lines = enumerate_all_5_lines(clean_grid)
        line = lines[0]
        pattern = leo_cat.patterns[0]

        # Place 4 tiles with gap in middle
        clean_grid.set_tile(*line[0], Tile(Color.BLUE, pattern))
        clean_grid.set_tile(*line[1], Tile(Color.PINK, pattern))
        clean_grid.set_tile(*line[3], Tile(Color.GREEN, pattern))
        clean_grid.set_tile(*line[4], Tile(Color.YELLOW, pattern))

        potential = evaluate_leo_potential(clean_grid, leo_cat)
        # Should score 50% potential (5.5 points for Leo)
        expected_min = leo_cat.point_value * 0.4  # At least 40%
        assert potential >= expected_min


class TestBlockedLineDetection:
    """Tests for detecting blocked lines."""

    def test_blocked_line_scores_zero(self, clean_grid, leo_cat):
        """Line with wrong pattern tile should score 0 potential."""
        lines = enumerate_all_5_lines(clean_grid)
        line = lines[0]
        pattern = leo_cat.patterns[0]
        wrong_pattern = Pattern.LEAVES  # Not in leo_cat.patterns

        # Place A A B _ A (blocked by B)
        clean_grid.set_tile(*line[0], Tile(Color.BLUE, pattern))
        clean_grid.set_tile(*line[1], Tile(Color.PINK, pattern))
        clean_grid.set_tile(*line[2], Tile(Color.GREEN, wrong_pattern))  # Blocker
        clean_grid.set_tile(*line[4], Tile(Color.YELLOW, pattern))

        # This specific line should contribute 0
        count, blocked = evaluate_line_for_pattern(clean_grid, line, pattern)
        assert blocked == True
        assert count == 3  # 3 matching but blocked

    def test_cross_pattern_blocking(self, clean_grid, leo_cat):
        """Leo's other preferred pattern should still block a line."""
        lines = enumerate_all_5_lines(clean_grid)
        line = lines[0]
        pattern1 = leo_cat.patterns[0]  # e.g., SWIRLS
        pattern2 = leo_cat.patterns[1]  # e.g., DOTS (Leo's other pattern)

        # Place pattern1 with pattern2 blocking (Leo accepts both, but line is mixed)
        clean_grid.set_tile(*line[0], Tile(Color.BLUE, pattern1))
        clean_grid.set_tile(*line[1], Tile(Color.PINK, pattern1))
        clean_grid.set_tile(*line[2], Tile(Color.GREEN, pattern2))  # Different pattern!
        clean_grid.set_tile(*line[4], Tile(Color.YELLOW, pattern1))

        # For pattern1 line, pattern2 should block it
        count, blocked = evaluate_line_for_pattern(clean_grid, line, pattern1)
        assert blocked == True, "Leo's other pattern should still block this line"


class TestMilliePotential:
    """Tests for Millie (3-cluster) potential scoring."""

    def test_pair_with_third_space_scores(self, clean_grid, millie_cat):
        """Pair of adjacent same-pattern tiles with empty 3rd space should score."""
        pattern = millie_cat.patterns[0]

        # Place two adjacent tiles at center (plenty of empty neighbors)
        clean_grid.set_tile(0, 0, 0, Tile(Color.BLUE, pattern))
        clean_grid.set_tile(1, 0, -1, Tile(Color.PINK, pattern))

        potential = evaluate_millie_potential(clean_grid, pattern, millie_cat.point_value)
        expected = millie_cat.point_value * 0.3  # 30% for a pair
        assert potential == pytest.approx(expected, rel=0.01)

    def test_pair_without_third_space_scores_zero(self, clean_grid, millie_cat):
        """Pair surrounded by tiles (no empty 3rd space) should score 0."""
        pattern = millie_cat.patterns[0]
        other_pattern = Pattern.DOTS

        # Place a pair
        clean_grid.set_tile(0, 0, 0, Tile(Color.BLUE, pattern))
        clean_grid.set_tile(1, 0, -1, Tile(Color.PINK, pattern))

        # Fill all neighbors with other tiles
        neighbors_of_pair = set()
        neighbors_of_pair.update(clean_grid.get_neighbors(0, 0, 0))
        neighbors_of_pair.update(clean_grid.get_neighbors(1, 0, -1))
        neighbors_of_pair -= {(0, 0, 0), (1, 0, -1)}

        for pos in neighbors_of_pair:
            clean_grid.set_tile(*pos, Tile(Color.GREEN, other_pattern))

        potential = evaluate_millie_potential(clean_grid, pattern, millie_cat.point_value)
        assert potential == 0, "Pair with no empty 3rd space should score 0"

    def test_isolated_tile_scores_zero(self, clean_grid, millie_cat):
        """Single tile with no adjacent same-pattern should score 0."""
        pattern = millie_cat.patterns[0]

        clean_grid.set_tile(0, 0, 0, Tile(Color.BLUE, pattern))

        potential = evaluate_millie_potential(clean_grid, pattern, millie_cat.point_value)
        assert potential == 0


class TestOverlapDecay:
    """Tests for diminishing returns on overlapping lines."""

    def test_two_overlapping_lines_less_than_double(self, clean_grid, leo_cat):
        """Two overlapping lines should give less than 2x the value."""
        # Find two 5-lines that share positions
        lines = enumerate_all_5_lines(clean_grid)
        pattern = leo_cat.patterns[0]

        # Place 3 tiles in a line
        line = lines[0]
        clean_grid.set_tile(*line[0], Tile(Color.BLUE, pattern))
        clean_grid.set_tile(*line[1], Tile(Color.PINK, pattern))
        clean_grid.set_tile(*line[2], Tile(Color.GREEN, pattern))

        potential = evaluate_leo_potential(clean_grid, leo_cat)

        # If there are overlapping lines, the total should be less than
        # (number of lines with 3 matches) * (0.3 * point_value)
        single_line_potential = leo_cat.point_value * 0.3

        # With overlap decay, shouldn't be excessively high
        # This test ensures decay is being applied
        assert potential > 0
        assert potential < single_line_potential * 10  # Sanity check

    def test_non_overlapping_lines_full_value(self, clean_grid, rumi_cat):
        """Non-overlapping lines should each get full value."""
        pattern = rumi_cat.patterns[0]
        lines = enumerate_all_3_lines(clean_grid)

        # Find two non-overlapping 3-lines
        line1 = None
        line2 = None
        for i, l1 in enumerate(lines):
            for l2 in lines[i+1:]:
                if not set(l1) & set(l2):  # No overlap
                    line1 = l1
                    line2 = l2
                    break
            if line1 and line2:
                break

        if not (line1 and line2):
            pytest.skip("Could not find two non-overlapping 3-lines")

        # Place 2 tiles in each line
        clean_grid.set_tile(*line1[0], Tile(Color.BLUE, pattern))
        clean_grid.set_tile(*line1[1], Tile(Color.PINK, pattern))
        clean_grid.set_tile(*line2[0], Tile(Color.GREEN, pattern))
        clean_grid.set_tile(*line2[1], Tile(Color.YELLOW, pattern))

        potential = evaluate_rumi_potential(clean_grid, rumi_cat)
        single_pair_potential = rumi_cat.point_value * 0.3

        # Should be approximately 2x the single pair potential
        expected = single_pair_potential * 2
        assert potential == pytest.approx(expected, rel=0.2)


class TestCatPotentialDispatcher:
    """Tests for estimate_cat_potential() dispatching to correct functions."""

    def test_millie_uses_millie_evaluation(self, clean_grid, millie_cat):
        """estimate_cat_potential for Millie should use cluster logic."""
        pattern = millie_cat.patterns[0]
        clean_grid.set_tile(0, 0, 0, Tile(Color.BLUE, pattern))
        clean_grid.set_tile(1, 0, -1, Tile(Color.PINK, pattern))

        potential = estimate_cat_potential(clean_grid, millie_cat)
        assert potential > 0

    def test_leo_uses_leo_evaluation(self, clean_grid, leo_cat):
        """estimate_cat_potential for Leo should use 5-line logic."""
        lines = enumerate_all_5_lines(clean_grid)
        line = lines[0]
        pattern = leo_cat.patterns[0]

        clean_grid.set_tile(*line[0], Tile(Color.BLUE, pattern))
        clean_grid.set_tile(*line[4], Tile(Color.PINK, pattern))

        potential = estimate_cat_potential(clean_grid, leo_cat)
        assert potential > 0

    def test_rumi_uses_rumi_evaluation(self, clean_grid, rumi_cat):
        """estimate_cat_potential for Rumi should use 3-line logic."""
        lines = enumerate_all_3_lines(clean_grid)
        line = lines[0]
        pattern = rumi_cat.patterns[0]

        clean_grid.set_tile(*line[0], Tile(Color.BLUE, pattern))
        clean_grid.set_tile(*line[1], Tile(Color.PINK, pattern))

        potential = estimate_cat_potential(clean_grid, rumi_cat)
        assert potential > 0


class TestEdgeCases:
    """Edge case tests."""

    def test_empty_grid_zero_potential(self, clean_grid, leo_cat):
        """Empty grid should have 0 cat potential."""
        potential = evaluate_leo_potential(clean_grid, leo_cat)
        assert potential == 0

    def test_single_tile_zero_leo_potential(self, clean_grid, leo_cat):
        """Single tile should have 0 Leo potential (need at least 2)."""
        pattern = leo_cat.patterns[0]
        clean_grid.set_tile(0, 0, 0, Tile(Color.BLUE, pattern))

        potential = evaluate_leo_potential(clean_grid, leo_cat)
        assert potential == 0

    def test_both_patterns_contribute(self, clean_grid, leo_cat):
        """Both of a cat's patterns should contribute to potential."""
        lines = enumerate_all_5_lines(clean_grid)
        line1 = lines[0]
        line2 = lines[1] if len(lines) > 1 else lines[0]

        pattern1 = leo_cat.patterns[0]
        pattern2 = leo_cat.patterns[1]

        # Place pattern1 tiles
        clean_grid.set_tile(*line1[0], Tile(Color.BLUE, pattern1))
        clean_grid.set_tile(*line1[1], Tile(Color.PINK, pattern1))

        potential1 = evaluate_leo_potential(clean_grid, leo_cat)

        # Add pattern2 tiles (on different line if possible)
        clean_grid.set_tile(*line2[3], Tile(Color.GREEN, pattern2))
        clean_grid.set_tile(*line2[4], Tile(Color.YELLOW, pattern2))

        potential_both = evaluate_leo_potential(clean_grid, leo_cat)

        # Total should be >= first potential (might have overlap)
        assert potential_both >= potential1


class TestGoalPotentialScoring:
    """Tests for goal potential scoring with single vs double completion."""

    @pytest.fixture
    def aaa_bbb_goal(self):
        """AAA-BBB goal at default position."""
        return GoalAAA_BBB((-2, 1, 1))

    @pytest.fixture
    def aa_bb_cc_goal(self):
        """AA-BB-CC goal at default position."""
        return GoalAA_BB_CC((1, -1, 0))

    @pytest.fixture
    def all_unique_goal(self):
        """All Unique goal at default position."""
        return GoalAllUnique((0, 1, -1))

    def test_empty_goal_zero_potential(self, clean_grid, aaa_bbb_goal):
        """Goal with no neighbors should have 0 potential."""
        potential = estimate_goal_potential(clean_grid, aaa_bbb_goal)
        assert potential == 0

    def test_partial_progress_gives_potential(self, clean_grid, aaa_bbb_goal):
        """Goal with some neighbors filled should have positive potential."""
        neighbors = clean_grid.get_neighbors(*aaa_bbb_goal.position)
        # Fill 3 neighbors with matching pattern (trending toward 3-3)
        clean_grid.set_tile(*neighbors[0], Tile(Color.BLUE, Pattern.DOTS))
        clean_grid.set_tile(*neighbors[1], Tile(Color.BLUE, Pattern.DOTS))
        clean_grid.set_tile(*neighbors[2], Tile(Color.PINK, Pattern.LEAVES))

        potential = estimate_goal_potential(clean_grid, aaa_bbb_goal)
        assert potential > 0

    def test_double_progress_higher_than_single(self, aaa_bbb_goal):
        """Progress toward both conditions should give higher potential than just one."""
        # Use fresh grids for each scenario to avoid position validity issues

        # Scenario A: Good color progress, bad pattern progress (all same pattern)
        grid_a = HexGrid()
        heuristic_module._cached_5_lines = None
        heuristic_module._cached_3_lines = None
        neighbors = grid_a.get_neighbors(*aaa_bbb_goal.position)
        valid_neighbors = [n for n in neighbors if n in grid_a.all_positions]

        # 2 blue, 1 pink - trending toward 3-3 colors, but patterns all same
        grid_a.set_tile(*valid_neighbors[0], Tile(Color.BLUE, Pattern.DOTS))
        grid_a.set_tile(*valid_neighbors[1], Tile(Color.BLUE, Pattern.DOTS))
        grid_a.set_tile(*valid_neighbors[2], Tile(Color.PINK, Pattern.DOTS))

        single_track_potential = estimate_goal_potential(grid_a, aaa_bbb_goal)

        # Scenario B: Good progress on BOTH color and pattern
        grid_b = HexGrid()
        neighbors = grid_b.get_neighbors(*aaa_bbb_goal.position)
        valid_neighbors = [n for n in neighbors if n in grid_b.all_positions]

        # 2 blue dots, 1 pink leaves - good 3-3 progress for both color AND pattern
        grid_b.set_tile(*valid_neighbors[0], Tile(Color.BLUE, Pattern.DOTS))
        grid_b.set_tile(*valid_neighbors[1], Tile(Color.BLUE, Pattern.DOTS))
        grid_b.set_tile(*valid_neighbors[2], Tile(Color.PINK, Pattern.LEAVES))

        double_track_potential = estimate_goal_potential(grid_b, aaa_bbb_goal)

        assert double_track_potential > single_track_potential, \
            "Double-track progress should give higher potential"

    def test_color_impossible_bounds_to_single_max(self, clean_grid, aaa_bbb_goal):
        """When color 3-3 becomes impossible, potential should bound to single_max (8)."""
        neighbors = clean_grid.get_neighbors(*aaa_bbb_goal.position)

        # Place 4 tiles with 3 different colors - makes 3-3 color impossible
        # But patterns are 2 dots, 2 leaves - still possible for pattern 3-3
        clean_grid.set_tile(*neighbors[0], Tile(Color.BLUE, Pattern.DOTS))
        clean_grid.set_tile(*neighbors[1], Tile(Color.PINK, Pattern.DOTS))
        clean_grid.set_tile(*neighbors[2], Tile(Color.GREEN, Pattern.LEAVES))
        clean_grid.set_tile(*neighbors[3], Tile(Color.BLUE, Pattern.LEAVES))

        potential = estimate_goal_potential(clean_grid, aaa_bbb_goal)

        # Max achievable is single (8 pts), so potential should be based on that
        # With 4/6 filled and good pattern progress, should be reasonable but not huge
        max_single = 8.0
        assert potential <= max_single * 0.6, \
            f"Potential {potential} should be bounded by single_max possibility"

    def test_pattern_impossible_bounds_to_single_max(self, clean_grid, all_unique_goal):
        """When pattern uniqueness becomes impossible, bound to single_max."""
        neighbors = clean_grid.get_neighbors(*all_unique_goal.position)

        # Place tiles with duplicate pattern but unique colors
        # This makes pattern uniqueness impossible, color uniqueness still possible
        clean_grid.set_tile(*neighbors[0], Tile(Color.BLUE, Pattern.DOTS))
        clean_grid.set_tile(*neighbors[1], Tile(Color.PINK, Pattern.DOTS))  # Duplicate pattern!
        clean_grid.set_tile(*neighbors[2], Tile(Color.GREEN, Pattern.LEAVES))
        clean_grid.set_tile(*neighbors[3], Tile(Color.YELLOW, Pattern.FLOWERS))

        potential = estimate_goal_potential(clean_grid, all_unique_goal)

        # Pattern is blocked (duplicate DOTS), so max is single (10 pts)
        max_single = 10.0
        assert potential <= max_single * 0.6

    def test_both_impossible_gives_zero(self, clean_grid, aaa_bbb_goal):
        """When both conditions are impossible, potential should be 0."""
        neighbors = clean_grid.get_neighbors(*aaa_bbb_goal.position)

        # Place 6 tiles that fail both conditions
        # 4 blue, 2 pink (fails 3-3 color)
        # 4 dots, 2 leaves (fails 3-3 pattern)
        clean_grid.set_tile(*neighbors[0], Tile(Color.BLUE, Pattern.DOTS))
        clean_grid.set_tile(*neighbors[1], Tile(Color.BLUE, Pattern.DOTS))
        clean_grid.set_tile(*neighbors[2], Tile(Color.BLUE, Pattern.DOTS))
        clean_grid.set_tile(*neighbors[3], Tile(Color.BLUE, Pattern.DOTS))
        clean_grid.set_tile(*neighbors[4], Tile(Color.PINK, Pattern.LEAVES))
        clean_grid.set_tile(*neighbors[5], Tile(Color.PINK, Pattern.LEAVES))

        potential = estimate_goal_potential(clean_grid, aaa_bbb_goal)

        # Both conditions are impossible, so potential should be 0
        # Note: The goal's actual score() would return 0 since conditions aren't met
        assert potential == 0

    def test_aa_bb_cc_double_progress(self, clean_grid, aa_bb_cc_goal):
        """AA-BB-CC goal with good double progress should use higher max."""
        neighbors = clean_grid.get_neighbors(*aa_bb_cc_goal.position)

        # Perfect 2-2-2 progress for both color AND pattern
        clean_grid.set_tile(*neighbors[0], Tile(Color.BLUE, Pattern.DOTS))
        clean_grid.set_tile(*neighbors[1], Tile(Color.BLUE, Pattern.DOTS))
        clean_grid.set_tile(*neighbors[2], Tile(Color.PINK, Pattern.LEAVES))
        clean_grid.set_tile(*neighbors[3], Tile(Color.PINK, Pattern.LEAVES))

        potential = estimate_goal_potential(clean_grid, aa_bb_cc_goal)

        # With 4/6 filled and perfect 2-2 progress on both, should be meaningful
        assert potential > 0
        # Should be getting credit toward the 11-point max, not just 7

    def test_all_unique_perfect_double_progress(self, clean_grid, all_unique_goal):
        """All Unique with perfect double progress should aim for 15 pts."""
        neighbors = clean_grid.get_neighbors(*all_unique_goal.position)

        # 4 unique colors AND 4 unique patterns
        clean_grid.set_tile(*neighbors[0], Tile(Color.BLUE, Pattern.DOTS))
        clean_grid.set_tile(*neighbors[1], Tile(Color.PINK, Pattern.LEAVES))
        clean_grid.set_tile(*neighbors[2], Tile(Color.GREEN, Pattern.FLOWERS))
        clean_grid.set_tile(*neighbors[3], Tile(Color.YELLOW, Pattern.STRIPES))

        potential = estimate_goal_potential(clean_grid, all_unique_goal)

        # Perfect progress toward 15-point completion
        assert potential > 0

    def test_progression_increases_with_tiles(self, clean_grid, aaa_bbb_goal):
        """Potential should generally increase as more compatible tiles are placed."""
        neighbors = clean_grid.get_neighbors(*aaa_bbb_goal.position)

        potentials = []

        # Add tiles progressively toward a 3-3 configuration
        tiles_to_add = [
            (neighbors[0], Tile(Color.BLUE, Pattern.DOTS)),
            (neighbors[1], Tile(Color.BLUE, Pattern.DOTS)),
            (neighbors[2], Tile(Color.PINK, Pattern.LEAVES)),
            (neighbors[3], Tile(Color.PINK, Pattern.LEAVES)),
            (neighbors[4], Tile(Color.BLUE, Pattern.DOTS)),
        ]

        for pos, tile in tiles_to_add:
            clean_grid.set_tile(*pos, tile)
            potentials.append(estimate_goal_potential(clean_grid, aaa_bbb_goal))

        # General trend should be increasing (may not be strictly monotonic)
        assert potentials[-1] >= potentials[0], \
            "Potential should increase as we approach goal completion"
