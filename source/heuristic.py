"""
Heuristic evaluation functions for Calico MCTS.

Estimates the final score from a partial game state by:
1. Counting current scoring (cats, goals, buttons)
2. Adding potential points for near-complete patterns
"""
from typing import List, Set, Tuple
from collections import Counter

from hex_grid import HexGrid, Pattern, Color
from cat import Cat, CatMillie, CatLeo, CatRumi
from button import score_buttons, count_buttons_by_color


def evaluate_state(game) -> float:
    """
    Estimate final score from current game state.

    Args:
        game: SimulationMode instance

    Returns:
        Estimated final score as float
    """
    grid = game.player.grid

    score = 0.0
    score += evaluate_cats(game)
    score += evaluate_goals(game)
    score += evaluate_buttons(grid)

    return score


def evaluate_cats(game) -> float:
    """
    Evaluate cat scoring: current score plus potential from partial matches.
    """
    grid = game.player.grid
    total = 0.0

    for cat in game.cats:
        # Current actual score
        actual_score = cat.score(grid)
        total += actual_score

        # Potential from incomplete groups
        potential = estimate_cat_potential(grid, cat)
        total += potential

    return total


def estimate_cat_potential(grid: HexGrid, cat: Cat) -> float:
    """
    Estimate additional points possible from partial pattern matches.

    For each cat type:
    - Millie (3 touching): pairs of matching patterns = 30% potential
    - Leo (5 in line): 4 in line = 50%, 3 in line = 20% potential
    - Rumi (3 in line): 2 in line = 30% potential
    """
    potential = 0.0

    for pattern in cat.patterns:
        if isinstance(cat, CatMillie):
            # Millie needs 3 touching tiles
            cluster_sizes = find_pattern_cluster_sizes(grid, pattern)
            for size in cluster_sizes:
                if size == 2:
                    potential += cat.point_value * 0.3  # Pair is promising

        elif isinstance(cat, CatLeo):
            # Leo needs 5 in a line
            line_lengths = find_line_lengths(grid, pattern)
            for length in line_lengths:
                if length == 4:
                    potential += cat.point_value * 0.5
                elif length == 3:
                    potential += cat.point_value * 0.2

        elif isinstance(cat, CatRumi):
            # Rumi needs 3 in a line
            line_lengths = find_line_lengths(grid, pattern)
            for length in line_lengths:
                if length == 2:
                    potential += cat.point_value * 0.3

    return potential


def find_pattern_cluster_sizes(grid: HexGrid, pattern: Pattern) -> List[int]:
    """
    Find sizes of all connected clusters of tiles with given pattern.
    Uses BFS to find connected components.
    """
    visited: Set[Tuple[int, int, int]] = set()
    sizes = []

    for pos in grid.all_positions:
        if pos in visited:
            continue

        tile = grid.grid.get(pos)
        if tile is None or tile.pattern != pattern:
            continue

        # BFS to find connected cluster
        cluster_size = 0
        queue = [pos]

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue

            current_tile = grid.grid.get(current)
            if current_tile is None or current_tile.pattern != pattern:
                continue

            visited.add(current)
            cluster_size += 1

            for neighbor in grid.get_neighbors(*current):
                if neighbor not in visited:
                    queue.append(neighbor)

        if cluster_size > 0:
            sizes.append(cluster_size)

    return sizes


def find_line_lengths(grid: HexGrid, pattern: Pattern) -> List[int]:
    """
    Find lengths of line segments with given pattern in all 3 hex directions.
    Only counts lines of length >= 2.
    """
    directions = [
        (1, 0, -1),   # east
        (1, -1, 0),   # northeast
        (0, -1, 1),   # northwest
    ]

    lengths = []
    counted_lines: Set[frozenset] = set()  # Avoid double-counting

    for pos in grid.all_positions:
        tile = grid.grid.get(pos)
        if tile is None or tile.pattern != pattern:
            continue

        for dq, dr, ds in directions:
            # Count length in positive direction from this position
            line_positions = [pos]
            q, r, s = pos

            while True:
                q, r, s = q + dq, r + dr, s + ds
                next_pos = (q, r, s)
                next_tile = grid.grid.get(next_pos)

                if next_tile is None or next_tile.pattern != pattern:
                    break

                line_positions.append(next_pos)

            length = len(line_positions)
            if length >= 2:
                # Create hashable key to avoid duplicates
                line_key = frozenset(line_positions)
                if line_key not in counted_lines:
                    counted_lines.add(line_key)
                    lengths.append(length)

    return lengths


def evaluate_goals(game) -> float:
    """
    Evaluate goal scoring: current score plus potential from partial progress.
    """
    grid = game.player.grid
    total = 0.0

    for goal in game.goals:
        # Current actual score
        actual = goal.score(grid)
        total += actual

        # If not fully scored, estimate potential
        if actual == 0:
            potential = estimate_goal_potential(grid, goal)
            total += potential

    return total


def estimate_goal_potential(grid: HexGrid, goal) -> float:
    """
    Estimate potential for a goal based on filled neighbors.

    Awards partial credit scaled by:
    - Number of neighbors filled (out of 6)
    - Whether current distribution is compatible with goal
    """
    tiles = goal.get_neighbor_tiles(grid)
    filled_count = len(tiles)

    if filled_count == 0:
        return 0.0

    # Completion ratio
    completion_ratio = filled_count / 6.0

    # Check partial pattern match based on goal type
    goal_name = goal.name
    progress = 0.0

    if goal_name == "AAA-BBB":
        # Need 3-3 distribution
        max_points = 7.0
        progress = check_3_3_progress(tiles)
    elif goal_name == "AA-BB-CC":
        # Need 2-2-2 distribution
        max_points = 7.0
        progress = check_2_2_2_progress(tiles)
    elif goal_name == "All Unique":
        # Need all different
        max_points = 10.0
        progress = check_unique_progress(tiles)
    else:
        return 0.0

    # Scale by progress, completion ratio, and discount factor
    discount = 0.4  # Don't overvalue incomplete goals
    return max_points * progress * completion_ratio * discount


