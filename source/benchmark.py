"""
Benchmark runner with MLflow tracking for Calico MCTS experiments.

Usage:
    python benchmark.py                          # Run default benchmark (16 games, 4 workers)
    python benchmark.py -n 20 -i 1000           # 20 games, 1000 iterations
    python benchmark.py --workers 8             # Use 8 parallel workers
    python benchmark.py --tag "improved_heuristic"  # Add a tag for this run
    python benchmark.py --sweep                  # Run parameter sweep
    python benchmark.py --seeds 0-9             # Use fixed seeds for reproducibility

MLflow UI:
    mlflow ui --backend-store-uri sqlite:///mlflow.db  # Start UI at http://localhost:5000
"""
import argparse
import random
import time
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from statistics import mean, stdev
from typing import Dict, Any, List, Tuple, Optional

import mlflow

# Configure MLflow to use SQLite database in project root
PROJECT_ROOT = Path(__file__).parent.parent
MLFLOW_DB_PATH = PROJECT_ROOT / "mlflow.db"
mlflow.set_tracking_uri(f"sqlite:///{MLFLOW_DB_PATH.as_posix()}")

from simulation_mode import SimulationMode
from board_configurations import BOARD_1
from mcts_agent import MCTSAgent
from game_record import GameRecorder, GameRecord
from run_mcts import save_game_record
from heuristic import HeuristicConfig


