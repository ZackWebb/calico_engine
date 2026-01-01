import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from source.hex_grid import HexGrid, Color, Pattern
from source.tile import Tile
from source.cat import (
    initialize_game_cats, CatMillie, CatLeo, CatRumi, CatTecolote,
    BUCKET_1, BUCKET_2, BUCKET_3
)

@pytest.fixture
def game_setup():
    cats, remaining_patterns = initialize_game_cats()
    grid = HexGrid()
    return cats, remaining_patterns, grid

def test_game_setup(game_setup):
    cats, remaining_patterns, grid = game_setup
    
    # Test that we have 3 cats
    assert len(cats) == 3
    
    # Test that each cat has 2 unique patterns
    all_cat_patterns = [pattern for cat in cats for pattern in cat.patterns]
    assert len(all_cat_patterns) == 6
    assert len(set(all_cat_patterns)) == 6
    
    # Test that remaining patterns are not in cat patterns
    assert set(remaining_patterns).isdisjoint(set(all_cat_patterns))
    
    # Test that all patterns are accounted for
    assert set(all_cat_patterns + remaining_patterns) == set(Pattern)

def test_millie_condition(game_setup):
    cats, _, grid = game_setup
    millie = next(cat for cat in cats if isinstance(cat, CatMillie))

    pattern = millie.patterns[0]

    # Place 3 adjacent tiles with matching pattern (cube coordinates)
    grid.set_tile(0, 0, 0, Tile(Color.PINK, pattern))
    grid.set_tile(1, -1, 0, Tile(Color.BLUE, pattern))
    grid.set_tile(1, 0, -1, Tile(Color.GREEN, pattern))

    assert millie.check_condition(grid)

def test_millie_condition_not_met(game_setup):
    cats, remaining_patterns, grid = game_setup
    millie = next(cat for cat in cats if isinstance(cat, CatMillie))

    wrong_pattern = next(p for p in Pattern if p not in millie.patterns)

    # Place 3 adjacent tiles with wrong pattern (cube coordinates)
    grid.set_tile(0, 0, 0, Tile(Color.PINK, wrong_pattern))
    grid.set_tile(1, -1, 0, Tile(Color.BLUE, wrong_pattern))
    grid.set_tile(1, 0, -1, Tile(Color.GREEN, wrong_pattern))

    assert not millie.check_condition(grid)


def test_leo_condition(game_setup):
    cats, _, grid = game_setup
    leo = next((cat for cat in cats if isinstance(cat, CatLeo)), None)
    if not leo:
        pytest.skip("Leo was not randomly selected for this test.")

    pattern = leo.patterns[0]

    # Create a straight line of 5 tiles along east direction (cube coordinates)
    # Direction (1, 0, -1) starting from (-2, 0, 2)
    grid.set_tile(-2, 0, 2, Tile(Color.PINK, pattern))
    grid.set_tile(-1, 0, 1, Tile(Color.PINK, pattern))
    grid.set_tile(0, 0, 0, Tile(Color.PINK, pattern))
    grid.set_tile(1, 0, -1, Tile(Color.PINK, pattern))
    grid.set_tile(2, 0, -2, Tile(Color.PINK, pattern))

    assert leo.check_condition(grid)

def test_leo_condition_not_met(game_setup):
    cats, _, grid = game_setup
    leo = next((cat for cat in cats if isinstance(cat, CatLeo)), None)
    if not leo:
        pytest.skip("Leo was not randomly selected for this test.")

    pattern = leo.patterns[0]

    # Create a straight line of only 4 tiles (not enough for Leo)
    grid.set_tile(-2, 0, 2, Tile(Color.PINK, pattern))
    grid.set_tile(-1, 0, 1, Tile(Color.PINK, pattern))
    grid.set_tile(0, 0, 0, Tile(Color.PINK, pattern))
    grid.set_tile(1, 0, -1, Tile(Color.PINK, pattern))

    assert not leo.check_condition(grid)

