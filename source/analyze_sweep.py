"""
Statistical analysis of weight ratio sweep results.

Analyzes whether ratio differences are statistically significant
and identifies general trends vs noise.

Usage:
    python analyze_sweep.py              # Analyze from MLflow
    python analyze_sweep.py --help       # Show options
"""
import argparse
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict
import statistics

import mlflow

# Configure MLflow
PROJECT_ROOT = Path(__file__).parent.parent
MLFLOW_DB_PATH = PROJECT_ROOT / "mlflow.db"
mlflow.set_tracking_uri(f"sqlite:///{MLFLOW_DB_PATH.as_posix()}")


def load_sweep_data(experiment_name: str = "calico-ratio-sweep") -> List[Dict[str, Any]]:
    """Load all ratio sweep runs from MLflow."""
    client = mlflow.tracking.MlflowClient()

    experiment = client.get_experiment_by_name(experiment_name)
    if experiment is None:
        print(f"No experiment found: {experiment_name}")
        return []

    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        filter_string="tags.sweep = 'ratios'",
    )

    results = []
    for run in runs:
        p = run.data.params
        m = run.data.metrics

        results.append({
            "cat_ratio": float(p.get('cat_ratio', 1.0)),
            "button_ratio": float(p.get('button_ratio', 1.0)),
            "mcts_mean": m.get('mcts_mean', 0),
            "mcts_std": m.get('mcts_std', 0),
            "cat_score_mean": m.get('cat_score_mean', 0),
            "goal_score_mean": m.get('goal_score_mean', 0),
            "button_score_mean": m.get('button_score_mean', 0),
            "n_games": int(p.get('n_games', 16)),
        })

    return results


def compute_standard_error(std: float, n: int) -> float:
    """Compute standard error of the mean."""
    return std / (n ** 0.5)


def compute_confidence_interval(mean: float, std: float, n: int, confidence: float = 0.95) -> tuple:
    """
    Compute confidence interval for the mean.
    Uses t-distribution approximation (z=1.96 for 95% CI with large n).
    """
    # For 95% CI with n=16, t-value is ~2.13, but z=1.96 is close enough
    z = 1.96 if confidence == 0.95 else 2.58  # 99%
    se = compute_standard_error(std, n)
    margin = z * se
    return (mean - margin, mean + margin)


def analyze_by_ratio(results: List[Dict], ratio_name: str) -> Dict[float, Dict]:
    """Group results by a single ratio and compute aggregate statistics."""
    grouped = defaultdict(list)

    for r in results:
        key = r[f"{ratio_name}_ratio"]
        grouped[key].append(r)

    analysis = {}
    for ratio_val, runs in sorted(grouped.items()):
        means = [r['mcts_mean'] for r in runs]
        cat_means = [r['cat_score_mean'] for r in runs]
        goal_means = [r['goal_score_mean'] for r in runs]
        button_means = [r['button_score_mean'] for r in runs]

        analysis[ratio_val] = {
            "n_configs": len(runs),
            "mean_of_means": statistics.mean(means),
            "std_of_means": statistics.stdev(means) if len(means) > 1 else 0,
            "min": min(means),
            "max": max(means),
            "cat_mean": statistics.mean(cat_means),
            "goal_mean": statistics.mean(goal_means),
            "button_mean": statistics.mean(button_means),
        }

    return analysis


def two_sample_t_test(mean1: float, std1: float, n1: int,
                       mean2: float, std2: float, n2: int) -> Dict:
    """
    Perform Welch's t-test for comparing two means.
    Returns t-statistic, degrees of freedom, and approximate p-value.
    """
    import math

    se1 = std1 ** 2 / n1
    se2 = std2 ** 2 / n2
    se_diff = math.sqrt(se1 + se2)

    if se_diff == 0:
        return {"t_stat": 0, "df": 0, "significant": False, "diff": 0}

    t_stat = (mean1 - mean2) / se_diff

    # Welch-Satterthwaite degrees of freedom
    num = (se1 + se2) ** 2
    denom = (se1 ** 2) / (n1 - 1) + (se2 ** 2) / (n2 - 1)
    df = num / denom if denom > 0 else 1

    # Approximate p-value (two-tailed)
    # For |t| > 2.0 with df > 10, p < 0.05 approximately
    significant_95 = abs(t_stat) > 2.0 and df > 10
    significant_99 = abs(t_stat) > 2.6 and df > 10

    return {
        "t_stat": t_stat,
        "df": df,
        "significant_95": significant_95,
        "significant_99": significant_99,
        "diff": mean1 - mean2,
    }


def analyze_statistical_significance(results: List[Dict]) -> None:
    """Analyze whether top configs are significantly different from baseline."""
    print("\n" + "=" * 70)
    print("STATISTICAL SIGNIFICANCE ANALYSIS")
    print("=" * 70)

    # Find baseline (1.0, 1.0)
    baseline = None
    for r in results:
        if r['cat_ratio'] == 1.0 and r['button_ratio'] == 1.0:
            baseline = r
            break

    if baseline is None:
        print("No baseline (1.0, 1.0) found in results")
        return

    print(f"\nBaseline (cat=1.0, button=1.0, goal=1.0):")
    print(f"  Mean: {baseline['mcts_mean']:.1f}, Std: {baseline['mcts_std']:.1f}")
    ci = compute_confidence_interval(baseline['mcts_mean'], baseline['mcts_std'], baseline['n_games'])
    print(f"  95% CI: [{ci[0]:.1f}, {ci[1]:.1f}]")

    # Sort by mean and compare top configs to baseline
    sorted_results = sorted(results, key=lambda x: x['mcts_mean'], reverse=True)

    print(f"\nComparison of all configs to baseline:")
    print(f"{'Config':^15} | {'Mean':>6} {'Std':>5} | {'Diff':>5} | {'95% CI':^15} | {'Sig?':^6}")
    print("-" * 65)

    for r in sorted_results:
        config = f"({r['cat_ratio']}, {r['button_ratio']})"
        ci = compute_confidence_interval(r['mcts_mean'], r['mcts_std'], r['n_games'])

        # T-test against baseline
        test = two_sample_t_test(
            r['mcts_mean'], r['mcts_std'], r['n_games'],
            baseline['mcts_mean'], baseline['mcts_std'], baseline['n_games']
        )

        sig_marker = "**" if test['significant_99'] else ("*" if test['significant_95'] else "")
        diff = r['mcts_mean'] - baseline['mcts_mean']

        print(f"{config:^15} | {r['mcts_mean']:6.1f} {r['mcts_std']:5.1f} | {diff:+5.1f} | [{ci[0]:5.1f}, {ci[1]:5.1f}] | {sig_marker:^6}")

    print()
    print("* = p < 0.05, ** = p < 0.01 (vs baseline)")


