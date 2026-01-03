from typing import Optional, Callable, List

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

        # Goal selection state (used during GOAL_SELECTION phase)
        # Maps slot index (0-2) to goal option index (0-3), None if empty
        self.goal_slot_assignments: List[Optional[int]] = [None, None, None]
        self.dragging_goal_index: Optional[int] = None  # Goal being dragged

    def set_state_change_callback(self, callback: Callable):
        """Set callback to notify visualizer of state changes."""
        self._on_state_change = callback

    def _notify_state_change(self):
        """Notify visualizer that state has changed."""
        if self._on_state_change:
            self._on_state_change()

    # --- Goal Selection Methods ---

    def start_drag_goal(self, goal_index: int) -> bool:
        """
        Begin dragging a goal from options or from a slot.

        Args:
            goal_index: Index of goal option (0-3) to start dragging

        Returns:
            True if drag started successfully
        """
        if self.turn_phase != TurnPhase.GOAL_SELECTION:
            return False
        if goal_index < 0 or goal_index >= 4:
            return False

        # If this goal is already in a slot, remove it from that slot
        for slot_idx, assigned in enumerate(self.goal_slot_assignments):
            if assigned == goal_index:
                self.goal_slot_assignments[slot_idx] = None

        self.dragging_goal_index = goal_index
        return True

    def drop_goal_on_slot(self, slot_index: int) -> bool:
        """
        Drop the currently dragged goal onto a position slot.

        Args:
            slot_index: Index of slot (0-2) to drop onto

        Returns:
            True if drop was successful
        """
        if self.turn_phase != TurnPhase.GOAL_SELECTION:
            return False
        if self.dragging_goal_index is None:
            return False
        if slot_index < 0 or slot_index >= 3:
            return False

        # If slot already has a goal, that goal goes back to available pool
        # (implicitly happens since we just overwrite the slot)
        self.goal_slot_assignments[slot_index] = self.dragging_goal_index
        self.dragging_goal_index = None
        self._notify_state_change()
        return True

    def cancel_drag(self):
        """Cancel the current drag operation."""
        self.dragging_goal_index = None

    def is_goal_available(self, goal_index: int) -> bool:
        """Check if a goal option is available (not placed in a slot)."""
        return goal_index not in self.goal_slot_assignments

    def get_slot_goal_index(self, slot_index: int) -> Optional[int]:
        """Get the goal option index assigned to a slot, or None if empty."""
        if 0 <= slot_index < 3:
            return self.goal_slot_assignments[slot_index]
        return None

    def can_confirm_goal_selection(self) -> bool:
        """Check if all 3 slots are filled and selection can be confirmed."""
        return all(slot is not None for slot in self.goal_slot_assignments)

    def confirm_goal_selection(self) -> bool:
        """
        Finalize goal selection and transition to tile placement.

        Returns:
            True if selection was confirmed, False if not all slots filled
        """
        if self.turn_phase != TurnPhase.GOAL_SELECTION:
            return False
        if not self.can_confirm_goal_selection():
            return False

        # Create the selection tuple: (goal at slot 0, goal at slot 1, goal at slot 2)
        selected_indices = tuple(self.goal_slot_assignments)

        action = Action(
            action_type="select_goals",
            selected_goal_indices=selected_indices
        )

        success = self.apply_action(action)
        if success:
            # Clear goal selection state
            self.goal_slot_assignments = [None, None, None]
            self.dragging_goal_index = None
            self._notify_state_change()
        return success

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
        if self.turn_phase == TurnPhase.GOAL_SELECTION:
            filled = sum(1 for slot in self.goal_slot_assignments if slot is not None)
            if self.dragging_goal_index is not None:
                return "Drop goal on a position slot"
            elif filled < 3:
                return f"Drag goals to positions ({filled}/3) - Press ENTER when done"
            else:
                return "Press ENTER to confirm goal selection"
        elif self.turn_phase == TurnPhase.GAME_OVER:
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
