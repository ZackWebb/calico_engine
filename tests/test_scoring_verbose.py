"""
Verbose scoring tests for manual verification.
Run with: python -m pytest tests/test_scoring_verbose.py -v -s
The -s flag shows print output for manual inspection.
"""
import random
from collections import Counter

from source.simulation_mode import SimulationMode
from source.board_configurations import BOARD_1
from source.tile import Color, Pattern, Tile
from source.hex_grid import HexGrid
from source.goal import GoalAAA_BBB, GoalAA_BB_CC, GoalAllUnique
from source.cat import CatMillie, CatLeo, CatRumi


def print_tile(tile):
    """Format tile for display."""
    if tile is None:
        return "empty"
    return f"{tile.color.name[:3]}-{tile.pattern.name[:3]}"


def print_neighbors_for_goal(grid, goal):
    """Print the 6 neighbors around a goal position with their attributes."""
    print(f"\n  Goal '{goal.name}' at {goal.position}:")
    neighbors = grid.get_neighbors(*goal.position)
    tiles = []
    for i, pos in enumerate(neighbors):
        tile = grid.grid.get(pos)
        tiles.append(tile)
        tile_str = print_tile(tile) if tile else "EMPTY"
        print(f"    Neighbor {i+1} at {pos}: {tile_str}")

    if all(t is not None for t in tiles):
        colors = [t.color for t in tiles]
        patterns = [t.pattern for t in tiles]
        color_counts = Counter(colors)
        pattern_counts = Counter(patterns)
        print(f"    Color distribution: {dict(color_counts)}")
        print(f"    Pattern distribution: {dict(pattern_counts)}")
        print(f"    Color counts sorted: {sorted(color_counts.values(), reverse=True)}")
        print(f"    Pattern counts sorted: {sorted(pattern_counts.values(), reverse=True)}")
    else:
        print(f"    (Not all neighbors filled - {sum(1 for t in tiles if t is None)} empty)")

    return tiles


def check_cat_condition_verbose(cat, grid):
    """Verbose check of cat condition."""
    print(f"\n  Cat '{cat.name}' (worth {cat.point_value} pts):")
    print(f"    Looking for patterns: {[p.name for p in cat.patterns]}")

    met = cat.check_condition(grid)
    score = cat.score(grid)
    print(f"    Condition met: {met}")
    print(f"    Score: {score}")
    return score


