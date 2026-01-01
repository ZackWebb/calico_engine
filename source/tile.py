from enum import Enum

class Color(Enum):
    PINK = 1
    BLUE = 2
    GREEN = 3
    YELLOW = 4
    PURPLE = 5
    TEAL = 6

class Pattern(Enum):
    DOTS = 1
    STRIPES = 2
    FLOWERS = 3
    LEAVES = 4
    CLUBS = 5
    SWIRLS = 6

class Tile:
    __slots__ = ('color', 'pattern')

    def __init__(self, color: Color, pattern: Pattern):
        self.color = color
        self.pattern = pattern

    def __repr__(self):
        return f"Tile({self.color.name}, {self.pattern.name})"