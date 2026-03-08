# Speeding up MCTS in Azul

Monte Carlo Tree Search (MCTS) relies on performing as many simulations as possible. Here is how to maximize its efficiency:

## 1. Heuristic-Guided Rollout (RAVE / AMAF)
The current "Rollout" phase picks moves randomly. Using a "light" heuristic to pick better moves during the simulation phase leads to more accurate win/loss statistics with fewer iterations.
- **Rapid Action Value Estimation (RAVE)**: Share information between different branches of the tree if they involve the same move.
- **AMAF (All Moves As First)**: Update statistics for all moves made during a rollout, not just the one being expanded.

## 2. Parallelization
MCTS is naturally parallelizable.
- **Root Parallelization**: Run N separate MCTS trees in parallel on different CPU cores, then merge their results (vote on the best move) at the end. In Python, use `multiprocessing` to bypass the GIL.
- **Leaf Parallelization**: Run multiple rollouts from the same leaf node in parallel.

## 3. State Caching & Fast Cloning
Like Minimax, the `state.clone()` call is a major bottleneck in the simulation loop.
- **Simulation Pools**: Reuse `GameState` objects instead of creating new ones for every iteration.
- **Condensed State**: Use a more compact representation (e.g., NumPy arrays or bitsets) for the simulation engine to reduce the overhead of `execute_move`.

## 4. Early Simulation Exit
Not every simulation needs to reach the end of the game.
- **Max Depth**: Cap the simulation depth (e.g., 20 moves) and use the `evaluate_state` heuristic to estimate the winner rather than waiting for a full game completion.

## 5. Tree Pruning & Progressive Widening
- **Pruning**: If a move is clearly terrible after a few simulations, stop exploring it entirely.
- **Progressive Widening**: Only consider a small subset of the most promising moves initially, and gradually add more "untried moves" as the number of simulations for that node increases.