def test_leo_condition_interrupted(game_setup):
    cats, _, grid = game_setup
    leo = next((cat for cat in cats if isinstance(cat, CatLeo)), None)
    if not leo:
        pytest.skip("Leo was not randomly selected for this test.")

    pattern = leo.patterns[0]
    other_pattern = next(p for p in Pattern if p != pattern)

    # Create a line of 5 tiles with an interruption in the middle
    grid.set_tile(-2, 0, 2, Tile(Color.PINK, pattern))
    grid.set_tile(-1, 0, 1, Tile(Color.PINK, pattern))
    grid.set_tile(0, 0, 0, Tile(Color.BLUE, other_pattern))  # Interruption
    grid.set_tile(1, 0, -1, Tile(Color.PINK, pattern))
    grid.set_tile(2, 0, -2, Tile(Color.PINK, pattern))

    assert not leo.check_condition(grid)

def test_leo_condition_diagonal(game_setup, capsys):
    cats, _, grid = game_setup
    leo = next((cat for cat in cats if isinstance(cat, CatLeo)), None)
    if not leo:
        pytest.skip("Leo was not randomly selected for this test.")

    pattern = leo.patterns[0]

    print(f"\nLeo's patterns: {leo.patterns}")
    print(f"Using pattern: {pattern}")

    # Create a diagonal line of 5 tiles along northeast direction (1, -1, 0)
    grid.set_tile(-2, 2, 0, Tile(Color.PINK, pattern))
    grid.set_tile(-1, 1, 0, Tile(Color.PINK, pattern))
    grid.set_tile(0, 0, 0, Tile(Color.PINK, pattern))
    grid.set_tile(1, -1, 0, Tile(Color.PINK, pattern))
    grid.set_tile(2, -2, 0, Tile(Color.PINK, pattern))

    print("\nGrid after setting diagonal tiles:")
    print(grid)

    result = leo.check_condition(grid)
    print(f"\nLeo's condition met: {result}")

    assert result, f"Leo's diagonal condition should be met. Grid:\n{grid}"

def test_rumi_condition(game_setup):
    cats, _, grid = game_setup
    rumi = next((cat for cat in cats if isinstance(cat, CatRumi)), None)
    if not rumi:
        pytest.skip("Rumi was not randomly selected for this test.")

    pattern = rumi.patterns[0]

    # Create a straight line of 3 tiles (cube coordinates)
    grid.set_tile(-1, 0, 1, Tile(Color.BLUE, pattern))
    grid.set_tile(0, 0, 0, Tile(Color.BLUE, pattern))
    grid.set_tile(1, 0, -1, Tile(Color.BLUE, pattern))

    assert rumi.check_condition(grid)

def test_rumi_condition_not_met(game_setup):
    cats, _, grid = game_setup
    rumi = next((cat for cat in cats if isinstance(cat, CatRumi)), None)
    if not rumi:
        pytest.skip("Rumi was not randomly selected for this test.")

    pattern = rumi.patterns[0]

    # Create a straight line of only 2 tiles (not enough for Rumi)
    grid.set_tile(0, 0, 0, Tile(Color.BLUE, pattern))
    grid.set_tile(1, 0, -1, Tile(Color.BLUE, pattern))

    assert not rumi.check_condition(grid)

def test_rumi_condition_interrupted(game_setup):
    cats, _, grid = game_setup
    rumi = next((cat for cat in cats if isinstance(cat, CatRumi)), None)
    if not rumi:
        pytest.skip("Rumi was not randomly selected for this test.")

    pattern = rumi.patterns[0]
    other_pattern = next(p for p in Pattern if p != pattern)

    # Create a line of 3 tiles with an interruption in the middle
    grid.set_tile(-1, 0, 1, Tile(Color.BLUE, pattern))
    grid.set_tile(0, 0, 0, Tile(Color.YELLOW, other_pattern))  # Interruption
    grid.set_tile(1, 0, -1, Tile(Color.BLUE, pattern))

    assert not rumi.check_condition(grid)

def test_rumi_condition_vertical(game_setup):
    cats, _, grid = game_setup
    rumi = next((cat for cat in cats if isinstance(cat, CatRumi)), None)
    if not rumi:
        pytest.skip("Rumi was not randomly selected for this test.")

    pattern = rumi.patterns[0]

    # Create a line of 3 tiles along northwest direction (0, -1, 1)
    grid.set_tile(0, 1, -1, Tile(Color.BLUE, pattern))
    grid.set_tile(0, 0, 0, Tile(Color.BLUE, pattern))
    grid.set_tile(0, -1, 1, Tile(Color.BLUE, pattern))

    assert rumi.check_condition(grid)

