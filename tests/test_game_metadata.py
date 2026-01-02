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


class TestGoalArrangementKeys:
    """Tests for goal arrangement tracking keys."""

    def test_goal_arrangement_key_format(self):
        """Should produce key with goal@position format."""
        game = SimulationMode(BOARD_1)
        metadata = GameMetadata.from_game(game)
        key = metadata.get_goal_arrangement_key()

        # Key should have 3 parts separated by |
        parts = key.split("|")
        assert len(parts) == 3

        # Each part should have goal@(position) format
        for part in parts:
            assert "@" in part
            assert "(" in part
            assert ")" in part

    def test_goal_arrangement_key_sorted(self):
        """Key should be sorted for consistent ordering."""
        game = SimulationMode(BOARD_1)
        metadata = GameMetadata.from_game(game)
        key = metadata.get_goal_arrangement_key()

        parts = key.split("|")
        assert parts == sorted(parts)

    def test_goals_only_key_format(self):
        """Should produce sorted comma-separated goal names."""
        game = SimulationMode(BOARD_1)
        metadata = GameMetadata.from_game(game)
        key = metadata.get_goals_only_key()

        # Should have comma-separated goal names
        goal_names = key.split(",")
        assert len(goal_names) == 3
        assert goal_names == sorted(goal_names)

    def test_setup_key_includes_all_components(self):
        """Setup key should include board, cats, and goal arrangement."""
        game = SimulationMode(BOARD_1)
        metadata = GameMetadata.from_game(game)
        key = metadata.get_setup_key()

        # Should contain board name
        assert "BOARD_1" in key

        # Should have pipes separating components
        parts = key.split("|")
        assert len(parts) >= 3  # board | cats | goals...

    def test_same_setup_produces_same_key(self):
        """Identical setups should produce identical keys."""
        # Create metadata with known values
        metadata1 = GameMetadata(
            cat_names=["Millie", "Rumi", "Leo"],
            cat_points=[3, 5, 11],
            cat_patterns=[["DOTS", "LEAVES"], ["FLOWERS", "STRIPES"], ["CLUBS", "SWIRLS"]],
            goal_names=["AAA-BBB", "AA-BB-CC", "All Unique"],
            goal_positions=[[-2, 1, 1], [1, -1, 0], [0, 1, -1]],
            board_name="BOARD_1"
        )
        metadata2 = GameMetadata(
            cat_names=["Millie", "Rumi", "Leo"],
            cat_points=[3, 5, 11],
            cat_patterns=[["DOTS", "LEAVES"], ["FLOWERS", "STRIPES"], ["CLUBS", "SWIRLS"]],
            goal_names=["AAA-BBB", "AA-BB-CC", "All Unique"],
            goal_positions=[[-2, 1, 1], [1, -1, 0], [0, 1, -1]],
            board_name="BOARD_1"
        )

        assert metadata1.get_setup_key() == metadata2.get_setup_key()
        assert metadata1.get_goal_arrangement_key() == metadata2.get_goal_arrangement_key()

    def test_different_arrangement_produces_different_key(self):
        """Different goal positions should produce different keys."""
        metadata1 = GameMetadata(
            goal_names=["AAA-BBB", "AA-BB-CC", "All Unique"],
            goal_positions=[[-2, 1, 1], [1, -1, 0], [0, 1, -1]],
            board_name="BOARD_1"
        )
        # Same goals but different positions
        metadata2 = GameMetadata(
            goal_names=["AAA-BBB", "AA-BB-CC", "All Unique"],
            goal_positions=[[0, 1, -1], [-2, 1, 1], [1, -1, 0]],  # Swapped
            board_name="BOARD_1"
        )

        # Goal arrangement keys should differ
        assert metadata1.get_goal_arrangement_key() != metadata2.get_goal_arrangement_key()

        # But goals_only keys should be the same (same 3 goals selected)
        assert metadata1.get_goals_only_key() == metadata2.get_goals_only_key()
