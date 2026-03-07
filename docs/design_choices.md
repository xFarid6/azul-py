# Design Choices for Azul Python

This document outlines the architectural and design decisions made while developing the Azul clone in Python.

## 1. Separation of Concerns (SRP)
- **Game Engine vs UI**: The core logic (`game/`) holds the true state of the game. It knows nothing about pixels, fonts, or Pygame events. The Pygame UI (`ui/`) will only read the state and pass moves to the engin using simple logical objects/integers.
- **Bot Interface**: Bots are treated as a separate entity that queries the generic `GameEngine` for valid moves, applies them on cloned states, and evaluates them.

## 2. State Representation
- **Immutable/Clonable States**: To accommodate the Minimax and MCTS bots, the `GameState` must be deeply clonable (via a `clone` method or standard `copy.deepcopy` if optimized).
- **Pattern Lines & Wall**: Arrays of integers representing colors (0=Empty, 1=Blue, 2=Yellow, 3=Red, 4=Black, 5=White, -1=FirstPlayer). 

## 3. Bot Implementations
- **Minimax**: Implements Alpha-Beta pruning out of the box. Since the branching factor can reach 5 (colors) * (5 possible lines + Floor) * 5-9 factories/center = ~150 possible drafts, pruning and caching (transposition tables) are critical.
- **MCTS**: Due to the randomness of the bag in upper nodes, MCTS is often well-suited. MCTS handles the simulation gracefully without relying on a rigid heuristic, though a light heuristic scoring may be used in rollout to prevent completely random (and very poor) playouts.

## 4. Pygame Architecture
- A central `Director` or `App` class manages scenes (Menu, Game, End Screen).
- Drawing the board leverages the generated extracted tile images directly, saving memory by loading the 5 images once and rendering them dynamically.
