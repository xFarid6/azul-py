import time
import numpy as np
from bots.heuristic import evaluate_state, _evaluate_player_jit
from game.engine import GameEngine

def benchmark():
    engine = GameEngine(num_players=2)
    state = engine.state
    
    # Warm up JIT
    evaluate_state(state, 0)
    
    N = 10000
    start = time.time()
    for _ in range(N):
        evaluate_state(state, 0)
    end = time.time()
    print(f'JIT Eval time (with wrapper) for {N} calls: {end - start:.4f}s')
    print(f'Avg time per call: {(end - start)/N*1000000:.2f}us')

    # Benchmark raw JIT function (no wrapper)
    player = state.players[0]
    pattern_colors = (int(player.pattern_lines[0]["color"]), int(player.pattern_lines[1]["color"]), int(player.pattern_lines[2]["color"]), int(player.pattern_lines[3]["color"]), int(player.pattern_lines[4]["color"]))
    pattern_counts = (player.pattern_lines[0]["count"], player.pattern_lines[1]["count"], player.pattern_lines[2]["count"], player.pattern_lines[3]["count"], player.pattern_lines[4]["count"])
    floor_len = len(player.floor_line)
    
    start = time.time()
    for _ in range(N):
        _evaluate_player_jit(player.score, player.wall_mask, pattern_colors, pattern_counts, floor_len)
    end = time.time()
    print(f'Raw JIT Eval time (no wrapper) for {N} calls: {end - start:.4f}s')
    print(f'Avg time per call: {(end - start)/N*1000000:.2f}us')

if __name__ == '__main__':
    benchmark()
