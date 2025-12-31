"""
Heuristic evaluation functions for Calico MCTS.

Estimates the final score from a partial game state by:
1. Counting current scoring (cats, goals, buttons)
2. Adding potential points for near-complete patterns
"""
from typing import List, Set, Tuple, Optional
from collections import Counter
from functools import lru_cache

from hex_grid import HexGrid, Pattern, Color
from cat import Cat, CatMillie, CatLeo, CatRumi
from button import score_buttons, count_buttons_by_color


# Decay factors for overlapping lines - more complete lines have higher backup value
OVERLAP_DECAY = {
    4: 0.70,  # 4/5 complete - backup line worth 70%
    3: 0.40,  # 3/5 complete - backup line worth 40%
    2: 0.20,  # 2/5 complete - backup line worth 20%
}

# Cache for line enumerations (board structure doesn't change)
_cached_5_lines: Optional[List[List[Tuple[int, int, int]]]] = None
_cached_3_lines: Optional[List[List[Tuple[int, int, int]]]] = None


def enumerate_all_5_lines(grid: HexGrid) -> List[List[Tuple[int, int, int]]]:
    """
    Return all valid 5-position lines on the board.

    A line is valid if all 5 positions exist in grid.all_positions.
    Uses caching since board structure doesn't change during a game.
    """
    global _cached_5_lines
    if _cached_5_lines is not None:
        return _cached_5_lines

    lines = []
    all_pos = set(grid.all_positions)

    # Three hex directions
    directions = [
        (1, 0, -1),   # east
        (1, -1, 0),   # northeast
        (0, -1, 1),   # northwest
    ]

    for start_pos in all_pos:
        for dq, dr, ds in directions:
            line = [start_pos]
            q, r, s = start_pos
            for _ in range(4):
                q += dq
                r += dr
                s += ds
                if (q, r, s) not in all_pos:
                    break
                line.append((q, r, s))
            if len(line) == 5:
                # Avoid duplicates (only keep if start < end lexicographically)
                if line[0] < line[4]:
                    lines.append(line)

    _cached_5_lines = lines
    return lines


def enumerate_all_3_lines(grid: HexGrid) -> List[List[Tuple[int, int, int]]]:
    """
    Return all valid 3-position lines on the board.

    A line is valid if all 3 positions exist in grid.all_positions.
    Uses caching since board structure doesn't change during a game.
    """
    global _cached_3_lines
    if _cached_3_lines is not None:
        return _cached_3_lines

    lines = []
    all_pos = set(grid.all_positions)

    # Three hex directions
    directions = [
        (1, 0, -1),   # east
        (1, -1, 0),   # northeast
        (0, -1, 1),   # northwest
    ]

    for start_pos in all_pos:
        for dq, dr, ds in directions:
            line = [start_pos]
            q, r, s = start_pos
            for _ in range(2):
                q += dq
                r += dr
                s += ds
                if (q, r, s) not in all_pos:
                    break
                line.append((q, r, s))
            if len(line) == 3:
                # Avoid duplicates (only keep if start < end lexicographically)
                if line[0] < line[2]:
                    lines.append(line)

    _cached_3_lines = lines
    return lines


def evaluate_line_for_pattern(
    grid: HexGrid,
    line: List[Tuple[int, int, int]],
    pattern: Pattern
) -> Tuple[int, bool]:
    """
    Evaluate a line for a specific pattern.

    Args:
        grid: The hex grid
        line: List of positions forming the line
        pattern: The pattern to check for

    Returns:
        (matching_count, is_blocked)
        - matching_count: Number of tiles with this pattern
        - is_blocked: True if any tile has a DIFFERENT pattern (line is dead)
    """
    matching = 0
    blocked = False

    for pos in line:
        tile = grid.grid.get(pos)
        if tile is None:
            continue  # Empty space - doesn't block
        elif tile.pattern == pattern:
            matching += 1
        else:
            blocked = True  # Wrong pattern placed - line cannot be completed

    return matching, blocked


