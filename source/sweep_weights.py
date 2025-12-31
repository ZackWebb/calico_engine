"""
Grid search over heuristic weight combinations.

Runs full 16-game benchmarks for each weight combination and logs to MLflow.
Results can be analyzed afterward using MLflow UI or the --analyze flag.

Usage:
    python sweep_weights.py                    # Run full grid search
    python sweep_weights.py --analyze          # Analyze previous sweep results
    python sweep_weights.py --dry-run          # Show combinations without running
    python sweep_weights.py -n 8 -i 1000       # Fewer games/iterations for testing
"""
import argparse
import itertools
import time
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Dict, Any

import mlflow

from benchmark import run_benchmark, log_to_mlflow, get_git_info

# Configure MLflow
PROJECT_ROOT = Path(__file__).parent.parent
MLFLOW_DB_PATH = PROJECT_ROOT / "mlflow.db"
mlflow.set_tracking_uri(f"sqlite:///{MLFLOW_DB_PATH.as_posix()}")


def generate_weight_combinations(
    cat_values: List[float],
    goal_values: List[float],
    button_values: List[float],
) -> List[Tuple[float, float, float]]:
    """Generate all combinations of weight values."""
    return list(itertools.product(cat_values, goal_values, button_values))


def run_sweep(
    n_games: int = 16,
    iterations: int = 5000,
    workers: int = 4,
    cat_values: List[float] = None,
    goal_values: List[float] = None,
    button_values: List[float] = None,
    experiment_name: str = "calico-weight-sweep",
    tag: str = None,
) -> List[Dict[str, Any]]:
    """
    Run benchmark for each weight combination.

    Returns list of result dicts with weights and metrics.
    """
    if cat_values is None:
        cat_values = [0.8, 1.0, 1.2]
    if goal_values is None:
        goal_values = [0.8, 1.0, 1.2]
    if button_values is None:
        button_values = [0.8, 1.0, 1.2]

    combinations = generate_weight_combinations(cat_values, goal_values, button_values)
    total = len(combinations)

    print("=" * 70)
    print("WEIGHT SWEEP")
    print("=" * 70)
    print(f"Weight values:")
    print(f"  cat:    {cat_values}")
    print(f"  goal:   {goal_values}")
    print(f"  button: {button_values}")
    print(f"Total combinations: {total}")
    print(f"Games per combination: {n_games}")
    print(f"MCTS iterations: {iterations}")
    print(f"Workers: {workers}")
    print()

    # Estimate time
    est_time_per_game = 40  # seconds at 5000 iterations
    est_total = total * n_games * est_time_per_game / workers / 60
    print(f"Estimated time: ~{est_total:.0f} minutes")
    print("=" * 70)
    print()

    mlflow.set_experiment(experiment_name)
    sweep_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    all_results = []

    for i, (cat_w, goal_w, button_w) in enumerate(combinations, 1):
        print(f"\n[{i}/{total}] cat={cat_w}, goal={goal_w}, button={button_w}")
        print("-" * 50)

        start_time = time.time()

        results, _, seeds_used = run_benchmark(
            n_games=n_games,
            iterations=iterations,
            workers=workers,
            cat_weight=cat_w,
            goal_weight=goal_w,
            button_weight=button_w,
            record=False,  # Skip recording for speed
        )

        elapsed = time.time() - start_time

        # Store results with weights
        result_entry = {
            "cat_weight": cat_w,
            "goal_weight": goal_w,
            "button_weight": button_w,
            **results,
        }
        all_results.append(result_entry)

        # Log to MLflow
        params = {
            "n_games": n_games,
            "iterations": iterations,
            "cat_weight": cat_w,
            "goal_weight": goal_w,
            "button_weight": button_w,
            "use_heuristic": True,
            "use_combined_actions": True,
        }

        tags = {
            "sweep": "weights",
            "sweep_id": sweep_id,
        }
        if tag:
            tags["tag"] = tag

        run_name = f"w_c{cat_w}_g{goal_w}_b{button_w}"
        log_to_mlflow(results, params, tags, run_name=run_name, seeds_used=seeds_used)

        print(f"\nResult: mean={results['mcts_mean']:.1f}, std={results['mcts_std']:.1f}")
        print(f"  cats={results['cat_score_mean']:.1f}, goals={results['goal_score_mean']:.1f}, buttons={results['button_score_mean']:.1f}")
        print(f"  Time: {elapsed:.1f}s")

    return all_results


def print_summary(results: List[Dict[str, Any]]) -> None:
    """Print summary table sorted by mean score."""
    print("\n")
    print("=" * 70)
    print("SWEEP RESULTS - Sorted by Mean Score")
    print("=" * 70)
    print()
    print(f"{'Cat':>5} {'Goal':>5} {'Btn':>5} | {'Mean':>6} {'Std':>5} | {'Cats':>5} {'Goals':>5} {'Btns':>5}")
    print("-" * 70)

    # Sort by mean score descending
    sorted_results = sorted(results, key=lambda x: x['mcts_mean'], reverse=True)

    for r in sorted_results:
        print(f"{r['cat_weight']:5.1f} {r['goal_weight']:5.1f} {r['button_weight']:5.1f} | "
              f"{r['mcts_mean']:6.1f} {r['mcts_std']:5.1f} | "
              f"{r['cat_score_mean']:5.1f} {r['goal_score_mean']:5.1f} {r['button_score_mean']:5.1f}")

    print()
    print("Best configuration:")
    best = sorted_results[0]
    print(f"  cat_weight={best['cat_weight']}, goal_weight={best['goal_weight']}, button_weight={best['button_weight']}")
    print(f"  Mean score: {best['mcts_mean']:.1f} (std={best['mcts_std']:.1f})")


