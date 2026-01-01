import random
from typing import List, Tuple, Set, FrozenSet
from abc import ABC, abstractmethod
from hex_grid import Pattern, HexGrid, ALL_3_LINES, ALL_4_LINES, ALL_5_LINES


class Cat(ABC):
    def __init__(self, name: str, point_value: int, patterns: tuple[Pattern, Pattern] = None):
        self.name = name
        self.point_value = point_value
        self.patterns = patterns if patterns else tuple(random.sample(list(Pattern), 2))

    @abstractmethod
    def find_all_groups(self, grid: HexGrid, used_tiles: Set[Tuple[int, int, int]]) -> List[FrozenSet[Tuple[int, int, int]]]:
        """
        Find all valid scoring groups for this cat that don't use already-used tiles
        and are not adjacent to used tiles.
        Returns list of frozensets, each containing the positions in a valid group.
        """
        pass

    def score(self, grid: HexGrid, used_tiles: Set[Tuple[int, int, int]] = None) -> int:
        """
        Calculate score and return (score, newly_used_tiles).
        Cats score point_value for EACH valid non-adjacent group.
        """
        if used_tiles is None:
            used_tiles = set()
        groups = self.find_all_groups(grid, used_tiles)
        return len(groups) * self.point_value

    def score_with_usage(self, grid: HexGrid, used_tiles: Set[Tuple[int, int, int]] = None) -> Tuple[int, Set[Tuple[int, int, int]]]:
        """
        Calculate score and return (score, all_used_tiles including new ones).
        """
        if used_tiles is None:
            used_tiles = set()
        groups = self.find_all_groups(grid, used_tiles)
        new_used = used_tiles.copy()
        for group in groups:
            new_used.update(group)
        return len(groups) * self.point_value, new_used

    def check_condition(self, grid: HexGrid) -> bool:
        """Legacy method - returns True if at least one valid group exists."""
        return len(self.find_all_groups(grid, set())) > 0

    def _is_adjacent_to_used(self, grid: HexGrid, positions: Set[Tuple[int, int, int]],
                              used_tiles: Set[Tuple[int, int, int]]) -> bool:
        """Check if any position in the group is adjacent to any used tile."""
        for pos in positions:
            neighbors = set(grid.get_neighbors(*pos))
            if neighbors & used_tiles:
                return True
        return False

    def __str__(self):
        return f"{self.name} (Points: {self.point_value})"

    def __repr__(self):
        return f"Cat(name='{self.name}', point_value={self.point_value}, patterns={self.patterns})"


