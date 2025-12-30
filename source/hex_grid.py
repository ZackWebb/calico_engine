from tile import Tile, Color, Pattern

class HexGrid:
    def __init__(self):
        self.grid = {}
        self.goal_positions = set()  # Positions where goals are placed (cannot place tiles)
        self.initialize_grid()

    @property
    def all_positions(self):
        """Return all valid positions in the grid."""
        return list(self.grid.keys())

    def add_hex(self, qr):
        q, r = qr
        s = -q - r
        self.grid[(q, r, s)] = None

    def initialize_grid(self):
        for q in range(-3, 4):
            for r in range(-3, 4):
                s = -q - r
                if abs(s) <= 3:
                    self.grid[(q, r, s)] = None

        extra_coordinates = [
            (-1,4), (-2, 4), (-3,4),
            (4,-1), (4,-2),
            (-4,3), (-4,2), (-4,1),
            (2,-4), (1,-4),
            ]
        for coord in extra_coordinates:
            self.add_hex(coord)

    def get_neighbors(self, q, r, s):
        directions = [
            (1, -1, 0), (1, 0, -1), (0, 1, -1),
            (-1, 1, 0), (-1, 0, 1), (0, -1, 1)
        ]
        neighbors = []
        for dq, dr, ds in directions:
            neighbor = (q + dq, r + dr, s + ds)
            if neighbor in self.grid:
                neighbors.append(neighbor)
        return neighbors

    def is_valid_position(self, q, r, s):
        return (q, r, s) in self.grid and -4 <= q <= 4 and -4 <= r <= 4 and -4 <= s <= 4

    def set_tile(self, q, r, s, tile):
        if self.is_valid_position(q, r, s):
            self.grid[(q, r, s)] = tile
        else:
            raise ValueError(f"Invalid grid position: ({q}, {r}, {s})")

    def get_tile(self, q, r, s):
        if self.is_valid_position(q, r, s):
            return self.grid[(q, r, s)]
        else:
            raise ValueError(f"Invalid grid position: ({q}, {r}, {s})")

    def initialize_from_config(self, config):
        for coord, (color, pattern) in config.items():
            q, r, s = coord
            self.set_tile(q, r, s, Tile(color, pattern))

    def set_goal_positions(self, positions):
        """Set the goal positions where tiles cannot be placed."""
        self.goal_positions = set(tuple(pos) for pos in positions)
        # Remove goal positions from the grid (they're not playable spaces)
        for pos in self.goal_positions:
            if pos in self.grid:
                del self.grid[pos]

    def is_goal_position(self, q, r, s):
        """Check if a position is a goal tile position."""
        return (q, r, s) in self.goal_positions


    def __str__(self):
        result = ""
        for r in range(-3, 4):
            result += " " * (3 - abs(r))
            for q in range(-3, 4):
                s = -q - r
                if self.is_valid_position(q, r, s):
                    tile = self.get_tile(q, r, s)
                    if tile:
                        result += f"{tile.color.name[0]}{tile.pattern.name[0]} "
                    else:
                        result += ".. "
                else:
                    result += "   "
            result += "\n"
        return result

    def get_empty_positions(self):
        """Return list of positions with no tile placed."""
        return [pos for pos, tile in self.grid.items() if tile is None]

    def is_position_empty(self, q, r, s):
        """Check if a specific position is empty and valid for placement."""
        if not self.is_valid_position(q, r, s):
            return False
        return self.grid.get((q, r, s)) is None