# Engine Suggestion Feature - Implementation Plan

## Overview

Add chess-computer-style analysis features to play mode:
1. **Engine Suggestions** (Phase 1) - Toggle to see MCTS-recommended moves with score breakdowns
2. **Analysis Mode** (Phase 2) - Sandbox for exploring alternative lines
3. **Full Analysis** (Phase 3) - Monte Carlo comparison and detailed reasoning

---

## Phase 1: Engine Suggestions in Play Mode (IMPLEMENT NOW)

### Goal
Press `E` during play to see MCTS evaluation of current position with top candidate moves and specific reasons.

### User Experience

```
┌─────────────────────────────────────────┐
│ ENGINE ANALYSIS (1000 iterations)       │
├─────────────────────────────────────────┤
│ ★ Place BLUE/DOTS at (2,1) → take PINK  │
│   Expected: 74.2 pts  (visits: 412)     │
│   Cats: +3.1 (Leo line 4/5 STRIPES)     │
│   Goals: +2.0 (AAA-BBB 5/6 filled)      │
│   Buttons: +0.5 (blue pair → button)    │
├─────────────────────────────────────────┤
│   Place GREEN/STRIPES at (1,2) → ORANGE │
│   Expected: 71.8 pts  (visits: 298)     │
│   Cats: +2.4 (Tecolote potential)       │
│   Goals: +1.8 (AA-BB-CC progress)       │
│   Buttons: +0.2 (green pair)            │
└─────────────────────────────────────────┘
[E] Hide suggestions
```

### Files to Modify

#### 1. `source/heuristic.py` - Add detailed breakdown

```python
@dataclass
class ScoreBreakdown:
    """Detailed breakdown of why a position scores well."""
    total: float
    cat_score: float
    goal_score: float
    button_score: float
    cat_reasons: list[str]    # ["Leo 4/5 STRIPES line", "Millie pair"]
    goal_reasons: list[str]   # ["AAA-BBB: 5/6 (colors)", "All Unique: 4/6"]
    button_reasons: list[str] # ["Blue pair → button potential", "Rainbow 5/6"]

def evaluate_state_with_breakdown(game, config=None) -> ScoreBreakdown:
    """Evaluate state and return detailed breakdown with reasons."""
    # Similar to evaluate_state but collects reasons along the way
    ...
```

**Implementation details:**
- Modify `evaluate_cats()` to optionally return reasons (cat name, pattern, progress)
- Modify `evaluate_goals()` to optionally return reasons (goal name, progress fraction)
- Modify `evaluate_buttons()` to optionally return reasons (which colors have pairs)
- Create `ScoreBreakdown` dataclass to hold all this info

#### 2. `source/mcts_agent.py` - Extend analysis method

```python
def select_action_with_detailed_analysis(
    self,
    game,
    n_candidates: int = 5
) -> tuple[Action, list[CandidateInfo]]:
    """
    Return best action plus detailed analysis of top candidates.

    Each CandidateInfo contains:
    - action: The Action object
    - visits: Number of MCTS visits
    - avg_score: Average expected score
    - breakdown: ScoreBreakdown with reasons
    """
    ...
```

**Implementation:**
- After MCTS completes, for each top candidate:
  - Apply the action to a game copy
  - Call `evaluate_state_with_breakdown()` on resulting position
  - Package into `CandidateInfo`

#### 3. `source/play_mode.py` - Add suggestion state

```python
class PlayMode(GameMode):
    def __init__(self, ...):
        ...
        self.show_engine_suggestion = False
        self.engine_candidates: list[CandidateInfo] | None = None
        self.engine_computing = False

    def toggle_engine_suggestion(self):
        """Toggle engine suggestion display."""
        self.show_engine_suggestion = not self.show_engine_suggestion
        if self.show_engine_suggestion and self.engine_candidates is None:
            self._compute_engine_suggestion()

    def _compute_engine_suggestion(self):
        """Run MCTS to get candidate moves with analysis."""
        self.engine_computing = True
        # Create MCTS agent with default config
        agent = MCTSAgent(iterations=1000)
        _, candidates = agent.select_action_with_detailed_analysis(self.game, n_candidates=5)
        self.engine_candidates = candidates
        self.engine_computing = False
        self._notify_state_change()

    def _on_action_complete(self):
        """Clear cached suggestions when position changes."""
        self.engine_candidates = None
```

#### 4. `source/play_mode_visualizer.py` - Add rendering

