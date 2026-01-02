# MAGIC DOC: 
# Calico MCTS AI - Developer Documentation

## Project Overview

A Monte Carlo Tree Search (MCTS) AI for the Calico board game - a hexagonal tile-placement puzzle game where players place colored/patterned tiles to score points via cats, goals, and buttons.

## Project Structure

```
cli.py                     # Root-level CLI entry point (run with: uv run cli.py)
source/
├── cli_app.py             # CLI implementation (play, mcts, replay, benchmark)
├── game_mode.py           # Abstract game mode base class
├── simulation_mode.py     # Non-visual mode for MCTS (contains copy logic)
├── play_mode.py           # Interactive human-playable mode with pygame
├── mcts_agent.py          # MCTS algorithm with UCT
├── heuristic.py           # Board evaluation heuristics
├── hex_grid.py            # Hexagonal grid with cube coordinates
├── tile_bag.py            # Tile drawing bag (108 tiles)
├── market.py              # 3-tile market display
├── player.py              # Player hand and grid state
├── cat.py                 # Cat scoring (Millie, Leo, Rumi, Tecolote)
├── goal.py                # Goal tile scoring
├── button.py              # Color group scoring
├── game_state.py          # Immutable state snapshot for agents
├── benchmark.py           # MLflow-tracked benchmarking
├── game_record.py         # Game recording/replay data structures
├── game_metadata.py       # Game metadata serialization for MLflow
├── run_mcts.py            # MCTS game runner with recording
└── replay_visualizer.py   # Step-by-step game replay visualization
tests/                     # Comprehensive test suite
game_records/              # Saved game recordings (JSON)
```

## Game Mechanics

- **Board:** 47-position hexagonal grid with 4 board variants (randomly selected at game start)
  - 22 pre-filled edge tiles (decorative border, used for button scoring)
  - 3 goal tile positions (fixed scoring reference points, cannot place tiles)
  - 22 playable empty positions (where player places tiles)
  - **Board variants:** BOARD_1 (Teal), BOARD_2 (Yellow), BOARD_3 (Purple), BOARD_4 (Green)
- **Tiles:** 108 tiles in bag (6 colors × 6 patterns × 3 copies each)
- **Turn:** Place tile from hand → Choose replacement from market
- **Scoring:** Cats (pattern groups) + Goals (neighbor distributions) + Buttons (color clusters)

## Goal System

### Goal Selection

At game start, 3 goal tiles are randomly selected from 6 available types and randomly placed on the 3 goal positions.

### Goal Types

| Goal | Single | Both | Requirement |
|------|--------|------|-------------|
| AAA-BBB | 8 | 13 | 3 of one color/pattern + 3 of another |
| AA-BB-CC | 7 | 11 | 2 each of 3 colors/patterns |
| All Unique | 10 | 15 | 6 different colors/patterns |
| AAAA-BB | 7 | 14 | 4 of one color/pattern + 2 of another |
| AA-BB-C-D | 5 | 7 | 2+2+1+1 distribution |
| AAA-BB-C | 7 | 11 | 3+2+1 distribution |

Goals score based on the 6 tiles adjacent to the goal position. "Single" points if color OR pattern condition is met; "Both" points if both conditions are met simultaneously.

## Cat System

### Bucket-Based Selection

Cats are organized into buckets for random selection at game start. Each game picks one cat from each bucket:

```python
# source/cat.py
BUCKET_1 = [CatMillie, CatRumi]   # Target: 4 cats (cluster/3-line scoring)
BUCKET_2 = [CatTecolote]          # Target: 4 cats (4-line scoring)
BUCKET_3 = [CatLeo]               # Target: 2 cats (5-line scoring)
```

### Current Cats

| Cat | Points | Requirement | Bucket |
|-----|--------|-------------|--------|
| Millie | 3 | 3 touching tiles, same pattern | 1 |
| Rumi | 5 | 3 tiles in a line, same pattern | 1 |
| Tecolote | 7 | 4 tiles in a line, same pattern | 2 |
| Leo | 11 | 5 tiles in a line, same pattern | 3 |

### Adding New Cats

To add a new cat:

