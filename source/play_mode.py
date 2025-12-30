from typing import Optional, Callable

from game_mode import GameMode
from game_state import Action, TurnPhase


class PlayMode(GameMode):
    """
    Interactive single-player mode with pygame visualization.
    Manages game logic; visualization handled by PlayModeVisualizer.
    """

    def __init__(self, board_config=None):
        super().__init__(board_config)
        self.selected_hand_tile: Optional[int] = None
        self._on_state_change: Optional[Callable] = None

    def set_state_change_callback(self, callback: Callable):
        """Set callback to notify visualizer of state changes."""
        self._on_state_change = callback

    def _notify_state_change(self):
        """Notify visualizer that state has changed."""
        if self._on_state_change:
            self._on_state_change()

    # --- User Interaction Methods ---

    def select_hand_tile(self, index: int) -> bool:
        """Player selects a tile from hand to place."""
        if 0 <= index < len(self.player.tiles):
            self.selected_hand_tile = index
            return True
        return False

    def deselect_hand_tile(self):
        """Clear hand tile selection."""
        self.selected_hand_tile = None

    def try_place_at_position(self, q: int, r: int, s: int) -> bool:
        """
        Attempt to place selected hand tile at position.
        Called when player clicks on hex grid.
        """
        if self.selected_hand_tile is None:
            return False
        if self.turn_phase != TurnPhase.PLACE_TILE:
            return False

        action = Action(
            action_type="place_tile",
            position=(q, r, s),
            hand_index=self.selected_hand_tile
        )

        success = self.apply_action(action)
        if success:
            self.selected_hand_tile = None
            self._notify_state_change()
        return success

    def try_choose_market_tile(self, index: int) -> bool:
        """
        Attempt to choose tile from market.
        Called when player clicks on market tile.
        """
        if self.turn_phase != TurnPhase.CHOOSE_MARKET:
            return False

        action = Action(
            action_type="choose_market",
            market_index=index
        )

        success = self.apply_action(action)
        if success:
            self._notify_state_change()
        return success

    def run(self):
        """
        Start the game with pygame visualization.
        Delegates to PlayModeVisualizer.
        """
        from play_mode_visualizer import PlayModeVisualizer
        visualizer = PlayModeVisualizer(self)
        visualizer.run()

    # --- UI Helper Methods ---

    def get_status_message(self) -> str:
        """Get current status message for UI."""
        if self.turn_phase == TurnPhase.GAME_OVER:
            return f"Game Over! Final Score: {self.get_final_score()}"
        elif self.turn_phase == TurnPhase.PLACE_TILE:
            if self.selected_hand_tile is None:
                return "Select a tile from your hand"
            else:
                return "Click on an empty hex to place tile"
        elif self.turn_phase == TurnPhase.CHOOSE_MARKET:
            return "Choose a tile from the market"
        return ""

    def get_detailed_score(self) -> dict:
        """Get breakdown of score by cat."""
        scores = {}
        for cat in self.cats:
            scores[cat.name] = {
                'score': cat.score(self.player.grid),
                'patterns': cat.patterns
            }
        return scores
