"""
Tests for game metadata serialization.
"""
import pytest
import sys
import os

# Add source directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'source'))

from simulation_mode import SimulationMode
from board_configurations import BOARD_1
from game_metadata import GameMetadata, extract_game_metadata


class TestGameMetadata:
    """Tests for GameMetadata class."""

    def test_from_game_captures_cats(self):
        """Should capture cat names and patterns from game."""
        game = SimulationMode(BOARD_1)
        metadata = GameMetadata.from_game(game)

        assert len(metadata.cat_names) == 3
        assert len(metadata.cat_points) == 3
        assert len(metadata.cat_patterns) == 3

        # Each cat should have 2 patterns
        for patterns in metadata.cat_patterns:
            assert len(patterns) == 2

    def test_from_game_captures_goals(self):
        """Should capture goal names and positions from game."""
        game = SimulationMode(BOARD_1)
        metadata = GameMetadata.from_game(game)

        assert len(metadata.goal_names) == 3
        assert len(metadata.goal_positions) == 3

        # Each position should have 3 coordinates (q, r, s)
        for position in metadata.goal_positions:
            assert len(position) == 3

    def test_to_mlflow_params(self):
        """Should convert to MLflow parameters dict."""
        game = SimulationMode(BOARD_1)
        metadata = GameMetadata.from_game(game)
        params = metadata.to_mlflow_params()

        # Should have cat parameters
        assert "cat_1_name" in params
        assert "cat_1_points" in params
        assert "cat_1_patterns" in params
        assert "cat_2_name" in params
        assert "cat_3_name" in params

        # Should have goal parameters
        assert "goal_1_name" in params
        assert "goal_1_position" in params
        assert "goal_2_name" in params
        assert "goal_3_name" in params

        # Should have board
        assert "board_name" in params

    def test_to_mlflow_tags(self):
        """Should convert to MLflow tags dict."""
        game = SimulationMode(BOARD_1)
        metadata = GameMetadata.from_game(game)
        tags = metadata.to_mlflow_tags()

        assert "cats" in tags
        assert "goals" in tags
        assert "board" in tags

        # Tags should be comma-separated strings
        assert "," in tags["cats"]  # Multiple cats
        assert "," in tags["goals"]  # Multiple goals

    def test_json_roundtrip(self):
        """Should serialize to and from JSON."""
        game = SimulationMode(BOARD_1)
        original = GameMetadata.from_game(game)

        json_str = original.to_json()
        restored = GameMetadata.from_json(json_str)

        assert restored.cat_names == original.cat_names
        assert restored.cat_points == original.cat_points
        assert restored.cat_patterns == original.cat_patterns
        assert restored.goal_names == original.goal_names
        assert restored.goal_positions == original.goal_positions
        assert restored.board_name == original.board_name

    def test_from_mlflow_params(self):
        """Should reconstruct from MLflow parameters."""
        game = SimulationMode(BOARD_1)
        original = GameMetadata.from_game(game)

        params = original.to_mlflow_params()
        restored = GameMetadata.from_mlflow_params(params)

        assert restored.cat_names == original.cat_names
        assert restored.cat_points == original.cat_points
        assert restored.goal_names == original.goal_names
        assert restored.board_name == original.board_name

    def test_summary(self):
        """Should produce human-readable summary."""
        game = SimulationMode(BOARD_1)
        metadata = GameMetadata.from_game(game)
        summary = metadata.summary()

        assert "Cats:" in summary
        assert "Goals:" in summary
        assert "Board:" in summary


class TestExtractGameMetadata:
    """Tests for the convenience function."""

    def test_extract_game_metadata(self):
        """Should extract metadata from game."""
        game = SimulationMode(BOARD_1)
        metadata = extract_game_metadata(game)

        assert isinstance(metadata, GameMetadata)
        assert len(metadata.cat_names) == 3
        assert len(metadata.goal_names) == 3
