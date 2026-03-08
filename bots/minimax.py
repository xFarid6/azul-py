from .bot import Bot
from .heuristic import evaluate_state
import math
import copy

class MinimaxBot(Bot):
    def __init__(self, player_idx, max_depth=4):
        super().__init__(player_idx)
        self.max_depth = max_depth
        # Stats
        self.total_nodes = 0
        self.last_nodes = 0
        self.last_think_ms = 0

    def get_best_move(self, engine):
        import time
        t_start = time.time()
        
        valid_moves = engine.get_valid_moves(self.player_idx)
        if not valid_moves:
            return None
            
        best_score = -math.inf
        best_move = valid_moves[0]
        self._nodes = 0
        
        # We need a deep clone of the engine state to simulate moves
        # But cloning the whole engine is tricky if it holds a lot of logic.
        # Instead, we clone the state, then temporarily swap it in a dummy engine.
        
        from game.engine import GameEngine
        dummy_engine = GameEngine(engine.state.num_players)
        
        alpha = -math.inf
        beta = math.inf
        
        for move in valid_moves:
            dummy_engine.state = engine.state.clone()
            dummy_engine.game_over = engine.game_over
            
            dummy_engine.execute_move(move)
            self._nodes += 1
            
            score = self._alphabeta(dummy_engine, self.max_depth - 1, alpha, beta, False)
            
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
        if depth == 0 or engine.game_over:
            return evaluate_state(engine.state, self.player_idx)
            
        current_p = engine.state.current_player_idx
        # If it's technically our turn again (e.g., in some weird state), we should maximize.
        maximizing_now = (current_p == self.player_idx)
        
        valid_moves = engine.get_valid_moves(current_p)
        if not valid_moves:
            return evaluate_state(engine.state, self.player_idx)
            
        # We need to clone engine state for simulations inside this node
        base_state = engine.state.clone()
        base_game_over = engine.game_over
            
        if maximizing_now:
            v = -math.inf
            for move in valid_moves:
                engine.state = base_state.clone()
                engine.game_over = base_game_over
                
                engine.execute_move(move)
                
                v = max(v, self._alphabeta(engine, depth-1, alpha, beta, False))
                alpha = max(alpha, v)
                if beta <= alpha:
                    break # Beta cut-off
            return v
        else:
            v = math.inf
            for move in valid_moves:
                engine.state = base_state.clone()
                engine.game_over = base_game_over
                
                engine.execute_move(move)
                
                v = min(v, self._alphabeta(engine, depth-1, alpha, beta, True))
                beta = min(beta, v)
                if beta <= alpha:
                    break # Alpha cut-off
            return v