def get_git_info() -> Dict[str, str]:
    """Get current git commit hash and branch."""
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL
        ).decode().strip()[:8]

        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL
        ).decode().strip()

        # Check for uncommitted changes
        status = subprocess.check_output(
            ["git", "status", "--porcelain"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        dirty = " (dirty)" if status else ""

        return {"git_commit": commit + dirty, "git_branch": branch}
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {"git_commit": "unknown", "git_branch": "unknown"}


def parse_seeds(seeds_str: str) -> List[int]:
    """
    Parse seeds argument string into list of seed integers.

    Formats supported:
        "0-9"      -> [0, 1, 2, ..., 9]
        "0,5,10"   -> [0, 5, 10]
        "fixed"    -> [0, 1, 2, ..., n_games-1] (handled in run_benchmark)
    """
    if seeds_str == "fixed":
        return None  # Signal to use range(n_games)

    if "-" in seeds_str and "," not in seeds_str:
        # Range format: "0-9"
        start, end = seeds_str.split("-")
        return list(range(int(start), int(end) + 1))
    elif "," in seeds_str:
        # List format: "0,5,10"
        return [int(s.strip()) for s in seeds_str.split(",")]
    else:
        # Single seed
        return [int(seeds_str)]


def run_single_game(
    agent: MCTSAgent,
    verbose: bool = False,
    record: bool = False,
    seed: Optional[int] = None
) -> Tuple[int, float, Dict, GameRecord | None]:
    """Run a single MCTS game and return score, time, breakdown, and optional game record."""
    # Seed random before game creation for reproducible tile bag shuffle
    if seed is not None:
        random.seed(seed)

    game = SimulationMode(BOARD_1)

    # Create recorder with MCTS config if recording
    recorder = None
    if record:
        mcts_config = {
            "exploration_constant": agent.exploration_constant,
            "max_iterations": agent.max_iterations,
            "late_game_threshold": agent.late_game_threshold,
            "use_heuristic": agent.use_heuristic,
            "use_combined_actions": agent.use_combined_actions
        }
        recorder = GameRecorder(game, mcts_config)

    start_time = time.time()
    while not game.is_game_over():
        action, candidates = agent.select_action_with_analysis(game) if record else (agent.select_action(game), None)
        if recorder:
            recorder.record_decision(action, candidates)
        game.apply_action(action)
    elapsed = time.time() - start_time

    score = game.get_final_score()

    # Build score breakdown
    breakdown = {
        "cats": game.get_cat_scores(),
        "goals": game.get_goal_scores(),
        "buttons": game.get_button_scores(),
    }

    if verbose:
        print(f"  Score: {score} ({elapsed:.1f}s)")

    game_record = recorder.finalize() if recorder else None
    return score, elapsed, breakdown, game_record


def run_random_game(seed: Optional[int] = None) -> int:
    """Run a single random game."""
    if seed is not None:
        random.seed(seed)
    game = SimulationMode(BOARD_1)
    return game.play_random_game()


def _run_game_worker(args: Tuple) -> Dict[str, Any]:
    """
    Worker function for parallel game execution.
    Creates its own agent instance since agents can't be pickled across processes.

    Args is a tuple of (seed, agent_config, record, heuristic_config_dict)
    Returns dict with game results.
    """
    seed, agent_config, record, heuristic_config_dict = args

    # Recreate HeuristicConfig in this process (config is passed as dict for pickling)
    heuristic_config = None
    if heuristic_config_dict:
        heuristic_config = HeuristicConfig(**heuristic_config_dict)

    # Create agent in this process
    agent = MCTSAgent(
        exploration_constant=agent_config["exploration_constant"],
        max_iterations=agent_config["max_iterations"],
        late_game_threshold=agent_config["late_game_threshold"],
        use_heuristic=agent_config["use_heuristic"],
        use_deterministic_rollout=agent_config["use_deterministic_rollout"],
        use_combined_actions=agent_config["use_combined_actions"],
        heuristic_config=heuristic_config,
        verbose=False
    )

    # Run MCTS game
    score, elapsed, breakdown, game_record = run_single_game(
        agent, verbose=False, record=record, seed=seed
    )

    # Run random game with same seed
    random_score = run_random_game(seed=seed)

    # Extract breakdown totals
    cats_total = sum(breakdown.get('cats', {}).values())
    goals_total = sum(breakdown.get('goals', {}).values())
    buttons_info = breakdown.get('buttons', {})
    buttons_total = buttons_info.get('button_score', 0) + buttons_info.get('rainbow_score', 0)

    return {
        "seed": seed,
        "mcts_score": score,
        "elapsed": elapsed,
        "random_score": random_score,
        "cats_total": cats_total,
        "goals_total": goals_total,
        "buttons_total": buttons_total,
        "game_record": game_record,
    }


def run_benchmark(
    n_games: int = 16,
    iterations: int = 5000,
    exploration: float = 1.4,
    late_game_threshold: int = 5,
    use_heuristic: bool = True,
    use_deterministic_rollout: bool = False,
    use_combined_actions: bool = True,
    verbose: bool = False,
    record: bool = True,
    tags: Dict[str, str] = None,
    seeds: Optional[List[int]] = None,
    workers: int = 4,
    cat_ratio: float = 1.0,
    button_ratio: float = 1.0,
) -> Tuple[Dict[str, Any], List[str], Optional[List[int]]]:
    """
    Run benchmark and log to MLflow.

    Args:
        seeds: Optional list of seeds for reproducibility. If provided, must have
               length >= n_games. Each game uses the corresponding seed.
        workers: Number of parallel workers (default 4). Set to 1 for sequential.
        cat_ratio: Ratio of cat weight to goal weight (default 1.0)
        button_ratio: Ratio of button weight to goal weight (default 1.0)

    Returns (results dict, list of game record filenames, seeds used).
    """
    # Agent config (passed to workers, not the agent itself)
    agent_config = {
        "exploration_constant": exploration,
        "max_iterations": iterations,
        "late_game_threshold": late_game_threshold,
        "use_heuristic": use_heuristic,
        "use_deterministic_rollout": use_deterministic_rollout,
        "use_combined_actions": use_combined_actions,
    }

    # Heuristic config (passed as dict for pickling across processes)
    # Uses ratio-based weights (goal weight is implicitly 1.0)
    heuristic_config_dict = {
        "cat_ratio": cat_ratio,
        "button_ratio": button_ratio,
    }

    # Resolve seeds - default to 0-(n_games-1) if not specified
    if seeds is not None:
        if len(seeds) < n_games:
            raise ValueError(f"Not enough seeds ({len(seeds)}) for {n_games} games")
        seeds_used = seeds[:n_games]
    else:
        # Default to fixed seeds for reproducibility
        seeds_used = list(range(n_games))

    # Collect results
    mcts_scores = []
    mcts_times = []
    random_scores = []
    game_record_files = []

    # Score breakdown accumulators
    cat_scores = []
    goal_scores = []
    button_scores = []

    print(f"Running {n_games} games with {workers} workers...")
    print(f"  Iterations: {iterations}")
    print(f"  Exploration: {exploration}")
    print(f"  Heuristic: {use_heuristic}")
    print(f"  Combined actions: {use_combined_actions}")
    print(f"  Recording: {record}")
    # Show seeds info - check if they're sequential (fixed) or random
    if seeds is not None:
        print(f"  Seeds: {seeds_used[0]}-{seeds_used[-1]} (fixed)")
    else:
        print(f"  Seeds: random")
    if cat_ratio != 1.0 or button_ratio != 1.0:
        print(f"  Ratios: cat={cat_ratio}, button={button_ratio} (goal=1.0)")
    print()

    # Prepare work items
    work_items = [(seed, agent_config, record, heuristic_config_dict) for seed in seeds_used]

    if workers == 1:
        # Sequential execution (useful for debugging)
        results_list = []
        for i, item in enumerate(work_items):
            print(f"Game {i+1}/{n_games} (seed={item[0]})...", end=" ", flush=True)
            result = _run_game_worker(item)
            results_list.append(result)
            print(f"MCTS: {result['mcts_score']:3d} ({result['elapsed']:.1f}s), Random: {result['random_score']:3d}")
    else:
        # Parallel execution
        results_list = []
        completed = 0
        with ProcessPoolExecutor(max_workers=workers) as executor:
            # Submit all jobs
            future_to_seed = {executor.submit(_run_game_worker, item): item[0] for item in work_items}

            # Collect results as they complete
            for future in as_completed(future_to_seed):
                seed = future_to_seed[future]
                result = future.result()
                results_list.append(result)
                completed += 1
                print(f"[{completed}/{n_games}] Seed {seed}: MCTS={result['mcts_score']:3d} ({result['elapsed']:.1f}s), Random={result['random_score']:3d}")

        # Sort by seed for consistent ordering
        results_list.sort(key=lambda x: x['seed'])

    # Process results
    for result in results_list:
        mcts_scores.append(result['mcts_score'])
        mcts_times.append(result['elapsed'])
        random_scores.append(result['random_score'])
        cat_scores.append(result['cats_total'])
        goal_scores.append(result['goals_total'])
        button_scores.append(result['buttons_total'])

        # Save game record if present
        if result['game_record']:
            record_path = save_game_record(result['game_record'])
            game_record_files.append(Path(record_path).name)

    # Calculate statistics
    results = {
        # MCTS stats
        "mcts_mean": mean(mcts_scores),
        "mcts_std": stdev(mcts_scores) if len(mcts_scores) > 1 else 0,
        "mcts_min": min(mcts_scores),
        "mcts_max": max(mcts_scores),
        "mcts_time_mean": mean(mcts_times),

        # Random baseline
        "random_mean": mean(random_scores),
        "random_std": stdev(random_scores) if len(random_scores) > 1 else 0,

        # Improvement
        "improvement_pct": ((mean(mcts_scores) - mean(random_scores)) / mean(random_scores) * 100)
                          if mean(random_scores) > 0 else 0,

        # Score breakdown
        "cat_score_mean": mean(cat_scores),
        "goal_score_mean": mean(goal_scores),
        "button_score_mean": mean(button_scores),
    }

    return results, game_record_files, seeds_used


def log_to_mlflow(
    results: Dict[str, Any],
    params: Dict[str, Any],
    tags: Dict[str, str] = None,
    run_name: str = None,
    game_record_files: List[str] = None,
    seeds_used: Optional[List[int]] = None
):
    """Log benchmark results to MLflow."""
    with mlflow.start_run(run_name=run_name):
        # Log parameters
        mlflow.log_params(params)

        # Log git info
        git_info = get_git_info()
        mlflow.log_params(git_info)

        # Log metrics
        mlflow.log_metrics(results)

        # Log tags
        if tags:
            mlflow.set_tags(tags)

        # Log timestamp
        mlflow.set_tag("timestamp", datetime.now().isoformat())

        # Log seeds for reproducibility
        if seeds_used:
            mlflow.set_tag("seeds", f"{seeds_used[0]}-{seeds_used[-1]}")
            mlflow.log_param("seed_start", seeds_used[0])
            mlflow.log_param("seed_end", seeds_used[-1])

        # Log game record filenames
        if game_record_files:
            mlflow.set_tag("game_records", ",".join(game_record_files))
            mlflow.log_param("n_game_records", len(game_record_files))

        print(f"\nMLflow run logged: {mlflow.active_run().info.run_id}")


def main():
    parser = argparse.ArgumentParser(description="Benchmark MCTS with MLflow tracking")

    # Benchmark parameters
    parser.add_argument("-n", "--n-games", type=int, default=16,
                       help="Number of games to run (default: 16)")
    parser.add_argument("-i", "--iterations", type=int, default=5000,
                       help="MCTS iterations per move (default: 5000)")
    parser.add_argument("-e", "--exploration", type=float, default=1.4,
                       help="UCB1 exploration constant (default: 1.4)")
    parser.add_argument("-t", "--threshold", type=int, default=5,
                       help="Late game threshold (default: 5)")

    # Flags
    parser.add_argument("--no-heuristic", action="store_true",
                       help="Disable heuristic evaluation")
    parser.add_argument("--deterministic", action="store_true",
                       help="Use deterministic rollouts")
    parser.add_argument("--separate", action="store_true",
                       help="Use separate actions instead of combined")

    # MLflow options
    parser.add_argument("--tag", type=str, default=None,
                       help="Tag for this experiment run")
    parser.add_argument("--experiment", type=str, default="calico-mcts",
                       help="MLflow experiment name (default: calico-mcts)")
    parser.add_argument("--run-name", type=str, default=None,
                       help="Name for this MLflow run")

    # Parallelization
    parser.add_argument("-w", "--workers", type=int, default=4,
                       help="Number of parallel workers (default: 4, use 1 for sequential)")

    # Heuristic weight ratios (relative to goals, which has implicit weight 1.0)
    parser.add_argument("--cat-ratio", type=float, default=1.0,
                       help="Cat weight ratio relative to goals (default: 1.0)")
    parser.add_argument("--button-ratio", type=float, default=1.0,
                       help="Button weight ratio relative to goals (default: 1.0)")

    # Special modes
    parser.add_argument("--sweep", action="store_true",
                       help="Run parameter sweep across iterations")
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="Verbose output")
    parser.add_argument("--no-mlflow", action="store_true",
                       help="Skip MLflow logging (just print results)")
    parser.add_argument("--no-record", action="store_true",
                       help="Disable game recording (default: recording enabled)")
    parser.add_argument("--seeds", type=str, default=None,
                       help="Seeds for reproducibility: '0-9', '0,5,10', or 'fixed' (default: random)")

    args = parser.parse_args()

    # Parse seeds
    seeds = None
    if args.seeds:
        if args.seeds == "fixed":
            seeds = list(range(args.n_games))
        else:
            seeds = parse_seeds(args.seeds)

    # Set up MLflow
    if not args.no_mlflow:
        mlflow.set_experiment(args.experiment)

    if args.sweep:
        # Parameter sweep mode
        iteration_values = [100, 250, 500, 1000, 2000]
        print("=" * 60)
        print("PARAMETER SWEEP")
        print("=" * 60)

        for iters in iteration_values:
            print(f"\n--- Iterations: {iters} ---")

            params = {
                "n_games": args.n_games,
                "iterations": iters,
                "exploration": args.exploration,
                "late_game_threshold": args.threshold,
                "use_heuristic": not args.no_heuristic,
                "use_deterministic_rollout": args.deterministic,
                "use_combined_actions": not args.separate,
                "cat_ratio": args.cat_ratio,
                "button_ratio": args.button_ratio,
            }

            results, game_record_files, seeds_used = run_benchmark(
                n_games=args.n_games,
                iterations=iters,
                exploration=args.exploration,
                late_game_threshold=args.threshold,
                use_heuristic=not args.no_heuristic,
                use_deterministic_rollout=args.deterministic,
                use_combined_actions=not args.separate,
                verbose=args.verbose,
                record=not args.no_record,
                seeds=seeds,
                workers=args.workers,
                cat_ratio=args.cat_ratio,
                button_ratio=args.button_ratio,
            )

            print(f"\nResults: mean={results['mcts_mean']:.1f}, "
                  f"std={results['mcts_std']:.1f}, "
                  f"improvement={results['improvement_pct']:.1f}%")

            if not args.no_mlflow:
                tags = {"sweep": "iterations", "tag": args.tag} if args.tag else {"sweep": "iterations"}
                log_to_mlflow(results, params, tags, run_name=f"sweep_iter_{iters}",
                             game_record_files=game_record_files, seeds_used=seeds_used)
    else:
        # Single run mode
        params = {
            "n_games": args.n_games,
            "iterations": args.iterations,
            "exploration": args.exploration,
            "late_game_threshold": args.threshold,
            "use_heuristic": not args.no_heuristic,
            "use_deterministic_rollout": args.deterministic,
            "use_combined_actions": not args.separate,
            "cat_ratio": args.cat_ratio,
            "button_ratio": args.button_ratio,
        }

        results, game_record_files, seeds_used = run_benchmark(
            n_games=args.n_games,
            iterations=args.iterations,
            exploration=args.exploration,
            late_game_threshold=args.threshold,
            use_heuristic=not args.no_heuristic,
            use_deterministic_rollout=args.deterministic,
            use_combined_actions=not args.separate,
            verbose=args.verbose,
            record=not args.no_record,
            seeds=seeds,
            workers=args.workers,
            cat_ratio=args.cat_ratio,
            button_ratio=args.button_ratio,
        )

        # Print summary
        print()
        print("=" * 50)
        print("RESULTS")
        print("=" * 50)
        print(f"MCTS:   mean={results['mcts_mean']:.1f}, "
              f"std={results['mcts_std']:.1f}, "
              f"min={results['mcts_min']}, max={results['mcts_max']}")
        print(f"Random: mean={results['random_mean']:.1f}, "
              f"std={results['random_std']:.1f}")
        print(f"Improvement: {results['improvement_pct']:.1f}%")
        print()
        print(f"Score breakdown (MCTS average):")
        print(f"  Cats:    {results['cat_score_mean']:.1f}")
        print(f"  Goals:   {results['goal_score_mean']:.1f}")
        print(f"  Buttons: {results['button_score_mean']:.1f}")
        print()
        print(f"Avg time per game: {results['mcts_time_mean']:.1f}s")

        if game_record_files:
            print(f"\nGame records saved: {len(game_record_files)} files in game_records/")

        if not args.no_mlflow:
            tags = {"tag": args.tag} if args.tag else None
            log_to_mlflow(results, params, tags, run_name=args.run_name,
                         game_record_files=game_record_files, seeds_used=seeds_used)
            print("\nView results: mlflow ui")


if __name__ == "__main__":
    main()