def check_3_3_progress(tiles) -> float:
    """
    Check how close tiles are to 3-3 distribution.
    Returns 0.0 to 1.0 progress score.
    """
    if not tiles:
        return 0.0

    # Check both colors and patterns
    color_progress = _check_3_3_for_values([t.color for t in tiles])
    pattern_progress = _check_3_3_for_values([t.pattern for t in tiles])

    return max(color_progress, pattern_progress)


def _check_3_3_for_values(values) -> float:
    """Check 3-3 progress for a list of values."""
    counts = Counter(values)
    sorted_counts = sorted(counts.values(), reverse=True)

    # Perfect would be [3, 3] for 6 tiles
    # For fewer tiles, check if trending toward 3-3
    if len(sorted_counts) == 0:
        return 0.0
    elif len(sorted_counts) == 1:
        # All same - bad for 3-3
        return 0.2
    elif len(sorted_counts) == 2:
        # Two types - good!
        # Best is equal split
        diff = abs(sorted_counts[0] - sorted_counts[1])
        if diff <= 1:
            return 0.8
        else:
            return 0.5
    else:
        # More than 2 types - getting worse
        return 0.3


def check_2_2_2_progress(tiles) -> float:
    """
    Check how close tiles are to 2-2-2 distribution.
    Returns 0.0 to 1.0 progress score.
    """
    if not tiles:
        return 0.0

    color_progress = _check_2_2_2_for_values([t.color for t in tiles])
    pattern_progress = _check_2_2_2_for_values([t.pattern for t in tiles])

    return max(color_progress, pattern_progress)


def _check_2_2_2_for_values(values) -> float:
    """Check 2-2-2 progress for a list of values."""
    counts = Counter(values)
    sorted_counts = sorted(counts.values(), reverse=True)

    # Perfect would be [2, 2, 2] for 6 tiles
    if len(sorted_counts) == 0:
        return 0.0
    elif len(sorted_counts) == 1:
        # All same - bad
        return 0.1
    elif len(sorted_counts) == 2:
        # Two types - okay
        return 0.4
    elif len(sorted_counts) == 3:
        # Three types - good!
        # Check if counts are balanced
        if sorted_counts == [2, 2, 2]:
            return 1.0
        elif max(sorted_counts) <= 3:
            return 0.7
        else:
            return 0.5
    else:
        # More than 3 types - getting harder
        return 0.3


def check_unique_progress(tiles) -> float:
    """
    Check how close tiles are to all unique.
    Returns 0.0 to 1.0 progress score.
    """
    if not tiles:
        return 0.0

    color_progress = _check_unique_for_values([t.color for t in tiles])
    pattern_progress = _check_unique_for_values([t.pattern for t in tiles])

    return max(color_progress, pattern_progress)


def _check_unique_for_values(values) -> float:
    """Check uniqueness progress for a list of values."""
    if not values:
        return 0.0

    unique_count = len(set(values))
    total_count = len(values)

    # All unique is perfect
    if unique_count == total_count:
        return 1.0
    else:
        # Some duplicates - progress based on ratio
        return unique_count / total_count


def evaluate_buttons(grid: HexGrid) -> float:
    """
    Evaluate button scoring: current score plus potential from color pairs.
    """
    # Current button score
    current_score = score_buttons(grid)

    # Potential from color pairs (adjacent same-color not yet in button)
    pair_potential = 0.0
    for color in Color:
        pairs = count_color_pairs(grid, color)
        pair_potential += pairs * 1.0  # Each pair worth ~1 potential point

    # Rainbow potential
    button_counts = count_buttons_by_color(grid)
    colors_with_buttons = sum(1 for count in button_counts.values() if count >= 1)

    rainbow_potential = 0.0
    if colors_with_buttons >= 5:
        rainbow_potential = 4.0  # Close to rainbow bonus
    elif colors_with_buttons >= 4:
        rainbow_potential = 2.5

    return current_score + pair_potential + rainbow_potential


def count_color_pairs(grid: HexGrid, color: Color) -> int:
    """
    Count pairs of adjacent tiles with same color.
    Only counts pairs, not larger groups (those are already buttons).
    """
    counted: Set[frozenset] = set()
    pairs = 0

    for pos in grid.all_positions:
        tile = grid.grid.get(pos)
        if tile is None or tile.color != color:
            continue

        # Check neighbors for same-color tiles
        neighbors_same_color = 0
        for neighbor_pos in grid.get_neighbors(*pos):
            neighbor = grid.grid.get(neighbor_pos)
            if neighbor is not None and neighbor.color == color:
                neighbors_same_color += 1

                # Count as pair if not already counted
                pair_key = frozenset([pos, neighbor_pos])
                if pair_key not in counted:
                    counted.add(pair_key)

        # Only count if this position has exactly 1 same-color neighbor
        # (larger groups are already scoring as buttons)
        if neighbors_same_color == 1:
            pairs += 1

    # Divide by 2 since we counted each pair twice
    return pairs // 2
