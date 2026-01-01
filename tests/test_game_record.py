"""
Tests for game recording and tile tracking.
"""
import pytest
import sys
import os
import tempfile
import json

# Add source directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'source'))

from tile import Tile, Color, Pattern
from simulation_mode import SimulationMode
from board_configurations import BOARD_1
from mcts_agent import MCTSAgent
from game_record import (
    GameRecord, DecisionRecord, CandidateMove, TileRecord,
    CatRecord, GoalRecord, GameRecorder
)


class TestTileRecord:
    """Tests for TileRecord serialization."""

    def test_from_tile(self):
        """TileRecord should capture tile color and pattern."""
        tile = Tile(Color.BLUE, Pattern.DOTS)
        record = TileRecord.from_tile(tile)

        assert record.color == "BLUE"
        assert record.pattern == "DOTS"

    def test_to_tile(self):
        """TileRecord should reconstruct original tile."""
        record = TileRecord(color="GREEN", pattern="SWIRLS")
        tile = record.to_tile()

        assert tile.color == Color.GREEN
        assert tile.pattern == Pattern.SWIRLS

    def test_roundtrip(self):
        """Converting tile to record and back should preserve data."""
        original = Tile(Color.PINK, Pattern.FLOWERS)
        record = TileRecord.from_tile(original)
        reconstructed = record.to_tile()

        assert reconstructed.color == original.color
        assert reconstructed.pattern == original.pattern

    def test_to_dict(self):
        """TileRecord should serialize to dict."""
        record = TileRecord(color="YELLOW", pattern="LEAVES")
        d = record.to_dict()

        assert d["color"] == "YELLOW"
        assert d["pattern"] == "LEAVES"

    def test_from_dict(self):
        """TileRecord should deserialize from dict."""
        d = {"color": "PURPLE", "pattern": "CLUBS"}
        record = TileRecord.from_dict(d)

        assert record.color == "PURPLE"
        assert record.pattern == "CLUBS"


class TestCandidateMove:
    """Tests for CandidateMove serialization."""

    def test_place_tile_candidate(self):
        """Should serialize place_tile candidates."""
        candidate = CandidateMove(
            action_type="place_tile",
            position=(1, -1, 0),
            hand_index=0,
            market_index=None,
            visits=50,
            avg_score=25.5
        )

        d = candidate.to_dict()
        assert d["action_type"] == "place_tile"
        assert d["position"] == [1, -1, 0]
        assert d["hand_index"] == 0
        assert d["visits"] == 50
        assert d["avg_score"] == 25.5

    def test_choose_market_candidate(self):
        """Should serialize choose_market candidates."""
        candidate = CandidateMove(
            action_type="choose_market",
            position=None,
            hand_index=None,
            market_index=2,
            visits=30,
            avg_score=18.3
        )

        d = candidate.to_dict()
        assert d["action_type"] == "choose_market"
        assert d["position"] is None
        assert d["market_index"] == 2

    def test_roundtrip(self):
        """Serialization should be reversible."""
        original = CandidateMove(
            action_type="place_tile",
            position=(0, 0, 0),
            hand_index=1,
            market_index=None,
            visits=100,
            avg_score=45.0
        )

        d = original.to_dict()
        restored = CandidateMove.from_dict(d)

        assert restored.action_type == original.action_type
        assert restored.position == original.position
        assert restored.hand_index == original.hand_index
        assert restored.visits == original.visits