def test_rumi_condition_diagonal(game_setup, capsys):
    cats, _, grid = game_setup
    rumi = next((cat for cat in cats if isinstance(cat, CatRumi)), None)
    if not rumi:
        pytest.skip("Rumi was not randomly selected for this test.")

    pattern = rumi.patterns[0]

    print(f"\nRumi's patterns: {rumi.patterns}")
    print(f"Using pattern: {pattern}")

    # Create a diagonal line of 3 tiles along northeast direction (1, -1, 0)
    grid.set_tile(-1, 1, 0, Tile(Color.BLUE, pattern))
    grid.set_tile(0, 0, 0, Tile(Color.BLUE, pattern))
    grid.set_tile(1, -1, 0, Tile(Color.BLUE, pattern))

    print("\nGrid after setting diagonal tiles:")
    print(grid)

    result = rumi.check_condition(grid)
    print(f"\nRumi's condition met: {result}")

    assert result, f"Rumi's diagonal condition should be met. Grid:\n{grid}"


# --- Tecolote Tests ---

@pytest.fixture
def tecolote_setup():
    """Create a Tecolote cat with known patterns for testing."""
    tecolote = CatTecolote()
    tecolote.patterns = (Pattern.DOTS, Pattern.STRIPES)
    grid = HexGrid()
    return tecolote, grid


def test_tecolote_condition(tecolote_setup):
    tecolote, grid = tecolote_setup
    pattern = tecolote.patterns[0]

    # Create a straight line of 4 tiles along east direction (1, 0, -1)
    grid.set_tile(-1, 0, 1, Tile(Color.PINK, pattern))
    grid.set_tile(0, 0, 0, Tile(Color.PINK, pattern))
    grid.set_tile(1, 0, -1, Tile(Color.PINK, pattern))
    grid.set_tile(2, 0, -2, Tile(Color.PINK, pattern))

    assert tecolote.check_condition(grid)


def test_tecolote_condition_not_met_only_3(tecolote_setup):
    tecolote, grid = tecolote_setup
    pattern = tecolote.patterns[0]

    # Create a straight line of only 3 tiles (not enough for Tecolote)
    grid.set_tile(-1, 0, 1, Tile(Color.PINK, pattern))
    grid.set_tile(0, 0, 0, Tile(Color.PINK, pattern))
    grid.set_tile(1, 0, -1, Tile(Color.PINK, pattern))

    assert not tecolote.check_condition(grid)


def test_tecolote_condition_interrupted(tecolote_setup):
    tecolote, grid = tecolote_setup
    pattern = tecolote.patterns[0]
    other_pattern = Pattern.FLOWERS  # Different from tecolote's patterns

    # Create a line of 4 tiles with an interruption in the middle
    grid.set_tile(-1, 0, 1, Tile(Color.PINK, pattern))
    grid.set_tile(0, 0, 0, Tile(Color.BLUE, other_pattern))  # Interruption
    grid.set_tile(1, 0, -1, Tile(Color.PINK, pattern))
    grid.set_tile(2, 0, -2, Tile(Color.PINK, pattern))

    assert not tecolote.check_condition(grid)


def test_tecolote_scores_7_points(tecolote_setup):
    tecolote, grid = tecolote_setup
    pattern = tecolote.patterns[0]

    # Create a valid 4-tile line
    grid.set_tile(-1, 0, 1, Tile(Color.PINK, pattern))
    grid.set_tile(0, 0, 0, Tile(Color.PINK, pattern))
    grid.set_tile(1, 0, -1, Tile(Color.PINK, pattern))
    grid.set_tile(2, 0, -2, Tile(Color.PINK, pattern))

    assert tecolote.score(grid) == 7


def test_tecolote_diagonal(tecolote_setup):
    tecolote, grid = tecolote_setup
    pattern = tecolote.patterns[0]

    # Create a diagonal line of 4 tiles along northeast direction (1, -1, 0)
    grid.set_tile(-1, 1, 0, Tile(Color.BLUE, pattern))
    grid.set_tile(0, 0, 0, Tile(Color.BLUE, pattern))
    grid.set_tile(1, -1, 0, Tile(Color.BLUE, pattern))
    grid.set_tile(2, -2, 0, Tile(Color.BLUE, pattern))

    assert tecolote.check_condition(grid)