class CatMillie(Cat):
    """
    Millie: 3 touching tiles of the SAME pattern (must be one of her preferred patterns).
    Scores 3 points per valid group.
    """
    def __init__(self):
        patterns = random.sample(list(Pattern), 2)
        super().__init__("Millie", 3, tuple(patterns))

    def find_all_groups(self, grid: HexGrid, used_tiles: Set[Tuple[int, int, int]]) -> List[FrozenSet[Tuple[int, int, int]]]:
        valid_groups = []
        all_used = used_tiles.copy()

        # Try each of Millie's preferred patterns separately
        for pattern in self.patterns:
            # Find all groups of 3 touching tiles with this pattern
            groups = self._find_pattern_groups(grid, pattern, all_used)
            for group in groups:
                valid_groups.append(group)
                all_used.update(group)

        return valid_groups

    def _find_pattern_groups(self, grid: HexGrid, pattern: Pattern,
                              used_tiles: Set[Tuple[int, int, int]]) -> List[FrozenSet[Tuple[int, int, int]]]:
        """Find all valid 3-tile clusters of a specific pattern."""
        groups = []
        grid_dict = grid.grid  # Local reference for speed

        for pos in grid.all_positions:
            if pos in used_tiles:
                continue

            tile = grid_dict.get(pos)
            if not tile or tile.pattern != pattern:
                continue

            # Try to find a group of 3 starting from this position
            found_groups = self._find_clusters_from(grid, pos, pattern, used_tiles)
            for group in found_groups:
                # Check adjacency to used tiles
                if not self._is_adjacent_to_used(grid, group, used_tiles):
                    groups.append(group)
                    # Mark these as used for subsequent searches
                    used_tiles = used_tiles | group
                    break  # Only take one group per starting position

        return groups

    def _find_clusters_from(self, grid: HexGrid, start: Tuple[int, int, int],
                            pattern: Pattern, used_tiles: Set[Tuple[int, int, int]]) -> List[FrozenSet[Tuple[int, int, int]]]:
        """Find all valid 3-tile clusters starting from a position."""
        results = []
        self._dfs_cluster(grid, start, pattern, used_tiles, [], results)
        return results

    def _dfs_cluster(self, grid: HexGrid, pos: Tuple[int, int, int], pattern: Pattern,
                     used_tiles: Set[Tuple[int, int, int]], current: List[Tuple[int, int, int]],
                     results: List[FrozenSet[Tuple[int, int, int]]]):
        """DFS to find 3-tile clusters. Uses mutable list to avoid set copies."""
        if pos in used_tiles:
            return
        if pos in current:
            return
        if pos not in grid.grid:
            return

        tile = grid.grid.get(pos)
        if not tile or tile.pattern != pattern:
            return

        current.append(pos)

        if len(current) == 3:
            # Verify all 3 are connected (each adjacent to at least one other)
            if self._is_connected_cluster(grid, current):
                results.append(frozenset(current))
            current.pop()
            return

        # Expand to neighbors
        for neighbor in grid.get_neighbors(*pos):
            self._dfs_cluster(grid, neighbor, pattern, used_tiles, current, results)

        current.pop()

    def _is_connected_cluster(self, grid: HexGrid, positions) -> bool:
        """Check that all positions form a connected cluster."""
        positions = list(positions)
        for i, p1 in enumerate(positions):
            neighbors = grid.get_neighbors(*p1)
            has_connection = False
            for j, p2 in enumerate(positions):
                if i != j and p2 in neighbors:
                    has_connection = True
                    break
            if not has_connection:
                return False
        return True


class CatLeo(Cat):
    """
    Leo: 5 tiles in a line, all the SAME pattern (must be one of his preferred patterns).
    Scores 11 points per valid group.
    """
    def __init__(self):
        super().__init__("Leo", 11, tuple(random.sample(list(Pattern), 2)))

    def find_all_groups(self, grid: HexGrid, used_tiles: Set[Tuple[int, int, int]]) -> List[FrozenSet[Tuple[int, int, int]]]:
        """Find all valid 5-tile lines using pre-computed line positions."""
        valid_groups = []
        all_used = used_tiles.copy()
        grid_dict = grid.grid  # Local reference for speed

        for pattern in self.patterns:
            for line in ALL_5_LINES:
                # Check first tile immediately - most lines will fail here
                first_pos = line[0]
                if first_pos in all_used:
                    continue
                first_tile = grid_dict.get(first_pos)
                if not first_tile or first_tile.pattern != pattern:
                    continue

                # Check remaining tiles
                valid = True
                for pos in line[1:]:
                    if pos in all_used:
                        valid = False
                        break
                    tile = grid_dict.get(pos)
                    if not tile or tile.pattern != pattern:
                        valid = False
                        break

                if valid and not self._is_adjacent_to_used(grid, frozenset(line), all_used):
                    group = frozenset(line)
                    valid_groups.append(group)
                    all_used.update(line)

        return valid_groups

    def __str__(self):
        return f"Leo (Points: {self.point_value}, Patterns: {self.patterns})"


