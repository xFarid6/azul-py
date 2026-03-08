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
    for line_idx in range(5):
        line = player.pattern_lines[line_idx]
        if line['count'] == line_idx + 1:
            color = line['color']
            col_idx = PlayerBoard.WALL_PATTERN[line_idx].index(color)
            
            h_score, v_score = 1, 1
            # check left/right
            c = col_idx - 1
            while c >= 0 and player.wall[line_idx][c]: h_score += 1; c -= 1
            c = col_idx + 1
            while c < 5 and player.wall[line_idx][c]: h_score += 1; c += 1
            # check up/down
            r = line_idx - 1
            while r >= 0 and player.wall[r][col_idx]: v_score += 1; r -= 1
            r = line_idx + 1
            while r < 5 and player.wall[r][col_idx]: v_score += 1; r += 1
                
            pts = 0
            if h_score > 1 and v_score > 1: pts = h_score + v_score
            else: pts = max(h_score, v_score)
            score += pts
            
        elif line['count'] > 0:
            # Encourage finishing lines, especially larger ones
            score += 0.2 * line['count']

    # Long-term goal bonuses (completed columns, rows, or colors)
    # 7 points per column, 2 per row, 10 per color set
    
    # Column completion check
    for c in range(5):
        filled_in_col = sum(1 for r in range(5) if player.wall[r][c])
        if filled_in_col > 0:
            score += filled_in_col * 0.5  # 0.5 points per tile in a col
            if filled_in_col == 5:
                score += 7 # Column bonus
                
    # Row completion check
    for r in range(5):
        filled_in_row = sum(1 for c in range(5) if player.wall[r][c])
        if filled_in_row > 0:
            score += filled_in_row * 0.2 # 0.2 points per tile in a row
            if filled_in_row == 5:
                score += 2 # Row bonus
                
    # Color set completion check
    for color in range(1, 6):
        filled_of_color = 0
        for r in range(5):
            c = PlayerBoard.WALL_PATTERN[r].index(color)
            if player.wall[r][c]:
                filled_of_color += 1
        if filled_of_color > 0:
            score += filled_of_color * 0.8 # Color sets are valuable
            if filled_of_color == 5:
                score += 10 # Color set bonus

    # Sub penalty for floor (tiles are already negative, but prioritize avoiding them)
    penalty = 0
    for i, tile in enumerate(player.floor_line):
        if i < len(PlayerBoard.FLOOR_PENALTIES):
            penalty += PlayerBoard.FLOOR_PENALTIES[i]
            
    score += penalty * 1.2 # Make bot even more adverse to floor tiles
    return score
