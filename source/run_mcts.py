"""
Entry point for running MCTS agent for Calico.

Usage:
    python run_mcts.py                    # Run single MCTS game with verbose output
    python run_mcts.py --baseline 10      # Compare 10 games MCTS vs random
    python run_mcts.py --iterations 2000  # Set iterations per move
    python run_mcts.py --verbose          # Show per-move decision details
    python run_mcts.py --no-heuristic     # Use full rollouts only
    python run_mcts.py --save-boards 5    # Save top 5 boards to JSON
    python run_mcts.py --record           # Record game with MCTS decision analysis
"""
import argparse
import json
import os
import time
from datetime import datetime
from statistics import mean, stdev
from typing import List, Tuple

from simulation_mode import SimulationMode
from board_configurations import BOARD_1
from mcts_agent import MCTSAgent
from game_record import GameRecorder, GameRecord


def run_mcts_game(agent: MCTSAgent, verbose: bool = False) -> Tuple[int, SimulationMode]:
    """
    Run a single game with MCTS agent.

    Args:
        agent: MCTSAgent instance
        verbose: Print per-move details

    Returns:
        Tuple of (final_score, completed_game)
    """
    game = SimulationMode(BOARD_1)
    turn = 0

    while not game.is_game_over():
        actions = game.get_legal_actions()
        if not actions:
            break

        # Use MCTS to select action
        start = time.time()
        action = agent.select_action(game)
        elapsed = time.time() - start

        if verbose:
            state = game.get_game_state()
            remaining = len(state.empty_positions)
            phase = state.turn_phase.name
            print(f"Turn {turn:2d} | Phase: {phase:13s} | "
                  f"Remaining: {remaining:2d} | Time: {elapsed:.2f}s")

            if action.action_type == "place_tile":
                hand_tile = state.player_hand[action.hand_index]
                print(f"         Action: Place {hand_tile.color.name} "
                      f"{hand_tile.pattern.name} at {action.position}")
            else:
                market_tile = state.market_tiles[action.market_index]
                print(f"         Action: Take {market_tile.color.name} "
                      f"{market_tile.pattern.name} from market")

        game.apply_action(action)
        turn += 1

    final_score = game.get_final_score()

    if verbose:
        print("\n" + "=" * 50)
        print("GAME COMPLETE")
        print("=" * 50)
        print(f"Final Score: {final_score}")
        print()
        print("Score Breakdown:")
        print(f"  Cat Scores:    {game.get_cat_scores()}")
        print(f"  Goal Scores:   {game.get_goal_scores()}")
        button_info = game.get_button_scores()
        print(f"  Button Score:  {button_info['total_score']} "
              f"({button_info['total_buttons']} buttons, "
              f"rainbow: {button_info['has_rainbow']})")

    return final_score, game