class TestGameRecorder:
    """Tests for GameRecorder."""

    def test_recorder_creation(self):
        """Recorder should initialize with game and config."""
        game = SimulationMode(BOARD_1)
        config = {"max_iterations": 100}

        recorder = GameRecorder(game, config)

        assert recorder.mcts_config == config
        assert len(recorder.cats) == 3
        assert len(recorder.goals) == 3

    def test_record_decision(self):
        """Recorder should capture decisions."""
        game = SimulationMode(BOARD_1)
        config = {"max_iterations": 50}
        recorder = GameRecorder(game, config)

        # Get an action from the game
        actions = game.get_legal_actions()
        action = actions[0]
        candidates = [(action, 10, 5.0)]

        recorder.record_decision(action, candidates)

        assert len(recorder.decisions) == 1
        decision = recorder.decisions[0]
        assert decision.turn_number == 0
        assert decision.action_type == action.action_type

    def test_finalize_creates_record(self):
        """Finalize should create complete GameRecord."""
        game = SimulationMode(BOARD_1)
        config = {"max_iterations": 50}
        recorder = GameRecorder(game, config)

        # Play a few moves
        for _ in range(3):
            actions = game.get_legal_actions()
            if not actions:
                break
            action = actions[0]
            recorder.record_decision(action, [(action, 5, 3.0)])
            game.apply_action(action)

        record = recorder.finalize()

        assert isinstance(record, GameRecord)
        assert record.mcts_config == config
        assert len(record.decisions) == 3
        assert record.final_score >= 0


class TestGameRecord:
    """Tests for GameRecord serialization."""

    def test_save_and_load(self):
        """GameRecord should save to and load from JSON."""
        game = SimulationMode(BOARD_1)
        config = {"max_iterations": 50}
        recorder = GameRecorder(game, config)

        # Record some decisions
        for _ in range(2):
            actions = game.get_legal_actions()
            if not actions:
                break
            action = actions[0]
            recorder.record_decision(action, [(action, 5, 3.0)])
            game.apply_action(action)

        record = recorder.finalize()

        # Save to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name

        try:
            record.save(filepath)

            # Load it back
            loaded = GameRecord.load(filepath)

            assert loaded.timestamp == record.timestamp
            assert loaded.mcts_config == record.mcts_config
            assert loaded.final_score == record.final_score
            assert len(loaded.decisions) == len(record.decisions)
            assert len(loaded.cats) == len(record.cats)
            assert len(loaded.goals) == len(record.goals)
        finally:
            os.unlink(filepath)


class TestIntegrationRecording:
    """Integration tests for recording during MCTS."""

    def test_record_full_game(self):
        """Should record a complete MCTS game."""
        game = SimulationMode(BOARD_1)
        agent = MCTSAgent(max_iterations=20)
        config = {
            "max_iterations": agent.max_iterations,
            "exploration_constant": agent.exploration_constant,
        }
        recorder = GameRecorder(game, config)

        # Play the full game with recording
        while not game.is_game_over():
            action, candidates = agent.select_action_with_analysis(game)
            recorder.record_decision(action, candidates)
            game.apply_action(action)

        record = recorder.finalize()

        # Verify record completeness
        assert record.final_score == game.get_final_score()
        assert len(record.decisions) > 0
        assert all(len(d.candidates) > 0 for d in record.decisions)

    def test_recorded_game_save_load(self):
        """Recorded game should survive save/load cycle."""
        game = SimulationMode(BOARD_1)
        agent = MCTSAgent(max_iterations=10)
        recorder = GameRecorder(game, {"iterations": 10})

        # Play a few moves
        for _ in range(5):
            if game.is_game_over():
                break
            action, candidates = agent.select_action_with_analysis(game)
            recorder.record_decision(action, candidates)
            game.apply_action(action)

        original = recorder.finalize()

        # Save and reload
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name

        try:
            original.save(filepath)
            loaded = GameRecord.load(filepath)

            # Verify key data preserved
            assert loaded.final_score == original.final_score
            assert len(loaded.decisions) == len(original.decisions)

            # Verify decision details preserved
            for orig_d, load_d in zip(original.decisions, loaded.decisions):
                assert orig_d.turn_number == load_d.turn_number
                assert orig_d.action_type == load_d.action_type
                assert len(orig_d.candidates) == len(load_d.candidates)
        finally:
            os.unlink(filepath)
