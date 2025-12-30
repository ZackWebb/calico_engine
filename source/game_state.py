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
    """Represents a player action."""
    action_type: str  # "place_tile" or "choose_market"
    position: Optional[Tuple[int, int, int]] = None  # For place_tile (q, r, s)
    hand_index: Optional[int] = None  # Which tile from hand (0 or 1)
    market_index: Optional[int] = None  # For choose_market (0, 1, or 2)
