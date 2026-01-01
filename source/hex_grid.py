from tile import Tile, Color, Pattern

# Hex grid neighbor directions (constant)
_HEX_DIRECTIONS = (
    (1, -1, 0), (1, 0, -1), (0, 1, -1),
    (-1, 1, 0), (-1, 0, 1), (0, -1, 1)
)

# Line directions for cat scoring (only need 3 - opposite directions give same lines)
_LINE_DIRECTIONS = (
    (1, 0, -1),   # east
    (1, -1, 0),   # northeast
    (0, -1, 1),   # northwest
)


def _build_all_grid_positions():
    """Build the set of all valid grid positions (matches HexGrid.initialize_grid)."""
    positions = set()
    # Main hex area
    for q in range(-3, 4):
        for r in range(-3, 4):
            s = -q - r
            if abs(s) <= 3:
                positions.add((q, r, s))
    # Extra coordinates
    extras = [
        (-1, 4), (-2, 4), (-3, 4),
        (4, -1), (4, -2),
        (-4, 3), (-4, 2), (-4, 1),
        (2, -4), (1, -4),
    ]
    for q, r in extras:
        positions.add((q, r, -q - r))
    return positions


def _enumerate_lines(positions, length):
    """
    Enumerate all valid lines of given length on the hex grid.
    Returns tuple of tuples, each inner tuple is a line (sequence of positions).
    """
    lines = []
    for start in positions:
        q, r, s = start
        for dq, dr, ds in _LINE_DIRECTIONS:
            line = []
            valid = True
            for i in range(length):
                pos = (q + dq * i, r + dr * i, s + ds * i)
                if pos not in positions:
                    valid = False
                    break
                line.append(pos)
            if valid:
                lines.append(tuple(line))
    return tuple(lines)


# Pre-compute all valid lines at module load time
_ALL_POSITIONS = _build_all_grid_positions()
ALL_3_LINES = _enumerate_lines(_ALL_POSITIONS, 3)  # For Rumi (5 pts)
ALL_4_LINES = _enumerate_lines(_ALL_POSITIONS, 4)  # For future cat
ALL_5_LINES = _enumerate_lines(_ALL_POSITIONS, 5)  # For Leo (11 pts)

class HexGrid:
    __slots__ = ('grid', 'goal_positions', '_neighbor_cache', '_all_positions_cache')

    def __init__(self):
        self.grid = {}
        self.goal_positions = set()  # Positions where goals are placed (cannot place tiles)
        self._neighbor_cache = {}
        self._all_positions_cache = None
        self.initialize_grid()
        self._build_neighbor_cache()

    def _build_neighbor_cache(self):
        """Pre-compute neighbors for all positions (called after grid is built)."""
        for pos in self.grid:
            q, r, s = pos
            self._neighbor_cache[pos] = tuple(
                (q + dq, r + dr, s + ds)
                for dq, dr, ds in _HEX_DIRECTIONS
                if (q + dq, r + dr, s + ds) in self.grid
            )
        self._all_positions_cache = None  # Invalidate cache

    @property
    def all_positions(self):
        """Return all valid positions in the grid (cached)."""
        if self._all_positions_cache is None:
            self._all_positions_cache = tuple(self.grid.keys())
        return self._all_positions_cache

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
        """Return cached neighbors for position (O(1) lookup)."""
        return self._neighbor_cache.get((q, r, s), ())

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
        # Rebuild neighbor cache after grid modification
        self._build_neighbor_cache()

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

    def __copy__(self):
        """Shallow copy - shares Tile refs and neighbor cache (structure is immutable)."""
        new_grid = object.__new__(HexGrid)
        new_grid.grid = self.grid.copy()  # Shallow dict copy
        new_grid.goal_positions = self.goal_positions  # Share immutable set
        new_grid._neighbor_cache = self._neighbor_cache  # Share cache
        new_grid._all_positions_cache = self._all_positions_cache  # Share cache
        return new_grid