def run_recorded_mcts_game(
    agent: MCTSAgent, verbose: bool = False
) -> Tuple[int, SimulationMode, GameRecord]:
    """
    Run a single game with MCTS agent and record all decisions.

    Args:
        agent: MCTSAgent instance
        verbose: Print per-move details

    Returns:
        Tuple of (final_score, completed_game, game_record)
    """
    game = SimulationMode(BOARD_1)

    # Create recorder with MCTS config
    mcts_config = {
        "exploration_constant": agent.exploration_constant,
        "max_iterations": agent.max_iterations,
        "late_game_threshold": agent.late_game_threshold,
        "use_heuristic": agent.use_heuristic
    }
    recorder = GameRecorder(game, mcts_config)

    turn = 0

    while not game.is_game_over():
        actions = game.get_legal_actions()
        if not actions:
            break

        # Use MCTS to select action WITH analysis
        start = time.time()
        action, candidates = agent.select_action_with_analysis(game)
        elapsed = time.time() - start

        if verbose:
            state = game.get_game_state()
            remaining = len(state.empty_positions)
            phase = state.turn_phase.name
            print(f"Turn {turn:2d} | Phase: {phase:13s} | "
                  f"Remaining: {remaining:2d} | Time: {elapsed:.2f}s")

            if action.action_type == "place_tile":
                hand_tile = state.player_hand[action.hand_index]
                print(f"         Action: Place {hand_tile.color.name} "
                      f"{hand_tile.pattern.name} at {action.position}")
            else:
                market_tile = state.market_tiles[action.market_index]
                print(f"         Action: Take {market_tile.color.name} "
                      f"{market_tile.pattern.name} from market")

            # Show top candidates
            print(f"         Candidates ({len(candidates)}):")
            for i, (cand_action, visits, avg_score) in enumerate(candidates[:3]):
                marker = "*" if cand_action == action else " "
                if cand_action.action_type == "place_tile":
                    print(f"           {marker} {i+1}. place at {cand_action.position} "
                          f"(visits={visits}, avg={avg_score:.1f})")
                else:
                    print(f"           {marker} {i+1}. market[{cand_action.market_index}] "
                          f"(visits={visits}, avg={avg_score:.1f})")

        # Record decision BEFORE applying action
        recorder.record_decision(action, candidates)

        game.apply_action(action)
        turn += 1

    final_score = game.get_final_score()

    if verbose:
        print("\n" + "=" * 50)
        print("GAME COMPLETE")
        print("=" * 50)
        print(f"Final Score: {final_score}")
        print()
        print("Score Breakdown:")
        print(f"  Cat Scores:    {game.get_cat_scores()}")
        print(f"  Goal Scores:   {game.get_goal_scores()}")
        button_info = game.get_button_scores()
        print(f"  Button Score:  {button_info['total_score']} "
              f"({button_info['total_buttons']} buttons, "
              f"rainbow: {button_info['has_rainbow']})")

    # Finalize recording
    game_record = recorder.finalize()

    return final_score, game, game_record


def run_random_game() -> int:
    """Run a single game with random agent (baseline)."""
    game = SimulationMode(BOARD_1)
    return game.play_random_game()


def serialize_game(game: SimulationMode, score: int) -> dict:
    """
    Serialize a completed game to a dictionary for JSON export.

    Returns dict with:
    - score breakdown
    - board state (all tile positions with color/pattern)
    - cat configurations
    - goal configurations
    """
    grid = game.player.grid

    # Serialize board tiles
    board_tiles = {}
    for pos, tile in grid.grid.items():
        if tile is not None:
            pos_key = f"{pos[0]},{pos[1]},{pos[2]}"
            board_tiles[pos_key] = {
                "color": tile.color.name,
                "pattern": tile.pattern.name
            }

    # Serialize cats
    cats_info = []
    for cat in game.cats:
        cats_info.append({
            "name": cat.name,
            "point_value": cat.point_value,
            "patterns": [p.name for p in cat.patterns],
            "score": cat.score(grid)
        })

    # Serialize goals
    goals_info = []
    for goal in game.goals:
        goals_info.append({
            "name": goal.name,
            "position": list(goal.position),
            "score": goal.score(grid)
        })

    # Get button details
    button_info = game.get_button_scores()

    return {
        "total_score": score,
        "cat_scores": game.get_cat_scores(),
        "goal_scores": game.get_goal_scores(),
        "button_info": {
            "total_buttons": button_info["total_buttons"],
            "button_score": button_info["button_score"],
            "has_rainbow": button_info["has_rainbow"],
            "rainbow_score": button_info["rainbow_score"],
            "buttons_by_color": {c.name: v for c, v in button_info["buttons_by_color"].items()}
        },
        "board_tiles": board_tiles,
        "cats": cats_info,
        "goals": goals_info
    }


