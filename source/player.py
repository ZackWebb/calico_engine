import copy as copy_module
from hex_grid import HexGrid

class Player:
    __slots__ = ('name', 'grid', 'tiles')

    def __init__(self, name, tile_bag):
        self.name = name
        self.grid = HexGrid()
        self.tiles = [tile_bag.draw_tile() for _ in range(2)]

    def add_tile(self, tile):
        self.tiles.append(tile)

    def place_tile(self, q, r, s, tile_index):
        """Place tile from hand onto grid at cube coordinates (q, r, s)."""
        if not (0 <= tile_index < len(self.tiles)):
            return False
        if not self.grid.is_position_empty(q, r, s):
            return False
        tile = self.tiles.pop(tile_index)
        self.grid.set_tile(q, r, s, tile)
        return True

    def __str__(self):
        return f"Player {self.name}: {', '.join(str(tile) for tile in self.tiles)}"

    def __copy__(self):
        """Shallow copy - copies grid and hand, shares Tile references."""
        new_player = object.__new__(Player)
        new_player.name = self.name
        new_player.grid = copy_module.copy(self.grid)
        new_player.tiles = self.tiles.copy()
        return new_player