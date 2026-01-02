"""
Game metadata serialization for MLflow tracking.

Provides a flexible system to serialize game configuration (cats, goals, boards)
into formats suitable for MLflow logging and later parsing.

This module supports:
- Cats: name, point value, patterns, bucket
- Goals: name, position
- Board: identifier/name
- Extensible for future additions (new cat types, goal types, etc.)
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import json


@dataclass
class GameMetadata:
    """
    Complete game configuration metadata.

    Designed for MLflow logging - all fields serialize to simple types
    (strings, numbers) that can be logged as parameters or tags.
    """
    # Cat information
    cat_names: List[str] = field(default_factory=list)
    cat_points: List[int] = field(default_factory=list)
    cat_patterns: List[List[str]] = field(default_factory=list)

    # Goal information
    goal_names: List[str] = field(default_factory=list)
    goal_positions: List[List[int]] = field(default_factory=list)

    # Board information
    board_name: str = "BOARD_1"

    @classmethod
    def from_game(cls, game) -> 'GameMetadata':
        """
        Extract metadata from a SimulationMode or similar game instance.

        Args:
            game: Game instance with .cats, .goals, and .board_name
        """
        metadata = cls()

        # Extract cat info
        for cat in game.cats:
            metadata.cat_names.append(cat.name)
            metadata.cat_points.append(cat.point_value)
            metadata.cat_patterns.append([p.name for p in cat.patterns])

        # Extract goal info
        for goal in game.goals:
            metadata.goal_names.append(goal.name)
            metadata.goal_positions.append(list(goal.position))

        # Board name from game instance
        metadata.board_name = getattr(game, 'board_name', 'BOARD_1')

        return metadata

    def to_mlflow_params(self) -> Dict[str, Any]:
        """
        Convert to MLflow parameters dict.

        Returns dict with keys like:
            cat_1_name, cat_1_points, cat_1_patterns, ...
            goal_1_name, goal_1_position, ...
            board_name
        """
        params = {}

        # Cat parameters
        for i, (name, points, patterns) in enumerate(
            zip(self.cat_names, self.cat_points, self.cat_patterns), start=1
        ):
            params[f"cat_{i}_name"] = name
            params[f"cat_{i}_points"] = points
            params[f"cat_{i}_patterns"] = ",".join(patterns)

        # Goal parameters
        for i, (name, position) in enumerate(
            zip(self.goal_names, self.goal_positions), start=1
        ):
            params[f"goal_{i}_name"] = name
            params[f"goal_{i}_position"] = ",".join(str(p) for p in position)

        # Board
        params["board_name"] = self.board_name

        return params

    def to_mlflow_tags(self) -> Dict[str, str]:
        """
        Convert to MLflow tags dict for quick filtering.

        Returns dict with keys like:
            cats: "Millie,Rumi,Leo"
            goals: "AAA-BBB,AA-BB-CC,All Unique"
            board: "BOARD_1"
        """
        return {
            "cats": ",".join(self.cat_names),
            "goals": ",".join(self.goal_names),
            "board": self.board_name,
        }

    def to_json(self) -> str:
        """Serialize to JSON string for storage."""
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, json_str: str) -> 'GameMetadata':
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls(**data)

    @classmethod
    def from_mlflow_params(cls, params: Dict[str, Any]) -> 'GameMetadata':
        """
        Reconstruct from MLflow parameters dict.

        Parses keys like cat_1_name, cat_1_points, etc.
        """
        metadata = cls()

        # Parse cats (look for cat_1_, cat_2_, cat_3_)
        for i in range(1, 10):  # Support up to 9 cats
            name_key = f"cat_{i}_name"
            if name_key not in params:
                break
            metadata.cat_names.append(params[name_key])
            metadata.cat_points.append(int(params[f"cat_{i}_points"]))
            patterns_str = params[f"cat_{i}_patterns"]
            metadata.cat_patterns.append(patterns_str.split(","))

        # Parse goals
        for i in range(1, 10):  # Support up to 9 goals
            name_key = f"goal_{i}_name"
            if name_key not in params:
                break
            metadata.goal_names.append(params[name_key])
            pos_str = params[f"goal_{i}_position"]
            metadata.goal_positions.append([int(p) for p in pos_str.split(",")])

        # Board
        metadata.board_name = params.get("board_name", "BOARD_1")

        return metadata

    def summary(self) -> str:
        """Human-readable summary string."""
        cats = ", ".join(self.cat_names)
        goals = ", ".join(self.goal_names)
        return f"Cats: [{cats}] | Goals: [{goals}] | Board: {self.board_name}"


def extract_game_metadata(game) -> GameMetadata:
    """
    Convenience function to extract metadata from a game instance.

    Args:
        game: SimulationMode or similar game instance

    Returns:
        GameMetadata instance
    """
    return GameMetadata.from_game(game)