1. Create class in `source/cat.py` extending `Cat`
2. Implement `find_all_groups()` method using pre-computed line constants (`ALL_3_LINES`, `ALL_4_LINES`, `ALL_5_LINES`)
3. Add to appropriate bucket list
4. Add tests in `tests/test_cats.py` with dedicated fixture (see existing `millie_setup`, `leo_setup`, etc.)

Example for line-based cats:
```python
class CatNewCat(Cat):
    def __init__(self):
        super().__init__("NewCat", 8, tuple(random.sample(list(Pattern), 2)))

    def find_all_groups(self, grid: HexGrid, used_tiles: Set[Tuple[int, int, int]]) -> List[FrozenSet[Tuple[int, int, int]]]:
        # Use ALL_X_LINES constant and pattern matching
        # See CatTecolote for reference implementation
        ...
```

## MCTS Integrity

**The MCTS implementation is HONEST and cannot cheat by seeing future tile draws.**

### Key Protections

1. **Independent tile bag copies:** Each simulation branch gets its own copy via `tile_bag.__copy__()`
2. **Shuffled future tiles:** `shuffle_remaining()` called on each copy randomizes draw order
3. **Hidden bag order:** `GameState` only exposes tile count, not actual list
4. **No original state mutation:** Each MCTS branch works on independent copy

### Verification Points

- `source/simulation_mode.py:copy()` - Creates isolated game state with shuffled bag
- `source/tile_bag.py:shuffle_remaining()` - Randomizes remaining tiles
- `source/game_state.py` - Only exposes `tiles_remaining_in_bag` count

## CLI Commands

Run all commands from the project root directory using `uv run cli.py`:

```bash
uv run cli.py play              # Interactive game with pygame
uv run cli.py mcts              # Run single MCTS game
uv run cli.py mcts --baseline 10  # Compare MCTS vs random
uv run cli.py mcts --record     # Record game for replay
uv run cli.py replay --latest   # Replay most recent recorded game
uv run cli.py replay --list     # List available recordings
uv run cli.py benchmark         # Run benchmark with MLflow tracking
uv run cli.py mlflow-ui         # Start MLflow UI at localhost:5000
```

## Game Recording

Games are recorded in `game_records/` as JSON files containing:
- MCTS configuration
- Cat and goal assignments (name, point value, patterns)
- All decisions with candidates and visit counts
- Final score breakdown

Example structure:
```json
{
  "format_version": "2.0",
  "timestamp": "20251231_095041",
  "mcts_config": {...},
  "cats": [
    {"name": "Rumi", "point_value": 5, "patterns": ["CLUBS", "FLOWERS"]}
  ],
  "goals": [...],
  "decisions": [...],
  "final_score": 77,
  "score_breakdown": {...}
}
```

## MLflow Benchmarking

Benchmarks log to SQLite database (`mlflow.db`) with:
- MCTS parameters (iterations, exploration, etc.)
- Performance metrics (mean score, improvement over random)
- Git commit info
- Seeds for reproducibility
- **Game metadata (cats, goals, boards)** - tracked via `GameMetadata` class

```bash
uv run cli.py benchmark -n 16 -i 5000 --tag "experiment_name"
uv run cli.py mlflow-ui  # View results at http://localhost:5000
```

### MLflow Game Metadata

Each benchmark run logs:
- **Tags:** `cats_used`, `goals_used`, `boards_used` - comma-separated names for filtering
- **Parameters:** Detailed first-game metadata (`cat_1_name`, `cat_1_patterns`, etc.)

The `GameMetadata` class (in `source/game_metadata.py`) provides:
- Extraction from game instances
- Serialization to MLflow params/tags
- JSON round-trip for storage
- Parsing back from MLflow params

This is designed to be extensible - when you add new boards, goals, or cat types, the metadata system will capture them automatically.

## Test Suite

Run tests with:
```bash
uv run cli.py test
# or
uv run pytest tests/ -v
```

Key test files:
- `tests/test_cats.py` - Cat scoring with deterministic fixtures
- `tests/test_mcts.py` - MCTS integrity and state isolation
- `tests/test_game_record.py` - Recording/replay functionality
- `tests/test_game_metadata.py` - Game metadata serialization
- `tests/test_heuristic.py` - Heuristic evaluation

## Known TODOs

- [ ] Add remaining cats to complete buckets (6 more cats needed)
- [ ] Add remaining goal tile scoring visuals/display
