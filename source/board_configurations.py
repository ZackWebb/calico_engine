from hex_grid import Color, Pattern
import random

# Goal tile positions - these cannot have regular tiles placed on them
GOAL_POSITIONS = [
    (-2, 1, 1),
    (1, -1, 0),
    (0, 1, -1),
]

# Board name constants
BOARD_1_NAME = "BOARD_1"  # Teal Board
BOARD_2_NAME = "BOARD_2"  # Yellow Board
BOARD_3_NAME = "BOARD_3"  # Purple Board
BOARD_4_NAME = "BOARD_4"  # Green Board

BOARD_1 = {
    # Teal Board
    # Format: (q, r, s): (Color, Pattern)
    # Note: In cube coordinates, q + r + s should always equal 0
    
    # Top row
    (-1, 4, -3): (Color.YELLOW, Pattern.STRIPES),
    (0, 3, -3): (Color.TEAL, Pattern.SWIRLS),
    (1, 2, -3): (Color.PINK, Pattern.LEAVES),
    (2, 1, -3): (Color.PURPLE, Pattern.CLUBS),
    (3, 0, -3): (Color.YELLOW, Pattern.FLOWERS),
    (4, -1, -3): (Color.GREEN, Pattern.STRIPES),
    
    # Right side (top to bottom)
    (4, -2, -2): (Color.BLUE, Pattern.DOTS),
    (3, -2, -1): (Color.PURPLE, Pattern.SWIRLS),
    (3, -3, 0): (Color.YELLOW, Pattern.LEAVES),
    (2, -3, 1): (Color.GREEN, Pattern.CLUBS),
    (2, -4, 2): (Color.BLUE, Pattern.FLOWERS),
    
    # Bottom row (right to left)
    (1, -4, 3): (Color.TEAL, Pattern.STRIPES),
    (0, -3, 3): (Color.PINK, Pattern.DOTS),
    (-1, -2, 3): (Color.GREEN, Pattern.SWIRLS),
    (-2, -1, 3): (Color.BLUE, Pattern.LEAVES),
    (-3, 0, 3): (Color.PINK, Pattern.FLOWERS),
    (-4, 1, 3): (Color.TEAL, Pattern.CLUBS),
    
    # Left side (bottom to top)
    (-4, 2, 2): (Color.YELLOW, Pattern.DOTS),
    (-4, 3, 1): (Color.PURPLE, Pattern.STRIPES),
    (-3, 3, 0): (Color.TEAL, Pattern.LEAVES),
    (-3, 4, -1): (Color.BLUE, Pattern.CLUBS),
    (-2, 4, -2): (Color.GREEN, Pattern.LEAVES),
}

BOARD_2 = {
    # Yellow Board
    # Format: (q, r, s): (Color, Pattern)
    # Note: In cube coordinates, q + r + s should always equal 0
    
    # Top row
    (-1, 4, -3): (Color.BLUE, Pattern.FLOWERS),
    (0, 3, -3): (Color.YELLOW, Pattern.STRIPES),
    (1, 2, -3): (Color.PURPLE, Pattern.DOTS),
    (2, 1, -3): (Color.BLUE, Pattern.SWIRLS),
    (3, 0, -3): (Color.GREEN, Pattern.LEAVES),
    (4, -1, -3): (Color.PINK, Pattern.CLUBS),
    
    # Right side (top to bottom)
    (4, -2, -2): (Color.TEAL, Pattern.SWIRLS),
    (3, -2, -1): (Color.BLUE, Pattern.STRIPES),
    (3, -3, 0): (Color.GREEN, Pattern.DOTS),
    (2, -3, 1): (Color.PINK, Pattern.SWIRLS),
    (2, -4, 2): (Color.TEAL, Pattern.LEAVES),
    
    # Bottom row (right to left)
    (1, -4, 3): (Color.YELLOW, Pattern.CLUBS),
    (0, -3, 3): (Color.PURPLE, Pattern.FLOWERS),
    (-1, -2, 3): (Color.PINK, Pattern.STRIPES),
    (-2, -1, 3): (Color.BLUE, Pattern.DOTS),
    (-3, 0, 3): (Color.YELLOW, Pattern.SWIRLS),
    (-4, 1, 3): (Color.PURPLE, Pattern.LEAVES),
    
    # Left side (bottom to top)
    (-4, 2, 2): (Color.BLUE, Pattern.CLUBS),
    (-4, 3, 1): (Color.GREEN, Pattern.FLOWERS),
    (-3, 3, 0): (Color.YELLOW, Pattern.DOTS),
    (-3, 4, -1): (Color.PURPLE, Pattern.SWIRLS),
    (-2, 4, -2): (Color.PINK, Pattern.LEAVES),
}