```python
class PlayModeVisualizer:
    def __init__(self, ...):
        ...
        self.suggestion_panel_rect = pygame.Rect(...)  # Position on screen

    def handle_events(self):
        ...
        elif event.key == pygame.K_e:
            self.play_mode.toggle_engine_suggestion()
        ...

    def _draw_engine_suggestions(self, surface):
        """Draw engine suggestion panel if visible."""
        if not self.play_mode.show_engine_suggestion:
            return

        if self.play_mode.engine_computing:
            # Draw "Computing..." message
            ...
        elif self.play_mode.engine_candidates:
            # Draw candidates with breakdowns
            for i, candidate in enumerate(self.play_mode.engine_candidates):
                self._draw_candidate(surface, candidate, i, is_best=(i == 0))

    def _draw_candidate(self, surface, candidate, index, is_best):
        """Draw a single candidate move with breakdown."""
        # Star for best move
        # Action description (tile placement + market choice)
        # Expected score and visit count
        # Cat/Goal/Button breakdown with reasons
        ...
```

### New Data Structures

```python
# In source/heuristic.py or new source/analysis.py

@dataclass
class ScoreBreakdown:
    """Detailed score breakdown with human-readable reasons."""
    total: float
    cat_score: float
    goal_score: float
    button_score: float
    cat_reasons: list[str]
    goal_reasons: list[str]
    button_reasons: list[str]

    def format_summary(self) -> str:
        """Format as compact string for display."""
        parts = []
        if self.cat_reasons:
            parts.append(f"Cats: +{self.cat_score:.1f} ({self.cat_reasons[0]})")
        if self.goal_reasons:
            parts.append(f"Goals: +{self.goal_score:.1f} ({self.goal_reasons[0]})")
        if self.button_reasons:
            parts.append(f"Buttons: +{self.button_score:.1f} ({self.button_reasons[0]})")
        return "\n".join(parts)


@dataclass
class CandidateInfo:
    """Full analysis of a candidate move."""
    action: Action
    visits: int
    avg_score: float
    breakdown: ScoreBreakdown

    @property
    def action_description(self) -> str:
        """Human-readable description of the action."""
        # "Place BLUE/DOTS at (2,1) → take PINK/STRIPES"
        ...
```

### Key Implementation Notes

1. **Performance**: MCTS takes 100-500ms. Show "Computing..." while running.

2. **Caching**: Cache suggestions until position changes. Clear on any action.

3. **Reason Generation**:
   - For cats: Include cat name, pattern being worked on, progress (e.g., "Leo 4/5 STRIPES")
   - For goals: Include goal name, which attribute (color/pattern), progress (e.g., "AAA-BBB colors 5/6")
   - For buttons: Include color, state (pair vs button), rainbow progress

4. **UI Layout**: Put suggestion panel on right side, similar to replay visualizer's candidate display.

5. **Toggle UX**:
   - `E` to show/hide
   - Computing state shows spinner or "Analyzing..."
   - Results persist until next action

---

## Phase 2: Analysis Mode (FUTURE)

### Goal
Enter a sandbox mode to explore alternative lines without affecting the actual game.

### Entry/Exit
- `A` - Enter analysis mode (freeze game, snapshot state)
- `Escape` - Exit analysis mode (return to frozen position)
- `Enter` - Commit: exit and make the currently shown move in real game

### State Management

```python
@dataclass
class TileBagSnapshot:
    """Snapshot of tile bag for deterministic replay."""
    remaining_tiles: list[Tile]  # Exact order

    def restore_to(self, tile_bag: TileBag):
        """Restore tile bag to this exact state."""
        tile_bag._tiles = list(self.remaining_tiles)

@dataclass
class GameSnapshot:
    """Complete game state for analysis mode."""
    game_copy: SimulationMode  # Deep copy of game
    tile_bag_snapshot: TileBagSnapshot
    turn_number: int

@dataclass
class AnalysisBranch:
    """A line of play from a decision point."""
    moves: list[Action]
    expected_score: float
    breakdown: ScoreBreakdown
    description: str  # "Your move" or "Engine recommendation"

@dataclass
class AnalysisState:
    """Full analysis mode state."""
    original_snapshot: GameSnapshot  # Return point
    current_game: SimulationMode  # Working copy (can be modified)
    branches: list[AnalysisBranch]  # Alternative lines
    current_branch_index: int
    current_depth: int  # Position within branch
    tile_mode: Literal["actual", "monte_carlo"]
```

### Key Features

1. **Snapshot on entry**: Deep copy game + tile bag state
2. **Branch navigation**: `←/→` to switch branches, `↑/↓` to move within branch
3. **Extend branch**: `Space` to have engine play one more move
4. **Tile mode toggle**: `T` to switch between actual tiles and Monte Carlo

