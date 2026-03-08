import pygame
import os
import math
from game.entities import Tile, PlayerBoard
from .constants import *

class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.SysFont('Arial', 24)
        self.small_font = pygame.font.SysFont('Arial', 18)
        self.large_font = pygame.font.SysFont('Arial', 36, bold=True)
        # Load images mapping
        self.tile_images = self._load_images()

    def get_layout(self):
        w, h = self.screen.get_size()
        cx, cy = w // 2, h // 2
        
        # Determine factory radius and layout offsets based on available space
        min_dim = min(w, h)
        factory_radius = max(80, min(150, int(min_dim * 0.15)))
        
        padding = 20
        positions = [
            (padding, padding),
            (w - BOARD_WIDTH - padding, padding),
            (padding, h - BOARD_HEIGHT - padding),
            (w - BOARD_WIDTH - padding, h - BOARD_HEIGHT - padding)
        ]
        
        return {
            'w': w, 'h': h,
            'factory_center': (cx, cy),
            'factory_radius': factory_radius,
            'player_positions': positions
        }

    def _load_images(self):
        images = {}
        color_map = {
            Tile.BLUE: 'blue.png',
            Tile.YELLOW: 'yellow.png',
            Tile.RED: 'red.png',
            Tile.GREEN: 'green.png',
            Tile.WHITE: 'white.png'
        }
        assets_dir = 'assets/tiles'
        for tile, filename in color_map.items():
            path = os.path.join(assets_dir, filename)
            if os.path.exists(path):
                img = pygame.image.load(path).convert_alpha()
                images[tile] = pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
            else:
                images[tile] = None
        return images

    def draw_tile(self, tile, x, y, size=TILE_SIZE):
        rect = pygame.Rect(x, y, size, size)
        if tile in self.tile_images and self.tile_images[tile]:
            if size != TILE_SIZE: # dynamically scale if needed
                img = pygame.transform.scale(self.tile_images[tile], (size, size))
                self.screen.blit(img, (x, y))
            else:
                self.screen.blit(self.tile_images[tile], (x, y))
        else:
            color = TILE_COLORS.get(tile, TILE_COLORS[Tile.EMPTY])
            pygame.draw.rect(self.screen, color, rect)
            pygame.draw.rect(self.screen, (0,0,0), rect, 1)

        if tile == Tile.FIRST_PLAYER:
            text = self.small_font.render("1st", True, (0, 0, 0))
            text_rect = text.get_rect(center=rect.center)
            self.screen.blit(text, text_rect)

    def draw_game_state(self, game_state, selected_draft=None, highlighted_line=None, mouse_pos=None):
        self.screen.fill(BG_COLOR)
        layout = self.get_layout()
        w, h = layout['w'], layout['h']
        
        # Draw status text
        round_text = self.font.render(f"Round: {game_state.round_number}", True, TEXT_COLOR)
        player_text = self.large_font.render(f"Player {game_state.current_player_idx + 1}'s Turn", True, TEXT_COLOR)
        self.screen.blit(round_text, (20, h // 2))
        self.screen.blit(player_text, (w//2 - player_text.get_width()//2, 20))
        
        # Draw Undo button
        undo_rect = pygame.Rect(20, h - 60, 100, 40)
        pygame.draw.rect(self.screen, (200, 190, 180), undo_rect)
        pygame.draw.rect(self.screen, (100, 90, 80), undo_rect, 2)
        undo_text = self.font.render("Undo", True, TEXT_COLOR)
        self.screen.blit(undo_text, (undo_rect.centerx - undo_text.get_width()//2, undo_rect.centery - undo_text.get_height()//2))
        
        # Info about hotkeys
        hotkey_text = self.small_font.render("Press 'R' to Restart | 'Q' to Quit", True, TEXT_COLOR)
        self.screen.blit(hotkey_text, (140, h - 50))

        # Draw factories
        self._draw_factories(game_state.factories, layout)
        
        # Draw center
        self._draw_center(game_state.center, layout)
        
        # Draw player boards
        for i, player in enumerate(game_state.players):
            # If 3 players, can center the 3rd or just use bottom-left.
            # Using corner slots 0, 1, 2, 3
            pos = layout['player_positions'][i % 4]
            self._draw_player_board(player, f"Player {i+1}", pos[0], pos[1], 
                                    game_state.current_player_idx == i, highlighted_line)

        # Draw current selection
        if selected_draft:
            src_type, src_idx, color = selected_draft
            info_text = self.font.render(f"Selected: {color.name} from {src_type} {src_idx if src_type=='factory' else ''}", True, HIGHLIGHT_COLOR)
            self.screen.blit(info_text, (w//2 - info_text.get_width()//2, 70))
            
        if mouse_pos:
            pygame.draw.circle(self.screen, (100, 100, 100), mouse_pos, 5, 2)
            
    def _draw_factories(self, factories, layout):
        num = len(factories)
        angle_step = 2 * math.pi / num
        fcx, fcy = layout['factory_center']
        fradius = layout['factory_radius']
        
        for i, factory in enumerate(factories):
            angle = i * angle_step - math.pi/2 # Start top
            fx = fcx + fradius * math.cos(angle)
            fy = fcy + fradius * math.sin(angle)
            
            # Draw factory circle - made larger
            factory_draw_radius = 55
            pygame.draw.circle(self.screen, BOARD_BG, (int(fx), int(fy)), factory_draw_radius)
            pygame.draw.circle(self.screen, (150, 140, 130), (int(fx), int(fy)), factory_draw_radius, 2)
            
            # Draw 4 tiles inside with more padding
            t_pad = PADDING + 4
            positions = [
                (fx - TILE_SIZE//2 - t_pad, fy - TILE_SIZE//2 - t_pad),
                (fx + t_pad, fy - TILE_SIZE//2 - t_pad),
                (fx - TILE_SIZE//2 - t_pad, fy + t_pad),
                (fx + t_pad, fy + t_pad)
            ]
            for j, tile in enumerate(factory.tiles):
                if j < 4:
                    self.draw_tile(tile, positions[j][0], positions[j][1])

    def _draw_center(self, center, layout):
        fcx, fcy = layout['factory_center']
        pygame.draw.circle(self.screen, BOARD_BG, (fcx, fcy), 75)
        pygame.draw.circle(self.screen, (150, 140, 130), (fcx, fcy), 75, 2)
        
        # Draw center tiles in a spiral or grid
        cx, cy = fcx - TILE_SIZE//2, fcy - TILE_SIZE//2
        
        for i, tile in enumerate(center.tiles):
            # Simple grid for center
            row = i // 4
            col = i % 4
            x = cx - 40 + col * (TILE_SIZE//2 + 2)
            y = cy - 20 + row * (TILE_SIZE//2 + 2)
            self.draw_tile(tile, x, y, TILE_SIZE//2) # Draw smaller

    def _draw_player_board(self, player, text, x, y, is_current, highlighted_line):
        # Background
        board_rect = pygame.Rect(x, y, BOARD_WIDTH, BOARD_HEIGHT)
        color = (255, 250, 230) if is_current else BOARD_BG
        pygame.draw.rect(self.screen, color, board_rect)
        pygame.draw.rect(self.screen, (100, 90, 80), board_rect, 3 if is_current else 1)

        # Name and Score
        name_surf = self.font.render(f"{text} Score: {player.score}", True, TEXT_COLOR)
        self.screen.blit(name_surf, (x + 10, y + 10))

        # Config
        start_y = y + 60
        pattern_x = x + 200
        wall_x = x + 230

        # Pattern Lines
        for r in range(5):
            line = player.pattern_lines[r]
            # Draw right to left
            for c in range(r + 1):
                tx = pattern_x - c * (TILE_SIZE + PADDING)
                ty = start_y + r * (TILE_SIZE + PADDING)
                
                # Check if highlight
                if is_current and highlighted_line == r:
                    pygame.draw.rect(self.screen, HIGHLIGHT_COLOR, (tx-2, ty-2, TILE_SIZE+4, TILE_SIZE+4), 2)
                    
                # Draw empty slot
                pygame.draw.rect(self.screen, (200, 190, 180), (tx, ty, TILE_SIZE, TILE_SIZE))
                
                # Draw tile if present
                if c < line['count']:
                    self.draw_tile(line['color'], tx, ty)

        # Wall (move to right with more padding separating it from pattern lines)
        wall_x = x + 250
        for r in range(5):
            for c in range(5):
                tx = wall_x + c * (TILE_SIZE + PADDING)
                ty = start_y + r * (TILE_SIZE + PADDING)
                
                wall_color = PlayerBoard.WALL_PATTERN[r][c]
                
                if player.wall[r][c]:
                    self.draw_tile(wall_color, tx, ty)
                else:
                    # Draw translucent/empty wall slot
                    s = pygame.Surface((TILE_SIZE, TILE_SIZE))
                    s.set_alpha(128)
                    s.fill(TILE_COLORS[wall_color])
                    self.screen.blit(s, (tx, ty))
                    pygame.draw.rect(self.screen, (180, 170, 160), (tx, ty, TILE_SIZE, TILE_SIZE), 1)

        # Floor Line
        floor_y = start_y + 5 * (TILE_SIZE + PADDING) + 20
        floor_x = x + 20
        floor_text = self.small_font.render("Floor:", True, TEXT_COLOR)
        self.screen.blit(floor_text, (floor_x, floor_y + 10))
        
        for i in range(7):
            tx = floor_x + 60 + i * (TILE_SIZE + PADDING)
            
            # Draw empty slot and penalty text
            pygame.draw.rect(self.screen, (200, 190, 180), (tx, floor_y, TILE_SIZE, TILE_SIZE))
            pen_text = self.small_font.render(str(PlayerBoard.FLOOR_PENALTIES[i]), True, ERROR_COLOR)
            self.screen.blit(pen_text, (tx + 10, floor_y + TILE_SIZE + 5))
            
            # Draw highlight for floor (-1)
            if is_current and highlighted_line == -1:
                pygame.draw.rect(self.screen, HIGHLIGHT_COLOR, (tx-2, floor_y-2, TILE_SIZE+4, TILE_SIZE+4), 2)
                
            if i < len(player.floor_line):
                self.draw_tile(player.floor_line[i], tx, floor_y)
