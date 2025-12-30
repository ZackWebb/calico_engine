"""
Game recording system for Calico MCTS analysis.

Records complete games with decision info for step-by-step replay and analysis.
"""
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any

from tile import Tile, Color, Pattern
from game_state import Action, TurnPhase


@dataclass
class CandidateMove:
    """A candidate move considered by MCTS."""
    action_type: str
    position: Optional[Tuple[int, int, int]]  # For place_tile
    hand_index: Optional[int]
    market_index: Optional[int]
    visits: int
    avg_score: float

    def to_dict(self) -> dict:
        return {
            "action_type": self.action_type,
            "position": list(self.position) if self.position else None,
            "hand_index": self.hand_index,
            "market_index": self.market_index,
            "visits": self.visits,
            "avg_score": round(self.avg_score, 2)
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'CandidateMove':
        return cls(
            action_type=data["action_type"],
            position=tuple(data["position"]) if data["position"] else None,
            hand_index=data["hand_index"],
            market_index=data["market_index"],
            visits=data["visits"],
            avg_score=data["avg_score"]
        )

    @classmethod
    def from_action(cls, action: Action, visits: int, avg_score: float) -> 'CandidateMove':
        return cls(
            action_type=action.action_type,
            position=action.position,
            hand_index=action.hand_index,
            market_index=action.market_index,
            visits=visits,
            avg_score=avg_score
        )


@dataclass
class TileRecord:
    """Serializable tile representation."""
    color: str
    pattern: str

    def to_dict(self) -> dict:
        return {"color": self.color, "pattern": self.pattern}

    @classmethod
    def from_dict(cls, data: dict) -> 'TileRecord':
        return cls(color=data["color"], pattern=data["pattern"])

    @classmethod
    def from_tile(cls, tile: Tile) -> 'TileRecord':
        return cls(color=tile.color.name, pattern=tile.pattern.name)

    def to_tile(self) -> Tile:
        return Tile(Color[self.color], Pattern[self.pattern])


@dataclass
class DecisionRecord:
    """Record of a single decision point in the game."""
    turn_number: int
    phase: str  # "PLACE_TILE" or "CHOOSE_MARKET"

    # State before decision
    hand_tiles: List[TileRecord]
    market_tiles: List[TileRecord]
    board_tiles: Dict[str, TileRecord]  # "q,r,s" -> TileRecord
    tiles_remaining: int

    # Action taken
    action_type: str
    action_position: Optional[List[int]]  # [q, r, s] for place_tile
    action_hand_index: Optional[int]
    action_market_index: Optional[int]

    # MCTS analysis
    candidates: List[CandidateMove]

    # Result (what happened after action)
    tiles_drawn: List[TileRecord] = field(default_factory=list)
    simulated_discards: List[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "turn_number": self.turn_number,
            "phase": self.phase,
            "hand_tiles": [t.to_dict() for t in self.hand_tiles],
            "market_tiles": [t.to_dict() for t in self.market_tiles],
            "board_tiles": {k: v.to_dict() for k, v in self.board_tiles.items()},
            "tiles_remaining": self.tiles_remaining,
            "action_type": self.action_type,
            "action_position": self.action_position,
            "action_hand_index": self.action_hand_index,
            "action_market_index": self.action_market_index,
            "candidates": [c.to_dict() for c in self.candidates],
            "tiles_drawn": [t.to_dict() for t in self.tiles_drawn],
            "simulated_discards": self.simulated_discards
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'DecisionRecord':
        return cls(
            turn_number=data["turn_number"],
            phase=data["phase"],
            hand_tiles=[TileRecord.from_dict(t) for t in data["hand_tiles"]],
            market_tiles=[TileRecord.from_dict(t) for t in data["market_tiles"]],
            board_tiles={k: TileRecord.from_dict(v) for k, v in data["board_tiles"].items()},
            tiles_remaining=data["tiles_remaining"],
            action_type=data["action_type"],
            action_position=data.get("action_position"),
            action_hand_index=data.get("action_hand_index"),
            action_market_index=data.get("action_market_index"),
            candidates=[CandidateMove.from_dict(c) for c in data["candidates"]],
            tiles_drawn=[TileRecord.from_dict(t) for t in data.get("tiles_drawn", [])],
            simulated_discards=data.get("simulated_discards", [])
        )


@dataclass
class CatRecord:
    """Record of a cat's configuration."""
    name: str
    point_value: int
    patterns: List[str]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "point_value": self.point_value,
            "patterns": self.patterns
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'CatRecord':
        return cls(
            name=data["name"],
            point_value=data["point_value"],
            patterns=data["patterns"]
        )


@dataclass
class GoalRecord:
    """Record of a goal's configuration."""
    name: str
    position: List[int]

    def to_dict(self) -> dict:
        return {"name": self.name, "position": self.position}

    @classmethod
    def from_dict(cls, data: dict) -> 'GoalRecord':
        return cls(name=data["name"], position=data["position"])


@dataclass
class GameRecord:
    """Complete record of a game for replay and analysis."""
    timestamp: str
    mcts_config: dict
    cats: List[CatRecord]
    goals: List[GoalRecord]

    decisions: List[DecisionRecord]

    final_score: int
    score_breakdown: dict

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "mcts_config": self.mcts_config,
            "cats": [c.to_dict() for c in self.cats],
            "goals": [g.to_dict() for g in self.goals],
            "decisions": [d.to_dict() for d in self.decisions],
            "final_score": self.final_score,
            "score_breakdown": self.score_breakdown
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'GameRecord':
        return cls(
            timestamp=data["timestamp"],
            mcts_config=data["mcts_config"],
            cats=[CatRecord.from_dict(c) for c in data["cats"]],
            goals=[GoalRecord.from_dict(g) for g in data["goals"]],
            decisions=[DecisionRecord.from_dict(d) for d in data["decisions"]],
            final_score=data["final_score"],
            score_breakdown=data["score_breakdown"]
        )

    def save(self, filepath: str):
        """Save game record to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> 'GameRecord':
        """Load game record from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)


class GameRecorder:
    """Records a game as it's played."""

    def __init__(self, game, mcts_config: dict):
        """
        Initialize recorder with game instance.

        Args:
            game: SimulationMode instance
            mcts_config: dict with MCTS parameters
        """
        self.game = game
        self.mcts_config = mcts_config
        self.decisions: List[DecisionRecord] = []
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Record initial cat/goal configuration
        self.cats = [
            CatRecord(
                name=cat.name,
                point_value=cat.point_value,
                patterns=[p.name for p in cat.patterns]
            )
            for cat in game.cats
        ]
        self.goals = [
            GoalRecord(name=goal.name, position=list(goal.position))
            for goal in game.goals
        ]

    def _get_board_snapshot(self) -> Dict[str, TileRecord]:
        """Capture current board state."""
        board = {}
        for pos, tile in self.game.player.grid.grid.items():
            if tile is not None:
                key = f"{pos[0]},{pos[1]},{pos[2]}"
                board[key] = TileRecord.from_tile(tile)
        return board

    def record_decision(
        self,
        action: Action,
        candidates: List[Tuple[Action, int, float]],
        tiles_drawn: List[Tile] = None,
        simulated_discards: List[int] = None
    ):
        """
        Record a decision point.

        Args:
            action: The action taken
            candidates: List of (action, visits, avg_score) tuples for top candidates
            tiles_drawn: Tiles drawn from bag after action
            simulated_discards: Market indices discarded by P2/P3/P4
        """
        state = self.game.get_game_state()

        decision = DecisionRecord(
            turn_number=state.turn_number,
            phase=state.turn_phase.name,
            hand_tiles=[TileRecord.from_tile(t) for t in state.player_hand],
            market_tiles=[TileRecord.from_tile(t) for t in state.market_tiles],
            board_tiles=self._get_board_snapshot(),
            tiles_remaining=state.tiles_remaining_in_bag,
            action_type=action.action_type,
            action_position=list(action.position) if action.position else None,
            action_hand_index=action.hand_index,
            action_market_index=action.market_index,
            candidates=[
                CandidateMove.from_action(a, v, s) for a, v, s in candidates
            ],
            tiles_drawn=[TileRecord.from_tile(t) for t in (tiles_drawn or [])],
            simulated_discards=simulated_discards or []
        )

        self.decisions.append(decision)

    def finalize(self) -> GameRecord:
        """Create final game record after game ends."""
        button_info = self.game.get_button_scores()

        return GameRecord(
            timestamp=self.timestamp,
            mcts_config=self.mcts_config,
            cats=self.cats,
            goals=self.goals,
            decisions=self.decisions,
            final_score=self.game.get_final_score(),
            score_breakdown={
                "cats": self.game.get_cat_scores(),
                "goals": self.game.get_goal_scores(),
                "buttons": {
                    "total_buttons": button_info["total_buttons"],
                    "button_score": button_info["button_score"],
                    "has_rainbow": button_info["has_rainbow"],
                    "rainbow_score": button_info["rainbow_score"]
                }
            }
        )
