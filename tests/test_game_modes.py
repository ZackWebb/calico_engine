import pytest
from game_state import GameState, Action, TurnPhase
from simulation_mode import SimulationMode
from play_mode import PlayMode
from board_configurations import BOARD_1


def complete_goal_selection(game):
    """Helper to complete goal selection phase and transition to tile placement."""
    if game.turn_phase == TurnPhase.GOAL_SELECTION:
        actions = game.get_legal_actions()
        game.apply_action(actions[0])
    return game


class TestSimulationMode:
    def test_initial_state_after_goal_selection(self):
        game = SimulationMode(BOARD_1)
        complete_goal_selection(game)
        state = game.get_game_state()

        assert len(state.player_hand) == 2
        assert len(state.market_tiles) == 3
        assert state.turn_phase == TurnPhase.PLACE_TILE
        assert state.turn_number == 0
        # BOARD_1 has 22 tiles, grid has ~47 positions, so ~25 empty
        assert len(state.empty_positions) > 0

    def test_get_legal_actions_place_phase(self):
        game = SimulationMode(BOARD_1)
        complete_goal_selection(game)
        actions = game.get_legal_actions()

        # Should have 2 hand tiles * empty positions
        empty_count = len(game.player.grid.get_empty_positions())
        assert len(actions) == 2 * empty_count
        assert all(a.action_type == "place_tile" for a in actions)

    def test_apply_place_action(self):
        game = SimulationMode(BOARD_1)
        complete_goal_selection(game)
        actions = game.get_legal_actions()

        action = actions[0]
        success = game.apply_action(action)

        assert success
        assert game.turn_phase == TurnPhase.CHOOSE_MARKET
        assert len(game.player.tiles) == 1  # One tile placed

    def test_get_legal_actions_market_phase(self):
        game = SimulationMode(BOARD_1)
        complete_goal_selection(game)

        # Place a tile first
        place_actions = game.get_legal_actions()
        game.apply_action(place_actions[0])

        # Now should be in market phase
        market_actions = game.get_legal_actions()
        assert all(a.action_type == "choose_market" for a in market_actions)
        assert len(market_actions) == 3  # 3 market tiles

    def test_full_turn_cycle(self):
        game = SimulationMode(BOARD_1)
        complete_goal_selection(game)

        # Place tile
        place_actions = game.get_legal_actions()
        game.apply_action(place_actions[0])

        # Choose market tile
        market_actions = game.get_legal_actions()
        game.apply_action(market_actions[0])

        # Should be back to place phase, turn 1
        assert game.turn_phase == TurnPhase.PLACE_TILE
        assert game.turn_number == 1
        assert len(game.player.tiles) == 2  # Back to 2 tiles

    def test_simulated_players_discard(self):
        game = SimulationMode(BOARD_1)
        complete_goal_selection(game)
        initial_bag_count = game.tile_bag.tiles_remaining()

        # Complete one turn
        place_actions = game.get_legal_actions()
        game.apply_action(place_actions[0])
        market_actions = game.get_legal_actions()
        game.apply_action(market_actions[0])

        # P1 took 1 from market, P2/P3/P4 each discarded 1 and market refilled
        # Net: P1 takes 1, market refills 4 times (initial + 3 simulated)
        # So bag should have lost 4 tiles (1 for P1 + 3 discards that got replaced)
        # Actually: P1 takes 1, market refills. Then P2 discards 1, refill. P3 discards 1, refill. P4 discards 1, refill.
        # That's 4 tiles drawn from bag total
        tiles_used = initial_bag_count - game.tile_bag.tiles_remaining()
        assert tiles_used == 4  # 1 for P1 + 3 for simulated discards

    def test_game_completion(self):
        game = SimulationMode(BOARD_1)
        score = game.play_random_game()

        assert game.is_game_over()
        assert game.turn_phase == TurnPhase.GAME_OVER
        assert score >= 0
        assert len(game.player.grid.get_empty_positions()) == 0

    def test_action_history(self):
        game = SimulationMode(BOARD_1)
        complete_goal_selection(game)

        # Do some actions
        actions = game.get_legal_actions()
        game.apply_action(actions[0])
        market_actions = game.get_legal_actions()
        game.apply_action(market_actions[0])

        history = game.get_action_history()
        # History includes goal selection + 2 actions
        assert len(history) == 3
        assert history[0].action_type == "select_goals"
        assert history[1].action_type == "place_tile"
        assert history[2].action_type == "choose_market"

    def test_copy_creates_independent_game(self):
        game = SimulationMode(BOARD_1)
        complete_goal_selection(game)
        game_copy = game.copy()

        # Modify original
        actions = game.get_legal_actions()
        game.apply_action(actions[0])

        # Copy should be unchanged
        assert game_copy.turn_phase == TurnPhase.PLACE_TILE
        assert len(game_copy.player.tiles) == 2

    def test_state_hash(self):
        game = SimulationMode(BOARD_1)
        complete_goal_selection(game)
        hash1 = game.get_state_hash()

        # Make a move
        actions = game.get_legal_actions()
        game.apply_action(actions[0])
        hash2 = game.get_state_hash()

        # Hashes should be different after state change
        assert hash1 != hash2