### Files to Modify

- `source/play_mode.py` - Add analysis mode state machine
- `source/play_mode_visualizer.py` - Add analysis mode UI
- `source/simulation_mode.py` - Add deep copy with tile bag snapshot
- New `source/analysis_state.py` - Data structures for analysis

---

## Phase 3: Full Analysis Features (FUTURE)

### Monte Carlo Mode

When in analysis mode with tile_mode="monte_carlo":
- Instead of using actual tile sequence, run N simulations with random tiles
- Show expected value as average over simulations
- Useful for "is this move generally better?" rather than "was it better given the tiles I got?"

```python
def evaluate_move_monte_carlo(
    game: SimulationMode,
    action: Action,
    n_simulations: int = 100
) -> tuple[float, float]:  # (mean_score, std_dev)
    """Evaluate a move by averaging over many random futures."""
    scores = []
    for _ in range(n_simulations):
        game_copy = game.copy()  # Gets shuffled tile bag
        game_copy.apply_action(action)
        # Play out rest of game with MCTS or random
        final_score = play_to_completion(game_copy)
        scores.append(final_score)
    return np.mean(scores), np.std(scores)
```

### Detailed Reasoning

Enhance `ScoreBreakdown` to include:
- Specific hex positions involved (for highlighting on board)
- Confidence levels (high/medium/low based on tiles remaining)
- Trade-off explanations ("sacrifices Leo potential for button completion")

### Visual Enhancements

- Highlight relevant hexes on board when viewing a reason
- Show "ghost" tiles for candidate placements
- Animate between branches

---

## Testing Strategy

### Phase 1 Tests

```python
# tests/test_engine_suggestion.py

def test_score_breakdown_generation():
    """ScoreBreakdown correctly identifies reasons."""
    game = create_test_game_with_leo_potential()
    breakdown = evaluate_state_with_breakdown(game)
    assert "Leo" in breakdown.cat_reasons[0]
    assert breakdown.cat_score > 0

def test_toggle_engine_suggestion():
    """Toggle triggers computation and caches result."""
    play_mode = PlayMode(...)
    assert play_mode.engine_candidates is None
    play_mode.toggle_engine_suggestion()
    assert play_mode.engine_candidates is not None
    assert len(play_mode.engine_candidates) <= 5

def test_suggestions_cleared_on_action():
    """Cached suggestions cleared when position changes."""
    play_mode = PlayMode(...)
    play_mode.toggle_engine_suggestion()
    assert play_mode.engine_candidates is not None
    play_mode.place_tile(...)  # Make a move
    assert play_mode.engine_candidates is None
```

### Phase 2 Tests

```python
def test_snapshot_restore():
    """Game snapshot restores exact state including tile bag."""
    game = create_test_game()
    snapshot = GameSnapshot.from_game(game)
    # Make moves
    game.apply_action(...)
    game.apply_action(...)
    # Restore
    restored = snapshot.restore()
    assert restored.turn_number == snapshot.turn_number
    # Tile bag should produce same tiles
    ...

def test_analysis_mode_isolation():
    """Changes in analysis mode don't affect real game."""
    play_mode = PlayMode(...)
    original_turn = play_mode.game.turn_number
    play_mode.enter_analysis_mode()
    play_mode.analysis_state.current_game.apply_action(...)
    play_mode.exit_analysis_mode()
    assert play_mode.game.turn_number == original_turn
```

---

## Implementation Order (Phase 1)

1. **ScoreBreakdown dataclass** in `heuristic.py`
2. **evaluate_state_with_breakdown()** function
3. **CandidateInfo dataclass**
4. **select_action_with_detailed_analysis()** in `mcts_agent.py`
5. **PlayMode state and toggle**
6. **PlayModeVisualizer rendering**
7. **Tests**
8. **Update docs.md**

---

## Design Decisions

1. **Iteration count**: Configurable via +/- keys (default 1000, range 250-5000)

2. **Panel position**: Right side, consistent with replay mode's candidate display

3. **Keyboard shortcuts**:
   - `E` - Toggle engine suggestions (Phase 1)
   - `+`/`-` - Increase/decrease MCTS iterations
   - `A` - Enter analysis mode (Phase 2)
   - `Escape` - Exit analysis mode
   - `Enter` - Commit move from analysis

4. **Background computation**: Phase 1 uses synchronous computation with "Computing..." indicator. Background threading can be added later if UX demands it.
