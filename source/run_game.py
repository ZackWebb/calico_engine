"""
Entry point for running different game modes.

Usage:
    python run_game.py play    # Interactive pygame mode
    python run_game.py sim     # Run random simulation
"""
import sys


def run_play_mode():
    from play_mode import PlayMode
    from board_configurations import BOARD_1

    print("Starting Play Mode...")
    game = PlayMode(BOARD_1)
    game.run()


def run_simulation_demo():
    from simulation_mode import SimulationMode
    from board_configurations import BOARD_1

    print("Running random simulation...")
    game = SimulationMode(BOARD_1)

    # Show initial state
    state = game.get_game_state()
    print(f"Initial empty positions: {len(state.empty_positions)}")
    print(f"Tiles in bag: {state.tiles_remaining_in_bag}")
    print(f"Player hand: {len(state.player_hand)} tiles")
    print(f"Market: {len(state.market_tiles)} tiles")
    print()

    # Play random game
    final_score = game.play_random_game()

    print(f"Game complete!")
    print(f"Turns played: {game.turn_number}")
    print(f"Final score: {final_score}")
    print(f"Tiles remaining in bag: {game.tile_bag.tiles_remaining()}")

    # Show cat scores
    print("\nCat scores:")
    for cat in game.cats:
        score = cat.score(game.player.grid)
        patterns = [p.name for p in cat.patterns]
        print(f"  {cat.name} ({', '.join(patterns)}): {score} points")


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_game.py [play|sim]")
        print("  play - Interactive pygame mode")
        print("  sim  - Run random simulation")
        return

    mode = sys.argv[1].lower()

    if mode == "play":
        run_play_mode()
    elif mode == "sim":
        run_simulation_demo()
    else:
        print(f"Unknown mode: {mode}")
        print("Usage: python run_game.py [play|sim]")


if __name__ == "__main__":
    main()
