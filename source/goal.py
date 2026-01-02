from abc import ABC, abstractmethod
from typing import List, Tuple
from collections import Counter

from hex_grid import HexGrid


class GoalTile(ABC):
    """Abstract base class for goal tiles."""

    def __init__(self, name: str, position: Tuple[int, int, int]):
        self.name = name
        self.position = position

    @abstractmethod
    def score(self, grid: HexGrid) -> int:
        """Calculate score based on neighboring tiles."""
        pass

    def get_neighbors(self, grid: HexGrid) -> List[Tuple[int, int, int]]:
        """Get the 6 neighbor positions for this goal."""
        return grid.get_neighbors(*self.position)

    def get_neighbor_tiles(self, grid: HexGrid):
        """Get the actual tiles from neighbor positions."""
        tiles = []
        for pos in self.get_neighbors(grid):
            tile = grid.grid.get(pos)
            if tile is not None:
                tiles.append(tile)
        return tiles

    def __repr__(self):
        return f"GoalTile({self.name}, {self.position})"


class GoalAAA_BBB(GoalTile):
    """
    AAA-BBB goal: 6 neighbors must have 3 of color A and 3 of color B,
    OR 3 of pattern A and 3 of pattern B.
    - 8 points for either condition
    - 13 points if BOTH conditions met
    """

    def __init__(self, position: Tuple[int, int, int] = (-2, 1, 1)):
        super().__init__("AAA-BBB", position)

    def score(self, grid: HexGrid) -> int:
        tiles = self.get_neighbor_tiles(grid)

        # Need exactly 6 neighbors filled
        if len(tiles) != 6:
            return 0

        color_met = self._check_3_3_condition([t.color for t in tiles])
        pattern_met = self._check_3_3_condition([t.pattern for t in tiles])

        if color_met and pattern_met:
            return 13
        elif color_met or pattern_met:
            return 8
        return 0

    def _check_3_3_condition(self, values: list) -> bool:
        """Check if values have exactly 3 of one type and 3 of another."""
        counts = Counter(values)
        count_values = sorted(counts.values(), reverse=True)
        return count_values == [3, 3]


class GoalAA_BB_CC(GoalTile):
    """
    AA-BB-CC goal: 6 neighbors must have 2 each of 3 colors,
    OR 2 each of 3 patterns.
    - 7 points for either condition
    - 11 points if BOTH conditions met
    """

    def __init__(self, position: Tuple[int, int, int] = (1, -1, 0)):
        super().__init__("AA-BB-CC", position)

    def score(self, grid: HexGrid) -> int:
        tiles = self.get_neighbor_tiles(grid)

        # Need exactly 6 neighbors filled
        if len(tiles) != 6:
            return 0

        color_met = self._check_2_2_2_condition([t.color for t in tiles])
        pattern_met = self._check_2_2_2_condition([t.pattern for t in tiles])

        if color_met and pattern_met:
            return 11
        elif color_met or pattern_met:
            return 7
        return 0

    def _check_2_2_2_condition(self, values: list) -> bool:
        """Check if values have exactly 2 each of 3 different types."""
        counts = Counter(values)
        count_values = sorted(counts.values(), reverse=True)
        return count_values == [2, 2, 2]


class GoalAllUnique(GoalTile):
    """
    All Unique goal: 6 neighbors must all be different colors,
    OR all different patterns.
    - 10 points for either condition
    - 15 points if BOTH conditions met (6 unique colors AND 6 unique patterns)
    """

    def __init__(self, position: Tuple[int, int, int] = (0, 1, -1)):
        super().__init__("All Unique", position)

    def score(self, grid: HexGrid) -> int:
        tiles = self.get_neighbor_tiles(grid)

        # Need exactly 6 neighbors filled
        if len(tiles) != 6:
            return 0

        colors = [t.color for t in tiles]
        patterns = [t.pattern for t in tiles]

        color_met = len(set(colors)) == 6
        pattern_met = len(set(patterns)) == 6

        if color_met and pattern_met:
            return 15
        elif color_met or pattern_met:
            return 10
        return 0


