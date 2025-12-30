"""
Monte Carlo Tree Search agent for Calico.

Uses UCT (Upper Confidence Bounds for Trees) for action selection.
Supports hybrid evaluation: heuristic for early game, full rollouts for late game.
"""
import math
import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from simulation_mode import SimulationMode
from game_state import Action


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

    def __post_init__(self):
        """Initialize untried actions from state if not provided."""
        if not self.untried_actions and not self.is_terminal:
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
            action=action
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
        verbose: Print debug information
    """

    def __init__(
        self,
        exploration_constant: float = 1.4,
        max_iterations: int = 1000,
        late_game_threshold: int = 5,
        use_heuristic: bool = True,
        use_deterministic_rollout: bool = False,
        verbose: bool = False
    ):
        self.exploration_constant = exploration_constant
        self.max_iterations = max_iterations
        self.late_game_threshold = late_game_threshold
        self.use_heuristic = use_heuristic
        self.use_deterministic_rollout = use_deterministic_rollout
        self.verbose = verbose

        # Import heuristic lazily to avoid circular imports
        self._heuristic = None

    def _get_heuristic(self):
        """Lazy load heuristic module."""
        if self._heuristic is None:
            try:
                from heuristic import evaluate_state
                self._heuristic = evaluate_state
            except ImportError:
                # Fall back to simple current score if heuristic not available
                self._heuristic = lambda game: float(game.get_final_score())
        return self._heuristic

    def select_action(self, game: SimulationMode) -> Action:
        """
        Select the best action using MCTS.

        Args:
            game: Current game state (will not be modified)

        Returns:
            Best action according to MCTS
        """
        # Create root node from current state
        root = MCTSNode(state=game.copy())

        # Run MCTS iterations
        for _ in range(self.max_iterations):
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
        root = MCTSNode(state=game.copy())

        # Run MCTS iterations
        for _ in range(self.max_iterations):
            node = self._select(root)

            if not node.is_terminal and not node.is_fully_expanded:
                node = node.expand()

            score = self._simulate(node)
            self._backpropagate(node, score)

        # Handle edge case
        if not root.children:
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
        - Late game (few positions left): full rollout (random or deterministic)
        - Early/mid game: heuristic evaluation
        """
        remaining = len(node.state.player.grid.get_empty_positions())

        if remaining <= self.late_game_threshold:
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
        return float(state_copy.play_random_game())

    def _deterministic_rollout(self, state: SimulationMode) -> float:
        """
        Play game using greedy heuristic instead of random.

        At each step, evaluates all legal actions and picks the one
        with the highest heuristic score. More accurate than random
        rollouts but slower.
        """
        state_copy = state.copy()
        evaluate = self._get_heuristic()

        while not state_copy.is_game_over():
            actions = state_copy.get_legal_actions()
            if not actions:
                break

            # Evaluate each action with heuristic
            best_action = None
            best_score = float('-inf')

            for action in actions:
                test_state = state_copy.copy()
                test_state.apply_action(action)
                score = evaluate(test_state)

                if score > best_score:
                    best_score = score
                    best_action = action

            state_copy.apply_action(best_action)

        return float(state_copy.get_final_score())

    def _heuristic_evaluate(self, state: SimulationMode) -> float:
        """Evaluate state using heuristic function."""
        evaluate = self._get_heuristic()
        return evaluate(state)

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
            print(f"    {child.action.action_type}: visits={child.visits}, avg_score={avg:.1f}")
