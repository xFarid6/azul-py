# Speeding up Minimax in Azul

Minimax with Alpha-Beta pruning is a powerful algorithm, but its performance depends heavily on the search depth. Here are strategies to speed it up:

## 1. Move Ordering (CRITICAL)
Alpha-Beta pruning works best when the "best" moves are explored first. This causes more frequent beta cut-offs, significantly reducing the number of nodes visited.
- **Heuristic sorting**: Sort the list of available moves using a simple heuristic (e.g., moves that complete a high-scoring row or grab more tiles) before calling `_alphabeta`.
- **Killer Heuristic**: Store moves that previously caused a cut-off and try them first in similar board states.

## 2. Transposition Tables (Zobrist Hashing)
Many different sequences of moves lead to the exact same game state. 
- **Zobrist Hashing**: Assign a unique random 64-bit integer to each possible tile-at-position combination. The hash of a state is the XOR of all active components.
- **Cache**: Store the evaluation of a hashed state. If you encounter the same hash at the same or greater depth, skip the search.

## 3. State Representation & Cloning
The current implementation clones the entire `GameState` object frequently, which is expensive in Python.
- **In-place updates**: Instead of `clone()`, modify the state, perform the recursive search, and then "undo" the move (reverse the changes). This avoids memory allocation overhead.
- **Bitboards**: Represent the wall as a 25-bit integer (5x5). Bitwise operations for adjacency checks and scoring are orders of magnitude faster than nested list lookups.

## 4. Iterative Deepening
Instead of searching to a fixed depth, search to depth 1, then 2, then 3, until a time limit is reached.
- This allows the bot to always return the best move found so far if the user wants a fast response.
- It also populates the Transposition Table with good move candidates for deeper searches.

## 5. Cython or Numba
Python's recursion and object overhead are the primary bottlenecks.
- Moving the core `_alphabeta` loop into **Cython** or using **Numba**'s `@jit` can provide a 10x-50x speedup, allowing for much deeper searches (depth 6+).
