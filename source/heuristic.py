"""
Heuristic evaluation functions for Calico MCTS.

Estimates the final score from a partial game state by:
1. Counting current scoring (cats, goals, buttons)
2. Adding potential points for near-complete patterns
"""
from dataclasses import dataclass
from typing import List, Set, Tuple, Optional
from collections import Counter
from functools import lru_cache

from hex_grid import HexGrid, Pattern, Color
from cat import Cat, CatMillie, CatLeo, CatRumi
from button import score_buttons, count_buttons_by_color


@dataclass
class HeuristicConfig:
    """Configuration for heuristic weights - enables strategy tuning via benchmarks."""
    # Top-level weights for each scoring category
    cat_weight: float = 1.0
    goal_weight: float = 1.0
    button_weight: float = 1.0

    # Sub-weights for fine-tuning
    goal_discount: float = 0.4  # Discount factor for incomplete goals
    rainbow_progress_bonus: float = 1.5  # Bonus when all 6 colors show button potential


# Default configuration
DEFAULT_HEURISTIC_CONFIG = HeuristicConfig()


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


def evaluate_state(game, config: HeuristicConfig = None) -> float:
    """
    Estimate final score from current game state.

    Args:
        game: SimulationMode instance
        config: HeuristicConfig for weight tuning (uses defaults if None)

    Returns:
        Estimated final score as float
    """
    if config is None:
        config = DEFAULT_HEURISTIC_CONFIG

    grid = game.player.grid

    score = 0.0
    score += config.cat_weight * evaluate_cats(game)
    score += config.goal_weight * evaluate_goals(game, config)
    score += config.button_weight * evaluate_buttons(grid, config)

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


def evaluate_goals(game, config: HeuristicConfig = None) -> float:
    """
    Evaluate goal scoring: current score plus potential from partial progress.
    """
    if config is None:
        config = DEFAULT_HEURISTIC_CONFIG

    grid = game.player.grid
    total = 0.0

    for goal in game.goals:
        # Current actual score
        actual = goal.score(grid)
        total += actual

        # If not fully scored, estimate potential
        if actual == 0:
            potential = estimate_goal_potential(grid, goal, config)
            total += potential

    return total


