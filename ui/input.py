import pygame
import math
from game.entities import Tile
from .constants import *

class InputManager:
    def __init__(self, engine):
        self.engine = engine
        self.selected_draft = None # ('factory'/'center', idx, Tile.COLOR)
        
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = pygame.mouse.get_pos()
            
            # If we haven't selected a draft yet
            if not self.selected_draft:
                draft = self._get_draft_click(pos)
                if draft:
                    self.selected_draft = draft
            else:
                # We have a draft, wait for line selection
                line_idx = self._get_line_click(pos)
                if line_idx is not None:
                    # Validate and execute move
                    move = {
                        'source_type': self.selected_draft[0],
                        'source_idx': self.selected_draft[1],
                        'color': self.selected_draft[2],
                        'target_line': line_idx
                    }
                    
                    # Check if move is in valid moves
                    valid_moves = self.engine.get_valid_moves(self.engine.state.current_player_idx)
                    is_valid = any(
                        m['source_type'] == move['source_type'] and
                        m['source_idx'] == move['source_idx'] and
                        m['color'] == move['color'] and
                        m['target_line'] == move['target_line']
                        for m in valid_moves
                    )
                    
                    if is_valid:
                        self.engine.execute_move(move)
                        self.selected_draft = None
                    else:
                        # Cancel selection if invalid line clicked or click elsewhere
                        self.selected_draft = None
                        
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.selected_draft = None

    def _get_draft_click(self, pos):
        """Returns ('factory'/'center', idx, color) or None"""
        x, y = pos
        state = self.engine.state
        
        # Check Center
        dist_center = math.hypot(x - FACTORY_CENTER[0], y - FACTORY_CENTER[1])
        if dist_center <= 60:
            if state.center.tiles:
                # Take first valid color clicked
                cx, cy = FACTORY_CENTER[0] - TILE_SIZE//2, FACTORY_CENTER[1] - TILE_SIZE//2
                for i, tile in enumerate(state.center.tiles):
                    if tile != Tile.FIRST_PLAYER and tile != Tile.EMPTY:
                        row = i // 4
                        col = i % 4
                        tx = cx - 40 + col * (TILE_SIZE//2 + 2)
                        ty = cy - 20 + row * (TILE_SIZE//2 + 2)
                        rect = pygame.Rect(tx, ty, TILE_SIZE//2, TILE_SIZE//2)
                        if rect.collidepoint(x, y):
                             return ('center', 0, tile)
                
                # If they clicked center but not a specific tile, just grab first available color
                for t in state.center.tiles:
                    if t != Tile.FIRST_PLAYER and t != Tile.EMPTY:
                        return ('center', 0, t)
                        
        # Check Factories
        num = len(state.factories)
        angle_step = 2 * math.pi / num
        for i, factory in enumerate(state.factories):
            angle = i * angle_step - math.pi/2 # Start top
            fx = FACTORY_CENTER[0] + FACTORY_RADIUS * math.cos(angle)
            fy = FACTORY_CENTER[1] + FACTORY_RADIUS * math.sin(angle)
            
            dist = math.hypot(x - fx, y - fy)
            if dist <= 45:
                # Find which tile was clicked
                positions = [
                    (fx - TILE_SIZE//2 - PADDING, fy - TILE_SIZE//2 - PADDING),
                    (fx + PADDING, fy - TILE_SIZE//2 - PADDING),
                    (fx - TILE_SIZE//2 - PADDING, fy + PADDING),
                    (fx + PADDING, fy + PADDING)
                ]
                for j, tile in enumerate(factory.tiles):
                    if j < 4 and tile != Tile.EMPTY:
                        rect = pygame.Rect(positions[j][0], positions[j][1], TILE_SIZE, TILE_SIZE)
                        if rect.collidepoint(x, y):
                            return ('factory', i, tile)
                            
                # Or just grab the first available if clicked the circle
                for t in factory.tiles:
                    if t != Tile.EMPTY:
                        return ('factory', i, t)
                        
        return None

    def _get_line_click(self, pos):
        """Returns 0-4 for pattern lines, -1 for floor, or None"""
        x, y = pos
        state = self.engine.state
        current_p = state.current_player_idx
        
        bx = PLAYER_1_POS[0] if current_p == 0 else PLAYER_2_POS[0]
        by = PLAYER_1_POS[1] if current_p == 0 else PLAYER_2_POS[1]
        
        # Fast bounding box check for board
        if not (bx <= x <= bx + BOARD_WIDTH and by <= y <= by + BOARD_HEIGHT):
            return None
            
        start_y = by + 60
        pattern_x = bx + 200
        
        # Check pattern lines 0-4
        for r in range(5):
            # Click area for a row could be the whole row height and left side of board
            row_rect = pygame.Rect(bx + 10, start_y + r * (TILE_SIZE + PADDING), 200, TILE_SIZE)
            if row_rect.collidepoint(x, y):
                return r
                
        # Check floor
        floor_y = start_y + 5 * (TILE_SIZE + PADDING) + 20
        floor_rect = pygame.Rect(bx + 10, floor_y, BOARD_WIDTH - 20, TILE_SIZE)
        if floor_rect.collidepoint(x, y):
            return -1
            
        return None
