"""
Migration script to convert existing game records to combined action format.

This script reads game records with separate place_tile/choose_market actions
and combines them into place_and_choose actions.

Usage:
    python migrate_game_records.py              # Migrate all records in game_records/
    python migrate_game_records.py --dry-run    # Show what would be done
"""
import argparse
import json
import os
from datetime import datetime
from typing import List, Dict, Any


def combine_candidates(
    place_candidates: List[dict],
    market_candidates: List[dict]
) -> List[dict]:
    """
    Combine place and market candidates into combined candidates.
    Uses cross-product of top candidates with weighted visit counts.
    """
    combined = []

    # Take top 3 from each to avoid explosion
    top_place = place_candidates[:3]
    top_market = market_candidates[:3]

    for pc in top_place:
        for mc in top_market:
            # Estimate combined visits using harmonic mean
            if pc["visits"] > 0 and mc["visits"] > 0:
                combined_visits = int(2 * pc["visits"] * mc["visits"] / (pc["visits"] + mc["visits"]))
            else:
                combined_visits = 0

            # Average the scores
            combined_score = (pc["avg_score"] + mc["avg_score"]) / 2

            combined.append({
                "action_type": "place_and_choose",
                "position": pc["position"],
                "hand_index": pc["hand_index"],
                "market_index": mc["market_index"],
                "visits": combined_visits,
                "avg_score": round(combined_score, 2)
            })

    # Sort by estimated visits
    combined.sort(key=lambda x: x["visits"], reverse=True)
    return combined[:5]


def migrate_decision_pair(place_decision: dict, market_decision: dict) -> dict:
    """
    Combine a place_tile decision and its following choose_market decision
    into a single place_and_choose decision.
    """
    combined = {
        "turn_number": place_decision["turn_number"],
        "phase": "PLACE_AND_CHOOSE",
        "hand_tiles": place_decision["hand_tiles"],
        "market_tiles": place_decision["market_tiles"],
        "board_tiles": place_decision["board_tiles"],
        "tiles_remaining": place_decision["tiles_remaining"],
        "action_type": "place_and_choose",
        "action_position": place_decision["action_position"],
        "action_hand_index": place_decision["action_hand_index"],
        "action_market_index": market_decision["action_market_index"],
        "candidates": combine_candidates(
            place_decision["candidates"],
            market_decision["candidates"]
        ),
        "tiles_drawn": market_decision.get("tiles_drawn", []),
        "simulated_discards": market_decision.get("simulated_discards", [])
    }
    return combined


def migrate_final_turn(place_decision: dict) -> dict:
    """
    Convert a final turn place_tile decision (no market choice follows)
    into a place_and_choose decision with market_index=None.
    """
    return {
        "turn_number": place_decision["turn_number"],
        "phase": "PLACE_AND_CHOOSE",
        "hand_tiles": place_decision["hand_tiles"],
        "market_tiles": place_decision["market_tiles"],
        "board_tiles": place_decision["board_tiles"],
        "tiles_remaining": place_decision["tiles_remaining"],
        "action_type": "place_and_choose",
        "action_position": place_decision["action_position"],
        "action_hand_index": place_decision["action_hand_index"],
        "action_market_index": None,
        "candidates": [{
            "action_type": "place_and_choose",
            "position": c["position"],
            "hand_index": c["hand_index"],
            "market_index": None,
            "visits": c["visits"],
            "avg_score": c["avg_score"]
        } for c in place_decision["candidates"][:5]],
        "tiles_drawn": [],
        "simulated_discards": []
    }


def migrate_game_record(record: dict) -> dict:
    """Migrate a single game record to combined action format."""
    decisions = record["decisions"]
    new_decisions = []

    i = 0
    while i < len(decisions):
        decision = decisions[i]

        if decision["action_type"] == "place_tile":
            # Check if next decision is choose_market for same turn
            if (i + 1 < len(decisions) and
                decisions[i + 1]["action_type"] == "choose_market" and
                decisions[i + 1]["turn_number"] == decision["turn_number"]):
                # Combine them
                combined = migrate_decision_pair(decision, decisions[i + 1])
                new_decisions.append(combined)
                i += 2
            else:
                # Final turn - no market choice
                final_decision = migrate_final_turn(decision)
                new_decisions.append(final_decision)
                i += 1
        elif decision["action_type"] == "place_and_choose":
            # Already migrated, keep as-is
            new_decisions.append(decision)
            i += 1
        else:
            # Standalone choose_market (shouldn't happen in normal flow)
            # Keep it for safety
            new_decisions.append(decision)
            i += 1

    # Create migrated record
    migrated = dict(record)
    migrated["decisions"] = new_decisions
    migrated["format_version"] = "2.0"

    # Update mcts_config to indicate combined actions
    if "mcts_config" in migrated:
        migrated["mcts_config"]["use_combined_actions"] = True

    return migrated


def main():
    parser = argparse.ArgumentParser(
        description="Migrate game records to combined action format"
    )
    parser.add_argument(
        "--input-dir", default=None,
        help="Input directory (default: ../game_records)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be done without making changes"
    )
    args = parser.parse_args()

    # Determine input directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if args.input_dir:
        input_dir = args.input_dir
    else:
        input_dir = os.path.join(os.path.dirname(current_dir), "game_records")

    if not os.path.exists(input_dir):
        print(f"Error: Directory not found: {input_dir}")
        return 1

    # Find all JSON files
    json_files = [f for f in os.listdir(input_dir) if f.endswith('.json')]

    if not json_files:
        print(f"No JSON files found in {input_dir}")
        return 0

    print(f"Found {len(json_files)} game record(s) in {input_dir}")
    if args.dry_run:
        print("(DRY RUN - no changes will be made)\n")
    else:
        print()

    migrated_count = 0
    skipped_count = 0
    error_count = 0

    for filename in sorted(json_files):
        input_path = os.path.join(input_dir, filename)

        try:
            with open(input_path, 'r') as f:
                record = json.load(f)

            # Check if already migrated
            if record.get("format_version") == "2.0":
                print(f"  {filename}: Already migrated (v2.0), skipping")
                skipped_count += 1
                continue

            original_decisions = len(record["decisions"])
            migrated = migrate_game_record(record)
            new_decisions = len(migrated["decisions"])

            print(f"  {filename}: {original_decisions} -> {new_decisions} decisions")

            if not args.dry_run:
                with open(input_path, 'w') as f:
                    json.dump(migrated, f, indent=2)

            migrated_count += 1

        except Exception as e:
            print(f"  {filename}: ERROR - {e}")
            error_count += 1

    print()
    print("=" * 50)
    print(f"Migrated: {migrated_count}")
    print(f"Skipped:  {skipped_count}")
    print(f"Errors:   {error_count}")

    if args.dry_run and migrated_count > 0:
        print("\nRun without --dry-run to apply changes.")

    return 0


if __name__ == "__main__":
    exit(main())
