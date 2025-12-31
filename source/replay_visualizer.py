"""
Pygame visualization for replaying recorded MCTS games.
Allows step-by-step analysis of decisions with arrow keys.
"""
import pygame
import numpy as np
import hexy as hx
import os
from typing import Optional, Tuple, List

from game_record import GameRecord, DecisionRecord, TileRecord
from tile import Tile, Color, Pattern
from board_configurations import GOAL_POSITIONS

# Base design dimensions (at scale 1.0)
BASE_WIDTH = 1350
BASE_HEIGHT = 750
BASE_HEX_RADIUS = 30

# Base UI Layout positions (at scale 1.0)
BASE_BOARD_CENTER = (350, 350)
BASE_HAND_POSITION = (670, 550)  # Moved 80px left
BASE_MARKET_POSITION = (620, 50)  # Moved 80px left
BASE_GOAL_INFO_POSITION = (1110, 30)
BASE_STATUS_POSITION = (50, 650)
BASE_CATS_POSITION = (1110, 120)
BASE_CANDIDATES_POSITION = (620, 380)  # Moved 80px left
BASE_ACTION_INFO_POSITION = (620, 150)  # Moved 80px left

# Unique abbreviations for colors and patterns
COLOR_ABBREV = {
    "BLUE": "Bl",
    "GREEN": "Gr",
    "YELLOW": "Yl",
    "PINK": "Pk",
    "PURPLE": "Pr",
    "CYAN": "Cy",
}

PATTERN_ABBREV = {
    "DOTS": "Dt",
    "LEAVES": "Lv",
    "FLOWERS": "Fl",
    "CLUBS": "Cb",
    "STRIPES": "St",
    "SWIRLS": "Sw",
}


def cube_to_rowcol(q: int, r: int, s: int) -> str:
    """
    Convert cube coordinates (q, r, s) to human-readable row/column format.

    Uses a letter for column (A-K) and number for row (1-9).
    The board is oriented with the flat side of hexes on top.

    Mapping:
    - Column (letter): based on q coordinate, offset by r to create diagonal columns
    - Row (number): based on r coordinate
    """
    # For a hex grid with pointy-top orientation:
    # We'll use "offset coordinates" style display
    # Column = q + offset based on row
    # Row = r

    # Convert to offset coordinates (odd-r offset)
    col = q + (r + (r & 1)) // 2
    row = r

    # Map column to letter (centered around 'F' for q=0)
    # Shift so that column 0 at center maps to 'F'
    col_letter = chr(ord('F') + col)

    # Map row to number (centered around 5 for r=0)
    row_num = 5 - row

    return f"{col_letter}{row_num}"


def rowcol_to_display(position: Tuple[int, int, int]) -> str:
    """Convert a (q, r, s) tuple to display string."""
    if position is None:
        return "?"
    q, r, s = position
    return cube_to_rowcol(q, r, s)


