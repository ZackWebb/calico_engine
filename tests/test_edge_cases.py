import pytest
from source.tile import Tile, Color, Pattern
from source.tile_bag import TileBag
from source.market import Market
from source.player import Player
from source.hex_grid import HexGrid
from source.cat import CatMillie, CatLeo, CatRumi
from source.goal import GoalAAA_BBB, GoalAA_BB_CC, GoalAllUnique
from source.simulation_mode import SimulationMode
from source.play_mode import PlayMode
from source.board_configurations import BOARD_1


class TestStringRepresentations:
    """Test __str__ and __repr__ methods."""

    def test_tile_str(self):
        tile = Tile(Color.BLUE, Pattern.DOTS)
        s = str(tile)
        assert "BLUE" in s or "Blue" in s.upper()

    def test_market_str(self):
        bag = TileBag()
        market = Market(bag)
        s = str(market)
        assert "Market" in s

    def test_player_str(self):
        bag = TileBag()
        player = Player("TestPlayer", bag)
        s = str(player)
        assert "TestPlayer" in s

    def test_cat_str(self):
        cat = CatMillie()
        s = str(cat)
        assert "Millie" in s

    def test_cat_repr(self):
        cat = CatLeo()
        r = repr(cat)
        assert "Leo" in r

    def test_goal_repr(self):
        goal = GoalAAA_BBB()
        r = repr(goal)
        assert "AAA-BBB" in r

    def test_hex_grid_str(self):
        grid = HexGrid()
        grid.set_tile(0, 0, 0, Tile(Color.BLUE, Pattern.DOTS))
        s = str(grid)
        assert len(s) > 0


class TestMarketEdgeCases:
    """Test Market edge cases."""

    def test_choose_invalid_index_negative(self):
        bag = TileBag()
        market = Market(bag)
        result = market.choose_tile(-1)
        assert result is None

    def test_choose_invalid_index_too_large(self):
        bag = TileBag()
        market = Market(bag)
        result = market.choose_tile(100)
        assert result is None

    def test_market_refill_empty_bag(self):
        bag = TileBag()
        # Drain the bag
        while bag.tiles_remaining() > 0:
            bag.draw_tile()
        market = Market(bag)
        assert len(market.tiles) == 0


class TestTileBagEdgeCases:
    """Test TileBag edge cases."""

    def test_draw_from_empty_bag(self):
        bag = TileBag()
        while bag.tiles_remaining() > 0:
            bag.draw_tile()
        result = bag.draw_tile()
        assert result is None

    def test_tiles_remaining_accuracy(self):
        bag = TileBag()
        initial = bag.tiles_remaining()
        bag.draw_tile()
        assert bag.tiles_remaining() == initial - 1


class TestHexGridEdgeCases:
    """Test HexGrid error handling."""

    def test_set_tile_invalid_position(self):
        grid = HexGrid()
        with pytest.raises(ValueError):
            grid.set_tile(100, 100, -200, Tile(Color.BLUE, Pattern.DOTS))

    def test_get_tile_invalid_position(self):
        grid = HexGrid()
        with pytest.raises(ValueError):
            grid.get_tile(100, 100, -200)

    def test_is_position_empty_invalid(self):
        grid = HexGrid()
        result = grid.is_position_empty(100, 100, -200)
        assert result is False


class TestPlayerEdgeCases:
    """Test Player edge cases."""

    def test_place_tile_invalid_index(self):
        bag = TileBag()
        player = Player("Test", bag)
        result = player.place_tile(0, 0, 0, 99)
        assert result is False

    def test_place_tile_negative_index(self):
        bag = TileBag()
        player = Player("Test", bag)
        result = player.place_tile(0, 0, 0, -1)
        assert result is False


class TestGameModeEdgeCases:
    """Test GameMode error paths."""

    def test_apply_invalid_action_type(self):
        from source.game_state import Action
        game = SimulationMode(BOARD_1)
        action = Action(action_type="invalid_type")
        result = game.apply_action(action)
        assert result is False

    def test_place_tile_wrong_phase(self):
        from source.game_state import Action
        game = SimulationMode(BOARD_1)
        # Place a tile to get to CHOOSE_MARKET phase
        actions = game.get_legal_actions()
        game.apply_action(actions[0])
        # Now try to place again (should fail)
        empty = game.player.grid.get_empty_positions()[0]
        action = Action(action_type="place_tile", position=empty, hand_index=0)
        result = game.apply_action(action)
        assert result is False

    def test_choose_market_wrong_phase(self):
        from source.game_state import Action
        game = SimulationMode(BOARD_1)
        # Try to choose market while in PLACE_TILE phase
        action = Action(action_type="choose_market", market_index=0)
        result = game.apply_action(action)
        assert result is False

    def test_simulation_mode_run(self):
        game = SimulationMode(BOARD_1)
        # run() is a no-op but should not raise
        game.run()


class TestPlayModeEdgeCases:
    """Test PlayMode edge cases."""

    def test_state_change_callback(self):
        game = PlayMode(BOARD_1)
        callback_called = [False]

        def callback():
            callback_called[0] = True

        game.set_state_change_callback(callback)
        # Callback is called on successful placement
        game.select_hand_tile(0)
        empty = game.player.grid.get_empty_positions()[0]
        game.try_place_at_position(*empty)
        assert callback_called[0]

    def test_try_place_invalid_position(self):
        game = PlayMode(BOARD_1)
        game.select_hand_tile(0)
        # Try to place at invalid position
        result = game.try_place_at_position(100, 100, -200)
        assert result is False

    def test_get_legal_actions_game_over(self):
        game = SimulationMode(BOARD_1)
        game.play_random_game()
        actions = game.get_legal_actions()
        assert len(actions) == 0
