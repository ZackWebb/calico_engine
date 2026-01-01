import random
from tile import Tile, Color, Pattern

class TileBag:
    __slots__ = ('tiles',)

    def __init__(self):
        self.tiles = []
        self.fill_bag()
        self.shuffle()

    def fill_bag(self):
        for color in Color:
            for pattern in Pattern:
                for _ in range(3):  # 3 of each combination
                    self.tiles.append(Tile(color, pattern))

    def shuffle(self):
        random.shuffle(self.tiles)

    def shuffle_remaining(self):
        """
        Shuffle remaining tiles in the bag.

        Used for chance node sampling in MCTS - each simulation explores
        a different possible future by randomizing the unknown tile order.
        """
        random.shuffle(self.tiles)

    def draw_tile(self):
        if self.tiles:
            return self.tiles.pop()
        else:
            return None  # Bag is empty

    def tiles_remaining(self):
        return len(self.tiles)

    def __str__(self):
        return f"Tile bag containing {self.tiles_remaining()} tiles"

    def __repr__(self):
        return self.__str__()

    def __copy__(self):
        """Shallow copy - shares Tile references since Tiles are immutable."""
        new_bag = object.__new__(TileBag)
        new_bag.tiles = self.tiles.copy()
        return new_bag