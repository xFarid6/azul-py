from .state import GameState
from .entities import Tile, PlayerBoard

class GameEngine:
    def __init__(self, num_players=2):
        self.state = GameState(num_players)
        self.game_over = False
        self._setup_round()

    def _setup_round(self):
        """Fills factories from bag. Checks if game should end and handles end if true."""
        self.state.center.tiles = [Tile.FIRST_PLAYER]
        
        for factory in self.state.factories:
            # Need to draw 4 tiles. If bag is empty, refill from box.
            if len(self.state.bag.tiles) < 4:
                self.state.bag.refill(self.state.box)
                self.state.box = []
                
            tiles = self.state.bag.draw(min(4, len(self.state.bag.tiles)))
            factory.fill(tiles)

    def reset_to_state(self, state, game_over=False):
        """Resets the engine to a specific state for simulation."""
        self.state.copy_from(state)
        self.game_over = game_over

    def to_dict(self):
        return {
            'game_over': self.game_over,
            'state': self.state.to_dict()
        }

    @classmethod
    def from_dict(cls, data):
        state_data = data['state']
        e = cls(num_players=state_data['num_players'])
        e.state = GameState.from_dict(state_data)
        e.game_over = data['game_over']
        return e

    def get_valid_moves(self, player_idx):
        """
        Returns a list of dicts:
        {
            'source_type': 'factory' | 'center',
            'source_idx': int,  # Factory index, or 0 for center
            'color': Tile,
            'target_line': int  # 0-4 for pattern lines, -1 for floor
        }
        """
        if self.game_over:
            return []

        player = self.state.players[player_idx]
        moves = []
        
        # 1. Gather all available colored tiles from factories and center
        available_drafts = []
        for i, factory in enumerate(self.state.factories):
            for color in set(factory.tiles):
                if color != Tile.EMPTY:
                    available_drafts.append(('factory', i, color))
                    
        for color in set(self.state.center.tiles):
            if color != Tile.EMPTY and color != Tile.FIRST_PLAYER:
                available_drafts.append(('center', 0, color))
                
        # 2. For each draft, check valid target lines
        for src_type, src_idx, color in available_drafts:
            # Always valid to put on floor
            moves.append({
                'source_type': src_type,
                'source_idx': src_idx,
                'color': color,
                'target_line': -1
            })
            
            # Check pattern lines
            for line_idx in range(5):
                if player.can_place_on_pattern_line(line_idx, color):
                    moves.append({
                        'source_type': src_type,
                        'source_idx': src_idx,
                        'color': color,
                        'target_line': line_idx
                    })
                    
        return moves

    def execute_move(self, move):
        """Applies a move dict to the current state."""
        src_type = move['source_type']
        src_idx = move['source_idx']
        color = move['color']
        target_line = move['target_line']
        
        player = self.state.players[self.state.current_player_idx]
        
        # 1. Take tiles
        if src_type == 'factory':
            taken, remaining = self.state.factories[src_idx].take(color)
            self.state.center.add(remaining)
        elif src_type == 'center':
            taken = self.state.center.take(color)
            if Tile.FIRST_PLAYER in taken:
                self.state.next_first_player_idx = self.state.current_player_idx
        else:
            raise ValueError(f"Invalid source type {src_type}")
            
        # 2. Place tiles
        overflow = player.add_to_pattern_line(target_line, taken)
        
        # The engine logic handles discarding. The player board places on floor,
        # but anything beyond floor capacity goes back to the box.
        # However, the player add_to_floor returns the overflow relative to floor capacity.
        # We need to explicitly handle overflow > 7 here.
        if overflow > 0:
            overflowed_tiles = [color] * overflow
            discarded = player.add_to_floor(overflowed_tiles)
            if discarded > 0:
                 self.state.box.extend([color] * discarded)

        # 3. Next player or end of round
        self.state.current_player_idx = (self.state.current_player_idx + 1) % self.state.num_players
        
        if self.state.is_round_over():
            self._score_round()

    def _score_round(self):
        """Scores completed pattern lines, moves tiles to wall, handles floor penalties."""
        for player in self.state.players:
            # 1. Move to wall and score
            for line_idx in range(5):
                line = player.pattern_lines[line_idx]
                if line['count'] == line_idx + 1:
                    color = line['color']
                    
                    # Find column for color
                    col_idx = PlayerBoard.WALL_PATTERN[line_idx].index(color)
                    
                    # Place on wall
                    player.wall[line_idx][col_idx] = True
                    
                    # Discard remaining tiles to box
                    self.state.box.extend([color] * line_idx)
                    
                    # Score placement
                    points = self._score_placement(player.wall, line_idx, col_idx)
                    player.score += points
                    
                    # Empty pattern line
                    line['count'] = 0
                    line['color'] = Tile.EMPTY
                    
            # 2. Apply floor penalties
            penalty = 0
            for i, tile in enumerate(player.floor_line):
                if i < len(PlayerBoard.FLOOR_PENALTIES):
                    penalty += PlayerBoard.FLOOR_PENALTIES[i]
                
                if tile != Tile.FIRST_PLAYER:
                     self.state.box.append(tile)

            player.floor_line = []
            player.score = max(0, player.score + penalty)
            
        # 3. Check for end game
        for player in self.state.players:
            for row in range(5):
                if all(player.wall[row]):
                    self.game_over = True
                    self._score_end_game()
                    return
                    
        # 4. Setup next round
        self.state.round_number += 1
        self.state.current_player_idx = self.state.next_first_player_idx
        self._setup_round()

    def _score_placement(self, wall, row, col):
        """Calculates points for placing a tile at (row, col) based on contiguous tiles."""
        h_score = 1
        v_score = 1
        
        # Horizontal
        c = col - 1
        while c >= 0 and wall[row][c]:
            h_score += 1
            c -= 1
        c = col + 1
        while c < 5 and wall[row][c]:
            h_score += 1
            c += 1
            
        # Vertical
        r = row - 1
        while r >= 0 and wall[r][col]:
            v_score += 1
            r -= 1
        r = row + 1
        while r < 5 and wall[r][col]:
            v_score += 1
            r += 1
            
        if h_score == 1 and v_score == 1:
            return 1
        elif h_score == 1:
            return v_score
        elif v_score == 1:
            return h_score
        else:
            return h_score + v_score

    def _score_end_game(self):
        """Applies endgame bonuses for completed rows, columns, and 5-of-a-color."""
        for player in self.state.players:
            # Score rows (2 pts)
            for row in range(5):
                if all(player.wall[row]):
                    player.score += 2
            
            # Score columns (7 pts)
            for col in range(5):
                if all(player.wall[r][col] for r in range(5)):
                    player.score += 7
            
            # Score 5-of-a-color (10 pts)
            for color in [Tile.BLUE, Tile.YELLOW, Tile.RED, Tile.GREEN, Tile.WHITE]:
                color_count = 0
                for r in range(5):
                    c = PlayerBoard.WALL_PATTERN[r].index(color)
                    if player.wall[r][c]:
                        color_count += 1
                if color_count == 5:
                    player.score += 10
