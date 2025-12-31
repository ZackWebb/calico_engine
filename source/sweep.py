"""
Grid search over MCTS parameters: weight ratios and iteration counts.

Sweeps cat_ratio, button_ratio (relative to goals), and MCTS iterations.
With chance node sampling, iteration count significantly impacts performance.

Usage:
    python sweep.py                              # Default 3x3 ratio sweep at 5000 iterations
    python sweep.py --iter 1000,3000,5000        # Sweep iterations too (3x3x3 = 27 configs)
    python sweep.py --cat 1.0 --button 1.0 --iter 1000,2000,3000,5000  # Iteration-only sweep
    python sweep.py --analyze                    # Analyze previous sweep results
    python sweep.py --dry-run                    # Show combinations without running
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


def generate_combinations(
    cat_ratios: List[float],
    button_ratios: List[float],
    iterations_list: List[int],
) -> List[Tuple[float, float, int]]:
    """Generate all combinations of parameters."""
    return list(itertools.product(cat_ratios, button_ratios, iterations_list))


def run_sweep(
    n_games: int = 16,
    workers: int = 4,
    cat_ratios: List[float] = None,
    button_ratios: List[float] = None,
    iterations_list: List[int] = None,
    experiment_name: str = "calico-sweep",
    tag: str = None,
    record: bool = False,
) -> List[Dict[str, Any]]:
    """
    Run benchmark for each parameter combination.

    Returns list of result dicts with parameters and metrics.
    """
    if cat_ratios is None:
        cat_ratios = [0.8, 1.0, 1.2]
    if button_ratios is None:
        button_ratios = [0.8, 1.0, 1.2]
    if iterations_list is None:
        iterations_list = [5000]

    combinations = generate_combinations(cat_ratios, button_ratios, iterations_list)
    total = len(combinations)

    print("=" * 70)
    print("PARAMETER SWEEP")
    print("=" * 70)
    print(f"Parameters:")
    print(f"  cat_ratio:    {cat_ratios}")
    print(f"  button_ratio: {button_ratios}")
    print(f"  iterations:   {iterations_list}")
    print(f"Total combinations: {total}")
    print(f"Games per combination: {n_games}")
    print(f"Workers: {workers}")
    print(f"Recording games: {record}")
    print()

    # Estimate time (scale by iterations relative to 5000)
    est_time_per_game_5k = 40  # seconds at 5000 iterations
    total_game_seconds = sum(
        n_games * (iters / 5000) * est_time_per_game_5k
        for _, _, iters in combinations
    )
    est_total = total_game_seconds / workers / 60
    print(f"Estimated time: ~{est_total:.0f} minutes")
    print("=" * 70)
    print()

    mlflow.set_experiment(experiment_name)
    sweep_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    all_results = []

    for i, (cat_r, button_r, iters) in enumerate(combinations, 1):
        print(f"\n[{i}/{total}] cat={cat_r}, button={button_r}, iter={iters}")
        print("-" * 50)

        start_time = time.time()

        results, _, seeds_used = run_benchmark(
            n_games=n_games,
            iterations=iters,
            workers=workers,
            cat_ratio=cat_r,
            button_ratio=button_r,
            record=record,
        )

        elapsed = time.time() - start_time

        # Store results with parameters
        result_entry = {
            "cat_ratio": cat_r,
            "button_ratio": button_r,
            "iterations": iters,
            **results,
        }
        all_results.append(result_entry)

        # Log to MLflow
        params = {
            "n_games": n_games,
            "iterations": iters,
            "cat_ratio": cat_r,
            "button_ratio": button_r,
            "use_heuristic": True,
            "use_combined_actions": True,
        }

        tags = {
            "sweep": "params",
            "sweep_id": sweep_id,
        }
        if tag:
            tags["tag"] = tag

        run_name = f"c{cat_r}_b{button_r}_i{iters}"
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

    # Check if we have multiple iteration values
    iterations = set(r['iterations'] for r in results)
    has_iter_sweep = len(iterations) > 1

    if has_iter_sweep:
        print(f"{'Cat':>5} {'Btn':>5} {'Iter':>6} | {'Mean':>6} {'Std':>5} | {'Cats':>5} {'Goals':>5} {'Btns':>5}")
        print("-" * 65)
    else:
        print(f"{'Cat':>6} {'Btn':>6} | {'Mean':>6} {'Std':>5} | {'Cats':>5} {'Goals':>5} {'Btns':>5}")
        print("-" * 60)

    # Sort by mean score descending
    sorted_results = sorted(results, key=lambda x: x['mcts_mean'], reverse=True)

    for r in sorted_results:
        if has_iter_sweep:
            print(f"{r['cat_ratio']:5.2f} {r['button_ratio']:5.2f} {r['iterations']:6d} | "
                  f"{r['mcts_mean']:6.1f} {r['mcts_std']:5.1f} | "
                  f"{r['cat_score_mean']:5.1f} {r['goal_score_mean']:5.1f} {r['button_score_mean']:5.1f}")
        else:
            print(f"{r['cat_ratio']:6.2f} {r['button_ratio']:6.2f} | "
                  f"{r['mcts_mean']:6.1f} {r['mcts_std']:5.1f} | "
                  f"{r['cat_score_mean']:5.1f} {r['goal_score_mean']:5.1f} {r['button_score_mean']:5.1f}")

    print()
    print("Best configuration:")
    best = sorted_results[0]
    print(f"  cat_ratio={best['cat_ratio']}, button_ratio={best['button_ratio']}, iterations={best['iterations']}")
    print(f"  Mean score: {best['mcts_mean']:.1f} (std={best['mcts_std']:.1f})")

    # If sweeping iterations, show iteration impact
    if has_iter_sweep:
        print()
        print("Iteration impact (averaged across weight configs):")
        for iters in sorted(iterations):
            iter_results = [r for r in results if r['iterations'] == iters]
            avg_score = sum(r['mcts_mean'] for r in iter_results) / len(iter_results)
            print(f"  {iters:5d} iterations: mean={avg_score:.1f}")


def analyze_previous_sweeps(experiment_name: str = "calico-sweep") -> None:
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
            filter_string="tags.sweep = 'params'",
            order_by=["metrics.mcts_mean DESC"],
        )

        if not runs:
            print("No sweep runs found.")
            return

        print(f"Found {len(runs)} sweep runs")
        print()
        print(f"{'Cat':>5} {'Btn':>5} {'Iter':>6} | {'Mean':>6} {'Std':>5} | {'Cats':>5} {'Goals':>5} {'Btns':>5} | Sweep ID")
        print("-" * 85)

        for run in runs[:30]:  # Show top 30
            p = run.data.params
            m = run.data.metrics
            t = run.data.tags

            cat_r = float(p.get('cat_ratio', 1.0))
            button_r = float(p.get('button_ratio', 1.0))
            iters = int(p.get('iterations', 5000))

            print(f"{cat_r:5.2f} {button_r:5.2f} {iters:6d} | "
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
        print(f"  cat_ratio={p.get('cat_ratio')}, button_ratio={p.get('button_ratio')}, iterations={p.get('iterations')}")
        print(f"  Mean score: {m.get('mcts_mean', 0):.1f}")

    except Exception as e:
        print(f"Error querying MLflow: {e}")


def main():
    parser = argparse.ArgumentParser(description="Grid search over MCTS parameters")

    # Benchmark settings
    parser.add_argument("-n", "--n-games", type=int, default=16,
                       help="Games per configuration (default: 16)")
    parser.add_argument("-w", "--workers", type=int, default=4,
                       help="Parallel workers (default: 4)")

    # Parameter ranges
    parser.add_argument("--cat", type=str, default="0.8,1.0,1.2",
                       help="Cat ratio values (comma-separated, default: 0.8,1.0,1.2)")
    parser.add_argument("--button", type=str, default="0.8,1.0,1.2",
                       help="Button ratio values (comma-separated, default: 0.8,1.0,1.2)")
    parser.add_argument("--iter", type=str, default="5000",
                       help="MCTS iteration values (comma-separated, default: 5000)")

    # Options
    parser.add_argument("--experiment", type=str, default="calico-sweep",
                       help="MLflow experiment name")
    parser.add_argument("--tag", type=str, default=None,
                       help="Tag for this sweep")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show combinations without running")
    parser.add_argument("--analyze", action="store_true",
                       help="Analyze previous sweep results from MLflow")
    parser.add_argument("--record", action="store_true",
                       help="Save game records to game_records/ (slower)")

    args = parser.parse_args()

    if args.analyze:
        analyze_previous_sweeps(args.experiment)
        return

    # Parse parameter values
    cat_ratios = [float(x.strip()) for x in args.cat.split(",")]
    button_ratios = [float(x.strip()) for x in args.button.split(",")]
    iterations_list = [int(x.strip()) for x in args.iter.split(",")]

    combinations = generate_combinations(cat_ratios, button_ratios, iterations_list)

    if args.dry_run:
        print("Parameter combinations to test:")
        print()
        for i, (c, b, iters) in enumerate(combinations, 1):
            print(f"  {i:2d}. cat={c}, button={b}, iter={iters}")
        print()
        print(f"Total: {len(combinations)} combinations")
        print(f"Games per combination: {args.n_games}")
        print(f"Total games: {len(combinations) * args.n_games}")
        return

    # Run the sweep
    start_time = time.time()

    results = run_sweep(
        n_games=args.n_games,
        workers=args.workers,
        cat_ratios=cat_ratios,
        button_ratios=button_ratios,
        iterations_list=iterations_list,
        experiment_name=args.experiment,
        tag=args.tag,
        record=args.record,
    )

    total_time = time.time() - start_time

    print_summary(results)

    print()
    print(f"Total sweep time: {total_time / 60:.1f} minutes")
    print(f"\nView detailed results: mlflow ui")


if __name__ == "__main__":
    main()
