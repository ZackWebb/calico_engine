from hex_grid import Color, Pattern

# Goal tile positions - these cannot have regular tiles placed on them
GOAL_POSITIONS = [
    (-2, 1, 1),
    (1, -1, 0), 
    (0, 1, -1),
]

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

TEST_BOARD_ALL_CATS = {
    # Format: (q, r, s): (Color, Pattern)
    # Note: In cube coordinates, q + r + s should always equal 0

    # Leo's condition: 5 DOTS in a line along east direction (1, 0, -1)
    (-2, 0, 2): (Color.BLUE, Pattern.DOTS),
    (-1, 0, 1): (Color.BLUE, Pattern.DOTS),
    (0, 0, 0): (Color.BLUE, Pattern.DOTS),
    (1, 0, -1): (Color.BLUE, Pattern.DOTS),
    (2, 0, -2): (Color.BLUE, Pattern.DOTS),

    # Millie's condition: 3 FLOWERS touching (cluster)
    (0, 1, -1): (Color.PINK, Pattern.FLOWERS),
    (1, 1, -2): (Color.YELLOW, Pattern.FLOWERS),
    (0, 2, -2): (Color.GREEN, Pattern.FLOWERS),

    # Rumi's condition: 3 SWIRLS in a line along northwest direction (0, -1, 1)
    (2, -2, 0): (Color.PURPLE, Pattern.SWIRLS),
    (2, -3, 1): (Color.TEAL, Pattern.SWIRLS),
    (2, -4, 2): (Color.YELLOW, Pattern.SWIRLS),
}