def estimate_goal_potential(grid: HexGrid, goal, config: HeuristicConfig = None) -> float:
    """
    Estimate potential for a goal based on filled neighbors.

    Uses weighted combination scoring:
    - single_potential = single_max * max(color_progress, pattern_progress)
    - double_potential = double_max * min(color_progress, pattern_progress)
    - Returns max of the two, scaled by completion ratio

    This naturally handles impossibility:
    - If color becomes impossible (progress=0), double_potential=0, falls back to single
    - If both impossible, both potentials=0
    """
    if config is None:
        config = DEFAULT_HEURISTIC_CONFIG

    tiles = goal.get_neighbor_tiles(grid)
    filled_count = len(tiles)

    if filled_count == 0:
        return 0.0

    # Completion ratio
    completion_ratio = filled_count / 6.0

    # Get goal-specific point values and progress functions
    goal_name = goal.name

    if goal_name == "AAA-BBB":
        single_max = 8.0
        double_max = 13.0
        color_progress = _check_3_3_for_values([t.color for t in tiles])
        pattern_progress = _check_3_3_for_values([t.pattern for t in tiles])
    elif goal_name == "AA-BB-CC":
        single_max = 7.0
        double_max = 11.0
        color_progress = _check_2_2_2_for_values([t.color for t in tiles])
        pattern_progress = _check_2_2_2_for_values([t.pattern for t in tiles])
    elif goal_name == "All Unique":
        single_max = 10.0
        double_max = 15.0
        color_progress = _check_unique_for_values([t.color for t in tiles])
        pattern_progress = _check_unique_for_values([t.pattern for t in tiles])
    else:
        return 0.0

    # Weighted combination: use max() for single, min() for double
    # This naturally bounds to single_max when one track becomes impossible
    single_potential = single_max * max(color_progress, pattern_progress)
    double_potential = double_max * min(color_progress, pattern_progress)

    # Take the better of the two strategies
    best_potential = max(single_potential, double_potential)

    # Scale by completion ratio and discount factor
    return best_potential * completion_ratio * config.goal_discount


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
    """
    Check 3-3 progress for a list of values.

    Returns 0.0 when goal becomes impossible:
    - More than 2 distinct values (can't achieve 3-3)
    - Any single value has count > 3 (would exceed 3)
    """
    counts = Counter(values)
    sorted_counts = sorted(counts.values(), reverse=True)
    num_types = len(sorted_counts)

    if num_types == 0:
        return 0.0

    # IMPOSSIBLE: More than 2 types - can never achieve 3-3
    if num_types > 2:
        return 0.0

    # IMPOSSIBLE: Any type has more than 3 - can never achieve 3-3
    if sorted_counts[0] > 3:
        return 0.0

    # Perfect 3-3 achieved
    if sorted_counts == [3, 3]:
        return 1.0

    # One type so far - still possible, modest progress
    if num_types == 1:
        # 1, 2, or 3 of one type - needs the second type to appear
        return 0.3

    # Two types - good! Check balance
    diff = abs(sorted_counts[0] - sorted_counts[1])
    if diff <= 1:
        return 0.8  # Well balanced
    else:
        return 0.5  # Imbalanced but recoverable


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
    """
    Check 2-2-2 progress for a list of values.

    Returns 0.0 when goal becomes impossible:
    - More than 3 distinct values (can't achieve 2-2-2)
    - Any single value has count > 2 (would exceed 2)
    """
    counts = Counter(values)
    sorted_counts = sorted(counts.values(), reverse=True)
    num_types = len(sorted_counts)

    if num_types == 0:
        return 0.0

    # IMPOSSIBLE: More than 3 types - can never achieve 2-2-2
    if num_types > 3:
        return 0.0

    # IMPOSSIBLE: Any type has more than 2 - can never achieve 2-2-2
    if sorted_counts[0] > 2:
        return 0.0

    # Perfect 2-2-2 achieved
    if sorted_counts == [2, 2, 2]:
        return 1.0

    # Check progress based on how many types we have
    if num_types == 1:
        # 1 or 2 of one type - need more diversity
        return 0.2
    elif num_types == 2:
        # Two types with counts <= 2 each - okay progress
        return 0.5
    else:
        # Three types, all <= 2 - good progress!
        # Check balance
        if sorted_counts[0] == sorted_counts[1] == sorted_counts[2]:
            return 0.9  # Perfectly balanced
        else:
            return 0.7  # Slightly imbalanced


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
    """
    Check uniqueness progress for a list of values.

    Returns 0.0 when goal becomes impossible:
    - Any duplicate value means we can never have 6 unique
    """
    if not values:
        return 0.0

    unique_count = len(set(values))
    total_count = len(values)

    # IMPOSSIBLE: Any duplicates mean we can't achieve all-unique
    if unique_count < total_count:
        return 0.0

    # All unique so far - progress based on how many we have
    # 6/6 unique = 1.0, 5/6 = 0.83, 4/6 = 0.67, etc.
    return unique_count / 6.0


def evaluate_buttons(grid: HexGrid, config: HeuristicConfig = None) -> float:
    """
    Evaluate button scoring: current score plus potential from color pairs.

    Includes rainbow progress scoring - gives credit for colors that have
    pairs (potential buttons) even before the button is complete.
    """
    if config is None:
        config = DEFAULT_HEURISTIC_CONFIG

    # Current button score
    current_score = score_buttons(grid)

    # Potential from color pairs (adjacent same-color not yet in button)
    pair_potential = 0.0
    colors_with_pairs = 0
    for color in Color:
        pairs = count_color_pairs(grid, color)
        pair_potential += pairs * 1.0  # Each pair worth ~1 potential point
        if pairs > 0:
            colors_with_pairs += 1

    # Rainbow potential based on completed buttons
    button_counts = count_buttons_by_color(grid)
    colors_with_buttons = sum(1 for count in button_counts.values() if count >= 1)

    # Count colors with button potential (completed OR have pairs)
    colors_with_potential = colors_with_buttons
    for color in Color:
        if button_counts.get(color, 0) == 0:  # No completed button yet
            if count_color_pairs(grid, color) > 0:
                colors_with_potential += 1

    # Scale rainbow potential based on completed buttons
    rainbow_potential = 0.0
    if colors_with_buttons >= 5:
        rainbow_potential = 4.5  # Very close to 5 pts
    elif colors_with_buttons >= 4:
        rainbow_potential = 3.5
    elif colors_with_buttons >= 3:
        rainbow_potential = 2.0

    # Add potential-based rainbow bonus (colors with pairs count toward rainbow)
    if colors_with_potential >= 6 and colors_with_buttons < 6:
        rainbow_potential += config.rainbow_progress_bonus  # All 6 colors have progress
    elif colors_with_potential >= 5 and colors_with_buttons < 5:
        rainbow_potential += config.rainbow_progress_bonus * 0.67  # 5 colors have progress

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
