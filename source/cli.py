"""
Calico CLI - Unified command-line interface for the Calico board game AI.

Usage:
    python cli.py play              # Play interactive game with pygame
    python cli.py mcts              # Run single MCTS game
    python cli.py mcts --baseline 10  # Compare MCTS vs random
    python cli.py replay --latest   # Replay most recent recorded game
    python cli.py replay --list     # List available recordings
"""
import typer
from typing import Optional
from pathlib import Path
from enum import Enum

app = typer.Typer(
    name="calico",
    help="Calico board game AI - MCTS agent with game recording and replay",
    add_completion=False,
)


class RolloutMode(str, Enum):
    random = "random"
    deterministic = "deterministic"
    heuristic = "heuristic"


@app.command()
def play(
    scale: float = typer.Option(1.0, "--scale", "-s", help="Window scale factor"),
):
    """
    Play Calico interactively with pygame visualization.

    Use mouse to select tiles and place them on the board.
    """
    from play_mode import PlayMode
    from play_mode_visualizer import PlayModeVisualizer
    from board_configurations import BOARD_1

    typer.echo("Starting interactive Calico game...")
    game = PlayMode(BOARD_1)
    visualizer = PlayModeVisualizer(game, initial_scale=scale)
    visualizer.run()


@app.command()
def mcts(
    iterations: int = typer.Option(5000, "--iterations", "-i", help="MCTS iterations per move (default: 5000)"),
    exploration: float = typer.Option(1.4, "--exploration", "-e", help="UCB1 exploration constant"),
    threshold: int = typer.Option(5, "--threshold", "-t", help="Late game threshold for full rollouts"),
    baseline: int = typer.Option(0, "--baseline", "-b", help="Run N games comparing MCTS vs random"),
    save_boards: int = typer.Option(0, "--save-boards", help="Save top N boards to JSON"),
    record: bool = typer.Option(False, "--record", "-r", help="Record game with MCTS decision analysis"),
    no_heuristic: bool = typer.Option(False, "--no-heuristic", help="Disable heuristic (use full rollouts)"),
    deterministic: bool = typer.Option(False, "--deterministic", "-d", help="Use deterministic rollouts"),
    separate: bool = typer.Option(False, "--separate", help="Use separate actions (old behavior) instead of combined"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Print detailed per-move info"),
):
    """
    Run MCTS agent for Calico.

    By default runs a single game with verbose output.
    Use --baseline N to compare MCTS vs random over N games.
    Use --record to save game recording for replay analysis.

    By default, uses combined place_and_choose actions (atomic turns).
    Use --separate for the old two-phase behavior.
    """
    import time
    from statistics import mean, stdev
    from simulation_mode import SimulationMode
    from board_configurations import BOARD_1
    from mcts_agent import MCTSAgent
    from game_record import GameRecorder, GameRecord
    from run_mcts import (
        run_mcts_game, run_recorded_mcts_game, run_random_game,
        save_top_boards, save_game_record, print_board_summary
    )

    agent = MCTSAgent(
        exploration_constant=exploration,
        max_iterations=iterations,
        late_game_threshold=threshold,
        use_heuristic=not no_heuristic,
        use_deterministic_rollout=deterministic,
        use_combined_actions=not separate,
        verbose=verbose
    )

    typer.echo("MCTS Agent Configuration:")
    typer.echo(f"  Iterations: {iterations}")
    typer.echo(f"  Exploration: {exploration}")
    typer.echo(f"  Late game threshold: {threshold}")
    typer.echo(f"  Use heuristic: {not no_heuristic}")
    typer.echo(f"  Deterministic rollouts: {deterministic}")
    typer.echo(f"  Combined actions: {not separate}")
    typer.echo()

    if baseline > 0:
        _run_comparison(baseline, agent, save_boards, record)
    else:
        typer.echo("Running single MCTS game...")
        typer.echo()
        start = time.time()

        if record:
            score, game, game_record = run_recorded_mcts_game(agent, verbose=True)
        else:
            score, game = run_mcts_game(agent, verbose=True)

        total_time = time.time() - start
        typer.echo(f"\nTotal game time: {total_time:.1f}s")

        if save_boards > 0:
            typer.echo(f"\nSaving board...")
            saved_files = save_top_boards([(score, game)], 1)
            typer.echo(f"Saved to: {saved_files[0]}")

        if record:
            typer.echo(f"\nSaving game record...")
            record_path = save_game_record(game_record)
            typer.echo(f"Saved to: {record_path}")
            typer.echo(f"  Decisions recorded: {len(game_record.decisions)}")


def _run_comparison(n_games: int, agent, save_top: int, record: bool):
    """Run MCTS vs random comparison."""
    import time
    from statistics import mean, stdev
    from simulation_mode import SimulationMode
    from board_configurations import BOARD_1
    from game_record import GameRecord
    from run_mcts import (
        run_mcts_game, run_recorded_mcts_game, run_random_game,
        save_top_boards, save_game_record, print_board_summary
    )

    typer.echo(f"Running {n_games} games each for MCTS and Random...")
    if record:
        typer.echo("(Recording enabled - this may be slower)")
    typer.echo()

    mcts_games = []
    game_records = []
    random_scores = []
    mcts_times = []

    for i in range(n_games):
        typer.echo(f"Game {i+1}/{n_games}...", nl=False)

        start = time.time()
        if record:
            mcts_score, mcts_game, game_record = run_recorded_mcts_game(agent, verbose=False)
            game_records.append(game_record)
        else:
            mcts_score, mcts_game = run_mcts_game(agent, verbose=False)
        mcts_time = time.time() - start
        mcts_times.append(mcts_time)

        random_score = run_random_game()

        mcts_games.append((mcts_score, mcts_game))
        random_scores.append(random_score)

        typer.echo(f" MCTS: {mcts_score:3d} ({mcts_time:.1f}s), Random: {random_score:3d}")

    mcts_scores = [score for score, _ in mcts_games]

    typer.echo()
    typer.echo("=" * 50)
    typer.echo("RESULTS")
    typer.echo("=" * 50)

    mcts_mean = mean(mcts_scores)
    mcts_std = stdev(mcts_scores) if len(mcts_scores) > 1 else 0
    typer.echo(f"MCTS:   mean={mcts_mean:.1f}, stdev={mcts_std:.1f}, "
               f"min={min(mcts_scores)}, max={max(mcts_scores)}")

    random_mean = mean(random_scores)
    random_std = stdev(random_scores) if len(random_scores) > 1 else 0
    typer.echo(f"Random: mean={random_mean:.1f}, stdev={random_std:.1f}, "
               f"min={min(random_scores)}, max={max(random_scores)}")

    if random_mean > 0:
        improvement = (mcts_mean - random_mean) / random_mean * 100
        typer.echo(f"\nMCTS improvement: {improvement:+.1f}%")
    else:
        typer.echo(f"\nMCTS improvement: {mcts_mean - random_mean:+.1f} points")

    avg_time = mean(mcts_times)
    typer.echo(f"\nAverage MCTS game time: {avg_time:.1f}s")

    if save_top > 0:
        typer.echo(f"\nSaving top {save_top} boards...")
        saved_files = save_top_boards(mcts_games, save_top)
        typer.echo(f"Saved to:")
        for f in saved_files:
            typer.echo(f"  {f}")

    if record:
        typer.echo(f"\nSaving {len(game_records)} game records...")
        for game_record in game_records:
            record_path = save_game_record(game_record)
            typer.echo(f"  {record_path}")


@app.command()
def replay(
    file: Optional[Path] = typer.Argument(None, help="Path to game record JSON file"),
    list_recordings: bool = typer.Option(False, "--list", "-l", help="List available recordings"),
    latest: bool = typer.Option(False, "--latest", help="Replay the most recent recording"),
    scale: float = typer.Option(1.0, "--scale", "-s", help="Window scale factor"),
):
    """
    Replay recorded MCTS games with step-by-step visualization.

    Controls:
      Left/Right Arrow: Step backward/forward
      Home/End: Jump to start/end
      Space: Toggle auto-play
      Up/Down: Adjust auto-play speed
      C: Toggle candidate moves display
      F11: Fullscreen
    """
    from game_record import GameRecord
    from replay_visualizer import ReplayVisualizer
    import os

    def get_records_dir():
        current_dir = Path(__file__).parent
        return current_dir.parent / "game_records"

    if list_recordings:
        records_dir = get_records_dir()
        if not records_dir.exists():
            typer.echo("No game_records directory found.")
            typer.echo(f"Run 'python cli.py mcts --record' to create one.")
            raise typer.Exit(1)

        json_files = sorted(records_dir.glob("game_*.json"), reverse=True)
        if not json_files:
            typer.echo("No game recordings found.")
            typer.echo("Run 'python cli.py mcts --record' to create one.")
            raise typer.Exit(1)

        typer.echo(f"Available game recordings ({len(json_files)} total):\n")

        for f in json_files[:20]:
            try:
                record = GameRecord.load(str(f))
                cats_total = sum(record.score_breakdown.get('cats', {}).values())
                goals_total = sum(record.score_breakdown.get('goals', {}).values())
                buttons = record.score_breakdown.get('buttons', {}).get('button_score', 0)

                typer.echo(f"  {f.name}")
                typer.echo(f"    Score: {record.final_score} (cats={cats_total}, "
                          f"goals={goals_total}, buttons={buttons})")
                typer.echo(f"    Decisions: {len(record.decisions)}")
                typer.echo(f"    Config: {record.mcts_config.get('max_iterations', '?')} iterations\n")
            except Exception as e:
                typer.echo(f"  {f.name} (error loading: {e})")

        if len(json_files) > 20:
            typer.echo(f"  ... and {len(json_files) - 20} more")
        return

    # Determine file to load
    filepath = None
    if latest:
        records_dir = get_records_dir()
        if records_dir.exists():
            json_files = sorted(records_dir.glob("game_*.json"), reverse=True)
            if json_files:
                filepath = json_files[0]

        if not filepath:
            typer.echo("No recordings found. Run 'python cli.py mcts --record' first.")
            raise typer.Exit(1)
        typer.echo(f"Loading latest recording: {filepath.name}")
    elif file:
        filepath = file
        if not filepath.exists():
            # Try relative to game_records dir
            alt_path = get_records_dir() / file.name
            if alt_path.exists():
                filepath = alt_path
            else:
                typer.echo(f"File not found: {file}")
                raise typer.Exit(1)
    else:
        typer.echo("Usage: python cli.py replay <file> or --latest or --list")
        typer.echo("\nUse --list to see available recordings.")
        raise typer.Exit(1)

    # Load and display
    typer.echo(f"Loading: {filepath}")
    try:
        record = GameRecord.load(str(filepath))
    except Exception as e:
        typer.echo(f"Error loading game record: {e}")
        raise typer.Exit(1)

    typer.echo(f"  Final Score: {record.final_score}")
    typer.echo(f"  Decisions: {len(record.decisions)}")
    typer.echo(f"  MCTS Config: {record.mcts_config}")
    typer.echo()
    typer.echo("Controls:")
    typer.echo("  Left/Right: Step | Home/End: Jump | Space: Auto-play")
    typer.echo("  C: Toggle candidates | F11: Fullscreen | Esc: Quit")
    typer.echo()
    typer.echo("Starting replay...")

    visualizer = ReplayVisualizer(record, initial_scale=scale)
    visualizer.run()


@app.command()
def simulate(
    games: int = typer.Option(10, "--games", "-n", help="Number of games to simulate"),
    random_only: bool = typer.Option(False, "--random", help="Use random agent only"),
):
    """
    Run quick simulations without visualization.

    Useful for testing or gathering statistics.
    """
    from simulation_mode import SimulationMode
    from board_configurations import BOARD_1
    from statistics import mean, stdev

    scores = []
    typer.echo(f"Running {games} {'random' if random_only else 'simulation'} games...")

    for i in range(games):
        game = SimulationMode(BOARD_1)
        score = game.play_random_game()
        scores.append(score)
        if (i + 1) % 10 == 0:
            typer.echo(f"  {i + 1}/{games} complete...")

    avg = mean(scores)
    std = stdev(scores) if len(scores) > 1 else 0
    typer.echo()
    typer.echo(f"Results ({games} games):")
    typer.echo(f"  Mean: {avg:.1f}")
    typer.echo(f"  Stdev: {std:.1f}")
    typer.echo(f"  Min: {min(scores)}, Max: {max(scores)}")


@app.command()
def test(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose test output"),
    filter: Optional[str] = typer.Option(None, "--filter", "-k", help="Filter tests by name"),
):
    """
    Run the test suite.
    """
    import subprocess
    import sys

    cmd = [sys.executable, "-m", "pytest", "tests/"]
    if verbose:
        cmd.append("-v")
    if filter:
        cmd.extend(["-k", filter])

    typer.echo(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    raise typer.Exit(result.returncode)


@app.command()
def benchmark(
    n_games: int = typer.Option(16, "--games", "-n", help="Number of games to run (default: 16)"),
    iterations: int = typer.Option(5000, "--iterations", "-i", help="MCTS iterations per move (default: 5000)"),
    exploration: float = typer.Option(1.4, "--exploration", "-e", help="UCB1 exploration constant"),
    threshold: int = typer.Option(5, "--threshold", "-t", help="Late game threshold"),
    workers: int = typer.Option(4, "--workers", "-w", help="Parallel workers (default: 4)"),
    tag: Optional[str] = typer.Option(None, "--tag", help="Tag for this experiment run"),
    experiment: str = typer.Option("calico-mcts", "--experiment", help="MLflow experiment name"),
    run_name: Optional[str] = typer.Option(None, "--run-name", help="Name for this MLflow run"),
    sweep: bool = typer.Option(False, "--sweep", help="Run parameter sweep across iterations"),
    no_heuristic: bool = typer.Option(False, "--no-heuristic", help="Disable heuristic"),
    deterministic: bool = typer.Option(False, "--deterministic", help="Use deterministic rollouts"),
    separate: bool = typer.Option(False, "--separate", help="Use separate actions"),
    no_mlflow: bool = typer.Option(False, "--no-mlflow", help="Skip MLflow logging"),
    no_record: bool = typer.Option(False, "--no-record", help="Disable game recording (default: enabled)"),
    seeds: Optional[str] = typer.Option(None, "--seeds", help="Seeds for reproducibility: '0-9', 'fixed', or '0,5,10'"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """
    Run benchmarks with MLflow experiment tracking.

    Logs hyperparameters, metrics, and git info to MLflow.
    View results with: mlflow ui

    Examples:
        python cli.py benchmark                     # 16 games, 4 workers
        python cli.py benchmark -n 20 -i 1000 -w 8  # 20 games, 8 workers
        python cli.py benchmark --tag "improved_heuristic"
        python cli.py benchmark --sweep
    """
    import subprocess
    import sys

    cmd = [sys.executable, "benchmark.py"]
    cmd.extend(["-n", str(n_games)])
    cmd.extend(["-i", str(iterations)])
    cmd.extend(["-e", str(exploration)])
    cmd.extend(["-t", str(threshold)])
    cmd.extend(["-w", str(workers)])

    if tag:
        cmd.extend(["--tag", tag])
    if experiment != "calico-mcts":
        cmd.extend(["--experiment", experiment])
    if run_name:
        cmd.extend(["--run-name", run_name])
    if sweep:
        cmd.append("--sweep")
    if no_heuristic:
        cmd.append("--no-heuristic")
    if deterministic:
        cmd.append("--deterministic")
    if separate:
        cmd.append("--separate")
    if no_mlflow:
        cmd.append("--no-mlflow")
    if no_record:
        cmd.append("--no-record")
    if seeds:
        cmd.extend(["--seeds", seeds])
    if verbose:
        cmd.append("-v")

    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    raise typer.Exit(result.returncode)


@app.command()
def mlflow_ui():
    """
    Start the MLflow UI to view experiment results.

    Opens at http://localhost:5000
    """
    import subprocess
    import sys

    project_root = Path(__file__).parent.parent
    db_path = project_root / "mlflow.db"

    typer.echo("Starting MLflow UI at http://localhost:5000")
    typer.echo(f"Database: {db_path}")
    typer.echo("Press Ctrl+C to stop")

    tracking_uri = f"sqlite:///{db_path.as_posix()}"
    result = subprocess.run(
        [sys.executable, "-m", "mlflow", "ui",
         "--backend-store-uri", tracking_uri],
        cwd=project_root
    )
    raise typer.Exit(result.returncode)


@app.command()
def info():
    """
    Display information about the project and available commands.
    """
    typer.echo("=" * 60)
    typer.echo("Calico Board Game AI")
    typer.echo("=" * 60)
    typer.echo()
    typer.echo("A Monte Carlo Tree Search (MCTS) agent for the Calico board game.")
    typer.echo()
    typer.echo("Commands:")
    typer.echo("  play      - Interactive game with pygame")
    typer.echo("  mcts      - Run MCTS agent (single game or baseline comparison)")
    typer.echo("  replay    - Step through recorded games")
    typer.echo("  simulate  - Quick random simulations")
    typer.echo("  benchmark - Run experiments with MLflow tracking")
    typer.echo("  mlflow-ui - Start MLflow UI to view results")
    typer.echo("  test      - Run test suite")
    typer.echo()
    typer.echo("Quick Start:")
    typer.echo("  python cli.py play                    # Play interactively")
    typer.echo("  python cli.py mcts --record           # Run MCTS with recording")
    typer.echo("  python cli.py replay --latest         # Replay last game")
    typer.echo("  python cli.py benchmark -n 10 --tag v1  # Benchmark with MLflow")
    typer.echo()
    typer.echo("For help on any command: python cli.py <command> --help")


if __name__ == "__main__":
    app()
