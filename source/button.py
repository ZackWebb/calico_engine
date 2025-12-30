"""
Button scoring for Calico.

Buttons are awarded for groups of 3 adjacent tiles of the same color.
- Each button is worth 3 points
- Multiple buttons of the same color are allowed if groups are separated
- Groups of different colors can be adjacent without interference
- Rainbow button (+5 pts) awarded if player has at least one button of each color
"""
from typing import List, Tuple, Set, Dict, FrozenSet
from hex_grid import HexGrid
from tile import Color


BUTTON_POINTS = 3
RAINBOW_BUTTON_POINTS = 5


def find_color_groups(grid: HexGrid, color: Color,
                      used_tiles: Set[Tuple[int, int, int]]) -> List[FrozenSet[Tuple[int, int, int]]]:
    """
    Find all valid 3-tile clusters of a specific color.
    Groups must be separated (not adjacent to other used tiles of same color).
    """
    groups = []
    local_used = used_tiles.copy()

    for pos in grid.all_positions:
        if pos in local_used:
            continue

        tile = grid.grid.get(pos)
        if not tile or tile.color != color:
            continue

        # Try to find a group of 3 starting from this position
        found_groups = _find_clusters_from(grid, pos, color, local_used)
        for group in found_groups:
            # Check adjacency to already-used tiles of same color
            if not _is_adjacent_to_used(grid, group, local_used):
                groups.append(group)
                local_used.update(group)
                break  # Only take one group per starting position

    return groups


def _find_clusters_from(grid: HexGrid, start: Tuple[int, int, int],
                        color: Color, used_tiles: Set[Tuple[int, int, int]]) -> List[FrozenSet[Tuple[int, int, int]]]:
    """Find all valid 3-tile clusters starting from a position."""
    results = []
    _dfs_cluster(grid, start, color, used_tiles, set(), results)
    return results


def _dfs_cluster(grid: HexGrid, pos: Tuple[int, int, int], color: Color,
                 used_tiles: Set[Tuple[int, int, int]], current: Set[Tuple[int, int, int]],
                 results: List[FrozenSet[Tuple[int, int, int]]]):
    """DFS to find 3-tile clusters."""
    if pos in used_tiles or pos in current:
        return
    if pos not in grid.grid:
        return

    tile = grid.grid.get(pos)
    if not tile or tile.color != color:
        return

    current = current | {pos}

    if len(current) == 3:
        # Verify all 3 are connected (each adjacent to at least one other)
        if _is_connected_cluster(grid, current):
            results.append(frozenset(current))
        return

    # Expand to neighbors
    for neighbor in grid.get_neighbors(*pos):
        _dfs_cluster(grid, neighbor, color, used_tiles, current, results)


def _is_connected_cluster(grid: HexGrid, positions: Set[Tuple[int, int, int]]) -> bool:
    """Check that all positions form a connected cluster."""
    positions = list(positions)
    for i, p1 in enumerate(positions):
        neighbors = set(grid.get_neighbors(*p1))
        other_positions = set(positions[:i] + positions[i+1:])
        if not neighbors & other_positions:
            return False
    return True


def _is_adjacent_to_used(grid: HexGrid, positions: Set[Tuple[int, int, int]],
                          used_tiles: Set[Tuple[int, int, int]]) -> bool:
    """Check if any position in the group is adjacent to any used tile."""
    for pos in positions:
        neighbors = set(grid.get_neighbors(*pos))
        if neighbors & used_tiles:
            return True
    return False


def count_buttons_by_color(grid: HexGrid) -> Dict[Color, int]:
    """
    Count the number of buttons earned for each color.
    Returns dict mapping Color -> number of buttons.
    """
    button_counts = {}

    for color in Color:
        # Each color tracks its own used tiles independently
        groups = find_color_groups(grid, color, set())
        button_counts[color] = len(groups)

    return button_counts


def score_buttons(grid: HexGrid) -> int:
    """
    Calculate total button score for a grid.
    Returns total points from all buttons + rainbow bonus if applicable.
    """
    button_counts = count_buttons_by_color(grid)

    total_buttons = sum(button_counts.values())
    button_score = total_buttons * BUTTON_POINTS

    # Check for rainbow button (at least one of each color)
    has_rainbow = all(count >= 1 for count in button_counts.values())
    rainbow_score = RAINBOW_BUTTON_POINTS if has_rainbow else 0

    return button_score + rainbow_score


def get_button_details(grid: HexGrid) -> Dict:
    """
    Get detailed breakdown of button scoring.
    Returns dict with counts per color, total score, and rainbow status.
    """
    button_counts = count_buttons_by_color(grid)
    total_buttons = sum(button_counts.values())
    has_rainbow = all(count >= 1 for count in button_counts.values())

    return {
        'buttons_by_color': button_counts,
        'total_buttons': total_buttons,
        'button_score': total_buttons * BUTTON_POINTS,
        'has_rainbow': has_rainbow,
        'rainbow_score': RAINBOW_BUTTON_POINTS if has_rainbow else 0,
        'total_score': total_buttons * BUTTON_POINTS + (RAINBOW_BUTTON_POINTS if has_rainbow else 0)
    }
