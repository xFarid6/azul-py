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
        import copy
        return copy.deepcopy(self)

    def to_dict(self):
        return {
            'num_players': self.num_players,
            'bag': self.bag.to_dict(),
            'box': [int(t) for t in self.box],
            'factories': [f.to_dict() for f in self.factories],
            'center': self.center.to_dict(),
            'players': [p.to_dict() for p in self.players],
            'current_player_idx': self.current_player_idx,
            'next_first_player_idx': self.next_first_player_idx,
            'round_number': self.round_number
        }

    @classmethod
    def from_dict(cls, data):
        s = cls(data['num_players'])
        s.bag = Bag.from_dict(data['bag'])
        s.box = [Tile(t) for t in data['box']]
        s.factories = [Factory.from_dict(f) for f in data['factories']]
        s.center = Center.from_dict(data['center'])
        s.players = [PlayerBoard.from_dict(p) for p in data['players']]
        s.current_player_idx = data['current_player_idx']
        s.next_first_player_idx = data['next_first_player_idx']
        s.round_number = data['round_number']
        return s
        
    def is_round_over(self):
        """Round is over when all factories and center are empty."""
        for f in self.factories:
            if not f.is_empty():
                return False
        return self.center.is_empty()
