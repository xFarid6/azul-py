from .bot import Bot
from .heuristic import evaluate_state
import math
import copy

# Transposition Table Flags
TT_EXACT = 0
TT_LOWERBOUND = 1
TT_UPPERBOUND = 2

class MinimaxBot(Bot):
    def __init__(self, player_idx, max_depth=4):
        super().__init__(player_idx)
        self.max_depth = max_depth
        # Stats
        self.total_nodes = 0
        self.last_nodes = 0
        self.last_think_ms = 0
        self.killer_moves = {}
        self.transposition_table = {}
        self._state_pool = []
        self._dummy_engine = None

    def _get_pool_state(self, depth, num_players):
        while len(self._state_pool) <= depth:
            from game.state import GameState
            self._state_pool.append(GameState(num_players))
        return self._state_pool[depth]

    def _sort_moves(self, engine, moves, depth):
        """Sorts moves using a light heuristic and the killer heuristic."""
        def move_score(move):
            score = 0
            # Killer move priority
            if self.killer_moves.get(depth) == move:
                return 1000
                
            player = engine.state.players[engine.state.current_player_idx]
            target_line = move['target_line']
            
            # Simple heuristic
            if target_line == -1:
                score -= 10 # Avoid floor
            else:
                score += (target_line + 1)
            
            return score

        return sorted(moves, key=move_score, reverse=True)

    def get_best_move(self, engine):
        import time
        t_start = time.time()
        
        valid_moves = engine.get_valid_moves(self.player_idx)
        if not valid_moves:
            return None
        if len(valid_moves) == 1:
            return valid_moves[0]
            
        self.killer_moves = {} # Reset for this search
        self.transposition_table = {} # Reset for this search
        
        if self._dummy_engine is None:
            from game.engine import GameEngine
            self._dummy_engine = GameEngine(engine.state.num_players)
        
        sorted_moves = self._sort_moves(engine, valid_moves, self.max_depth)
        
        best_score = -math.inf
        best_move = sorted_moves[0]
        self._nodes = 0
        
        alpha = -math.inf
        beta = math.inf
        
        # Original state to restore
        original_state = engine.state
        
        for move in sorted_moves:
            # Reuse pool for simulations
            sim_state = self._get_pool_state(self.max_depth, engine.state.num_players)
            sim_state.copy_from(original_state)
            
            self._dummy_engine.state = sim_state
            self._dummy_engine.game_over = engine.game_over
            
            self._dummy_engine.execute_move(move)
            self._nodes += 1
            
            score = self._alphabeta(self._dummy_engine, self.max_depth - 1, alpha, beta, False)
            
            if score > best_score:
                best_score = score
                best_move = move
                
            alpha = max(alpha, best_score)
            
        elapsed = (time.time() - t_start) * 1000
        self.last_think_ms = elapsed
        self.last_nodes = self._nodes
        self.total_nodes += self._nodes
        return best_move

    def _alphabeta(self, engine, depth, alpha, beta, maximizing):
        self._nodes += 1
        
        # 1. Transposition Table Lookup
        state_hash = engine.state.get_hash()
        tt_entry = self.transposition_table.get(state_hash)
        if tt_entry and tt_entry['depth'] >= depth:
            val = tt_entry['value']
            flag = tt_entry['flag']
            if flag == TT_EXACT:
                return val
            elif flag == TT_LOWERBOUND:
                alpha = max(alpha, val)
            elif flag == TT_UPPERBOUND:
                beta = min(beta, val)
                
            if alpha >= beta:
                return val

        if depth == 0 or engine.game_over:
            res = evaluate_state(engine.state, self.player_idx)
            self.transposition_table[state_hash] = {'value': res, 'depth': depth, 'flag': TT_EXACT}
            return res
            
        alpha_orig = alpha
        current_p = engine.state.current_player_idx
        maximizing_now = (current_p == self.player_idx)
        
        valid_moves = engine.get_valid_moves(current_p)
        if not valid_moves:
            res = evaluate_state(engine.state, self.player_idx)
            self.transposition_table[state_hash] = {'value': res, 'depth': depth, 'flag': TT_EXACT}
            return res
            
        sorted_moves = self._sort_moves(engine, valid_moves, depth)
        
        # State pooling: capture the current state of the engine
        parent_state = engine.state
        base_game_over = engine.game_over
            
        if maximizing_now:
            v = -math.inf
            for move in sorted_moves:
                # Use a pooled state for the next level
                child_state = self._get_pool_state(depth, engine.state.num_players)
                child_state.copy_from(parent_state)
                
                engine.state = child_state
                engine.game_over = base_game_over
                engine.execute_move(move)
                
                v = max(v, self._alphabeta(engine, depth-1, alpha, beta, False))
                alpha = max(alpha, v)
                if beta <= alpha:
                    self.killer_moves[depth] = move
                    break # Beta cut-off
        else:
            v = math.inf
            for move in sorted_moves:
                child_state = self._get_pool_state(depth, engine.state.num_players)
                child_state.copy_from(parent_state)
                
                engine.state = child_state
                engine.game_over = base_game_over
                engine.execute_move(move)
                
                v = min(v, self._alphabeta(engine, depth-1, alpha, beta, True))
                beta = min(beta, v)
                if beta <= alpha:
                    self.killer_moves[depth] = move
                    break # Alpha cut-off
        
        # Restore engine state
        engine.state = parent_state
        
        # 2. Transposition Table Store
        if v <= alpha_orig:
            flag = TT_UPPERBOUND
        elif v >= beta:
            flag = TT_LOWERBOUND
        else:
            flag = TT_EXACT
            
        self.transposition_table[state_hash] = {'value': v, 'depth': depth, 'flag': flag}
        return v