def analyze_previous_sweeps(experiment_name: str = "calico-weight-sweep") -> None:
    """Query MLflow for previous sweep results and display summary."""
    print("Analyzing previous sweep results from MLflow...")
    print()

    client = mlflow.tracking.MlflowClient()

    try:
        experiment = client.get_experiment_by_name(experiment_name)
        if experiment is None:
            print(f"No experiment found with name '{experiment_name}'")
            return

        runs = client.search_runs(
            experiment_ids=[experiment.experiment_id],
            filter_string="tags.sweep = 'weights'",
            order_by=["metrics.mcts_mean DESC"],
        )

        if not runs:
            print("No weight sweep runs found.")
            return

        print(f"Found {len(runs)} weight sweep runs")
        print()
        print(f"{'Cat':>5} {'Goal':>5} {'Btn':>5} | {'Mean':>6} {'Std':>5} | {'Cats':>5} {'Goals':>5} {'Btns':>5} | Sweep ID")
        print("-" * 90)

        for run in runs[:30]:  # Show top 30
            p = run.data.params
            m = run.data.metrics
            t = run.data.tags

            cat_w = float(p.get('cat_weight', 1.0))
            goal_w = float(p.get('goal_weight', 1.0))
            button_w = float(p.get('button_weight', 1.0))

            print(f"{cat_w:5.1f} {goal_w:5.1f} {button_w:5.1f} | "
                  f"{m.get('mcts_mean', 0):6.1f} {m.get('mcts_std', 0):5.1f} | "
                  f"{m.get('cat_score_mean', 0):5.1f} {m.get('goal_score_mean', 0):5.1f} {m.get('button_score_mean', 0):5.1f} | "
                  f"{t.get('sweep_id', 'N/A')[:15]}")

        if len(runs) > 30:
            print(f"... and {len(runs) - 30} more")

        # Best result
        print()
        best = runs[0]
        p = best.data.params
        m = best.data.metrics
        print("Best configuration overall:")
        print(f"  cat_weight={p.get('cat_weight')}, goal_weight={p.get('goal_weight')}, button_weight={p.get('button_weight')}")
        print(f"  Mean score: {m.get('mcts_mean', 0):.1f}")

    except Exception as e:
        print(f"Error querying MLflow: {e}")


def main():
    parser = argparse.ArgumentParser(description="Grid search over heuristic weights")

    # Benchmark settings
    parser.add_argument("-n", "--n-games", type=int, default=16,
                       help="Games per weight combination (default: 16)")
    parser.add_argument("-i", "--iterations", type=int, default=5000,
                       help="MCTS iterations per move (default: 5000)")
    parser.add_argument("-w", "--workers", type=int, default=4,
                       help="Parallel workers (default: 4)")

    # Weight ranges
    parser.add_argument("--cat", type=str, default="0.8,1.0,1.2",
                       help="Cat weight values (comma-separated, default: 0.8,1.0,1.2)")
    parser.add_argument("--goal", type=str, default="0.8,1.0,1.2",
                       help="Goal weight values (comma-separated, default: 0.8,1.0,1.2)")
    parser.add_argument("--button", type=str, default="0.8,1.0,1.2",
                       help="Button weight values (comma-separated, default: 0.8,1.0,1.2)")

    # Options
    parser.add_argument("--experiment", type=str, default="calico-weight-sweep",
                       help="MLflow experiment name")
    parser.add_argument("--tag", type=str, default=None,
                       help="Tag for this sweep")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show combinations without running")
    parser.add_argument("--analyze", action="store_true",
                       help="Analyze previous sweep results from MLflow")

    args = parser.parse_args()

    if args.analyze:
        analyze_previous_sweeps(args.experiment)
        return

    # Parse weight values
    cat_values = [float(x.strip()) for x in args.cat.split(",")]
    goal_values = [float(x.strip()) for x in args.goal.split(",")]
    button_values = [float(x.strip()) for x in args.button.split(",")]

    combinations = generate_weight_combinations(cat_values, goal_values, button_values)

    if args.dry_run:
        print("Weight combinations to test:")
        print()
        for i, (c, g, b) in enumerate(combinations, 1):
            print(f"  {i:2d}. cat={c}, goal={g}, button={b}")
        print()
        print(f"Total: {len(combinations)} combinations")
        print(f"Games per combination: {args.n_games}")
        print(f"Total games: {len(combinations) * args.n_games}")
        return

    # Run the sweep
    start_time = time.time()

    results = run_sweep(
        n_games=args.n_games,
        iterations=args.iterations,
        workers=args.workers,
        cat_values=cat_values,
        goal_values=goal_values,
        button_values=button_values,
        experiment_name=args.experiment,
        tag=args.tag,
    )

    total_time = time.time() - start_time

    print_summary(results)

    print()
    print(f"Total sweep time: {total_time / 60:.1f} minutes")
    print(f"\nView detailed results: mlflow ui")


if __name__ == "__main__":
    main()
