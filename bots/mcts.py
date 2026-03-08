from .bot import Bot
from game.engine import GameEngine
from .heuristic import evaluate_state
import math
import random
import time

class MCTSNode:
    def __init__(self, move=None, parent=None):
        self.move = move
        self.parent = parent
        self.children = []
        self.visits = 0
        self.value = 0.0
        self.untried_moves = []
        self.player_just_moved = None

class MCTSBot(Bot):
    def __init__(self, player_idx, iterations=200, max_time=None):
        super().__init__(player_idx)
        self.iterations = iterations
        # Stats
        self.total_simulations = 0
        self.last_simulations = 0
        self.last_think_ms = 0
        
    def get_best_move(self, engine):
        t_start = time.time()
        valid_moves = engine.get_valid_moves(self.player_idx)
        if not valid_moves:
            return None
        if len(valid_moves) == 1:
            self.last_simulations = 0
            self.last_think_ms = 0
            return valid_moves[0]
            
        root = MCTSNode()
        root.untried_moves = valid_moves
        
        for i in range(self.iterations):
            node = root
            sim_engine = GameEngine(engine.state.num_players)
            sim_engine.state = engine.state.clone()
            sim_engine.game_over = engine.game_over
            
            # 1. Selection
            while node.untried_moves == [] and node.children != []:
                node = self._select_child(node)
                sim_engine.execute_move(node.move)
                
            # 2. Expansion
            if node.untried_moves != []:
                move = random.choice(node.untried_moves)
                node.untried_moves.remove(move)
                
                current_p = sim_engine.state.current_player_idx
                sim_engine.execute_move(move)
                
                child = MCTSNode(move=move, parent=node)
                child.player_just_moved = current_p
                
                if not sim_engine.game_over:
                    child.untried_moves = sim_engine.get_valid_moves(sim_engine.state.current_player_idx)
                    
                node.children.append(child)
                node = child
                
            # 3. Rollout
            depth = 0
            while not sim_engine.game_over and depth < 10:
                moves = sim_engine.get_valid_moves(sim_engine.state.current_player_idx)
                if not moves: break
                best_moves = [m for m in moves if m['target_line'] != -1]
                if not best_moves: best_moves = moves
                sim_engine.execute_move(random.choice(best_moves))
                depth += 1
                
            # 4. Backpropagation
            eval_score = evaluate_state(sim_engine.state, self.player_idx)
            reward = 0.5 + max(-0.5, min(0.5, eval_score / 20.0))
            
            while node is not None:
                node.visits += 1
                if node.player_just_moved == self.player_idx:
                    node.value += reward
                else:
                    node.value += (1.0 - reward)
                node = node.parent
                
        elapsed = (time.time() - t_start) * 1000
        self.last_think_ms = elapsed
        self.last_simulations = self.iterations
        self.total_simulations += self.iterations
        
        best_child = max(root.children, key=lambda c: c.visits)
        return best_child.move
        
    def _select_child(self, node):
        best_score = -1
        best_child = None
        for child in node.children:
            exploit = child.value / child.visits
            explore = math.sqrt(2.0 * math.log(node.visits) / child.visits)
            score = exploit + explore
            if score > best_score:
                best_score = score
                best_child = child
        return best_child