BOARD_3 = {
    # Purple Board
    # Format: (q, r, s): (Color, Pattern)
    # Note: In cube coordinates, q + r + s should always equal 0
    
    # Top row
    (-1, 4, -3): (Color.PINK, Pattern.DOTS),
    (0, 3, -3): (Color.PURPLE, Pattern.FLOWERS),
    (1, 2, -3): (Color.YELLOW, Pattern.LEAVES),
    (2, 1, -3): (Color.TEAL, Pattern.STRIPES),
    (3, 0, -3): (Color.PINK, Pattern.CLUBS),
    (4, -1, -3): (Color.GREEN, Pattern.DOTS),
    
    # Right side (top to bottom)
    (4, -2, -2): (Color.BLUE, Pattern.SWIRLS),
    (3, -2, -1): (Color.TEAL, Pattern.FLOWERS),
    (3, -3, 0): (Color.PINK, Pattern.LEAVES),
    (2, -3, 1): (Color.GREEN, Pattern.STRIPES),
    (2, -4, 2): (Color.BLUE, Pattern.CLUBS),
    
    # Bottom row (right to left)
    (1, -4, 3): (Color.PURPLE, Pattern.DOTS),
    (0, -3, 3): (Color.YELLOW, Pattern.SWIRLS),
    (-1, -2, 3): (Color.GREEN, Pattern.FLOWERS),
    (-2, -1, 3): (Color.BLUE, Pattern.LEAVES),
    (-3, 0, 3): (Color.PURPLE, Pattern.STRIPES),
    (-4, 1, 3): (Color.YELLOW, Pattern.CLUBS),
    
    # Left side (bottom to top)
    (-4, 2, 2): (Color.TEAL, Pattern.DOTS),
    (-4, 3, 1): (Color.PINK, Pattern.SWIRLS),
    (-3, 3, 0): (Color.GREEN, Pattern.LEAVES),
    (-3, 4, -1): (Color.BLUE, Pattern.STRIPES),
    (-2, 4, -2): (Color.TEAL, Pattern.CLUBS),
}

BOARD_4 = {
    # Green Board
    # Format: (q, r, s): (Color, Pattern)
    # Note: In cube coordinates, q + r + s should always equal 0
    
    # Top row
    (-1, 4, -3): (Color.YELLOW, Pattern.SWIRLS),
    (0, 3, -3): (Color.GREEN, Pattern.LEAVES),
    (1, 2, -3): (Color.BLUE, Pattern.STRIPES),
    (2, 1, -3): (Color.PURPLE, Pattern.CLUBS),
    (3, 0, -3): (Color.YELLOW, Pattern.DOTS),
    (4, -1, -3): (Color.TEAL, Pattern.SWIRLS),
    
    # Right side (top to bottom)
    (4, -2, -2): (Color.PINK, Pattern.FLOWERS),
    (3, -2, -1): (Color.PURPLE, Pattern.LEAVES),
    (3, -3, 0): (Color.YELLOW, Pattern.STRIPES),
    (2, -3, 1): (Color.TEAL, Pattern.CLUBS),
    (2, -4, 2): (Color.PINK, Pattern.DOTS),
    
    # Bottom row (right to left)
    (1, -4, 3): (Color.GREEN, Pattern.SWIRLS),
    (0, -3, 3): (Color.BLUE, Pattern.FLOWERS),
    (-1, -2, 3): (Color.TEAL, Pattern.LEAVES),
    (-2, -1, 3): (Color.PINK, Pattern.STRIPES),
    (-3, 0, 3): (Color.GREEN, Pattern.CLUBS),
    (-4, 1, 3): (Color.BLUE, Pattern.DOTS),
    
    # Left side (bottom to top)
    (-4, 2, 2): (Color.PURPLE, Pattern.SWIRLS),
    (-4, 3, 1): (Color.YELLOW, Pattern.FLOWERS),
    (-3, 3, 0): (Color.TEAL, Pattern.STRIPES),
    (-3, 4, -1): (Color.PINK, Pattern.CLUBS),
    (-2, 4, -2): (Color.PURPLE, Pattern.DOTS),
}

# All available boards for random selection
ALL_BOARDS = [
    (BOARD_1, BOARD_1_NAME),
    (BOARD_2, BOARD_2_NAME),
    (BOARD_3, BOARD_3_NAME),
    (BOARD_4, BOARD_4_NAME),
]

# Mapping from config dict to name (for reverse lookup)
BOARD_NAMES = {
    id(BOARD_1): BOARD_1_NAME,
    id(BOARD_2): BOARD_2_NAME,
    id(BOARD_3): BOARD_3_NAME,
    id(BOARD_4): BOARD_4_NAME,
}


def get_random_board():
    """
    Randomly select a board configuration.

    Returns:
        Tuple of (board_config dict, board_name str)
    """
    return random.choice(ALL_BOARDS)


def get_board_name(board_config) -> str:
    """
    Get the name of a board configuration.

    Args:
        board_config: The board configuration dict

    Returns:
        Board name string, or "UNKNOWN" if not recognized
    """
    return BOARD_NAMES.get(id(board_config), "UNKNOWN")