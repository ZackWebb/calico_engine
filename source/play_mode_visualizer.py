import pygame
import numpy as np
import hexy as hx
import os
from typing import Optional, Tuple

from play_mode import PlayMode
from game_state import TurnPhase
from tile import Color, Pattern
from board_configurations import GOAL_POSITIONS

# Base design dimensions (at scale 1.0)
BASE_WIDTH = 1000
BASE_HEIGHT = 700
BASE_HEX_RADIUS = 30

# Base UI Layout positions (at scale 1.0)
BASE_BOARD_CENTER = (350, 350)
BASE_HAND_POSITION = (750, 550)
BASE_MARKET_POSITION = (700, 50)
BASE_GOAL_INFO_POSITION = (960, 30)  # Goal info right of market, vertically aligned
BASE_STATUS_POSITION = (50, 650)
BASE_CATS_POSITION = (960, 120)  # Aligned with market


class PlayModeVisualizer:
    """
    Pygame visualization for PlayMode.
    Handles rendering and user input; game logic in PlayMode.
    Supports window resizing and fullscreen mode.
    """

    def __init__(self, play_mode: PlayMode, initial_scale: float = 1.0):
        pygame.init()

        # Scale factor for the entire UI
        self.scale = initial_scale
        self.is_fullscreen = False
        self.windowed_size = (int(BASE_WIDTH * initial_scale), int(BASE_HEIGHT * initial_scale))

        # Create resizable window
        self.screen = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
        pygame.display.set_caption("Calico - Play Mode (F11: Fullscreen, +/-: Scale)")
        self.clock = pygame.time.Clock()

        self.game = play_mode
        self.game.set_state_change_callback(self._on_game_state_change)

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

        # Map goal positions to image filenames
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

        # Map pattern enum to file number
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

        # Scaled fonts
        self.font = pygame.font.Font(None, max(16, int(24 * self.scale)))
        self.large_font = pygame.font.Font(None, max(20, int(32 * self.scale)))

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

        # Scaled cat images - each cat image is approximately 265x165 pixels
        # Scale to fit nicely in UI (target ~180x112 at scale 1.0)
        self.cat_images = {}
        self.cat_width = int(180 * self.scale)
        self.cat_height = int(112 * self.scale)
        for key, base_image in self._base_cat_images.items():
            self.cat_images[key] = pygame.transform.scale(
                base_image, (self.cat_width, self.cat_height)
            )

        # Scaled grey tile images for cat patterns
        # Original grey tiles are 120x139, scale to fit cat cutouts
        # Base size ~60x69 at scale 1.0 (25% larger than original 48x55)
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
            # Get display info for fullscreen
            display_info = pygame.display.Info()
            self.screen = pygame.display.set_mode(
                (display_info.current_w, display_info.current_h),
                pygame.FULLSCREEN
            )
            # Calculate scale to fit screen while maintaining aspect ratio
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
            # Calculate new scale based on window size
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

    def _on_game_state_change(self):
        """Callback when game state changes."""
        pass

    def handle_events(self) -> bool:
        """Handle pygame events. Returns False to quit."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.VIDEORESIZE:
                self._handle_resize(event.size)

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button
                    self._handle_click(event.pos)
                elif event.button == 4:  # Mouse wheel up
                    self._adjust_scale(0.1)
                elif event.button == 5:  # Mouse wheel down
                    self._adjust_scale(-0.1)

            if event.type == pygame.MOUSEMOTION:
                self._handle_hover(event.pos)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.is_fullscreen:
                        self._toggle_fullscreen()
                    else:
                        self.game.deselect_hand_tile()
                elif event.key == pygame.K_F11:
                    self._toggle_fullscreen()
                elif event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                    self._adjust_scale(0.1)
                elif event.key == pygame.K_MINUS:
                    self._adjust_scale(-0.1)
                elif event.key == pygame.K_0:
                    # Reset to default scale
                    self.scale = 1.0
                    if not self.is_fullscreen:
                        self.windowed_size = (BASE_WIDTH, BASE_HEIGHT)
                        self.screen = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
                    self._update_scaled_resources()

        return True

    def _handle_click(self, pos: Tuple[int, int]):
        """Handle mouse click at screen position."""
        # Check if clicked on hand tile
        hand_idx = self._get_hand_tile_at_pos(pos)
        if hand_idx is not None:
            self.game.select_hand_tile(hand_idx)
            return

        # Check if clicked on market tile
        market_idx = self._get_market_tile_at_pos(pos)
        if market_idx is not None:
            self.game.try_choose_market_tile(market_idx)
            return

        # Check if clicked on hex grid
        hex_coord = self._screen_to_hex(pos)
        if hex_coord and hex_coord in self.game.player.grid.grid:
            self.game.try_place_at_position(*hex_coord)

    def _handle_hover(self, pos: Tuple[int, int]):
        """Update hover states for visual feedback."""
        hex_coord = self._screen_to_hex(pos)
        if hex_coord and hex_coord in self.game.player.grid.grid:
            if self.game.player.grid.is_position_empty(*hex_coord):
                self.highlighted_hex = hex_coord
            else:
                self.highlighted_hex = None
        else:
            self.highlighted_hex = None

    def _screen_to_hex(self, pos: Tuple[int, int]) -> Optional[Tuple[int, int, int]]:
        """Convert screen position to hex cube coordinates."""
        mouse_pos = np.array([pos]) - self.center
        cube_coord = hx.pixel_to_cube(mouse_pos, self.hex_radius)[0]
        return tuple(map(int, cube_coord))

    def _get_hand_tile_at_pos(self, pos: Tuple[int, int]) -> Optional[int]:
        """Check if pos is over a hand tile, return index."""
        x, y = pos
        base_x, base_y = self.hand_position
        spacing = int(10 * self.scale)
        for i in range(len(self.game.player.tiles)):
            tile_x = base_x + i * (self.tile_size + spacing)
            if tile_x <= x <= tile_x + self.tile_size:
                if base_y <= y <= base_y + self.tile_size:
                    return i
        return None

    def _get_market_tile_at_pos(self, pos: Tuple[int, int]) -> Optional[int]:
        """Check if pos is over a market tile, return index."""
        x, y = pos
        base_x, base_y = self.market_position
        spacing = int(10 * self.scale)
        for i in range(len(self.game.market.tiles)):
            tile_x = base_x + i * (self.tile_size + spacing)
            if tile_x <= x <= tile_x + self.tile_size:
                if base_y <= y <= base_y + self.tile_size:
                    return i
        return None

    def draw(self):
        """Render the game."""
        self.screen.fill((245, 235, 220))  # Warm beige background

        self._draw_board()
        self._draw_hand()
        self._draw_market()
        self._draw_goal_info()
        self._draw_cats()
        self._draw_status()
        self._draw_turn_info()
        self._draw_controls_hint()

        pygame.display.update()

    def _draw_board(self):
        """Draw the hex grid."""
        # Draw regular tiles
        for hex_coord, tile in self.game.player.grid.grid.items():
            hex_coord_array = np.array([hex_coord])
            pixel = hx.cube_to_pixel(hex_coord_array, self.hex_radius)[0]
            pos = pixel + self.center

            if tile:
                key = (tile.color, tile.pattern)
                if key in self.tile_images:
                    self.screen.blit(
                        self.tile_images[key],
                        pos - np.array([self.hex_radius, self.hex_radius])
                    )
            else:
                # Draw empty hex
                color = (180, 180, 180)
                if hex_coord == self.highlighted_hex and self.game.selected_hand_tile is not None:
                    color = (100, 200, 100)  # Green highlight for valid placement
                pygame.draw.circle(self.screen, color, pos.astype(int), self.hex_radius, 2)

        # Draw goal tiles
        self._draw_goal_tiles()

    def _draw_goal_tiles(self):
        """Draw goal tiles using images."""
        # Fallback colors and labels if images not available
        goal_colors = {
            (-2, 1, 1): (255, 200, 100),   # AAA-BBB - orange
            (1, -1, 0): (100, 200, 255),   # AA-BB-CC - light blue
            (0, 1, -1): (200, 100, 255),   # All Unique - purple
        }
        goal_labels = {
            (-2, 1, 1): "3-3",
            (1, -1, 0): "2-2-2",
            (0, 1, -1): "6 Uniq",
        }

        for goal in self.game.goals:
            pos_tuple = goal.position
            hex_coord_array = np.array([pos_tuple])
            pixel = hx.cube_to_pixel(hex_coord_array, self.hex_radius)[0]
            pos = pixel + self.center

            # Try to draw goal image, fall back to placeholder if not available
            if pos_tuple in self.goal_images:
                self.screen.blit(
                    self.goal_images[pos_tuple],
                    pos - np.array([self.hex_radius, self.hex_radius])
                )
            else:
                # Fallback: Draw colored circle with label
                color = goal_colors.get(pos_tuple, (200, 200, 100))
                pygame.draw.circle(self.screen, color, pos.astype(int), self.hex_radius - 2)
                pygame.draw.circle(self.screen, (100, 100, 100), pos.astype(int), self.hex_radius, 2)

                label = goal_labels.get(pos_tuple, "?")
                text = self.font.render(label, True, (0, 0, 0))
                text_rect = text.get_rect(center=pos.astype(int))
                self.screen.blit(text, text_rect)

    def _draw_hand(self):
        """Draw player's hand tiles."""
        base_x, base_y = self.hand_position
        spacing = int(10 * self.scale)

        # Label
        label = self.font.render("Your Hand:", True, (0, 0, 0))
        self.screen.blit(label, (base_x, base_y - int(25 * self.scale)))

        # Highlight if we're in PLACE_TILE phase
        if self.game.turn_phase == TurnPhase.PLACE_TILE:
            rect_width = len(self.game.player.tiles) * (self.tile_size + spacing) + int(10 * self.scale)
            rect_height = self.tile_size + int(40 * self.scale)
            pygame.draw.rect(self.screen, (200, 230, 200),
                           (base_x - int(5 * self.scale), base_y - int(30 * self.scale),
                            rect_width, rect_height), border_radius=int(5 * self.scale))

        for i, tile in enumerate(self.game.player.tiles):
            x = base_x + i * (self.tile_size + spacing)
            key = (tile.color, tile.pattern)
            if key in self.tile_images:
                self.screen.blit(self.tile_images[key], (x, base_y))

            # Selection highlight
            if self.game.selected_hand_tile == i:
                border = int(3 * self.scale)
                pygame.draw.rect(self.screen, (0, 200, 0),
                               (x - border, base_y - border,
                                self.tile_size + border * 2, self.tile_size + border * 2), border)

    def _draw_market(self):
        """Draw market tiles."""
        base_x, base_y = self.market_position
        spacing = int(10 * self.scale)

        # Label
        label = self.font.render("Market:", True, (0, 0, 0))
        self.screen.blit(label, (base_x, base_y - int(25 * self.scale)))

        # Highlight if we're in CHOOSE_MARKET phase
        if self.game.turn_phase == TurnPhase.CHOOSE_MARKET:
            rect_width = len(self.game.market.tiles) * (self.tile_size + spacing) + int(10 * self.scale)
            rect_height = self.tile_size + int(40 * self.scale)
            pygame.draw.rect(self.screen, (200, 230, 200),
                           (base_x - int(5 * self.scale), base_y - int(30 * self.scale),
                            rect_width, rect_height), border_radius=int(5 * self.scale))

        for i, tile in enumerate(self.game.market.tiles):
            x = base_x + i * (self.tile_size + spacing)
            key = (tile.color, tile.pattern)
            if key in self.tile_images:
                self.screen.blit(self.tile_images[key], (x, base_y))

    def _draw_cats(self):
        """Draw cat scoring objectives using images."""
        x, y = self.cats_position

        # Increased spacing to allow grey hex tiles to hang below cat images
        cat_spacing = int(60 * self.scale)

        # Positions for grey tiles relative to cat image (bottom cutouts)
        # Grey tiles hang below the cat image's lower edge
        tile_offset_y = self.cat_height - int(20 * self.scale)  # Tiles extend below cat
        tile1_offset_x = int(20 * self.scale)   # Left cutout position
        tile2_offset_x = int(92 * self.scale)   # Right cutout position

        for i, cat in enumerate(self.game.cats):
            cat_y = y + i * (self.cat_height + cat_spacing)

            # Draw cat image if available
            if cat.name in self.cat_images:
                self.screen.blit(self.cat_images[cat.name], (x, cat_y))

                # Overlay grey pattern tiles in the cutouts
                if len(cat.patterns) >= 2:
                    pattern1, pattern2 = cat.patterns[0], cat.patterns[1]

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
                # Fallback: text-based display if image not available
                text = f"{cat.name} ({cat.point_value}pts):"
                text_surface = self.font.render(text, True, (0, 0, 0))
                self.screen.blit(text_surface, (x, cat_y))

                pattern_names = [p.name.capitalize() for p in cat.patterns]
                patterns_text = f"  {', '.join(pattern_names)}"
                patterns_surface = self.font.render(patterns_text, True, (80, 80, 80))
                self.screen.blit(patterns_surface, (x, cat_y + int(17 * self.scale)))

    def _draw_goal_info(self):
        """Draw goal tile scoring info at top right."""
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

    def _draw_status(self):
        """Draw status message."""
        x, y = self.status_position

        # Status message
        status = self.game.get_status_message()
        if self.game.turn_phase == TurnPhase.GAME_OVER:
            color = (0, 150, 0)
        else:
            color = (0, 0, 150)
        status_surface = self.large_font.render(status, True, color)
        self.screen.blit(status_surface, (x, y))

    def _draw_turn_info(self):
        """Draw turn number and tiles remaining."""
        x = int(50 * self.scale)
        line_height = int(25 * self.scale)

        # Turn number
        turn_text = f"Turn: {self.game.turn_number + 1}"
        turn_surface = self.font.render(turn_text, True, (0, 0, 0))
        self.screen.blit(turn_surface, (x, int(20 * self.scale)))

        # Empty spaces remaining
        empty_count = len(self.game.player.grid.get_empty_positions())
        empty_text = f"Empty spaces: {empty_count}"
        empty_surface = self.font.render(empty_text, True, (0, 0, 0))
        self.screen.blit(empty_surface, (x, int(20 * self.scale) + line_height))

        # Tiles in bag
        bag_text = f"Tiles in bag: {self.game.tile_bag.tiles_remaining()}"
        bag_surface = self.font.render(bag_text, True, (0, 0, 0))
        self.screen.blit(bag_surface, (x, int(20 * self.scale) + line_height * 2))

    def _draw_controls_hint(self):
        """Draw keyboard controls hint."""
        screen_width = self.screen.get_width()
        hint_text = "F11: Fullscreen | +/-: Scale | 0: Reset | Scroll: Zoom"
        hint_surface = self.font.render(hint_text, True, (120, 120, 120))
        hint_rect = hint_surface.get_rect()
        hint_rect.bottomright = (screen_width - int(10 * self.scale),
                                  self.screen.get_height() - int(10 * self.scale))
        self.screen.blit(hint_surface, hint_rect)

    def run(self):
        """Main game loop."""
        running = True
        while running:
            running = self.handle_events()
            self.draw()
            self.clock.tick(60)

        pygame.quit()
