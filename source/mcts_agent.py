"""
Monte Carlo Tree Search agent for Calico.

Uses UCT (Upper Confidence Bounds for Trees) for action selection.
Supports hybrid evaluation: heuristic for early game, full rollouts for late game.
"""
import math
import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, TYPE_CHECKING

from simulation_mode import SimulationMode
from game_state import Action, TurnPhase

if TYPE_CHECKING:
    from heuristic import HeuristicConfig


@dataclass
class MCTSNode:
    """Node in the MCTS search tree."""
    state: SimulationMode
    parent: Optional['MCTSNode'] = None
    action: Optional[Action] = None  # Action taken to reach this node
    children: List['MCTSNode'] = field(default_factory=list)
    visits: int = 0
    total_score: float = 0.0
    untried_actions: List[Action] = field(default_factory=list)
    use_combined_actions: bool = True  # Whether to use combined place_and_choose actions

    def __post_init__(self):
        """Initialize untried actions from state if not provided."""
        if not self.untried_actions and not self.is_terminal:
            # Goal selection phase always uses get_legal_actions()
            if self.state.turn_phase == TurnPhase.GOAL_SELECTION:
                self.untried_actions = self.state.get_legal_actions()
            elif self.use_combined_actions:
                self.untried_actions = self.state.get_combined_legal_actions()
            else:
                self.untried_actions = self.state.get_legal_actions()

    @property
    def is_fully_expanded(self) -> bool:
        """True if all legal actions have been tried."""
        return len(self.untried_actions) == 0

    @property
    def is_terminal(self) -> bool:
        """True if game is over at this node."""
        return self.state.is_game_over()

    def ucb1_score(self, exploration_constant: float) -> float:
        """
        Calculate UCB1 score for node selection.

        UCB1 = exploitation + exploration
             = (avg_score) + C * sqrt(ln(parent_visits) / visits)
        """
        if self.visits == 0:
            return float('inf')

        exploitation = self.total_score / self.visits
        exploration = exploration_constant * math.sqrt(
            math.log(self.parent.visits) / self.visits
        )
        return exploitation + exploration

    def best_child(self, exploration_constant: float) -> 'MCTSNode':
        """Return child with highest UCB1 score."""
        return max(self.children, key=lambda c: c.ucb1_score(exploration_constant))

    def expand(self) -> 'MCTSNode':
        """
        Expand one untried action and return the new child node.
        """
        action = self.untried_actions.pop()
        child_state = self.state.copy()
        child_state.apply_action(action)

        child = MCTSNode(
            state=child_state,
            parent=self,
            action=action,
            use_combined_actions=self.use_combined_actions
        )
        self.children.append(child)
        return child


