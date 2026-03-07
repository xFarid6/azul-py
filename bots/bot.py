class Bot:
    def __init__(self, player_idx):
        self.player_idx = player_idx
        
    def get_best_move(self, engine):
        """
        Takes the current game engine (which has state) and returns a valid move dict.
        """
        raise NotImplementedError()