def save_top_boards(games: List[Tuple[int, SimulationMode]], n_top: int, output_dir: str = None):
    """
    Save the top N scoring boards to JSON files.

    Args:
        games: List of (score, game) tuples
        n_top: Number of top boards to save
        output_dir: Directory to save to (default: ../mcts_boards/)
    """
    if output_dir is None:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(os.path.dirname(current_dir), "mcts_boards")

    os.makedirs(output_dir, exist_ok=True)

    # Sort by score descending
    sorted_games = sorted(games, key=lambda x: x[0], reverse=True)
    top_games = sorted_games[:n_top]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    saved_files = []
    for i, (score, game) in enumerate(top_games):
        data = serialize_game(game, score)
        data["rank"] = i + 1
        data["timestamp"] = timestamp

        filename = f"board_{timestamp}_rank{i+1}_score{score}.json"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        saved_files.append(filepath)

    return saved_files


def save_game_record(record: GameRecord, output_dir: str = None) -> str:
    """
    Save a game record to JSON file.

    Args:
        record: GameRecord to save
        output_dir: Directory to save to (default: ../game_records/)

    Returns:
        Path to saved file
    """
    if output_dir is None:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(os.path.dirname(current_dir), "game_records")

    os.makedirs(output_dir, exist_ok=True)

    filename = f"game_{record.timestamp}_score{record.final_score}.json"
    filepath = os.path.join(output_dir, filename)

    record.save(filepath)

    return filepath


def print_board_summary(game: SimulationMode, score: int):
    """Print a visual text summary of a board."""
    grid = game.player.grid

    print(f"\n{'='*60}")
    print(f"BOARD SUMMARY (Score: {score})")
    print(f"{'='*60}")

    # Print score breakdown
    print(f"\nScore Breakdown:")
    print(f"  Cats:    {game.get_cat_scores()}")
    print(f"  Goals:   {game.get_goal_scores()}")
    button_info = game.get_button_scores()
    print(f"  Buttons: {button_info['button_score']} ({button_info['total_buttons']} buttons)")
    if button_info['has_rainbow']:
        print(f"  Rainbow: +{button_info['rainbow_score']}")

    # Print cat info
    print(f"\nCat Configurations:")
    for cat in game.cats:
        patterns = [p.name for p in cat.patterns]
        cat_score = cat.score(grid)
        print(f"  {cat.name}: {patterns} -> {cat_score} pts")

    # Print simple board visualization
    print(f"\nBoard State (Color Pattern):")
    print(grid)


def run_comparison(n_games: int, agent: MCTSAgent, save_top: int = 0, record: bool = False):
    """
    Compare MCTS vs random over multiple games.

    Args:
        n_games: Number of games to run for each agent
        agent: MCTSAgent instance to use
        save_top: Save top N boards to JSON (0 to disable)
        record: Record all games with MCTS decision analysis
    """
    print(f"Running {n_games} games each for MCTS and Random...")
    if record:
        print("(Recording enabled - this may be slower)")
    print()

    mcts_games: List[Tuple[int, SimulationMode]] = []
    game_records: List[GameRecord] = []
    random_scores = []
    mcts_times = []

    for i in range(n_games):
        print(f"Game {i+1}/{n_games}...", end=" ", flush=True)

        # MCTS game
        start = time.time()
        if record:
            mcts_score, mcts_game, game_record = run_recorded_mcts_game(agent, verbose=False)
            game_records.append(game_record)
        else:
            mcts_score, mcts_game = run_mcts_game(agent, verbose=False)
        mcts_time = time.time() - start
        mcts_times.append(mcts_time)

        # Random game
        random_score = run_random_game()

        mcts_games.append((mcts_score, mcts_game))
        random_scores.append(random_score)

        print(f"MCTS: {mcts_score:3d} ({mcts_time:.1f}s), Random: {random_score:3d}")

    mcts_scores = [score for score, _ in mcts_games]

    print()
    print("=" * 50)
    print("RESULTS")
    print("=" * 50)

    # MCTS stats
    mcts_mean = mean(mcts_scores)
    mcts_std = stdev(mcts_scores) if len(mcts_scores) > 1 else 0
    print(f"MCTS:   mean={mcts_mean:.1f}, stdev={mcts_std:.1f}, "
          f"min={min(mcts_scores)}, max={max(mcts_scores)}")

    # Random stats
    random_mean = mean(random_scores)
    random_std = stdev(random_scores) if len(random_scores) > 1 else 0
    print(f"Random: mean={random_mean:.1f}, stdev={random_std:.1f}, "
          f"min={min(random_scores)}, max={max(random_scores)}")

    # Improvement
    if random_mean > 0:
        improvement = (mcts_mean - random_mean) / random_mean * 100
        print(f"\nMCTS improvement: {improvement:+.1f}%")
    else:
        print(f"\nMCTS improvement: {mcts_mean - random_mean:+.1f} points")

    # Timing stats
    avg_time = mean(mcts_times)
    print(f"\nAverage MCTS game time: {avg_time:.1f}s")

    # Save top boards if requested
    if save_top > 0:
        print(f"\nSaving top {save_top} boards...")
        saved_files = save_top_boards(mcts_games, save_top)
        print(f"Saved to:")
        for f in saved_files:
            print(f"  {f}")

    # Save game records if recording was enabled
    if record:
        print(f"\nSaving {len(game_records)} game records...")
        for game_record in game_records:
            record_path = save_game_record(game_record)
            print(f"  {record_path}")

        # Print summaries of top boards
        sorted_games = sorted(mcts_games, key=lambda x: x[0], reverse=True)
        for i, (score, game) in enumerate(sorted_games[:save_top]):
            print_board_summary(game, score)