class MCTSAgent:
    """
    MCTS agent for Calico using UCT selection.

    Parameters:
        exploration_constant: UCB1 exploration weight (default: 1.4, ~sqrt(2))
        max_iterations: Number of MCTS iterations per decision
        late_game_threshold: Remaining positions below which to use full rollouts
        use_heuristic: Whether to use heuristic evaluation in early/mid game
        use_deterministic_rollout: Use greedy heuristic rollouts instead of random
        use_combined_actions: Use combined place_and_choose actions (atomic turns)
        heuristic_config: Configuration for heuristic weights (cat/goal/button weights)
        goal_selection_iteration_multiplier: Multiplier for iterations during goal selection
        goal_selection_rollout_depth: Minimum moves to simulate before heuristic during
            goal selection evaluation. Ensures the tree sees early game development.
            0 = use heuristic immediately (original behavior)
            -1 = full rollout to end of game
            N = simulate N random moves, then evaluate with heuristic
        verbose: Print debug information
    """

    def __init__(
        self,
        exploration_constant: float = 1.4,
        max_iterations: int = 1000,
        late_game_threshold: int = 5,
        use_heuristic: bool = True,
        use_deterministic_rollout: bool = False,
        use_combined_actions: bool = True,
        heuristic_config: 'HeuristicConfig' = None,
        goal_selection_iteration_multiplier: float = 2.5,
        goal_selection_rollout_depth: int = 8,
        verbose: bool = False
    ):
        self.exploration_constant = exploration_constant
        self.max_iterations = max_iterations
        self.late_game_threshold = late_game_threshold
        self.use_heuristic = use_heuristic
        self.use_deterministic_rollout = use_deterministic_rollout
        self.use_combined_actions = use_combined_actions
        self.heuristic_config = heuristic_config
        self.goal_selection_iteration_multiplier = goal_selection_iteration_multiplier
        self.goal_selection_rollout_depth = goal_selection_rollout_depth
        self.verbose = verbose

        # Import heuristic lazily to avoid circular imports
        self._heuristic_func = None

    def _get_heuristic(self):
        """Lazy load heuristic module and return evaluation function."""
        if self._heuristic_func is None:
            try:
                from heuristic import evaluate_state, DEFAULT_HEURISTIC_CONFIG
                # Store the actual function
                self._heuristic_func = evaluate_state
                # Use provided config or default
                if self.heuristic_config is None:
                    self.heuristic_config = DEFAULT_HEURISTIC_CONFIG
            except ImportError:
                # Fall back to simple current score if heuristic not available
                self._heuristic_func = lambda game, config=None: float(game.get_final_score())
        return self._heuristic_func

    def _evaluate_state(self, state: SimulationMode) -> float:
        """Evaluate a state using the heuristic with configured weights."""
        evaluate = self._get_heuristic()
        return evaluate(state, self.heuristic_config)

    def _get_iterations_for_phase(self, game: SimulationMode) -> int:
        """Get the number of iterations to use based on game phase."""
        if game.turn_phase == TurnPhase.GOAL_SELECTION:
            return int(self.max_iterations * self.goal_selection_iteration_multiplier)
        return self.max_iterations

    def select_action(self, game: SimulationMode) -> Action:
        """
        Select the best action using MCTS.

        Args:
            game: Current game state (will not be modified)

        Returns:
            Best action according to MCTS
        """
        # Create root node from current state
        root = MCTSNode(state=game.copy(), use_combined_actions=self.use_combined_actions)

        # Get number of iterations (higher for goal selection)
        iterations = self._get_iterations_for_phase(game)

        # Run MCTS iterations
        for _ in range(iterations):
            # Selection: traverse tree using UCB1
            node = self._select(root)

            # Expansion: add one child if not terminal and not fully expanded
            if not node.is_terminal and not node.is_fully_expanded:
                node = node.expand()

            # Simulation: evaluate the position
            score = self._simulate(node)

            # Backpropagation: update statistics up the tree
            self._backpropagate(node, score)

        # Return action of most-visited child (robust selection)
        if not root.children:
            # Edge case: no children expanded (very few iterations)
            if game.turn_phase == TurnPhase.GOAL_SELECTION:
                actions = game.get_legal_actions()
            elif self.use_combined_actions:
                actions = game.get_combined_legal_actions()
            else:
                actions = game.get_legal_actions()
            return random.choice(actions) if actions else None

        best_child = max(root.children, key=lambda c: c.visits)

        if self.verbose:
            self._print_stats(root)

        return best_child.action

    def select_action_with_analysis(
        self, game: SimulationMode, n_candidates: int = 5
    ) -> Tuple[Action, List[Tuple[Action, int, float]]]:
        """
        Select the best action and return analysis of top candidates.

        Used for game recording to capture MCTS decision info.

        Args:
            game: Current game state (will not be modified)
            n_candidates: Number of top candidates to return

        Returns:
            Tuple of (best_action, candidates)
            where candidates is list of (action, visits, avg_score) tuples
        """
        # Create root node from current state
        root = MCTSNode(state=game.copy(), use_combined_actions=self.use_combined_actions)

        # Get number of iterations (higher for goal selection)
        iterations = self._get_iterations_for_phase(game)

        # Run MCTS iterations
        for _ in range(iterations):
            node = self._select(root)

            if not node.is_terminal and not node.is_fully_expanded:
                node = node.expand()

            score = self._simulate(node)
            self._backpropagate(node, score)

        # Handle edge case
        if not root.children:
            if game.turn_phase == TurnPhase.GOAL_SELECTION:
                actions = game.get_legal_actions()
            elif self.use_combined_actions:
                actions = game.get_combined_legal_actions()
            else:
                actions = game.get_legal_actions()
            if actions:
                return actions[0], [(actions[0], 0, 0.0)]
            return None, []

        # Sort children by visits (robust selection)
        sorted_children = sorted(root.children, key=lambda c: c.visits, reverse=True)
        best_child = sorted_children[0]

        # Extract top candidates
        candidates = []
        for child in sorted_children[:n_candidates]:
            avg_score = child.total_score / child.visits if child.visits > 0 else 0.0
            candidates.append((child.action, child.visits, avg_score))

        if self.verbose:
            self._print_stats(root)

        return best_child.action, candidates

    def _select(self, node: MCTSNode) -> MCTSNode:
        """
        Selection phase: traverse tree using UCB1 until we find
        a node that is not fully expanded or is terminal.
        """
        while not node.is_terminal:
            if not node.is_fully_expanded:
                return node
            node = node.best_child(self.exploration_constant)
        return node

    def _simulate(self, node: MCTSNode) -> float:
        """
        Simulation phase: evaluate the node's position.

        Uses hybrid strategy:
        - Goal selection: deeper partial rollouts to see early game development
        - Late game (few positions left): full rollout (random or deterministic)
        - Early/mid game: heuristic evaluation
        """
        remaining = len(node.state.player.grid.get_empty_positions())

        # Check if we're in or just after goal selection (no tiles placed yet)
        # This ensures deeper evaluation for early game states after goal selection
        is_early_game_after_goals = (
            node.state.turn_phase != TurnPhase.GOAL_SELECTION and
            remaining == 22  # Full board, just finished goal selection
        )

        if is_early_game_after_goals and self.goal_selection_rollout_depth != 0:
            # Use deeper rollouts for goal selection evaluation
            return self._partial_rollout(node.state, self.goal_selection_rollout_depth)
        elif remaining <= self.late_game_threshold:
            # Late game: rollout for accuracy
            if self.use_deterministic_rollout:
                return self._deterministic_rollout(node.state)
            else:
                return self._full_rollout(node.state)
        elif self.use_heuristic:
            # Early/mid game: heuristic evaluation for speed
            return self._heuristic_evaluate(node.state)
        else:
            # Fallback: rollout
            if self.use_deterministic_rollout:
                return self._deterministic_rollout(node.state)
            else:
                return self._full_rollout(node.state)

    def _full_rollout(self, state: SimulationMode) -> float:
        """Play random game to completion and return final score."""
        state_copy = state.copy()
        return float(state_copy.play_random_game(use_combined_actions=self.use_combined_actions))

    def _partial_rollout(self, state: SimulationMode, depth: int) -> float:
        """
        Play random moves for a specified depth, then evaluate with heuristic.

        This gives deeper evaluation than pure heuristic while being faster than
        full rollouts. Useful for goal selection where we need to see how early
        game develops but don't need to simulate the entire game.

        Args:
            state: Game state to evaluate
            depth: Number of moves to simulate (-1 for full rollout)

        Returns:
            Evaluation score (heuristic after partial rollout, or final score)
        """
        if depth == -1:
            # Full rollout mode
            return self._full_rollout(state)

        state_copy = state.copy()
        moves_made = 0

        while not state_copy.is_game_over() and moves_made < depth:
            # Get legal actions based on phase
            if state_copy.turn_phase == TurnPhase.GOAL_SELECTION:
                actions = state_copy.get_legal_actions()
            elif self.use_combined_actions:
                actions = state_copy.get_combined_legal_actions()
            else:
                actions = state_copy.get_legal_actions()

            if not actions:
                break

            # Random action selection for speed
            action = random.choice(actions)
            state_copy.apply_action(action)
            moves_made += 1

        # If game ended during rollout, return actual score
        if state_copy.is_game_over():
            return float(state_copy.get_final_score())

        # Otherwise evaluate with heuristic
        return self._heuristic_evaluate(state_copy)

    def _deterministic_rollout(self, state: SimulationMode) -> float:
        """
        Play game using greedy heuristic instead of random.

        At each step, evaluates all legal actions and picks the one
        with the highest heuristic score. More accurate than random
        rollouts but slower.
        """
        state_copy = state.copy()

        while not state_copy.is_game_over():
            # Goal selection uses regular actions, otherwise respect combined_actions flag
            if state_copy.turn_phase == TurnPhase.GOAL_SELECTION:
                actions = state_copy.get_legal_actions()
            elif self.use_combined_actions:
                actions = state_copy.get_combined_legal_actions()
            else:
                actions = state_copy.get_legal_actions()
            if not actions:
                break

            # Evaluate each action with heuristic
            best_action = None
            best_score = float('-inf')

            for action in actions:
                test_state = state_copy.copy()
                test_state.apply_action(action)
                score = self._evaluate_state(test_state)

                if score > best_score:
                    best_score = score
                    best_action = action

            state_copy.apply_action(best_action)

        return float(state_copy.get_final_score())

    def _heuristic_evaluate(self, state: SimulationMode) -> float:
        """Evaluate state using heuristic function with configured weights."""
        return self._evaluate_state(state)

    def _backpropagate(self, node: MCTSNode, score: float) -> None:
        """Update visit counts and scores up the tree."""
        while node is not None:
            node.visits += 1
            node.total_score += score
            node = node.parent

    def _print_stats(self, root: MCTSNode) -> None:
        """Print debug statistics about the search."""
        print(f"\nMCTS Statistics:")
        print(f"  Total iterations: {root.visits}")
        print(f"  Children explored: {len(root.children)}")
        print(f"  Top 5 actions by visits:")

        sorted_children = sorted(root.children, key=lambda c: c.visits, reverse=True)
        for child in sorted_children[:5]:
            avg = child.total_score / child.visits if child.visits > 0 else 0
            action = child.action
            if action.action_type == "place_and_choose":
                market_str = f", market={action.market_index}" if action.market_index is not None else " (final)"
                print(f"    place_and_choose: pos={action.position}, hand={action.hand_index}{market_str}, "
                      f"visits={child.visits}, avg={avg:.1f}")
            else:
                print(f"    {action.action_type}: visits={child.visits}, avg_score={avg:.1f}")
