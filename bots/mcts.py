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
        
        # RAVE stats: { (source_type, source_idx, color, target_line): [visits, value] }
        self.rave_visits = 0
        self.rave_value = 0.0
        # For simplicity, nodes will store RAVE stats for their own move in the parent's context
        # but actually RAVE often uses a global table or node-local table for actions.
        # Let's use node-local action stats for RAVE/AMAF.
        self.action_rave_stats = {} # move_tuple -> [visits, value]

class MCTSBot(Bot):
    def __init__(self, player_idx, iterations=200, max_time=None):
        super().__init__(player_idx)
        self.iterations = iterations
        # Stats
        self.total_simulations = 0
        self.last_simulations = 0
        self.last_think_ms = 0
        
import multiprocessing

def _mcts_search_task(engine_state, player_idx, iterations, game_over):
    engine = GameEngine(engine_state.num_players)
    engine.state.copy_from(engine_state)
    engine.game_over = game_over
    
    valid_moves = engine.get_valid_moves(player_idx)
    if not valid_moves:
        return {}
        
    root = MCTSNode()
    root.untried_moves = valid_moves
    
    # Reuse engine and state objects
    sim_engine = GameEngine(engine.state.num_players)
    
    for i in range(iterations):
        node = root
        sim_engine.reset_to_state(engine.state, engine.game_over)
        
        # 1. Selection
        while True:
            if node.untried_moves != [] and (len(node.children) < 1 + 1.0 * math.pow(node.visits, 0.5)):
                break
            if node.children == []:
                break
            # select_child logic inline or as a helper
            best_score = -1e9
            best_child = None
            b_equiv = 100
            for child in node.children:
                exploit = child.value / child.visits
                explore = math.sqrt(2.0 * math.log(node.visits) / child.visits)
                uct_score = exploit + explore
                move_tuple = (child.move['source_type'], child.move['source_idx'], child.move['color'], child.move['target_line'])
                if move_tuple in node.action_rave_stats:
                    rave_visits, rave_val = node.action_rave_stats[move_tuple]
                    rave_score = rave_val / rave_visits
                    beta = math.sqrt(b_equiv / (3.0 * node.visits + b_equiv))
                    score = (1.0 - beta) * uct_score + beta * rave_score
                else:
                    score = uct_score
                if score > best_score:
                    best_score = score
                    best_child = child
            
            if not best_child: break
            node = best_child
            sim_engine.execute_move(node.move)
            if sim_engine.game_over: break
            
        # 2. Expansion
        if not sim_engine.game_over and node.untried_moves != []:
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
        max_rollout_depth = 20
        rollout_moves = []
        while not sim_engine.game_over and depth < max_rollout_depth:
            moves = sim_engine.get_valid_moves(sim_engine.state.current_player_idx)
            if not moves: break
            best_moves = [m for m in moves if m['target_line'] != -1]
            if not best_moves: best_moves = moves
            move = random.choice(best_moves)
            move_tuple = (move['source_type'], move['source_idx'], move['color'], move['target_line'])
            rollout_moves.append((sim_engine.state.current_player_idx, move_tuple))
            sim_engine.execute_move(move)
            depth += 1
            
        # 4. Backprop
        eval_score = evaluate_state(sim_engine.state, player_idx)
        reward = 0.5 + max(-0.5, min(0.5, eval_score / 40.0))
        path_node = node
        while path_node is not None:
            path_node.visits += 1
            if path_node.player_just_moved == player_idx:
                path_node.value += reward
            else:
                path_node.value += (1.0 - reward)
            for p_idx, m_tuple in rollout_moves:
                if m_tuple not in path_node.action_rave_stats:
                    path_node.action_rave_stats[m_tuple] = [0, 0.0]
                path_node.action_rave_stats[m_tuple][0] += 1
                if p_idx == player_idx:
                    path_node.action_rave_stats[m_tuple][1] += reward
                else:
                    path_node.action_rave_stats[m_tuple][1] += (1.0 - reward)
            path_node = path_node.parent
            
    # Return move visits for merging
    results = {}
    for child in root.children:
        move_tuple = (child.move['source_type'], child.move['source_idx'], child.move['color'], child.move['target_line'])
        results[move_tuple] = (child.visits, child.value, child.move)
    return results

class MCTSBot(Bot):
    def __init__(self, player_idx, iterations=200, max_time=None, num_processes=None):
        super().__init__(player_idx)
        self.iterations = iterations
        self.num_processes = num_processes or max(1, multiprocessing.cpu_count() - 1)
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
            
        # Root Parallelization
        if self.num_processes > 1:
            iters_per_proc = self.iterations // self.num_processes
            args = (engine.state, self.player_idx, iters_per_proc, engine.game_over)
            
            with multiprocessing.Pool(processes=self.num_processes) as pool:
                tasks = [args] * self.num_processes
                results_list = pool.starmap(_mcts_search_task, tasks)
        else:
            # Sequential execution for debugging
            res = _mcts_search_task(engine.state, self.player_idx, self.iterations, engine.game_over)
            results_list = [res]
            
        # Merge results
        merged_visits = {}
        move_objects = {}
        for res_dict in results_list:
            for m_tuple, (visits, value, move_obj) in res_dict.items():
                if m_tuple not in merged_visits:
                    merged_visits[m_tuple] = 0
                    move_objects[m_tuple] = move_obj
                merged_visits[m_tuple] += visits
                
        if not merged_visits:
            return random.choice(valid_moves)
            
        best_tuple = max(merged_visits.keys(), key=lambda t: merged_visits[t])
        
        elapsed = (time.time() - t_start) * 1000
        self.last_think_ms = elapsed
        self.last_simulations = self.iterations
        self.total_simulations += self.iterations
        
        return move_objects[best_tuple]