def analyze_marginal_effects(results: List[Dict]) -> None:
    """Analyze the marginal effect of each ratio parameter."""
    print("\n" + "=" * 70)
    print("MARGINAL EFFECTS ANALYSIS")
    print("=" * 70)
    print("(Average effect of changing each ratio, holding the other constant)")
    print()

    for ratio_name in ['cat', 'button']:
        print(f"\n{ratio_name.upper()} RATIO (relative to goal=1.0):")
        print("-" * 50)

        analysis = analyze_by_ratio(results, ratio_name)

        print(f"{'Value':>6} | {'Configs':>7} | {'Mean':>6} | {'Range':^15} | Components")
        print("-" * 70)

        for val, stats in analysis.items():
            range_str = f"[{stats['min']:.1f}, {stats['max']:.1f}]"
            comp_str = f"C:{stats['cat_mean']:.0f} G:{stats['goal_mean']:.0f} B:{stats['button_mean']:.0f}"
            print(f"{val:6.2f} | {stats['n_configs']:7d} | {stats['mean_of_means']:6.1f} | {range_str:^15} | {comp_str}")

        # Effect size
        values = sorted(analysis.keys())
        if len(values) >= 2:
            low_mean = analysis[values[0]]['mean_of_means']
            high_mean = analysis[values[-1]]['mean_of_means']
            effect = high_mean - low_mean
            print(f"\nEffect of {values[0]} -> {values[-1]}: {effect:+.1f} points")


def analyze_variance_sources(results: List[Dict]) -> None:
    """Analyze how much variance comes from ratios vs inherent game variance."""
    print("\n" + "=" * 70)
    print("VARIANCE DECOMPOSITION")
    print("=" * 70)

    all_means = [r['mcts_mean'] for r in results]
    all_stds = [r['mcts_std'] for r in results]

    between_config_std = statistics.stdev(all_means) if len(all_means) > 1 else 0
    avg_within_config_std = statistics.mean(all_stds)

    print(f"\nBetween-configuration std (spread of means): {between_config_std:.2f}")
    print(f"Within-configuration std (avg game-to-game):  {avg_within_config_std:.2f}")
    print()

    # Signal-to-noise ratio
    snr = between_config_std / avg_within_config_std if avg_within_config_std > 0 else 0
    print(f"Signal-to-noise ratio: {snr:.2f}")

    if snr < 0.5:
        print("  -> Low: Ratio differences are small relative to game variance")
        print("     Most observed differences may be noise")
    elif snr < 1.0:
        print("  -> Moderate: Some ratio effects visible but noisy")
        print("     Need more games per config to be confident")
    else:
        print("  -> Good: Ratio differences are meaningful")

    # Required sample size for detecting differences
    if len(all_means) > 1:
        effect_size = max(all_means) - min(all_means)
        avg_std = statistics.mean(all_stds)

        # For 80% power, alpha=0.05, two-sample t-test
        # n ≈ 2 * (1.96 + 0.84)^2 * (std/effect)^2 = 15.7 * (std/effect)^2
        if effect_size > 0:
            required_n = 16 * (avg_std / effect_size) ** 2
            print(f"\nTo reliably detect {effect_size:.1f} pt difference (80% power):")
            print(f"  Need ~{required_n:.0f} games per configuration")


def main():
    parser = argparse.ArgumentParser(description="Statistical analysis of ratio sweep")
    parser.add_argument("--experiment", type=str, default="calico-ratio-sweep",
                       help="MLflow experiment name")
    args = parser.parse_args()

    print("Loading sweep data from MLflow...")
    results = load_sweep_data(args.experiment)

    if not results:
        print("No results found")
        return

    print(f"Loaded {len(results)} configurations")

    # Run all analyses
    analyze_variance_sources(results)
    analyze_statistical_significance(results)
    analyze_marginal_effects(results)

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    # Quick summary
    sorted_results = sorted(results, key=lambda x: x['mcts_mean'], reverse=True)
    baseline = next((r for r in results if r['cat_ratio'] == 1.0 and
                     r['button_ratio'] == 1.0), None)

    if baseline:
        top = sorted_results[0]
        print(f"\nTop config: (cat={top['cat_ratio']}, button={top['button_ratio']}) = {top['mcts_mean']:.1f}")
        print(f"Baseline:   (cat=1.0, button=1.0) = {baseline['mcts_mean']:.1f}")
        print(f"Difference: {top['mcts_mean'] - baseline['mcts_mean']:+.1f} points")

        # Count configs that beat baseline
        better_count = sum(1 for r in results if r['mcts_mean'] > baseline['mcts_mean'])
        print(f"\n{better_count}/{len(results)} configs scored higher than baseline")


if __name__ == "__main__":
    main()
