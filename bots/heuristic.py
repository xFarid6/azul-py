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
    
    # Add potential points for completed pattern lines
    for line_idx in range(5):
        line = player.pattern_lines[line_idx]
        if line['count'] == line_idx + 1:
            # Will move to wall. Conservatively add 1 point + any existing adjacencies
            color = line['color']
            col_idx = PlayerBoard.WALL_PATTERN[line_idx].index(color)
            
            # Simple simulation: if we place it, how much do we get?
            # We don't fully simulate but we can check horizontal/vertical
            h_score, v_score = 1, 1
            
            # check left
            c = col_idx - 1
            while c >= 0 and player.wall[line_idx][c]:
                h_score += 1
                c -= 1
            # check right
            c = col_idx + 1
            while c < 5 and player.wall[line_idx][c]:
                h_score += 1
                c += 1
                
            # check up
            r = line_idx - 1
            while r >= 0 and player.wall[r][col_idx]:
                v_score += 1
                r -= 1
            # check down
            r = line_idx + 1
            while r < 5 and player.wall[r][col_idx]:
                v_score += 1
                r += 1
                
            pts = 1
            if h_score > 1 and v_score > 1:
                pts = h_score + v_score
            else:
                pts = max(h_score, v_score)
                
            score += pts
            
        elif line['count'] > 0:
            # Partial lines are worth a tiny fraction just to encourage filling them
            score += 0.1 * line['count']

    # Sub penalty for floor
    penalty = 0
    for i, tile in enumerate(player.floor_line):
        if i < len(PlayerBoard.FLOOR_PENALTIES):
            penalty += PlayerBoard.FLOOR_PENALTIES[i]
            
    score += penalty
    return score
