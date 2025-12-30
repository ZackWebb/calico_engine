from source.hex_grid import Color, Pattern
from source.tile import Tile

def test_tile_creation():
    tile = Tile(Color.BLUE, Pattern.DOTS)
    assert tile.color == Color.BLUE
    assert tile.pattern == Pattern.DOTS

def test_tile_string_representation():
    tile = Tile(Color.BLUE, Pattern.DOTS)
    tile_str = str(tile)
    assert isinstance(tile_str, str)
    assert len(tile_str) > 0  # Ensure it's not an empty string

def test_tile_representation_contains_color_and_pattern():
    tile = Tile(Color.BLUE, Pattern.DOTS)
    tile_str = str(tile)
    assert "BLUE" in tile_str.upper() or "BL" in tile_str.upper()
    assert "DOTS" in tile_str.upper() or "DO" in tile_str.upper()
