"""
Tile tracking for probability-aware MCTS.

Tracks known vs unknown tiles throughout the game to enable
probability calculations instead of random sampling.
"""
from collections import Counter
from typing import Dict, List, Tuple, Optional, Callable
from dataclasses import dataclass, field

from tile import Tile, Color, Pattern


# Total tiles in a full game: 6 colors x 6 patterns x 3 copies = 108
TILES_PER_COMBINATION = 3
TOTAL_TILES = len(Color) * len(Pattern) * TILES_PER_COMBINATION


@dataclass
class TileDistribution:
    """Represents a probability distribution over tile types."""
    counts: Dict[Tuple[Color, Pattern], int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        """Total tiles in this distribution."""
        return sum(self.counts.values())

    def probability(self, color: Color, pattern: Pattern) -> float:
        """Probability of drawing a specific tile type."""
        if self.total == 0:
            return 0.0
        return self.counts.get((color, pattern), 0) / self.total

    def probability_of_tile(self, tile: Tile) -> float:
        """Probability of drawing a specific tile."""
        return self.probability(tile.color, tile.pattern)

    def expected_value(self, eval_fn: Callable[[Tile], float]) -> float:
        """
        Calculate expected value over all possible draws.

        Args:
            eval_fn: Function that takes a Tile and returns a score

        Returns:
            Expected score weighted by tile probabilities
        """
        if self.total == 0:
            return 0.0

        expected = 0.0
        for (color, pattern), count in self.counts.items():
            prob = count / self.total
            tile = Tile(color, pattern)
            expected += prob * eval_fn(tile)

        return expected

    def most_likely(self, n: int = 5) -> List[Tuple[Tuple[Color, Pattern], float]]:
        """Return the n most likely tile types with their probabilities."""
        if self.total == 0:
            return []

        sorted_items = sorted(
            self.counts.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [
            (tile_type, count / self.total)
            for tile_type, count in sorted_items[:n]
        ]


class TileTracker:
    """
    Track tile distribution for probability calculations.

    Tracks all observed tiles (in hand, market, board, discards)
    to calculate probabilities for tiles remaining in the bag.
    """

    def __init__(self):
        # Initial counts: 3 of each (color, pattern) combination
        self.initial_counts: Dict[Tuple[Color, Pattern], int] = {
            (color, pattern): TILES_PER_COMBINATION
            for color in Color
            for pattern in Pattern
        }

        # Observed tiles (tiles we've seen leave the bag)
        self.observed: Counter = Counter()

        # Track where tiles are for debugging/analysis
        self.in_hand: List[Tile] = []
        self.in_market: List[Tile] = []
        self.on_board: List[Tile] = []
        self.discarded: List[Tile] = []

    def reset(self):
        """Reset tracker to initial state."""
        self.observed.clear()
        self.in_hand.clear()
        self.in_market.clear()
        self.on_board.clear()
        self.discarded.clear()

    def observe_tile(self, tile: Tile, location: str = "unknown"):
        """
        Record a tile we've observed leaving the bag.

        Args:
            tile: The tile observed
            location: Where the tile is ("hand", "market", "board", "discard")
        """
        key = (tile.color, tile.pattern)
        self.observed[key] += 1

        if location == "hand":
            self.in_hand.append(tile)
        elif location == "market":
            self.in_market.append(tile)
        elif location == "board":
            self.on_board.append(tile)
        elif location == "discard":
            self.discarded.append(tile)

    def observe_tiles(self, tiles: List[Tile], location: str = "unknown"):
        """Observe multiple tiles at once."""
        for tile in tiles:
            self.observe_tile(tile, location)

    def move_tile(self, tile: Tile, from_loc: str, to_loc: str):
        """
        Record a tile moving between locations.

        This doesn't change the bag probability since the tile
        was already observed, but helps track game state.
        """
        # Remove from old location
        if from_loc == "hand" and tile in self.in_hand:
            self.in_hand.remove(tile)
        elif from_loc == "market" and tile in self.in_market:
            self.in_market.remove(tile)

        # Add to new location
        if to_loc == "board":
            self.on_board.append(tile)
        elif to_loc == "hand":
            self.in_hand.append(tile)
        elif to_loc == "discard":
            self.discarded.append(tile)

    def get_remaining_distribution(self) -> TileDistribution:
        """
        Calculate distribution of tiles remaining in bag.

        Returns:
            TileDistribution with counts for each tile type
        """
        remaining = {}
        for (color, pattern), initial_count in self.initial_counts.items():
            observed_count = self.observed.get((color, pattern), 0)
            remaining_count = initial_count - observed_count

            if remaining_count > 0:
                remaining[(color, pattern)] = remaining_count

        return TileDistribution(counts=remaining)

    def tiles_remaining_in_bag(self) -> int:
        """Number of tiles still in the bag."""
        return TOTAL_TILES - sum(self.observed.values())

    def probability_of_drawing(self, color: Color, pattern: Pattern) -> float:
        """Probability of drawing a specific tile type from the bag."""
        dist = self.get_remaining_distribution()
        return dist.probability(color, pattern)

    def expected_draw_value(self, eval_fn: Callable[[Tile], float]) -> float:
        """
        Calculate expected value of drawing a random tile.

        Args:
            eval_fn: Function that evaluates a tile (higher = better)

        Returns:
            Expected value over all possible draws
        """
        dist = self.get_remaining_distribution()
        return dist.expected_value(eval_fn)

    def get_color_distribution(self) -> Dict[Color, float]:
        """Get probability distribution over colors."""
        dist = self.get_remaining_distribution()
        if dist.total == 0:
            return {c: 0.0 for c in Color}

        color_counts = Counter()
        for (color, _), count in dist.counts.items():
            color_counts[color] += count

        return {
            color: color_counts[color] / dist.total
            for color in Color
        }

    def get_pattern_distribution(self) -> Dict[Pattern, float]:
        """Get probability distribution over patterns."""
        dist = self.get_remaining_distribution()
        if dist.total == 0:
            return {p: 0.0 for p in Pattern}

        pattern_counts = Counter()
        for (_, pattern), count in dist.counts.items():
            pattern_counts[pattern] += count

        return {
            pattern: pattern_counts[pattern] / dist.total
            for pattern in Pattern
        }

    def copy(self) -> 'TileTracker':
        """Create a copy of this tracker."""
        new_tracker = TileTracker()
        new_tracker.observed = Counter(self.observed)
        new_tracker.in_hand = list(self.in_hand)
        new_tracker.in_market = list(self.in_market)
        new_tracker.on_board = list(self.on_board)
        new_tracker.discarded = list(self.discarded)
        return new_tracker

    def __str__(self) -> str:
        remaining = self.tiles_remaining_in_bag()
        observed = sum(self.observed.values())
        return f"TileTracker(observed={observed}, remaining={remaining})"

    def debug_summary(self) -> str:
        """Return detailed summary for debugging."""
        lines = [
            f"TileTracker Summary:",
            f"  Total observed: {sum(self.observed.values())}",
            f"  Remaining in bag: {self.tiles_remaining_in_bag()}",
            f"  In hand: {len(self.in_hand)}",
            f"  In market: {len(self.in_market)}",
            f"  On board: {len(self.on_board)}",
            f"  Discarded: {len(self.discarded)}",
            "",
            "  Most likely draws:"
        ]

        dist = self.get_remaining_distribution()
        for (color, pattern), prob in dist.most_likely(5):
            lines.append(f"    {color.name} {pattern.name}: {prob:.1%}")

        return "\n".join(lines)


def create_tracker_from_game_state(
    hand_tiles: List[Tile],
    market_tiles: List[Tile],
    board_tiles: Dict[Tuple[int, int, int], Tile],
    discarded_tiles: List[Tile] = None
) -> TileTracker:
    """
    Create a TileTracker initialized with current game state.

    Args:
        hand_tiles: Tiles in player's hand
        market_tiles: Tiles in the market
        board_tiles: Dict mapping positions to tiles on the board
        discarded_tiles: Tiles that have been discarded (optional)

    Returns:
        TileTracker with all observed tiles recorded
    """
    tracker = TileTracker()

    for tile in hand_tiles:
        tracker.observe_tile(tile, "hand")

    for tile in market_tiles:
        tracker.observe_tile(tile, "market")

    for tile in board_tiles.values():
        if tile is not None:
            tracker.observe_tile(tile, "board")

    if discarded_tiles:
        for tile in discarded_tiles:
            tracker.observe_tile(tile, "discard")

    return tracker