def test_tecolote_wrong_pattern(tecolote_setup):
    tecolote, grid = tecolote_setup
    # Use a pattern that's NOT in tecolote's preferred patterns
    wrong_pattern = Pattern.FLOWERS

    # Create a valid 4-tile line but with wrong pattern
    grid.set_tile(-1, 0, 1, Tile(Color.PINK, wrong_pattern))
    grid.set_tile(0, 0, 0, Tile(Color.PINK, wrong_pattern))
    grid.set_tile(1, 0, -1, Tile(Color.PINK, wrong_pattern))
    grid.set_tile(2, 0, -2, Tile(Color.PINK, wrong_pattern))

    assert not tecolote.check_condition(grid)


# --- Bucket Selection Tests ---

class TestBucketConfiguration:
    """Tests for cat bucket configuration."""

    def test_bucket_1_contains_millie(self):
        """Bucket 1 should contain Millie."""
        assert CatMillie in BUCKET_1

    def test_bucket_1_contains_rumi(self):
        """Bucket 1 should contain Rumi."""
        assert CatRumi in BUCKET_1

    def test_bucket_2_contains_tecolote(self):
        """Bucket 2 should contain Tecolote."""
        assert CatTecolote in BUCKET_2

    def test_bucket_3_contains_leo(self):
        """Bucket 3 should contain Leo."""
        assert CatLeo in BUCKET_3

    def test_buckets_are_non_empty(self):
        """All buckets should have at least one cat."""
        assert len(BUCKET_1) >= 1
        assert len(BUCKET_2) >= 1
        assert len(BUCKET_3) >= 1


class TestBucketSelection:
    """Tests for bucket-based cat selection."""

    def test_bucket_selection_returns_three_cats(self):
        """Bucket selection should return exactly 3 cats."""
        cats, _ = initialize_game_cats(use_buckets=True)
        assert len(cats) == 3

    def test_bucket_selection_one_from_each_bucket(self):
        """Each cat should come from a different bucket."""
        # Run multiple times to test randomness
        for _ in range(10):
            cats, _ = initialize_game_cats(use_buckets=True)

            cat_classes = [type(cat) for cat in cats]

            # One cat should be from bucket 1
            assert any(cat_class in BUCKET_1 for cat_class in cat_classes)
            # One cat should be from bucket 2
            assert any(cat_class in BUCKET_2 for cat_class in cat_classes)
            # One cat should be from bucket 3
            assert any(cat_class in BUCKET_3 for cat_class in cat_classes)

    def test_bucket_selection_patterns_non_overlapping(self):
        """All cats should have non-overlapping pattern assignments."""
        cats, remaining = initialize_game_cats(use_buckets=True)

        all_cat_patterns = []
        for cat in cats:
            all_cat_patterns.extend(cat.patterns)

        # 6 patterns total, all unique
        assert len(all_cat_patterns) == 6
        assert len(set(all_cat_patterns)) == 6

    def test_legacy_selection_still_works(self):
        """Legacy selection (use_buckets=False) should still work."""
        cats, _ = initialize_game_cats(use_buckets=False)
        assert len(cats) == 3

        # All patterns should still be non-overlapping
        all_patterns = []
        for cat in cats:
            all_patterns.extend(cat.patterns)
        assert len(set(all_patterns)) == 6

    def test_default_uses_bucket_selection(self):
        """Default should use bucket selection."""
        # With bucket selection, we get one cat from each bucket
        cats, _ = initialize_game_cats()  # default

        cat_classes = [type(cat) for cat in cats]
        # One from bucket 1 (Millie)
        assert any(cat_class in BUCKET_1 for cat_class in cat_classes)
        # One from bucket 2 (Rumi or Tecolote)
        assert any(cat_class in BUCKET_2 for cat_class in cat_classes)
        # One from bucket 3 (Leo)
        assert any(cat_class in BUCKET_3 for cat_class in cat_classes)