class CatRumi(Cat):
    """
    Rumi: 3 tiles in a line, all the SAME pattern (must be one of her preferred patterns).
    Scores 5 points per valid group.
    """
    def __init__(self):
        super().__init__("Rumi", 5, tuple(random.sample(list(Pattern), 2)))

    def find_all_groups(self, grid: HexGrid, used_tiles: Set[Tuple[int, int, int]]) -> List[FrozenSet[Tuple[int, int, int]]]:
        """Find all valid 3-tile lines using pre-computed line positions."""
        valid_groups = []
        all_used = used_tiles.copy()
        grid_dict = grid.grid  # Local reference for speed

        for pattern in self.patterns:
            for line in ALL_3_LINES:
                # Check first tile immediately - most lines will fail here
                first_pos = line[0]
                if first_pos in all_used:
                    continue
                first_tile = grid_dict.get(first_pos)
                if not first_tile or first_tile.pattern != pattern:
                    continue

                # Check remaining tiles
                valid = True
                for pos in line[1:]:
                    if pos in all_used:
                        valid = False
                        break
                    tile = grid_dict.get(pos)
                    if not tile or tile.pattern != pattern:
                        valid = False
                        break

                if valid and not self._is_adjacent_to_used(grid, frozenset(line), all_used):
                    group = frozenset(line)
                    valid_groups.append(group)
                    all_used.update(line)

        return valid_groups


class CatTecolote(Cat):
    """
    Tecolote: 4 tiles in a line, all the SAME pattern (must be one of her preferred patterns).
    Scores 7 points per valid group.
    """
    def __init__(self):
        super().__init__("Tecolote", 7, tuple(random.sample(list(Pattern), 2)))

    def find_all_groups(self, grid: HexGrid, used_tiles: Set[Tuple[int, int, int]]) -> List[FrozenSet[Tuple[int, int, int]]]:
        """Find all valid 4-tile lines using pre-computed line positions."""
        valid_groups = []
        all_used = used_tiles.copy()
        grid_dict = grid.grid  # Local reference for speed

        for pattern in self.patterns:
            for line in ALL_4_LINES:
                # Check first tile immediately - most lines will fail here
                first_pos = line[0]
                if first_pos in all_used:
                    continue
                first_tile = grid_dict.get(first_pos)
                if not first_tile or first_tile.pattern != pattern:
                    continue

                # Check remaining tiles
                valid = True
                for pos in line[1:]:
                    if pos in all_used:
                        valid = False
                        break
                    tile = grid_dict.get(pos)
                    if not tile or tile.pattern != pattern:
                        valid = False
                        break

                if valid and not self._is_adjacent_to_used(grid, frozenset(line), all_used):
                    group = frozenset(line)
                    valid_groups.append(group)
                    all_used.update(line)

        return valid_groups


# Cat buckets for random selection
# Each game selects one cat from each bucket
# Bucket 1: 4 cats including Millie (cluster-based scoring)
# Bucket 2: 4 cats including Rumi (3-in-a-line scoring)
# Bucket 3: 2 cats including Leo (5-in-a-line scoring)
BUCKET_1 = [CatMillie]  # Will expand to 4 cats
BUCKET_2 = [CatRumi, CatTecolote]  # Will expand to 4 cats
BUCKET_3 = [CatLeo]     # Will expand to 2 cats

# Legacy list for backwards compatibility
ALL_CATS = [CatMillie, CatLeo, CatRumi, CatTecolote]


def initialize_game_cats(use_buckets: bool = True) -> Tuple[List[Cat], List[Pattern]]:
    """
    Initialize 3 cats with non-overlapping pattern assignments.

    Args:
        use_buckets: If True, select one cat from each bucket (default).
                     If False, use legacy random selection from ALL_CATS.

    Returns:
        Tuple of (list of 3 Cat instances, remaining unused patterns)
    """
    if use_buckets:
        # Select one cat from each bucket
        cat_from_bucket_1 = random.choice(BUCKET_1)
        cat_from_bucket_2 = random.choice(BUCKET_2)
        cat_from_bucket_3 = random.choice(BUCKET_3)
        chosen_cats = [cat_from_bucket_1, cat_from_bucket_2, cat_from_bucket_3]
    else:
        # Legacy: random selection from all cats
        chosen_cats = random.sample(ALL_CATS, 3)

    # Shuffle patterns and assign 2 to each cat (non-overlapping)
    all_patterns = list(Pattern)
    random.shuffle(all_patterns)

    cats = []
    for cat_class in chosen_cats:
        cat_patterns = tuple(all_patterns[:2])
        all_patterns = all_patterns[2:]
        cat = cat_class()
        cat.patterns = cat_patterns
        cats.append(cat)

    return cats, all_patterns
