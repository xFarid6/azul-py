import pygame
import math
from game.entities import Tile
from .constants import *

class InputManager:
    def __init__(self, engine, renderer):
        self.engine = engine
        self.renderer = renderer
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
                        return move  # signal that a move was made
                    else:
                        # Cancel selection if invalid line clicked
                        self.selected_draft = None
                        return None
                else:
                    new_draft = self._get_draft_click(pos)
                    if new_draft:
                        self.selected_draft = new_draft
                    else:
                        self.selected_draft = None
                        
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.selected_draft = None

    def _get_draft_click(self, pos):
        """Returns ('factory'/'center', idx, color) or None"""
        x, y = pos
        state = self.engine.state
        layout = self.renderer.get_layout()
        fcx, fcy = layout['factory_center']
        fradius = layout['factory_radius']
        
        GAP_F = 4   # same gap as renderer factory
        GAP_C = 6   # same gap as renderer center
        COLS_C = 4
        
        # ---- Check Factories ----
        num = len(state.factories)
        angle_step = 2 * math.pi / num
        
        for i, factory in enumerate(state.factories):
            angle = i * angle_step - math.pi / 2
            fx = int(fcx + fradius * math.cos(angle))
            fy = int(fcy + fradius * math.sin(angle))
            
            block_w = TILE_SIZE * 2 + GAP_F
            block_h = TILE_SIZE * 2 + GAP_F
            bx = fx - block_w // 2
            by = fy - block_h // 2
            
            positions = [
                (bx,                      by),
                (bx + TILE_SIZE + GAP_F,  by),
                (bx,                      by + TILE_SIZE + GAP_F),
                (bx + TILE_SIZE + GAP_F,  by + TILE_SIZE + GAP_F)
            ]
            
            for j, tile in enumerate(factory.tiles):
                if j < 4 and tile != Tile.EMPTY:
                    rect = pygame.Rect(positions[j][0], positions[j][1], TILE_SIZE, TILE_SIZE)
                    if rect.collidepoint(x, y):
                        return ('factory', i, tile)
        
        # ---- Check Center ----
        display_tiles = [(idx2, t) for idx2, t in enumerate(state.center.tiles) if t != Tile.EMPTY]
        
        if display_tiles:
            rows = (len(display_tiles) + COLS_C - 1) // COLS_C
            total_w = min(len(display_tiles), COLS_C) * (TILE_SIZE + GAP_C) - GAP_C
            total_h = rows * (TILE_SIZE + GAP_C) - GAP_C
            origin_x = fcx - total_w // 2
            origin_y = fcy - total_h // 2
            
            for idx2, (orig_i, tile) in enumerate(display_tiles):
                if tile == Tile.FIRST_PLAYER:
                    continue
                row = idx2 // COLS_C
                col = idx2 % COLS_C
                tx = origin_x + col * (TILE_SIZE + GAP_C)
                ty = origin_y + row * (TILE_SIZE + GAP_C)
                rect = pygame.Rect(tx, ty, TILE_SIZE, TILE_SIZE)
                if rect.collidepoint(x, y):
                    return ('center', 0, tile)
                    
        return None

    def _get_line_click(self, pos):
        """Returns 0-4 for pattern lines, -1 for floor, or None"""
        x, y = pos
        state = self.engine.state
        current_p = state.current_player_idx
        layout = self.renderer.get_layout()
        
        bx, by = layout['player_positions'][current_p % 4]
        
        # Fast bounding box check for board
        if not (bx <= x <= bx + BOARD_WIDTH and by <= y <= by + BOARD_HEIGHT):
            return None
            
        start_y = by + 42
        pattern_x = bx + 200
        
        # Check pattern lines 0-4
        for r in range(5):
            # Click area for a row: left side of board up to pattern_x
            row_rect = pygame.Rect(bx + 10, start_y + r * (TILE_SIZE + PADDING), 190, TILE_SIZE)
            if row_rect.collidepoint(x, y):
                return r
                
        # Check floor
        floor_y = start_y + 5 * (TILE_SIZE + PADDING) + 10
        floor_rect = pygame.Rect(bx + 10, floor_y, BOARD_WIDTH - 20, TILE_SIZE)
        if floor_rect.collidepoint(x, y):
            return -1
            
        return None
