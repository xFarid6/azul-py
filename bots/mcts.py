from .bot import Bot
from game.engine import GameEngine
from .heuristic import evaluate_state
import math
import random

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
    def __init__(self, player_idx, iterations=1000, max_time=None):
        super().__init__(player_idx)
        self.iterations = iterations
        
    def get_best_move(self, engine):
        valid_moves = engine.get_valid_moves(self.player_idx)
        if not valid_moves:
            return None
        if len(valid_moves) == 1:
            return valid_moves[0]
            
        root = MCTSNode()
        root.untried_moves = valid_moves
        
        for _ in range(self.iterations):
            node = root
            # Clone state for simulation
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
                
                # Check player before moving
                current_p = sim_engine.state.current_player_idx
                sim_engine.execute_move(move)
                
                child = MCTSNode(move=move, parent=node)
                child.player_just_moved = current_p
                
                # Get valid moves for the next player
                if not sim_engine.game_over:
                    child.untried_moves = sim_engine.get_valid_moves(sim_engine.state.current_player_idx)
                    
                node.children.append(child)
                node = child
                
            # 3. Rollout / Simulation
            # Instead of a full random rollout to the end of the game (which takes too long in Azul),
            # we do a limited rollout or just use the heuristic.
            depth = 0
            while not sim_engine.game_over and depth < 10:
                moves = sim_engine.get_valid_moves(sim_engine.state.current_player_idx)
                if not moves: break
                # Simple light heuristic for rollout: prefer not floor
                best_moves = [m for m in moves if m['target_line'] != -1]
                if not best_moves: best_moves = moves
                sim_engine.execute_move(random.choice(best_moves))
                depth += 1
                
            # 4. Backpropagation
            # evaluate_state returns positive if good for our bot's player_idx
            # We need to map this to a [0, 1] reward for the specific nodes.
            # Actually, evaluate_state is relative to self.player_idx.
            eval_score = evaluate_state(sim_engine.state, self.player_idx)
            # Normalize basic score delta to roughly 0..1
            reward = 0.5 + max(-0.5, min(0.5, eval_score / 20.0))
            
            while node is not None:
                node.visits += 1
                # If the player who just moved is us, we want the reward.
                # If it's the opponent, they want the opposite (1 - reward).
                if node.player_just_moved == self.player_idx:
                    node.value += reward
                else:
                    node.value += (1.0 - reward)
                node = node.parent
                
        # Return best move (most visited)
        best_child = max(root.children, key=lambda c: c.visits)
        return best_child.move
        
    def _select_child(self, node):
        # UCB1 formula
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