class TestVerboseScoring:
    """Tests that print detailed scoring information for manual verification."""

    def test_random_complete_game_scoring(self):
        """Play a random game and show detailed scoring breakdown."""
        print("\n" + "="*70)
        print("RANDOM COMPLETE GAME SCORING TEST")
        print("="*70)

        game = SimulationMode(BOARD_1)
        game.play_random_game()

        print("\n--- GOAL SCORING ---")
        total_goal = 0
        for goal in game.goals:
            print_neighbors_for_goal(game.player.grid, goal)
            score = goal.score(game.player.grid)
            print(f"    SCORE: {score}")
            total_goal += score

        print(f"\n  Total Goal Score: {total_goal}")

        print("\n--- CAT SCORING ---")
        total_cat = 0
        for cat in game.cats:
            score = check_cat_condition_verbose(cat, game.player.grid)
            total_cat += score

        print(f"\n  Total Cat Score: {total_cat}")

        print("\n--- BUTTON SCORING ---")
        button_scores = game.get_button_scores()
        total_buttons = button_scores['total_score']
        print(f"  Total Buttons: {button_scores['total_buttons']}")
        print(f"  Button Score: {button_scores['button_score']}")
        print(f"  Has Rainbow: {button_scores['has_rainbow']}")
        print(f"  Total Button Score: {total_buttons}")

        print("\n--- FINAL SCORE ---")
        print(f"  Goals: {total_goal}")
        print(f"  Cats: {total_cat}")
        print(f"  Buttons: {total_buttons}")
        print(f"  TOTAL: {game.get_final_score()}")

        assert game.get_final_score() == total_goal + total_cat + total_buttons

    def test_goal_aaa_bbb_manual_setup(self):
        """Test AAA-BBB goal with manually constructed board."""
        print("\n" + "="*70)
        print("AAA-BBB GOAL MANUAL TEST")
        print("="*70)

        grid = HexGrid()
        goal = GoalAAA_BBB((-2, 1, 1))
        neighbors = grid.get_neighbors(-2, 1, 1)

        # Setup: 3 BLUE DOTS, 3 PINK LEAVES (should score 13 - both conditions)
        print("\n  Test 1: 3 BLUE DOTS + 3 PINK LEAVES")
        for i, pos in enumerate(neighbors):
            if i < 3:
                grid.set_tile(*pos, Tile(Color.BLUE, Pattern.DOTS))
            else:
                grid.set_tile(*pos, Tile(Color.PINK, Pattern.LEAVES))

        print_neighbors_for_goal(grid, goal)
        score = goal.score(grid)
        print(f"    SCORE: {score} (expected: 13)")
        assert score == 13

        # Reset and test color-only
        grid = HexGrid()
        print("\n  Test 2: 3 BLUE + 3 PINK (different patterns each)")
        patterns = list(Pattern)
        for i, pos in enumerate(neighbors):
            color = Color.BLUE if i < 3 else Color.PINK
            grid.set_tile(*pos, Tile(color, patterns[i]))

        print_neighbors_for_goal(grid, goal)
        score = goal.score(grid)
        print(f"    SCORE: {score} (expected: 8 - color only)")
        assert score == 8

    def test_goal_aa_bb_cc_manual_setup(self):
        """Test AA-BB-CC goal with manually constructed board."""
        print("\n" + "="*70)
        print("AA-BB-CC GOAL MANUAL TEST")
        print("="*70)

        grid = HexGrid()
        goal = GoalAA_BB_CC((1, -1, 0))
        neighbors = grid.get_neighbors(1, -1, 0)

        # Setup: 2 each of 3 colors AND 2 each of 3 patterns (should score 11)
        print("\n  Test 1: 2-2-2 colors AND 2-2-2 patterns")
        tiles = [
            (Color.BLUE, Pattern.DOTS), (Color.BLUE, Pattern.DOTS),
            (Color.PINK, Pattern.LEAVES), (Color.PINK, Pattern.LEAVES),
            (Color.GREEN, Pattern.FLOWERS), (Color.GREEN, Pattern.FLOWERS),
        ]
        for i, pos in enumerate(neighbors):
            grid.set_tile(*pos, Tile(*tiles[i]))

        print_neighbors_for_goal(grid, goal)
        score = goal.score(grid)
        print(f"    SCORE: {score} (expected: 11)")
        assert score == 11

        # Test 2-2-2 colors only
        grid = HexGrid()
        print("\n  Test 2: 2-2-2 colors only (6 different patterns)")
        colors = [Color.BLUE, Color.BLUE, Color.PINK, Color.PINK, Color.GREEN, Color.GREEN]
        patterns = list(Pattern)[:6]
        for i, pos in enumerate(neighbors):
            grid.set_tile(*pos, Tile(colors[i], patterns[i]))

        print_neighbors_for_goal(grid, goal)
        score = goal.score(grid)
        print(f"    SCORE: {score} (expected: 7 - color only)")
        assert score == 7

    def test_goal_all_unique_manual_setup(self):
        """Test All Unique goal with manually constructed board."""
        print("\n" + "="*70)
        print("ALL UNIQUE GOAL MANUAL TEST")
        print("="*70)

        grid = HexGrid()
        goal = GoalAllUnique((0, 1, -1))
        neighbors = grid.get_neighbors(0, 1, -1)

        # Setup: 6 unique colors AND 6 unique patterns (should score 15)
        print("\n  Test 1: 6 unique colors AND 6 unique patterns")
        colors = list(Color)[:6]
        patterns = list(Pattern)[:6]
        for i, pos in enumerate(neighbors):
            grid.set_tile(*pos, Tile(colors[i], patterns[i]))

        print_neighbors_for_goal(grid, goal)
        score = goal.score(grid)
        print(f"    SCORE: {score} (expected: 15)")
        assert score == 15

        # Test unique patterns only
        grid = HexGrid()
        print("\n  Test 2: All BLUE, 6 unique patterns")
        for i, pos in enumerate(neighbors):
            grid.set_tile(*pos, Tile(Color.BLUE, patterns[i]))

        print_neighbors_for_goal(grid, goal)
        score = goal.score(grid)
        print(f"    SCORE: {score} (expected: 10 - pattern only)")
        assert score == 10

    def test_cat_millie_verbose(self):
        """Test Millie (3 touching tiles with her patterns)."""
        print("\n" + "="*70)
        print("CAT MILLIE VERBOSE TEST")
        print("="*70)

        grid = HexGrid()
        cat = CatMillie()
        cat.patterns = (Pattern.FLOWERS, Pattern.DOTS)

        print(f"\n  Millie's patterns: {[p.name for p in cat.patterns]}")

        # Place 3 touching FLOWERS tiles
        print("\n  Test 1: 3 touching FLOWERS tiles")
        grid.set_tile(0, 0, 0, Tile(Color.BLUE, Pattern.FLOWERS))
        grid.set_tile(1, 0, -1, Tile(Color.PINK, Pattern.FLOWERS))
        grid.set_tile(0, 1, -1, Tile(Color.GREEN, Pattern.FLOWERS))

        print(f"    Placed tiles at: (0,0,0), (1,0,-1), (0,1,-1)")
        print(f"    These are neighbors: {(1,0,-1) in grid.get_neighbors(0,0,0)}")

        score = check_cat_condition_verbose(cat, grid)
        print(f"    Expected: {cat.point_value}")
        assert score == cat.point_value

    def test_cat_leo_verbose(self):
        """Test Leo (5 in a line with his patterns)."""
        print("\n" + "="*70)
        print("CAT LEO VERBOSE TEST")
        print("="*70)

        grid = HexGrid()
        cat = CatLeo()
        cat.patterns = (Pattern.DOTS, Pattern.SWIRLS)

        print(f"\n  Leo's patterns: {[p.name for p in cat.patterns]}")

        # Place 5 DOTS in a line (east direction: +1, 0, -1)
        print("\n  Test 1: 5 DOTS in a line (east direction)")
        for i in range(-2, 3):
            grid.set_tile(i, 0, -i, Tile(Color.BLUE, Pattern.DOTS))
            print(f"    Placed DOTS at ({i}, 0, {-i})")

        score = check_cat_condition_verbose(cat, grid)
        print(f"    Expected: {cat.point_value}")
        assert score == cat.point_value

    def test_cat_rumi_verbose(self):
        """Test Rumi (3 in a line with her patterns)."""
        print("\n" + "="*70)
        print("CAT RUMI VERBOSE TEST")
        print("="*70)

        grid = HexGrid()
        cat = CatRumi()
        cat.patterns = (Pattern.LEAVES, Pattern.CLUBS)

        print(f"\n  Rumi's patterns: {[p.name for p in cat.patterns]}")

        # Place 3 LEAVES in a line
        print("\n  Test 1: 3 LEAVES in a line (east direction)")
        for i in range(3):
            grid.set_tile(i, 0, -i, Tile(Color.BLUE, Pattern.LEAVES))
            print(f"    Placed LEAVES at ({i}, 0, {-i})")

        score = check_cat_condition_verbose(cat, grid)
        print(f"    Expected: {cat.point_value}")
        assert score == cat.point_value

    def test_multiple_random_games(self):
        """Run multiple random games and show score distribution."""
        print("\n" + "="*70)
        print("MULTIPLE RANDOM GAMES - SCORE DISTRIBUTION")
        print("="*70)

        scores = []
        goal_scores = []
        cat_scores = []

        for i in range(5):
            game = SimulationMode(BOARD_1)
            game.play_random_game()

            g_score = sum(g.score(game.player.grid) for g in game.goals)
            c_score = sum(c.score(game.player.grid) for c in game.cats)
            total = game.get_final_score()

            scores.append(total)
            goal_scores.append(g_score)
            cat_scores.append(c_score)

            print(f"\n  Game {i+1}: Goals={g_score}, Cats={c_score}, Total={total}")

            # Show which goals/cats scored
            for goal in game.goals:
                s = goal.score(game.player.grid)
                if s > 0:
                    print(f"    - {goal.name}: {s}")
            for cat in game.cats:
                s = cat.score(game.player.grid)
                if s > 0:
                    print(f"    - {cat.name}: {s}")

        print(f"\n  Score range: {min(scores)} - {max(scores)}")
        print(f"  Average: {sum(scores)/len(scores):.1f}")
        print(f"  Goal scores: {goal_scores}")
        print(f"  Cat scores: {cat_scores}")
