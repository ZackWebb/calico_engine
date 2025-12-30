"""
Tests to verify cat scoring rules:
1. Lines must be all the SAME pattern (one of cat's preferred patterns)
2. Groups cannot be adjacent - must have separation
3. Same cat can score multiple times on non-adjacent groups
"""
import pytest
from source.hex_grid import HexGrid
from source.tile import Tile, Color, Pattern
from source.cat import CatMillie, CatLeo, CatRumi


class TestLeoScoringRules:
    """Leo requires 5 tiles in a line, all the SAME pattern."""

    def test_leo_scores_with_5_same_pattern(self):
        """5 DOTS in a line should score."""
        grid = HexGrid()
        leo = CatLeo()
        leo.patterns = (Pattern.DOTS, Pattern.LEAVES)

        # Place 5 DOTS in east direction
        for i in range(-2, 3):
            grid.set_tile(i, 0, -i, Tile(Color.BLUE, Pattern.DOTS))

        assert leo.check_condition(grid) == True
        print(f"PASS: Leo scores with 5 DOTS: {leo.score(grid)} pts")

    def test_leo_does_not_score_with_mixed_patterns(self):
        """DOT DOT LEAVES DOT DOT should NOT score."""
        grid = HexGrid()
        leo = CatLeo()
        leo.patterns = (Pattern.DOTS, Pattern.LEAVES)

        # Place DOT DOT LEAVES DOT DOT
        positions = [(-2, 0, 2), (-1, 0, 1), (0, 0, 0), (1, 0, -1), (2, 0, -2)]
        patterns_to_place = [Pattern.DOTS, Pattern.DOTS, Pattern.LEAVES, Pattern.DOTS, Pattern.DOTS]

        for pos, pat in zip(positions, patterns_to_place):
            grid.set_tile(*pos, Tile(Color.BLUE, pat))

        result = leo.check_condition(grid)
        print(f"  Mixed pattern line (DOT DOT LEAVES DOT DOT): scores = {result}")
        assert result == False, "Mixed patterns should NOT score for Leo!"

    def test_leo_does_not_score_with_4_in_line(self):
        """Only 4 in a line should NOT score."""
        grid = HexGrid()
        leo = CatLeo()
        leo.patterns = (Pattern.DOTS, Pattern.LEAVES)

        for i in range(-2, 2):  # Only 4 tiles
            grid.set_tile(i, 0, -i, Tile(Color.BLUE, Pattern.DOTS))

        assert leo.check_condition(grid) == False
        print("PASS: Leo does not score with only 4 in a line")


class TestRumiScoringRules:
    """Rumi requires 3 tiles in a line, all the SAME pattern."""

    def test_rumi_scores_with_3_same_pattern(self):
        """3 LEAVES in a line should score."""
        grid = HexGrid()
        rumi = CatRumi()
        rumi.patterns = (Pattern.LEAVES, Pattern.CLUBS)

        for i in range(3):
            grid.set_tile(i, 0, -i, Tile(Color.BLUE, Pattern.LEAVES))

        assert rumi.check_condition(grid) == True
        print(f"PASS: Rumi scores with 3 LEAVES: {rumi.score(grid)} pts")

    def test_rumi_does_not_score_with_mixed_patterns(self):
        """LEAVES CLUBS LEAVES should NOT score."""
        grid = HexGrid()
        rumi = CatRumi()
        rumi.patterns = (Pattern.LEAVES, Pattern.CLUBS)

        positions = [(0, 0, 0), (1, 0, -1), (2, 0, -2)]
        patterns_to_place = [Pattern.LEAVES, Pattern.CLUBS, Pattern.LEAVES]

        for pos, pat in zip(positions, patterns_to_place):
            grid.set_tile(*pos, Tile(Color.BLUE, pat))

        result = rumi.check_condition(grid)
        print(f"  Mixed pattern line (LEAVES CLUBS LEAVES): scores = {result}")
        assert result == False, "Mixed patterns should NOT score for Rumi!"


class TestMillieScoringRules:
    """Millie requires 3 touching tiles. Need to clarify: same pattern or any of her patterns?"""

    def test_millie_with_3_same_pattern(self):
        """3 touching FLOWERS should score."""
        grid = HexGrid()
        millie = CatMillie()
        millie.patterns = (Pattern.FLOWERS, Pattern.DOTS)

        # Triangle of 3 touching tiles
        grid.set_tile(0, 0, 0, Tile(Color.BLUE, Pattern.FLOWERS))
        grid.set_tile(1, 0, -1, Tile(Color.PINK, Pattern.FLOWERS))
        grid.set_tile(0, 1, -1, Tile(Color.GREEN, Pattern.FLOWERS))

        assert millie.check_condition(grid) == True
        print(f"PASS: Millie scores with 3 FLOWERS: {millie.score(grid)} pts")

    def test_millie_with_mixed_preferred_patterns_does_not_score(self):
        """
        3 touching tiles: FLOWERS FLOWERS DOTS (mixed preferred patterns).
        Should NOT score - Millie requires all 3 to be the SAME pattern.
        """
        grid = HexGrid()
        millie = CatMillie()
        millie.patterns = (Pattern.FLOWERS, Pattern.DOTS)

        grid.set_tile(0, 0, 0, Tile(Color.BLUE, Pattern.FLOWERS))
        grid.set_tile(1, 0, -1, Tile(Color.PINK, Pattern.FLOWERS))
        grid.set_tile(0, 1, -1, Tile(Color.GREEN, Pattern.DOTS))

        result = millie.check_condition(grid)
        print(f"\n  Mixed patterns (FLOWERS FLOWERS DOTS): scores = {result}")
        assert result == False, "Mixed patterns should NOT score for Millie!"