class TestPlayMode:
    def test_initial_state_after_goal_selection(self):
        game = PlayMode(BOARD_1)
        complete_goal_selection(game)

        assert game.selected_hand_tile is None
        assert game.turn_phase == TurnPhase.PLACE_TILE

    def test_select_hand_tile(self):
        game = PlayMode(BOARD_1)
        complete_goal_selection(game)

        assert game.selected_hand_tile is None
        assert game.select_hand_tile(0)
        assert game.selected_hand_tile == 0

    def test_select_other_hand_tile(self):
        game = PlayMode(BOARD_1)
        complete_goal_selection(game)

        game.select_hand_tile(0)
        game.select_hand_tile(1)
        assert game.selected_hand_tile == 1

    def test_invalid_hand_selection(self):
        game = PlayMode(BOARD_1)
        # No tiles in hand before goal selection
        assert not game.select_hand_tile(0)
        assert game.selected_hand_tile is None

    def test_deselect_hand_tile(self):
        game = PlayMode(BOARD_1)
        complete_goal_selection(game)

        game.select_hand_tile(0)
        game.deselect_hand_tile()
        assert game.selected_hand_tile is None

    def test_place_without_selection(self):
        game = PlayMode(BOARD_1)
        complete_goal_selection(game)
        empty = game.player.grid.get_empty_positions()[0]

        # No tile selected
        assert not game.try_place_at_position(*empty)

    def test_successful_placement(self):
        game = PlayMode(BOARD_1)
        complete_goal_selection(game)
        empty = game.player.grid.get_empty_positions()[0]

        game.select_hand_tile(0)
        assert game.try_place_at_position(*empty)
        assert game.turn_phase == TurnPhase.CHOOSE_MARKET
        assert game.selected_hand_tile is None

    def test_place_on_occupied_position(self):
        game = PlayMode(BOARD_1)
        complete_goal_selection(game)

        # Find an occupied position (from BOARD_1 config)
        occupied = None
        for pos, tile in game.player.grid.grid.items():
            if tile is not None:
                occupied = pos
                break

        game.select_hand_tile(0)
        assert not game.try_place_at_position(*occupied)
        # Should still have tile selected since placement failed
        assert game.selected_hand_tile == 0

    def test_choose_market_in_wrong_phase(self):
        game = PlayMode(BOARD_1)
        complete_goal_selection(game)

        # In PLACE_TILE phase, can't choose market
        assert not game.try_choose_market_tile(0)

    def test_choose_market_tile(self):
        game = PlayMode(BOARD_1)
        complete_goal_selection(game)
        empty = game.player.grid.get_empty_positions()[0]

        # Place tile first
        game.select_hand_tile(0)
        game.try_place_at_position(*empty)

        # Now choose market tile
        assert game.try_choose_market_tile(0)
        assert game.turn_phase == TurnPhase.PLACE_TILE
        assert len(game.player.tiles) == 2

    def test_status_messages(self):
        game = PlayMode(BOARD_1)
        complete_goal_selection(game)

        # Initial state - no selection
        assert "Select a tile" in game.get_status_message()

        # After selection
        game.select_hand_tile(0)
        assert "empty hex" in game.get_status_message()

        # After placement
        empty = game.player.grid.get_empty_positions()[0]
        game.try_place_at_position(*empty)
        assert "market" in game.get_status_message().lower()

    def test_game_over_status(self):
        game = PlayMode(BOARD_1)

        # Play to completion using simulation logic
        # Keep playing until we reach GAME_OVER phase
        while game.turn_phase != TurnPhase.GAME_OVER:
            actions = game.get_legal_actions()
            if not actions:
                break
            game.apply_action(actions[0])

        assert "Game Over" in game.get_status_message()
        assert str(game.get_final_score()) in game.get_status_message()