class ReplayVisualizer:
    """
    Pygame visualization for replaying recorded MCTS games.
    Step through decisions with arrow keys.
    """

    def __init__(self, game_record: GameRecord, initial_scale: float = 1.0):
        pygame.init()

        self.record = game_record
        self.current_step = 0
        self.show_candidates = True
        self.auto_play = False
        self.auto_play_delay = 1000  # ms between steps

        # Scale factor for the entire UI
        self.scale = initial_scale
        self.is_fullscreen = False
        self.windowed_size = (int(BASE_WIDTH * initial_scale), int(BASE_HEIGHT * initial_scale))

        # Create resizable window
        self.screen = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
        pygame.display.set_caption(f"Calico Replay - Score: {game_record.final_score}")
        self.clock = pygame.time.Clock()
        self.last_auto_step = 0

        # Load images and create scaled versions
        self._base_tile_images = self._load_base_tile_images()
        self._base_goal_images = self._load_base_goal_images()
        self._base_cat_images = self._load_base_cat_images()
        self._base_grey_tile_images = self._load_base_grey_tile_images()
        self._update_scaled_resources()

        # Visual feedback
        self.highlighted_hex: Optional[Tuple[int, int, int]] = None

    def _load_base_tile_images(self):
        """Load tile images from disk at base size."""
        images = {}
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        image_dir = os.path.join(parent_dir, 'images', 'calico_tiles')

        pattern_to_number = {
            Pattern.DOTS: 1,
            Pattern.LEAVES: 2,
            Pattern.FLOWERS: 3,
            Pattern.CLUBS: 4,
            Pattern.STRIPES: 5,
            Pattern.SWIRLS: 6
        }

        for color in Color:
            for pattern in Pattern:
                key = (color, pattern)
                filename = f"{color.name.lower()}_{pattern_to_number[pattern]}.png"
                filepath = os.path.join(image_dir, filename)
                if os.path.exists(filepath):
                    images[key] = pygame.image.load(filepath)
        return images

    def _load_base_goal_images(self):
        """Load goal tile images from disk at base size."""
        images = {}
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        image_dir = os.path.join(parent_dir, 'images', 'goal_tiles')

        goal_files = {
            (-2, 1, 1): 'aaa-bbb.png',
            (1, -1, 0): 'aa-bb-cc.png',
            (0, 1, -1): 'all_unique.png',
        }

        for pos, filename in goal_files.items():
            filepath = os.path.join(image_dir, filename)
            if os.path.exists(filepath):
                images[pos] = pygame.image.load(filepath)
        return images

    def _load_base_cat_images(self):
        """Load cat images from disk at base size."""
        images = {}
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        image_dir = os.path.join(parent_dir, 'images', 'cats')

        cat_files = ['leo.png', 'millie.png', 'rumi.png']
        for filename in cat_files:
            cat_name = filename.replace('.png', '').capitalize()
            filepath = os.path.join(image_dir, filename)
            if os.path.exists(filepath):
                images[cat_name] = pygame.image.load(filepath)
        return images

    def _load_base_grey_tile_images(self):
        """Load grey pattern tile images from disk at base size."""
        images = {}
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        image_dir = os.path.join(parent_dir, 'images', 'calico_grey_tiles')

        pattern_to_number = {
            Pattern.DOTS: 1,
            Pattern.LEAVES: 2,
            Pattern.FLOWERS: 3,
            Pattern.CLUBS: 4,
            Pattern.STRIPES: 5,
            Pattern.SWIRLS: 6
        }

        for pattern, num in pattern_to_number.items():
            filename = f"black_{num}.png"
            filepath = os.path.join(image_dir, filename)
            if os.path.exists(filepath):
                images[pattern] = pygame.image.load(filepath)
        return images

    def _update_scaled_resources(self):
        """Update all scaled resources based on current scale factor."""
        # Scaled dimensions
        self.hex_radius = int(BASE_HEX_RADIUS * self.scale)
        self.tile_size = self.hex_radius * 2

        # Scaled positions
        self.center = np.array([int(BASE_BOARD_CENTER[0] * self.scale),
                                int(BASE_BOARD_CENTER[1] * self.scale)])
        self.hand_position = (int(BASE_HAND_POSITION[0] * self.scale),
                              int(BASE_HAND_POSITION[1] * self.scale))
        self.market_position = (int(BASE_MARKET_POSITION[0] * self.scale),
                                int(BASE_MARKET_POSITION[1] * self.scale))
        self.status_position = (int(BASE_STATUS_POSITION[0] * self.scale),
                                int(BASE_STATUS_POSITION[1] * self.scale))
        self.cats_position = (int(BASE_CATS_POSITION[0] * self.scale),
                              int(BASE_CATS_POSITION[1] * self.scale))
        self.goal_info_position = (int(BASE_GOAL_INFO_POSITION[0] * self.scale),
                                   int(BASE_GOAL_INFO_POSITION[1] * self.scale))
        self.candidates_position = (int(BASE_CANDIDATES_POSITION[0] * self.scale),
                                    int(BASE_CANDIDATES_POSITION[1] * self.scale))
        self.action_info_position = (int(BASE_ACTION_INFO_POSITION[0] * self.scale),
                                     int(BASE_ACTION_INFO_POSITION[1] * self.scale))

        # Scaled fonts
        self.font = pygame.font.Font(None, max(16, int(24 * self.scale)))
        self.large_font = pygame.font.Font(None, max(20, int(32 * self.scale)))
        self.small_font = pygame.font.Font(None, max(14, int(20 * self.scale)))

        # Scaled tile images
        self.tile_images = {}
        for key, base_image in self._base_tile_images.items():
            self.tile_images[key] = pygame.transform.scale(
                base_image, (self.tile_size, self.tile_size)
            )

        # Scaled goal images
        self.goal_images = {}
        for key, base_image in self._base_goal_images.items():
            self.goal_images[key] = pygame.transform.scale(
                base_image, (self.tile_size, self.tile_size)
            )

        # Scaled cat images
        self.cat_images = {}
        self.cat_width = int(180 * self.scale)
        self.cat_height = int(112 * self.scale)
        for key, base_image in self._base_cat_images.items():
            self.cat_images[key] = pygame.transform.scale(
                base_image, (self.cat_width, self.cat_height)
            )

        # Scaled grey tile images for cat patterns
        self.grey_tile_images = {}
        self.grey_tile_width = int(70 * self.scale)
        self.grey_tile_height = int(80 * self.scale)
        for key, base_image in self._base_grey_tile_images.items():
            self.grey_tile_images[key] = pygame.transform.scale(
                base_image, (self.grey_tile_width, self.grey_tile_height)
            )

    def _toggle_fullscreen(self):
        """Toggle between fullscreen and windowed mode."""
        self.is_fullscreen = not self.is_fullscreen

        if self.is_fullscreen:
            display_info = pygame.display.Info()
            self.screen = pygame.display.set_mode(
                (display_info.current_w, display_info.current_h),
                pygame.FULLSCREEN
            )
            scale_x = display_info.current_w / BASE_WIDTH
            scale_y = display_info.current_h / BASE_HEIGHT
            self.scale = min(scale_x, scale_y)
        else:
            self.screen = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
            self.scale = self.windowed_size[0] / BASE_WIDTH

        self._update_scaled_resources()

    def _handle_resize(self, new_size: Tuple[int, int]):
        """Handle window resize event."""
        if not self.is_fullscreen:
            self.windowed_size = new_size
            self.screen = pygame.display.set_mode(new_size, pygame.RESIZABLE)
            scale_x = new_size[0] / BASE_WIDTH
            scale_y = new_size[1] / BASE_HEIGHT
            self.scale = min(scale_x, scale_y)
            self._update_scaled_resources()

    def _adjust_scale(self, delta: float):
        """Adjust the scale factor."""
        new_scale = max(0.5, min(3.0, self.scale + delta))
        if new_scale != self.scale:
            self.scale = new_scale
            if not self.is_fullscreen:
                self.windowed_size = (int(BASE_WIDTH * self.scale), int(BASE_HEIGHT * self.scale))
                self.screen = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
            self._update_scaled_resources()

    def get_current_decision(self) -> Optional[DecisionRecord]:
        """Get the current decision record."""
        if 0 <= self.current_step < len(self.record.decisions):
            return self.record.decisions[self.current_step]
        return None

    def step_forward(self):
        """Move to next decision."""
        if self.current_step < len(self.record.decisions) - 1:
            self.current_step += 1

    def step_backward(self):
        """Move to previous decision."""
        if self.current_step > 0:
            self.current_step -= 1

    def jump_to_start(self):
        """Jump to first decision."""
        self.current_step = 0

    def jump_to_end(self):
        """Jump to last decision."""
        self.current_step = len(self.record.decisions) - 1

    def handle_events(self) -> bool:
        """Handle pygame events. Returns False to quit."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.VIDEORESIZE:
                self._handle_resize(event.size)

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4:  # Mouse wheel up
                    self._adjust_scale(0.1)
                elif event.button == 5:  # Mouse wheel down
                    self._adjust_scale(-0.1)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.is_fullscreen:
                        self._toggle_fullscreen()
                    else:
                        return False
                elif event.key == pygame.K_F11:
                    self._toggle_fullscreen()
                elif event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                    self._adjust_scale(0.1)
                elif event.key == pygame.K_MINUS:
                    self._adjust_scale(-0.1)
                elif event.key == pygame.K_0:
                    self.scale = 1.0
                    if not self.is_fullscreen:
                        self.windowed_size = (BASE_WIDTH, BASE_HEIGHT)
                        self.screen = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
                    self._update_scaled_resources()
                # Navigation
                elif event.key == pygame.K_RIGHT:
                    self.step_forward()
                elif event.key == pygame.K_LEFT:
                    self.step_backward()
                elif event.key == pygame.K_HOME:
                    self.jump_to_start()
                elif event.key == pygame.K_END:
                    self.jump_to_end()
                # Toggle candidates display
                elif event.key == pygame.K_c:
                    self.show_candidates = not self.show_candidates
                # Toggle auto-play
                elif event.key == pygame.K_SPACE:
                    self.auto_play = not self.auto_play
                    self.last_auto_step = pygame.time.get_ticks()
                # Speed controls
                elif event.key == pygame.K_UP:
                    self.auto_play_delay = max(100, self.auto_play_delay - 200)
                elif event.key == pygame.K_DOWN:
                    self.auto_play_delay = min(3000, self.auto_play_delay + 200)

        # Auto-play logic
        if self.auto_play:
            now = pygame.time.get_ticks()
            if now - self.last_auto_step >= self.auto_play_delay:
                if self.current_step < len(self.record.decisions) - 1:
                    self.step_forward()
                    self.last_auto_step = now
                else:
                    self.auto_play = False

        return True

    def _tile_record_to_key(self, tile_record: TileRecord) -> Tuple[Color, Pattern]:
        """Convert TileRecord to (Color, Pattern) tuple for image lookup."""
        return (Color[tile_record.color], Pattern[tile_record.pattern])

    def draw(self):
        """Render the replay view."""
        self.screen.fill((245, 235, 220))  # Warm beige background

        decision = self.get_current_decision()
        if decision:
            self._draw_board(decision)
            self._draw_hand(decision)
            self._draw_market(decision)
            self._draw_action_info(decision)
            if self.show_candidates:
                self._draw_candidates(decision)

        self._draw_goal_info()
        self._draw_cats()
        self._draw_status()
        self._draw_navigation_info()
        self._draw_controls_hint()

        pygame.display.update()

    def _draw_board(self, decision: DecisionRecord):
        """Draw the hex grid at current state."""
        # Get all hex positions from the board snapshot
        board_tiles = decision.board_tiles

        # Define the standard hex grid positions
        # This should match your board configuration
        all_positions = self._get_all_board_positions()

        for hex_coord in all_positions:
            hex_coord_array = np.array([hex_coord])
            pixel = hx.cube_to_pixel(hex_coord_array, self.hex_radius)[0]
            pos = pixel + self.center

            # Check if there's a tile at this position
            key_str = f"{hex_coord[0]},{hex_coord[1]},{hex_coord[2]}"
            if key_str in board_tiles:
                tile_record = board_tiles[key_str]
                tile_key = self._tile_record_to_key(tile_record)
                if tile_key in self.tile_images:
                    self.screen.blit(
                        self.tile_images[tile_key],
                        pos - np.array([self.hex_radius, self.hex_radius])
                    )
            else:
                # Draw empty hex
                color = (180, 180, 180)
                fill_color = None
                # Highlight the action position for place_tile or place_and_choose actions
                if (decision.action_type in ("place_tile", "place_and_choose") and
                    decision.action_position and
                    tuple(decision.action_position) == hex_coord):
                    color = (100, 200, 100)  # Green highlight
                    fill_color = (200, 255, 200)  # Light green fill

                # Draw filled circle for highlighted positions
                if fill_color:
                    pygame.draw.circle(self.screen, fill_color, pos.astype(int), self.hex_radius - 2)

                pygame.draw.circle(self.screen, color, pos.astype(int), self.hex_radius, 2)

                # Add row/column label to empty hexes
                label = rowcol_to_display(hex_coord)
                label_surface = self.small_font.render(label, True, (120, 120, 120))
                label_rect = label_surface.get_rect(center=pos.astype(int))
                self.screen.blit(label_surface, label_rect)

        # Draw goal tiles
        self._draw_goal_tiles()

    def _get_all_board_positions(self) -> List[Tuple[int, int, int]]:
        """Get all valid board positions (including goals)."""
        # Standard positions from the game board
        positions = []

        # Inner ring and center
        for q in range(-3, 4):
            for r in range(-3, 4):
                s = -q - r
                if abs(q) <= 3 and abs(r) <= 3 and abs(s) <= 3:
                    positions.append((q, r, s))

        # Edge positions (from BOARD_1 configuration)
        edge_positions = [
            (-1, 4, -3), (-2, 4, -2), (-3, 4, -1),
            (4, -1, -3), (4, -2, -2),
            (-4, 3, 1), (-4, 2, 2), (-4, 1, 3),
            (2, -4, 2), (1, -4, 3)
        ]
        positions.extend(edge_positions)

        return positions

    def _draw_goal_tiles(self):
        """Draw goal tiles using images."""
        goal_colors = {
            (-2, 1, 1): (255, 200, 100),
            (1, -1, 0): (100, 200, 255),
            (0, 1, -1): (200, 100, 255),
        }
        goal_labels = {
            (-2, 1, 1): "3-3",
            (1, -1, 0): "2-2-2",
            (0, 1, -1): "6 Uniq",
        }

        for goal in self.record.goals:
            pos_tuple = tuple(goal.position)
            hex_coord_array = np.array([pos_tuple])
            pixel = hx.cube_to_pixel(hex_coord_array, self.hex_radius)[0]
            pos = pixel + self.center

            if pos_tuple in self.goal_images:
                self.screen.blit(
                    self.goal_images[pos_tuple],
                    pos - np.array([self.hex_radius, self.hex_radius])
                )
            else:
                color = goal_colors.get(pos_tuple, (200, 200, 100))
                pygame.draw.circle(self.screen, color, pos.astype(int), self.hex_radius - 2)
                pygame.draw.circle(self.screen, (100, 100, 100), pos.astype(int), self.hex_radius, 2)

                label = goal_labels.get(pos_tuple, "?")
                text = self.font.render(label, True, (0, 0, 0))
                text_rect = text.get_rect(center=pos.astype(int))
                self.screen.blit(text, text_rect)

    def _draw_hand(self, decision: DecisionRecord):
        """Draw player's hand tiles at current state."""
        base_x, base_y = self.hand_position
        spacing = int(10 * self.scale)

        label = self.font.render("Hand:", True, (0, 0, 0))
        self.screen.blit(label, (base_x, base_y - int(25 * self.scale)))

        # Highlight if this is a place_tile or place_and_choose decision
        if decision.phase in ("PLACE_TILE", "PLACE_AND_CHOOSE"):
            rect_width = len(decision.hand_tiles) * (self.tile_size + spacing) + int(10 * self.scale)
            rect_height = self.tile_size + int(40 * self.scale)
            pygame.draw.rect(self.screen, (200, 230, 200),
                           (base_x - int(5 * self.scale), base_y - int(30 * self.scale),
                            rect_width, rect_height), border_radius=int(5 * self.scale))

        for i, tile_record in enumerate(decision.hand_tiles):
            x = base_x + i * (self.tile_size + spacing)
            tile_key = self._tile_record_to_key(tile_record)
            if tile_key in self.tile_images:
                self.screen.blit(self.tile_images[tile_key], (x, base_y))

            # Highlight selected tile for place_tile or place_and_choose actions
            if decision.action_type in ("place_tile", "place_and_choose") and decision.action_hand_index == i:
                border = int(3 * self.scale)
                pygame.draw.rect(self.screen, (0, 200, 0),
                               (x - border, base_y - border,
                                self.tile_size + border * 2, self.tile_size + border * 2), border)

    def _draw_market(self, decision: DecisionRecord):
        """Draw market tiles at current state."""
        base_x, base_y = self.market_position
        spacing = int(10 * self.scale)

        label = self.font.render("Market:", True, (0, 0, 0))
        self.screen.blit(label, (base_x, base_y - int(25 * self.scale)))

        # Highlight if this is a choose_market or place_and_choose decision (with market choice)
        should_highlight = (
            decision.phase == "CHOOSE_MARKET" or
            (decision.phase == "PLACE_AND_CHOOSE" and decision.action_market_index is not None)
        )
        if should_highlight:
            rect_width = len(decision.market_tiles) * (self.tile_size + spacing) + int(10 * self.scale)
            rect_height = self.tile_size + int(40 * self.scale)
            pygame.draw.rect(self.screen, (200, 230, 200),
                           (base_x - int(5 * self.scale), base_y - int(30 * self.scale),
                            rect_width, rect_height), border_radius=int(5 * self.scale))

        for i, tile_record in enumerate(decision.market_tiles):
            x = base_x + i * (self.tile_size + spacing)
            tile_key = self._tile_record_to_key(tile_record)
            if tile_key in self.tile_images:
                self.screen.blit(self.tile_images[tile_key], (x, base_y))

            # Highlight selected market tile for choose_market or place_and_choose actions
            is_selected = (
                (decision.action_type == "choose_market" and decision.action_market_index == i) or
                (decision.action_type == "place_and_choose" and decision.action_market_index == i)
            )
            if is_selected:
                border = int(3 * self.scale)
                pygame.draw.rect(self.screen, (0, 200, 0),
                               (x - border, base_y - border,
                                self.tile_size + border * 2, self.tile_size + border * 2), border)

    def _draw_action_info(self, decision: DecisionRecord):
        """Draw info about the action taken."""
        x, y = self.action_info_position

        # Action header
        label = self.large_font.render("Action Taken:", True, (0, 100, 0))
        self.screen.blit(label, (x, y))

        y += int(30 * self.scale)

        if decision.action_type == "place_and_choose":
            # Combined action: show both placement and market choice
            hand_tile = decision.hand_tiles[decision.action_hand_index]
            text = f"Place {hand_tile.color} {hand_tile.pattern}"
            surface = self.font.render(text, True, (0, 0, 0))
            self.screen.blit(surface, (x, y))

            y += int(22 * self.scale)
            pos_display = rowcol_to_display(tuple(decision.action_position))
            pos_text = f"at position {pos_display}"
            pos_surface = self.font.render(pos_text, True, (80, 80, 80))
            self.screen.blit(pos_surface, (x, y))

            y += int(22 * self.scale)
            if decision.action_market_index is not None:
                market_tile = decision.market_tiles[decision.action_market_index]
                market_text = f"+ Take {market_tile.color} {market_tile.pattern}"
                market_surface = self.font.render(market_text, True, (0, 0, 0))
                self.screen.blit(market_surface, (x, y))

                y += int(22 * self.scale)
                idx_text = f"from market position {decision.action_market_index + 1}"
                idx_surface = self.font.render(idx_text, True, (80, 80, 80))
                self.screen.blit(idx_surface, (x, y))
            else:
                final_text = "(Final turn - no market choice)"
                final_surface = self.font.render(final_text, True, (100, 100, 100))
                self.screen.blit(final_surface, (x, y))

        elif decision.action_type == "place_tile":
            hand_tile = decision.hand_tiles[decision.action_hand_index]
            text = f"Place {hand_tile.color} {hand_tile.pattern}"
            surface = self.font.render(text, True, (0, 0, 0))
            self.screen.blit(surface, (x, y))

            y += int(22 * self.scale)
            # Convert position to human-readable format
            pos_display = rowcol_to_display(tuple(decision.action_position))
            pos_text = f"at position {pos_display}"
            pos_surface = self.font.render(pos_text, True, (80, 80, 80))
            self.screen.blit(pos_surface, (x, y))
        else:
            # choose_market
            market_tile = decision.market_tiles[decision.action_market_index]
            text = f"Take {market_tile.color} {market_tile.pattern}"
            surface = self.font.render(text, True, (0, 0, 0))
            self.screen.blit(surface, (x, y))

            y += int(22 * self.scale)
            idx_text = f"from market position {decision.action_market_index + 1}"
            idx_surface = self.font.render(idx_text, True, (80, 80, 80))
            self.screen.blit(idx_surface, (x, y))

    def _tile_abbrev(self, tile_record: TileRecord) -> str:
        """Get abbreviated tile description using unique abbreviations."""
        color_abbr = COLOR_ABBREV.get(tile_record.color, tile_record.color[:2])
        pattern_abbr = PATTERN_ABBREV.get(tile_record.pattern, tile_record.pattern[:2])
        return f"{color_abbr}{pattern_abbr}"

    def _draw_candidates(self, decision: DecisionRecord):
        """Draw MCTS candidate moves."""
        x, y = self.candidates_position

        # Header
        label = self.large_font.render("MCTS Candidates:", True, (100, 0, 100))
        self.screen.blit(label, (x, y))
        y += int(25 * self.scale)

        # Show top candidates
        for i, candidate in enumerate(decision.candidates[:5]):
            # Highlight chosen action
            is_chosen = (
                candidate.action_type == decision.action_type and
                candidate.position == (tuple(decision.action_position) if decision.action_position else None) and
                candidate.hand_index == decision.action_hand_index and
                candidate.market_index == decision.action_market_index
            )

            if is_chosen:
                marker = "*"
                color = (0, 150, 0)
            else:
                marker = " "
                color = (80, 80, 80)

            if candidate.action_type == "place_and_choose":
                # Combined action: show tile, position, and market choice with abbreviations
                pos_display = rowcol_to_display(candidate.position)
                hand_tile = decision.hand_tiles[candidate.hand_index]
                tile_abbr = self._tile_abbrev(hand_tile)
                if candidate.market_index is not None:
                    market_tile = decision.market_tiles[candidate.market_index]
                    market_abbr = self._tile_abbrev(market_tile)
                    text = f"{marker}{i+1}. {tile_abbr}@{pos_display} +{market_abbr}"
                else:
                    text = f"{marker}{i+1}. {tile_abbr}@{pos_display} (final)"
            elif candidate.action_type == "place_tile":
                # Convert position to human-readable format
                pos_display = rowcol_to_display(candidate.position)
                # Show which tile from hand is being placed
                hand_tile = decision.hand_tiles[candidate.hand_index]
                tile_abbr = self._tile_abbrev(hand_tile)
                text = f"{marker}{i+1}. {tile_abbr}@{pos_display}"
            else:
                market_tile = decision.market_tiles[candidate.market_index]
                market_abbr = self._tile_abbrev(market_tile)
                text = f"{marker}{i+1}. take {market_abbr}"

            text_surface = self.font.render(text, True, color)
            self.screen.blit(text_surface, (x, y))

            # Stats - position adjusted for new layout
            stats_text = f"v={candidate.visits} avg={candidate.avg_score:.1f}"
            stats_surface = self.small_font.render(stats_text, True, (120, 120, 120))
            self.screen.blit(stats_surface, (x + int(200 * self.scale), y + int(3 * self.scale)))

            y += int(22 * self.scale)

        # Add abbreviation legend below candidates
        y += int(10 * self.scale)
        legend_text = "Colors: Bl Gr Yl Pk Pr Cy | Patterns: Dt Lv Fl Cb St Sw"
        legend_surface = self.small_font.render(legend_text, True, (140, 140, 140))
        self.screen.blit(legend_surface, (x, y))

    def _draw_goal_info(self):
        """Draw goal tile scoring info."""
        x, y = self.goal_info_position

        goal_label = self.font.render("Goals:", True, (0, 0, 0))
        self.screen.blit(goal_label, (x, y))

        goal_info = [
            ("3-3", "8/13"),
            ("2-2-2", "7/11"),
            ("Unique", "10/15"),
        ]
        for i, (name, pts) in enumerate(goal_info):
            text = f"{name}: {pts}"
            text_surface = self.font.render(text, True, (80, 80, 80))
            self.screen.blit(text_surface, (x, y + int(20 * self.scale) + i * int(18 * self.scale)))

    def _draw_cats(self):
        """Draw cat scoring objectives using images."""
        x, y = self.cats_position
        cat_spacing = int(60 * self.scale)
        tile_offset_y = self.cat_height - int(20 * self.scale)
        tile1_offset_x = int(20 * self.scale)
        tile2_offset_x = int(92 * self.scale)

        for i, cat in enumerate(self.record.cats):
            cat_y = y + i * (self.cat_height + cat_spacing)

            if cat.name in self.cat_images:
                self.screen.blit(self.cat_images[cat.name], (x, cat_y))

                if len(cat.patterns) >= 2:
                    pattern1 = Pattern[cat.patterns[0]]
                    pattern2 = Pattern[cat.patterns[1]]

                    if pattern1 in self.grey_tile_images:
                        self.screen.blit(
                            self.grey_tile_images[pattern1],
                            (x + tile1_offset_x, cat_y + tile_offset_y)
                        )
                    if pattern2 in self.grey_tile_images:
                        self.screen.blit(
                            self.grey_tile_images[pattern2],
                            (x + tile2_offset_x, cat_y + tile_offset_y)
                        )
            else:
                text = f"{cat.name} ({cat.point_value}pts):"
                text_surface = self.font.render(text, True, (0, 0, 0))
                self.screen.blit(text_surface, (x, cat_y))

    def _draw_status(self):
        """Draw status message."""
        x, y = self.status_position
        decision = self.get_current_decision()

        if decision:
            # Step info
            step_text = f"Step {self.current_step + 1} / {len(self.record.decisions)}"
            step_surface = self.large_font.render(step_text, True, (0, 0, 150))
            self.screen.blit(step_surface, (x, y))

            # Turn and phase
            turn_text = f"Turn {decision.turn_number} - {decision.phase}"
            turn_surface = self.font.render(turn_text, True, (80, 80, 80))
            self.screen.blit(turn_surface, (x, y + int(30 * self.scale)))

            # Tiles remaining
            remaining_text = f"Tiles remaining: {decision.tiles_remaining}"
            remaining_surface = self.font.render(remaining_text, True, (80, 80, 80))
            self.screen.blit(remaining_surface, (x, y + int(50 * self.scale)))

    def _draw_navigation_info(self):
        """Draw navigation state."""
        x = int(50 * self.scale)
        y = int(20 * self.scale)
        line_height = int(22 * self.scale)

        # Final score
        score_text = f"Final Score: {self.record.final_score}"
        score_surface = self.large_font.render(score_text, True, (0, 100, 0))
        self.screen.blit(score_surface, (x, y))

        y += line_height + int(5 * self.scale)

        # Score breakdown
        breakdown = self.record.score_breakdown
        cat_scores = breakdown.get('cats', {})
        goal_scores = breakdown.get('goals', {})
        button_info = breakdown.get('buttons', {})

        cats_total = sum(cat_scores.values())
        goals_total = sum(goal_scores.values())
        button_score = button_info.get('button_score', 0)
        rainbow = button_info.get('rainbow_score', 0)

        breakdown_text = f"Cats: {cats_total} | Goals: {goals_total} | Buttons: {button_score}"
        if rainbow > 0:
            breakdown_text += f" (+{rainbow} rainbow)"
        breakdown_surface = self.font.render(breakdown_text, True, (80, 80, 80))
        self.screen.blit(breakdown_surface, (x, y))

        y += line_height

        # Auto-play status
        if self.auto_play:
            auto_text = f"Auto-playing ({self.auto_play_delay}ms)"
            auto_surface = self.font.render(auto_text, True, (200, 100, 0))
            self.screen.blit(auto_surface, (x, y))

    def _draw_controls_hint(self):
        """Draw keyboard controls hint."""
        screen_width = self.screen.get_width()
        screen_height = self.screen.get_height()

        hints = [
            "Left/Right: Step | Home/End: Jump | Space: Auto-play | Up/Down: Speed",
            "C: Toggle candidates | F11: Fullscreen | +/-: Scale | Esc: Quit"
        ]

        for i, hint_text in enumerate(hints):
            hint_surface = self.small_font.render(hint_text, True, (120, 120, 120))
            hint_rect = hint_surface.get_rect()
            hint_rect.bottomright = (screen_width - int(10 * self.scale),
                                     screen_height - int(10 * self.scale) - i * int(18 * self.scale))
            self.screen.blit(hint_surface, hint_rect)

    def run(self):
        """Main replay loop."""
        running = True
        while running:
            running = self.handle_events()
            self.draw()
            self.clock.tick(60)

        pygame.quit()