class TestMultipleScoringGroups:
    """Test that cats can score multiple times on non-adjacent groups."""

    def test_millie_scores_multiple_separate_clusters(self):
        """
        Two separate clusters of 3 FLOWERS each should score twice.
        """
        grid = HexGrid()
        millie = CatMillie()
        millie.patterns = (Pattern.FLOWERS, Pattern.DOTS)

        # Cluster 1: around (0,0,0)
        grid.set_tile(0, 0, 0, Tile(Color.BLUE, Pattern.FLOWERS))
        grid.set_tile(1, 0, -1, Tile(Color.PINK, Pattern.FLOWERS))
        grid.set_tile(0, 1, -1, Tile(Color.GREEN, Pattern.FLOWERS))

        # Cluster 2: far away around (3,-3,0) - not adjacent to cluster 1
        grid.set_tile(3, -3, 0, Tile(Color.BLUE, Pattern.FLOWERS))
        grid.set_tile(3, -2, -1, Tile(Color.PINK, Pattern.FLOWERS))
        grid.set_tile(2, -2, 0, Tile(Color.GREEN, Pattern.FLOWERS))

        score = millie.score(grid)
        expected = millie.point_value * 2
        print(f"\n  Two separate FLOWERS clusters:")
        print(f"  Score: {score} pts (expected: {expected})")
        assert score == expected, f"Should score {expected} for two clusters"

    def test_millie_scores_different_patterns_separately(self):
        """
        One cluster of FLOWERS and one cluster of DOTS should both score.
        """
        grid = HexGrid()
        millie = CatMillie()
        millie.patterns = (Pattern.FLOWERS, Pattern.DOTS)

        # Cluster 1: 3 FLOWERS
        grid.set_tile(0, 0, 0, Tile(Color.BLUE, Pattern.FLOWERS))
        grid.set_tile(1, 0, -1, Tile(Color.PINK, Pattern.FLOWERS))
        grid.set_tile(0, 1, -1, Tile(Color.GREEN, Pattern.FLOWERS))

        # Cluster 2: 3 DOTS (far away)
        grid.set_tile(3, -3, 0, Tile(Color.BLUE, Pattern.DOTS))
        grid.set_tile(3, -2, -1, Tile(Color.PINK, Pattern.DOTS))
        grid.set_tile(2, -2, 0, Tile(Color.GREEN, Pattern.DOTS))

        score = millie.score(grid)
        expected = millie.point_value * 2
        print(f"\n  One FLOWERS cluster + one DOTS cluster:")
        print(f"  Score: {score} pts (expected: {expected})")
        assert score == expected


class TestAdjacentGroupsSeparation:
    """Test that adjacent/overlapping groups don't double-count."""

    def test_overlapping_lines_current_behavior(self):
        """
        If we have 6 tiles in a line: DOT DOT DOT DOT DOT DOT
        This contains TWO overlapping 5-tile lines.

        QUESTION: Should this score once or twice?
        With adjacency rules, likely once (tiles can't be reused).
        """
        grid = HexGrid()
        leo = CatLeo()
        leo.patterns = (Pattern.DOTS, Pattern.LEAVES)

        # 6 DOTS in a line
        for i in range(-2, 4):
            grid.set_tile(i, 0, -i, Tile(Color.BLUE, Pattern.DOTS))

        score = leo.score(grid)
        print(f"\n  6 DOTS in a line (contains 2 overlapping 5-tile segments):")
        print(f"  Current score: {score} pts")
        print(f"  With proper rules: should probably be {leo.point_value} pts (once)")

        # Current behavior: only returns True once anyway
        assert score == leo.point_value


class TestScoringWithWrongPatterns:
    """Verify cats don't score with patterns not in their preferred list."""

    def test_leo_wrong_pattern(self):
        """5 STRIPES in a line should NOT score if STRIPES not in Leo's patterns."""
        grid = HexGrid()
        leo = CatLeo()
        leo.patterns = (Pattern.DOTS, Pattern.LEAVES)  # NOT stripes

        for i in range(-2, 3):
            grid.set_tile(i, 0, -i, Tile(Color.BLUE, Pattern.STRIPES))

        assert leo.check_condition(grid) == False
        print("PASS: Leo does not score with wrong pattern (STRIPES)")

    def test_millie_wrong_pattern(self):
        """3 touching SWIRLS should NOT score if SWIRLS not in Millie's patterns."""
        grid = HexGrid()
        millie = CatMillie()
        millie.patterns = (Pattern.FLOWERS, Pattern.DOTS)  # NOT swirls

        grid.set_tile(0, 0, 0, Tile(Color.BLUE, Pattern.SWIRLS))
        grid.set_tile(1, 0, -1, Tile(Color.PINK, Pattern.SWIRLS))
        grid.set_tile(0, 1, -1, Tile(Color.GREEN, Pattern.SWIRLS))

        assert millie.check_condition(grid) == False
        print("PASS: Millie does not score with wrong pattern (SWIRLS)")
