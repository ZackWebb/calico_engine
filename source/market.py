class Market:
    def __init__(self, tile_bag):
        self.tiles = []
        self.tile_bag = tile_bag
        self.refill()

    def refill(self):
        while len(self.tiles) < 3 and self.tile_bag.tiles_remaining() > 0:
            self.tiles.append(self.tile_bag.draw_tile())

    def choose_tile(self, index):
        if 0 <= index < len(self.tiles):
            return self.tiles.pop(index)
        return None

    def __str__(self):
        return f"Market: {', '.join(str(tile) for tile in self.tiles)}"