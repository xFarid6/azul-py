from game.entities import PlayerBoard

def evaluate_state(state, player_idx):
    """
    Evaluates the game state from the perspective of the given player.
    Positive means good for player_idx, negative means good for opponents.
    """
    my_score = _evaluate_player(state.players[player_idx])
    
    opp_scores = [
        _evaluate_player(player) 
        for i, player in enumerate(state.players) 
        if i != player_idx
    ]
    max_opp_score = max(opp_scores) if opp_scores else 0
    
    return my_score - max_opp_score

def _evaluate_player(player):
    score = player.score
    
    # Adjacency bonuses for tiles moving to wall this round
    mask = player.wall_mask
    for line_idx in range(5):
        line = player.pattern_lines[line_idx]
        if line['count'] == line_idx + 1:
            color = line['color']
            col_idx = PlayerBoard.WALL_PATTERN[line_idx].index(color)
            
            h_score, v_score = 1, 1
            # check left/right
            c = col_idx - 1
            while c >= 0 and (mask >> (line_idx * 5 + c)) & 1: h_score += 1; c -= 1
            c = col_idx + 1
            while c < 5 and (mask >> (line_idx * 5 + c)) & 1: h_score += 1; c += 1
            # check up/down
            r = line_idx - 1
            while r >= 0 and (mask >> (r * 5 + col_idx)) & 1: v_score += 1; r -= 1
            r = line_idx + 1
            while r < 5 and (mask >> (r * 5 + col_idx)) & 1: v_score += 1; r += 1
                
            pts = 0
            if h_score > 1 and v_score > 1: pts = h_score + v_score
            else: pts = max(h_score, v_score)
            score += pts
            
        elif line['count'] > 0:
            # Encourage finishing lines, especially larger ones
            score += 0.2 * line['count']

    # Long-term goal bonuses (completed columns, rows, or colors)
    
    # Column completion check
    for c in range(5):
        col_mask = (1 << c) | (1 << (c + 5)) | (1 << (c + 10)) | (1 << (c + 15)) | (1 << (c + 20))
        filled_in_col = bin(mask & col_mask).count('1')
        if filled_in_col > 0:
            score += filled_in_col * 0.5
            if filled_in_col == 5:
                score += 7
                
    # Row completion check
    for r in range(5):
        row_mask = 0x1F << (r * 5)
        filled_in_row = bin(mask & row_mask).count('1')
        if filled_in_row > 0:
            score += filled_in_row * 0.2
            if filled_in_row == 5:
                score += 2
                
    # Color set completion check
    for color in range(1, 6):
        color_mask = 0
        for r in range(5):
            c = PlayerBoard.WALL_PATTERN[r].index(color)
            color_mask |= (1 << (r * 5 + c))
            
        filled_of_color = bin(mask & color_mask).count('1')
        if filled_of_color > 0:
            score += filled_of_color * 0.8
            if filled_of_color == 5:
                score += 10

    # Sub penalty for floor
    penalty = 0
    for i, tile in enumerate(player.floor_line):
        if i < len(PlayerBoard.FLOOR_PENALTIES):
            penalty += PlayerBoard.FLOOR_PENALTIES[i]
            
    score += penalty * 1.2 # Make bot adverse to floor tiles
    return score