def main():
    parser = argparse.ArgumentParser(
        description="Run MCTS agent for Calico board game"
    )
    parser.add_argument(
        "--iterations", type=int, default=1000,
        help="MCTS iterations per move (default: 1000)"
    )
    parser.add_argument(
        "--exploration", type=float, default=1.4,
        help="Exploration constant C (default: 1.4)"
    )
    parser.add_argument(
        "--threshold", type=int, default=5,
        help="Late game threshold for full rollouts (default: 5)"
    )
    parser.add_argument(
        "--baseline", type=int, default=0,
        help="Run N games comparing MCTS vs random"
    )
    parser.add_argument(
        "--save-boards", type=int, default=0,
        help="Save top N boards to JSON files (use with --baseline)"
    )
    parser.add_argument(
        "--record", action="store_true",
        help="Record game with full MCTS decision analysis"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print detailed per-move info"
    )
    parser.add_argument(
        "--no-heuristic", action="store_true",
        help="Disable heuristic evaluation (use full rollouts only)"
    )

    args = parser.parse_args()

    agent = MCTSAgent(
        exploration_constant=args.exploration,
        max_iterations=args.iterations,
        late_game_threshold=args.threshold,
        use_heuristic=not args.no_heuristic,
        verbose=args.verbose
    )

    print(f"MCTS Agent Configuration:")
    print(f"  Iterations: {args.iterations}")
    print(f"  Exploration: {args.exploration}")
    print(f"  Late game threshold: {args.threshold}")
    print(f"  Use heuristic: {not args.no_heuristic}")
    print()

    if args.baseline > 0:
        run_comparison(args.baseline, agent, save_top=args.save_boards, record=args.record)
    else:
        print("Running single MCTS game...")
        print()
        start = time.time()

        if args.record:
            score, game, game_record = run_recorded_mcts_game(agent, verbose=True)
        else:
            score, game = run_mcts_game(agent, verbose=True)

        total_time = time.time() - start
        print(f"\nTotal game time: {total_time:.1f}s")

        # Save single game if requested
        if args.save_boards > 0:
            print(f"\nSaving board...")
            saved_files = save_top_boards([(score, game)], 1)
            print(f"Saved to: {saved_files[0]}")

        # Save recording if requested
        if args.record:
            print(f"\nSaving game record...")
            record_path = save_game_record(game_record)
            print(f"Saved to: {record_path}")
            print(f"  Decisions recorded: {len(game_record.decisions)}")


if __name__ == "__main__":
    main()
