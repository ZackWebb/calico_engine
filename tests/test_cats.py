import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from source.hex_grid import HexGrid, Color, Pattern
from source.tile import Tile
from source.cat import initialize_game_cats, CatMillie, CatLeo, CatRumi

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