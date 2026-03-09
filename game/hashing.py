import random
from .entities import Tile

class ZobristHasher:
    def __init__(self, seed=42):
        self.rng = random.Random(seed)
        
        # current_player_keys[idx]
        self.player_turn_keys = [self.rng.getrandbits(64) for _ in range(4)]
        
        # wall_keys[player_idx][row][col]
        self.wall_keys = [[[self.rng.getrandbits(64) for _ in range(5)] for _ in range(5)] for _ in range(4)]
        
        # pattern_keys[player_idx][row][color][count]
        # row 0..4, color 0..5 (Tile values), count 0..5
        self.pattern_keys = [[[[self.rng.getrandbits(64) for _ in range(6)] for _ in range(6)] for _ in range(5)] for _ in range(4)]
        
        # floor_keys[player_idx][slot][tile_type_index]
        # slot 0..6, tile_type_index 0..6 (mapping -1..5 to 0..6)
        self.floor_keys = [[[self.rng.getrandbits(64) for _ in range(7)] for _ in range(7)] for _ in range(4)]
        
        # factory_keys[factory_idx][color][count]
        # factory_idx 0..8, color 1..5, count 0..4
        self.factory_keys = [[[self.rng.getrandbits(64) for _ in range(5)] for _ in range(6)] for _ in range(9)]
        
        # center_keys[color][count]
        self.center_keys = [[self.rng.getrandbits(64) for _ in range(101)] for _ in range(6)]
        self.center_first_player_key = self.rng.getrandbits(64)
        
        # score_keys[player_idx][score]
        # Azul scores can go up to ~200, let's allow 300
        self.score_keys = [[self.rng.getrandbits(64) for _ in range(301)] for _ in range(4)]

    def get_hash(self, state):
        h = 0
        h ^= self.player_turn_keys[state.current_player_idx % 4]
        
        for p_idx, player in enumerate(state.players):
            if p_idx >= 4: break
            
            # Score
            score_val = max(0, min(300, int(player.score)))
            h ^= self.score_keys[p_idx][score_val]
            
            # Wall
            mask = player.wall_mask
            for r in range(5):
                for c in range(5):
                    if (mask >> (r * 5 + c)) & 1:
                        h ^= self.wall_keys[p_idx][r][c]
            
            # Pattern lines
            for r, line in enumerate(player.pattern_lines):
                color = int(line['color'])
                count = line['count']
                h ^= self.pattern_keys[p_idx][r][color][count]
            
            # Floor
            for slot, tile in enumerate(player.floor_line):
                if slot >= 7: break
                tile_idx = int(tile) + 1 # map -1..5 to 0..6
                h ^= self.floor_keys[p_idx][slot][tile_idx]
                
        # Factories (use counts to avoid permutation issues)
        for f_idx, factory in enumerate(state.factories):
            if f_idx >= 9: break
            from collections import Counter
            counts = Counter(factory.tiles)
            for color_val in range(1, 6):
                count = counts.get(Tile(color_val), 0)
                if count > 0:
                    h ^= self.factory_keys[f_idx][color_val][count]
                
        # Center
        from collections import Counter
        c_counts = Counter(state.center.tiles)
        for color_val in range(1, 6):
            count = c_counts.get(Tile(color_val), 0)
            if count > 0:
                h ^= self.center_keys[color_val][min(count, 100)]
        if Tile.FIRST_PLAYER in state.center.tiles:
            h ^= self.center_first_player_key
            
        return h

_hasher = ZobristHasher()

def get_state_hash(state):
    return _hasher.get_hash(state)