class GoalAAAA_BB(GoalTile):
    """
    AAAA-BB goal: 6 neighbors must have 4 of color A and 2 of color B,
    OR 4 of pattern A and 2 of pattern B.
    - 7 points for either condition
    - 14 points if BOTH conditions met
    """

    def __init__(self, position: Tuple[int, int, int] = (-2, 1, 1)):
        super().__init__("AAAA-BB", position)

    def score(self, grid: HexGrid) -> int:
        tiles = self.get_neighbor_tiles(grid)

        # Need exactly 6 neighbors filled
        if len(tiles) != 6:
            return 0

        color_met = self._check_4_2_condition([t.color for t in tiles])
        pattern_met = self._check_4_2_condition([t.pattern for t in tiles])

        if color_met and pattern_met:
            return 14
        elif color_met or pattern_met:
            return 7
        return 0

    def _check_4_2_condition(self, values: list) -> bool:
        """Check if values have exactly 4 of one type and 2 of another."""
        counts = Counter(values)
        count_values = sorted(counts.values(), reverse=True)
        return count_values == [4, 2]


class GoalAA_BB_C_D(GoalTile):
    """
    AA-BB-C-D goal: 6 neighbors must have 2 each of 2 colors + 1 each of a 3rd and 4th color,
    OR 2 each of 2 patterns + 1 each of a 3rd and 4th pattern.
    - 5 points for either condition
    - 7 points if BOTH conditions met
    """

    def __init__(self, position: Tuple[int, int, int] = (1, -1, 0)):
        super().__init__("AA-BB-C-D", position)

    def score(self, grid: HexGrid) -> int:
        tiles = self.get_neighbor_tiles(grid)

        # Need exactly 6 neighbors filled
        if len(tiles) != 6:
            return 0

        color_met = self._check_2_2_1_1_condition([t.color for t in tiles])
        pattern_met = self._check_2_2_1_1_condition([t.pattern for t in tiles])

        if color_met and pattern_met:
            return 7
        elif color_met or pattern_met:
            return 5
        return 0

    def _check_2_2_1_1_condition(self, values: list) -> bool:
        """Check if values have 2 each of 2 types and 1 each of 2 other types."""
        counts = Counter(values)
        count_values = sorted(counts.values(), reverse=True)
        return count_values == [2, 2, 1, 1]


class GoalAAA_BB_C(GoalTile):
    """
    AAA-BB-C goal: 6 neighbors must have 3 of Color 1, 2 of color 2, and 1 of a third color,
    OR 3 of Pattern 1, 2 of pattern 2, and 1 of a third pattern.
    - 7 points for either condition
    - 11 points if BOTH conditions met
    """

    def __init__(self, position: Tuple[int, int, int] = (0, 1, -1)):
        super().__init__("AAA-BB-C", position)

    def score(self, grid: HexGrid) -> int:
        tiles = self.get_neighbor_tiles(grid)

        # Need exactly 6 neighbors filled
        if len(tiles) != 6:
            return 0

        color_met = self._check_3_2_1_condition([t.color for t in tiles])
        pattern_met = self._check_3_2_1_condition([t.pattern for t in tiles])

        if color_met and pattern_met:
            return 11
        elif color_met or pattern_met:
            return 7
        return 0

    def _check_3_2_1_condition(self, values: list) -> bool:
        """Check if values have 3 of one type, 2 of another, and 1 of a third."""
        counts = Counter(values)
        count_values = sorted(counts.values(), reverse=True)
        return count_values == [3, 2, 1]


# All available goal tile classes
ALL_GOAL_CLASSES = [
    GoalAAA_BBB,     # 3-3 split: 8 or 13 points
    GoalAA_BB_CC,    # 2-2-2 split: 7 or 11 points
    GoalAllUnique,   # 6 unique: 10 or 15 points
    GoalAAAA_BB,     # 4-2 split: 7 or 14 points
    GoalAA_BB_C_D,   # 2-2-1-1 split: 5 or 7 points
    GoalAAA_BB_C,    # 3-2-1 split: 7 or 11 points
]


def create_random_goals() -> List[GoalTile]:
    """
    Create 3 randomly selected goal tiles from the 6 available types,
    randomly arranged on the 3 goal positions.

    Returns:
        List of 3 goal tiles with randomly selected types at randomized positions.
    """
    import random
    from board_configurations import GOAL_POSITIONS

    # Randomly select 3 goal types from the 6 available
    selected_classes = random.sample(ALL_GOAL_CLASSES, 3)

    # Shuffle positions for random arrangement
    positions = list(GOAL_POSITIONS)
    random.shuffle(positions)

    # Create goal instances at the shuffled positions
    goals = []
    for goal_class, position in zip(selected_classes, positions):
        goals.append(goal_class(position))

    return goals


def create_default_goals() -> List[GoalTile]:
    """Create the three default goal tiles."""
    return [
        GoalAAA_BBB((-2, 1, 1)),
        GoalAA_BB_CC((1, -1, 0)),
        GoalAllUnique((0, 1, -1)),
    ]
