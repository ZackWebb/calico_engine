"""
Entry point for replaying recorded MCTS games.

Usage:
    python run_replay.py game_records/game_20251229_123456_score50.json
    python run_replay.py --list                    # List available recordings
    python run_replay.py --latest                  # Replay most recent recording
"""
import argparse
import os
import sys
from pathlib import Path

from game_record import GameRecord
from replay_visualizer import ReplayVisualizer


def get_game_records_dir() -> Path:
    """Get the default game_records directory."""
    current_dir = Path(__file__).parent
    return current_dir.parent / "game_records"


def list_recordings():
    """List all available game recordings."""
    records_dir = get_game_records_dir()

    if not records_dir.exists():
        print("No game_records directory found.")
        print(f"Expected at: {records_dir}")
        return

    json_files = sorted(records_dir.glob("game_*.json"), reverse=True)

    if not json_files:
        print("No game recordings found.")
        print(f"Run 'python run_mcts.py --record' to create one.")
        return

    print(f"Available game recordings ({len(json_files)} total):")
    print()

    for f in json_files[:20]:  # Show most recent 20
        try:
            record = GameRecord.load(str(f))
            cats_total = sum(record.score_breakdown.get('cats', {}).values())
            goals_total = sum(record.score_breakdown.get('goals', {}).values())
            buttons = record.score_breakdown.get('buttons', {}).get('button_score', 0)

            print(f"  {f.name}")
            print(f"    Score: {record.final_score} (cats={cats_total}, "
                  f"goals={goals_total}, buttons={buttons})")
            print(f"    Decisions: {len(record.decisions)}")
            print(f"    Config: {record.mcts_config.get('max_iterations', '?')} iterations")
            print()
        except Exception as e:
            print(f"  {f.name} (error loading: {e})")

    if len(json_files) > 20:
        print(f"  ... and {len(json_files) - 20} more")


def get_latest_recording() -> Path:
    """Get the path to the most recent recording."""
    records_dir = get_game_records_dir()

    if not records_dir.exists():
        return None

    json_files = sorted(records_dir.glob("game_*.json"), reverse=True)
    return json_files[0] if json_files else None


def main():
    parser = argparse.ArgumentParser(
        description="Replay recorded MCTS games with step-by-step visualization"
    )
    parser.add_argument(
        "file", nargs="?",
        help="Path to game record JSON file"
    )
    parser.add_argument(
        "--list", "-l", action="store_true",
        help="List available game recordings"
    )
    parser.add_argument(
        "--latest", action="store_true",
        help="Replay the most recent recording"
    )
    parser.add_argument(
        "--scale", type=float, default=1.0,
        help="Initial window scale (default: 1.0)"
    )

    args = parser.parse_args()

    # Handle --list
    if args.list:
        list_recordings()
        return

    # Determine which file to load
    if args.latest:
        filepath = get_latest_recording()
        if not filepath:
            print("No recordings found. Run 'python run_mcts.py --record' first.")
            sys.exit(1)
        print(f"Loading latest recording: {filepath.name}")
    elif args.file:
        filepath = Path(args.file)
        if not filepath.exists():
            # Try relative to game_records dir
            alt_path = get_game_records_dir() / args.file
            if alt_path.exists():
                filepath = alt_path
            else:
                print(f"File not found: {args.file}")
                sys.exit(1)
    else:
        parser.print_help()
        print()
        print("Use --list to see available recordings, or --latest to replay the most recent.")
        sys.exit(1)

    # Load the game record
    print(f"Loading: {filepath}")
    try:
        record = GameRecord.load(str(filepath))
    except Exception as e:
        print(f"Error loading game record: {e}")
        sys.exit(1)

    # Print summary
    print(f"  Final Score: {record.final_score}")
    print(f"  Decisions: {len(record.decisions)}")
    print(f"  MCTS Config: {record.mcts_config}")
    print()
    print("Controls:")
    print("  Left/Right Arrow: Step backward/forward")
    print("  Home/End: Jump to start/end")
    print("  Space: Toggle auto-play")
    print("  Up/Down Arrow: Adjust auto-play speed")
    print("  C: Toggle candidate moves display")
    print("  F11: Toggle fullscreen")
    print("  +/-: Adjust scale")
    print("  Esc: Quit")
    print()
    print("Starting replay...")

    # Start the visualizer
    visualizer = ReplayVisualizer(record, initial_scale=args.scale)
    visualizer.run()


if __name__ == "__main__":
    main()