def evaluate_leo_potential(grid: HexGrid, cat: Cat) -> float:
    """
    Evaluate Leo's 5-in-line potential with overlap decay.

    Considers ALL 5-position lines on the board, counting matching tiles
    even if non-consecutive. Lines blocked by wrong patterns score 0.
    Overlapping lines get diminishing returns based on progress.
    """
    all_lines = enumerate_all_5_lines(grid)
    total = 0.0

    for pattern in cat.patterns:
        # Collect all valid lines with their progress
        line_scores = []
        for line in all_lines:
            count, blocked = evaluate_line_for_pattern(grid, line, pattern)
            if not blocked and count >= 2:
                # Base potential based on progress toward 5
                if count == 4:
                    base_potential = cat.point_value * 0.5
                elif count == 3:
                    base_potential = cat.point_value * 0.3
                else:  # count == 2
                    base_potential = cat.point_value * 0.15
                line_scores.append((count, base_potential, frozenset(line)))

        # Sort by progress (most complete first)
        line_scores.sort(key=lambda x: x[0], reverse=True)

        # Award full points for best line, decayed points for overlapping alternatives
        awarded_positions: Set[Tuple[int, int, int]] = set()
        for count, potential, positions in line_scores:
            overlap = len(awarded_positions & positions)
            if overlap == 0:
                # No overlap - full value
                total += potential
            else:
                # Overlapping - apply decay based on progress
                decay = OVERLAP_DECAY.get(count, 0.2)
                total += potential * decay

            awarded_positions |= positions

    return total


def evaluate_rumi_potential(grid: HexGrid, cat: Cat) -> float:
    """
    Evaluate Rumi's 3-in-line potential with overlap decay.

    Similar to Leo but for 3-position lines.
    """
    all_lines = enumerate_all_3_lines(grid)
    total = 0.0

    for pattern in cat.patterns:
        line_scores = []
        for line in all_lines:
            count, blocked = evaluate_line_for_pattern(grid, line, pattern)
            if not blocked and count == 2:
                # 2/3 complete
                line_scores.append((count, cat.point_value * 0.3, frozenset(line)))

        # Sort and apply overlap decay
        awarded_positions: Set[Tuple[int, int, int]] = set()
        for count, potential, positions in line_scores:
            if len(awarded_positions & positions) == 0:
                total += potential
            else:
                total += potential * 0.3  # Lower decay for 3-lines
            awarded_positions |= positions

    return total


def evaluate_millie_potential(grid: HexGrid, pattern: Pattern, point_value: int) -> float:
    """
    Evaluate Millie's cluster potential, only scoring pairs if a 3rd space is available.

    A pair of adjacent same-pattern tiles only counts as potential if there's
    at least one empty space adjacent to either tile that could complete the cluster.
    """
    potential = 0.0
    counted_pairs: Set[frozenset] = set()

    for pos in grid.all_positions:
        tile = grid.grid.get(pos)
        if tile is None or tile.pattern != pattern:
            continue

        # Check each neighbor for same pattern
        for neighbor_pos in grid.get_neighbors(*pos):
            neighbor = grid.grid.get(neighbor_pos)
            if neighbor is None or neighbor.pattern != pattern:
                continue

            # Found a pair - avoid double counting
            pair_key = frozenset([pos, neighbor_pos])
            if pair_key in counted_pairs:
                continue
            counted_pairs.add(pair_key)

            # Check if 3rd space exists (empty and adjacent to either tile)
            pair_neighbors = set(grid.get_neighbors(*pos)) | set(grid.get_neighbors(*neighbor_pos))
            pair_neighbors -= {pos, neighbor_pos}

            has_third_space = any(
                grid.grid.get(n) is None  # Empty space available
                for n in pair_neighbors
                if n in grid.grid
            )

            if has_third_space:
                potential += point_value * 0.3

    return potential


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

    Uses improved evaluation that:
    - Considers non-consecutive tiles in lines (e.g., A _ _ _ A)
    - Properly handles blocking (wrong patterns make line impossible)
    - Applies diminishing returns for overlapping lines
    - Only scores Millie pairs if a 3rd space is available

    For each cat type:
    - Millie (3 touching): pairs with available 3rd space = 30% potential
    - Leo (5 in line): 4/5 = 50%, 3/5 = 30%, 2/5 = 15% (with overlap decay)
    - Rumi (3 in line): 2/3 = 30% (with overlap decay)
    """
    if isinstance(cat, CatMillie):
        # Sum potential for each pattern Millie accepts
        total = 0.0
        for pattern in cat.patterns:
            total += evaluate_millie_potential(grid, pattern, cat.point_value)
        return total

    elif isinstance(cat, CatLeo):
        return evaluate_leo_potential(grid, cat)

    elif isinstance(cat, CatRumi):
        return evaluate_rumi_potential(grid, cat)

    return 0.0


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
        max_points = 8.0
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
