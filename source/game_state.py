from dataclasses import dataclass
from typing import List, Tuple, Optional
from enum import Enum, auto

from tile import Tile


class TurnPhase(Enum):
    PLACE_TILE = auto()
    CHOOSE_MARKET = auto()
    GAME_OVER = auto()


@dataclass
class GameState:
    """Immutable snapshot of game state for agents."""
    player_hand: List[Tile]
    market_tiles: List[Tile]
    empty_positions: List[Tuple[int, int, int]]
    turn_number: int
    turn_phase: TurnPhase
    tiles_remaining_in_bag: int


@dataclass
class Action:
    """Represents a player action.

    Action types:
    - "place_tile": Place a tile from hand onto the board
    - "choose_market": Take a tile from the market
    - "place_and_choose": Combined action - place tile AND choose from market (atomic turn)

    For place_and_choose:
    - Uses position, hand_index, and market_index
    - market_index=None indicates final turn (board fills, no market choice)
    """
    action_type: str  # "place_tile", "choose_market", or "place_and_choose"
    position: Optional[Tuple[int, int, int]] = None  # For place_tile/place_and_choose (q, r, s)
    hand_index: Optional[int] = None  # Which tile from hand (0 or 1)
    market_index: Optional[int] = None  # For choose_market/place_and_choose (0, 1, or 2; None for final turn)

    def is_combined_action(self) -> bool:
        """Check if this is a combined place_and_choose action."""
        return self.action_type == "place_and_choose"

    def is_final_turn_action(self) -> bool:
        """Check if this is the final turn (no market choice after placement)."""
        return self.action_type == "place_and_choose" and self.market_index is None
