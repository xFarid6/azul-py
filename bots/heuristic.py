from game.entities import PlayerBoard, Tile
import numpy as np
from numba import njit

# Pre-compute constants as NumPy arrays for Numba
WALL_PATTERN_NP = np.array([
    [Tile.BLUE, Tile.YELLOW, Tile.RED, Tile.GREEN, Tile.WHITE],
    [Tile.WHITE, Tile.BLUE, Tile.YELLOW, Tile.RED, Tile.GREEN],
    [Tile.GREEN, Tile.WHITE, Tile.BLUE, Tile.YELLOW, Tile.RED],
    [Tile.RED, Tile.GREEN, Tile.WHITE, Tile.BLUE, Tile.YELLOW],
    [Tile.YELLOW, Tile.RED, Tile.GREEN, Tile.WHITE, Tile.BLUE]
], dtype=np.int32)

FLOOR_PENALTIES_NP = np.array([-1, -1, -2, -2, -2, -3, -3], dtype=np.int32)

# Pre-compute masks
COL_MASKS = np.array([
    (1 << c) | (1 << (c + 5)) | (1 << (c + 10)) | (1 << (c + 15)) | (1 << (c + 20))
    for c in range(5)
], dtype=np.int32)

ROW_MASKS = np.array([
    0x1F << (r * 5)
    for r in range(5)
], dtype=np.int32)

COLOR_MASKS = np.zeros((6, 1), dtype=np.int32) # Not used directly as 2D, but for reference
# Better pre-compute color masks as a flat array
COLOR_MASKS_NP = np.zeros(6, dtype=np.int32)
for color_val in range(1, 6):
    mask = 0
    for r in range(5):
        # find col for color in row r
        for c in range(5):
            if WALL_PATTERN_NP[r, c] == color_val:
                mask |= (1 << (r * 5 + c))
                break
    COLOR_MASKS_NP[color_val] = mask

@njit
def count_set_bits(n):
    count = 0
    while n > 0:
        n &= n - 1
        count += 1
    return count

@njit
def _evaluate_player_jit(score, wall_mask, pattern_colors, pattern_counts, floor_len):
    eval_score = float(score)
    
    # Adjacency bonuses for tiles moving to wall this round
    for line_idx in range(5):
        count = pattern_counts[line_idx]
        if count == line_idx + 1:
            color = pattern_colors[line_idx]
            # Find col_idx
            col_idx = -1
            for c in range(5):
                if WALL_PATTERN_NP[line_idx, c] == color:
                    col_idx = c
                    break
            
            h_score, v_score = 1, 1
            # check left/right
            c_ptr = col_idx - 1
            while c_ptr >= 0 and (wall_mask >> (line_idx * 5 + c_ptr)) & 1: 
                h_score += 1
                c_ptr -= 1
            c_ptr = col_idx + 1
            while c_ptr < 5 and (wall_mask >> (line_idx * 5 + c_ptr)) & 1: 
                h_score += 1
                c_ptr += 1
            # check up/down
            r_ptr = line_idx - 1
            while r_ptr >= 0 and (wall_mask >> (r_ptr * 5 + col_idx)) & 1: 
                v_score += 1
                r_ptr -= 1
            r_ptr = line_idx + 1
            while r_ptr < 5 and (wall_mask >> (r_ptr * 5 + col_idx)) & 1: 
                v_score += 1
                r_ptr += 1
                
            pts = 0
            if h_score > 1 and v_score > 1: pts = h_score + v_score
            else: pts = max(h_score, v_score)
            eval_score += pts
            
        elif count > 0:
            eval_score += 0.2 * count

    # Long-term goal bonuses
    for c in range(5):
        filled_in_col = count_set_bits(wall_mask & COL_MASKS[c])
        if filled_in_col > 0:
            eval_score += filled_in_col * 0.5
            if filled_in_col == 5:
                eval_score += 7
                
    for r in range(5):
        filled_in_row = count_set_bits(wall_mask & ROW_MASKS[r])
        if filled_in_row > 0:
            eval_score += filled_in_row * 0.2
            if filled_in_row == 5:
                eval_score += 2
                
    for color_val in range(1, 6):
        filled_of_color = count_set_bits(wall_mask & COLOR_MASKS_NP[color_val])
        if filled_of_color > 0:
            eval_score += filled_of_color * 0.8
            if filled_of_color == 5:
                eval_score += 10

    # Sub penalty for floor
    penalty = 0
    for i in range(floor_len):
        if i < 7:
            penalty += FLOOR_PENALTIES_NP[i]
            
    eval_score += penalty * 1.2
    return eval_score

def evaluate_state(state, player_idx):
    """ Wrapper for JIT evaluation """
    my_score = _evaluate_player_wrapper(state.players[player_idx])
    
    opp_scores = [
        _evaluate_player_wrapper(player) 
        for i, player in enumerate(state.players) 
        if i != player_idx
    ]
    max_opp_score = max(opp_scores) if opp_scores else 0
    
    return my_score - max_opp_score

def _evaluate_player_wrapper(player):
    # Extract data for JIT-ed function as tuples (much faster than np.array allocation)
    lines = player.pattern_lines
    pattern_colors = (
        int(lines[0]['color']), int(lines[1]['color']), int(lines[2]['color']), 
        int(lines[3]['color']), int(lines[4]['color'])
    )
    pattern_counts = (
        lines[0]['count'], lines[1]['count'], lines[2]['count'], 
        lines[3]['count'], lines[4]['count']
    )
    
    return _evaluate_player_jit(
        player.score, 
        player.wall_mask, 
        pattern_colors, 
        pattern_counts, 
        len(player.floor_line)
    )
