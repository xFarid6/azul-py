from .entities import PlayerBoard, Factory, Center, Bag, Tile

class GameState:
    def __init__(self, num_players=2):
        self.num_players = num_players
        self.bag = Bag()
        self.box = [] # Discard pile
        
        self.factories = [Factory() for _ in range(self._num_factories(num_players))]
        self.center = Center()
        
        self.players = [PlayerBoard() for _ in range(num_players)]
        
        self.current_player_idx = 0
        self.next_first_player_idx = 0
        
        self.round_number = 1

    def _num_factories(self, num_players):
        if num_players == 2: return 5
        if num_players == 3: return 7
        if num_players == 4: return 9
        return 5

    def clone(self):
        """Deep copy for AI simulation"""
        cloned = GameState(self.num_players)
        cloned.bag = Bag(self.bag.tiles.copy())
        cloned.box = self.box.copy()
        
        for i, factory in enumerate(self.factories):
            cloned.factories[i].tiles = factory.tiles.copy()
            
        cloned.center.tiles = self.center.tiles.copy()
        
        cloned.players = [p.clone() for p in self.players]
        
        cloned.current_player_idx = self.current_player_idx
        cloned.next_first_player_idx = self.next_first_player_idx
        cloned.round_number = self.round_number
        
        return cloned
        
    def is_round_over(self):
        """Round is over when all factories and center are empty."""
        for f in self.factories:
            if not f.is_empty():
                return False
        return self.center.is_empty()
