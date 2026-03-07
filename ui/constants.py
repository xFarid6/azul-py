import pygame
from game.entities import Tile

# Window Settings
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
FPS = 60

# Colors
BG_COLOR = (240, 235, 225)
BOARD_BG = (220, 210, 190)
TEXT_COLOR = (50, 40, 30)
HIGHLIGHT_COLOR = (255, 200, 0)
ERROR_COLOR = (255, 50, 50)

# Tile mapping to actual colors if image fails to load
TILE_COLORS = {
    Tile.EMPTY: (200, 190, 180),
    Tile.BLUE: (0, 100, 200),
    Tile.YELLOW: (255, 200, 0),
    Tile.RED: (200, 40, 40),
    Tile.BLACK: (40, 40, 40),
    Tile.WHITE: (245, 245, 245),
    Tile.FIRST_PLAYER: (150, 200, 150)
}

# Dimensions
TILE_SIZE = 40
PADDING = 5

# Board positioning
BOARD_WIDTH = 450
BOARD_HEIGHT = 350
PLAYER_1_POS = (50, 400)
PLAYER_2_POS = (700, 400)

CENTER_START = (400, 150)
FACTORY_RADIUS = 120
FACTORY_CENTER = (600, 150)
