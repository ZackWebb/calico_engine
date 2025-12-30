import pytest
from source.hex_grid import HexGrid, Color, Pattern, Tile

def test_hex_grid_initialization():
    grid = HexGrid()
    # Grid uses cube coordinates - check that positions exist
    assert len(grid.grid) > 0
    # Origin should be valid
    assert (0, 0, 0) in grid.grid
    # Check some edge positions exist
    assert (3, 0, -3) in grid.grid
    assert (-3, 0, 3) in grid.grid

def test_set_and_get_tile():
    grid = HexGrid()
    tile = Tile(Color.BLUE, Pattern.DOTS)
    grid.set_tile(0, 0, 0, tile)
    assert grid.get_tile(0, 0, 0) == tile

def test_is_valid_position():
    grid = HexGrid()
    # Valid positions (in cube coordinates where q + r + s = 0)
    assert grid.is_valid_position(0, 0, 0)
    assert grid.is_valid_position(1, -1, 0)
    assert grid.is_valid_position(3, 0, -3)
    # Invalid positions
    assert not grid.is_valid_position(10, 0, -10)
    assert not grid.is_valid_position(5, 5, -10)

def test_grid_string_representation():
    grid = HexGrid()
    tile = Tile(Color.BLUE, Pattern.DOTS)
    grid.set_tile(0, 0, 0, tile)
    grid_str = str(grid)
    assert "BD" in grid_str  # Check if the tile is represented in the string (Blue Dots = BD)