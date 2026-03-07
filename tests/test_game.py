import unittest
from game.entities import Tile, PlayerBoard, Factory, Center, Bag
from game.engine import GameEngine

class TestGameEngine(unittest.TestCase):
    def test_setup_round(self):
        engine = GameEngine(num_players=2)
        # 5 factories, each with 4 tiles
        self.assertEqual(len(engine.state.factories), 5)
        for f in engine.state.factories:
            self.assertEqual(len(f.tiles), 4)
        # Center should have 1 first player token
        self.assertEqual(len(engine.state.center.tiles), 1)
        self.assertEqual(engine.state.center.tiles[0], Tile.FIRST_PLAYER)
        # Bag should have 100 - 20 = 80 tiles
        self.assertEqual(len(engine.state.bag.tiles), 80)

    def test_get_valid_moves(self):
        engine = GameEngine(num_players=2)
        
        # Override factory 0 to have predictable tiles
        engine.state.factories[0].fill([Tile.RED, Tile.RED, Tile.BLUE, Tile.YELLOW])
        
        moves = engine.get_valid_moves(0)
        self.assertTrue(len(moves) > 0)
        
        # We should be able to draft RED from factory 0 and put it on lines 0-4 or floor (-1)
        red_moves_from_0 = [m for m in moves if m['source_type'] == 'factory' and m['source_idx'] == 0 and m['color'] == Tile.RED]
        self.assertEqual(len(red_moves_from_0), 6) # 5 pattern lines + floor

        # After a move, state should change
        move = red_moves_from_0[0]
        engine.execute_move(move)
        
        # Factory 0 should be empty
        self.assertTrue(engine.state.factories[0].is_empty())
        
        # Center should have the leftover tiles: BLUE, YELLOW + FIRST_PLAYER
        self.assertEqual(len(engine.state.center.tiles), 3)
        self.assertTrue(Tile.BLUE in engine.state.center.tiles)
        self.assertTrue(Tile.YELLOW in engine.state.center.tiles)
        
        # Current player should be 1
        self.assertEqual(engine.state.current_player_idx, 1)

    def test_scoring_and_floor(self):
        engine = GameEngine(num_players=2)
        player = engine.state.players[0]
        
        # Force tiles to pattern lines to test scoring
        player.pattern_lines[0] = {'color': Tile.RED, 'count': 1}
        player.pattern_lines[1] = {'color': Tile.BLUE, 'count': 2}
        player.pattern_lines[2] = {'color': Tile.YELLOW, 'count': 2} # Incomplete
        
        # Force floor line
        player.floor_line = [Tile.FIRST_PLAYER, Tile.BLACK, Tile.BLACK]
        
        # Trigger round over
        for f in engine.state.factories:
            f.tiles = []
        engine.state.center.tiles = []
        
        engine._score_round()
        
        # Red on line 0 -> wall[0][2] (from WALL_PATTERN)
        self.assertTrue(player.wall[0][2])
        self.assertEqual(player.pattern_lines[0]['count'], 0)
        
        # Blue on line 1 -> wall[1][1]
        self.assertTrue(player.wall[1][1])
        self.assertEqual(player.pattern_lines[1]['count'], 0)
        
        # Yellow on line 2 -> Still incomplete
        self.assertEqual(player.pattern_lines[2]['count'], 2)
        
        # Score calculation:
        # Red tile -> 1 point, Blue tile -> 1 point = 2 points
        # Floor line penalties: FIRST_PLAYER (-1), BLACK (-1), BLACK (-2) = -4 points
        # Score cannot go below 0, so 0.
        self.assertEqual(player.score, 0)
        
        # Test adjacency scoring
        player.score = 10
        player.pattern_lines[0] = {'color': Tile.BLUE, 'count': 1} # wall[0][0]
        player.wall[0][2] = True # existing Red
        player.wall[0][1] = True # existing Yellow
        
        engine._score_round()
        
        # Blue at 0,0. Horizontal adjacent to 0,1 and 0,2. Length = 3.
        # So score should increase by 3.
        self.assertEqual(player.score, 13)

if __name__ == '__main__':
    unittest.main()
