from source.tile_bag import TileBag
from source.hex_grid import Color, Pattern, Tile

def test_tile_bag_initialization():
    bag = TileBag()
    assert bag.tiles_remaining() == 108  # 6 colors * 6 patterns * 3 of each

def test_draw_tile():
    bag = TileBag()
    initial_count = bag.tiles_remaining()
    tile = bag.draw_tile()
    assert isinstance(tile, Tile)
    assert bag.tiles_remaining() == initial_count - 1

def test_draw_all_tiles():
    bag = TileBag()
    tiles = [bag.draw_tile() for _ in range(108)]
    assert bag.tiles_remaining() == 0
    assert bag.draw_tile() is None  # Bag should be empty

def test_tile_distribution():
    bag = TileBag()
    tile_counts = {color: {pattern: 0 for pattern in Pattern} for color in Color}
    
    for _ in range(108):
        tile = bag.draw_tile()
        tile_counts[tile.color][tile.pattern] += 1
    
    for color in Color:
        for pattern in Pattern:
            assert tile_counts[color][pattern] == 3