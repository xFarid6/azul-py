from enum import IntEnum
import random

class Tile(IntEnum):
    EMPTY = 0
    BLUE = 1
    YELLOW = 2
    RED = 3
    GREEN = 4
    WHITE = 5
    FIRST_PLAYER = -1

class Bag:
    __slots__ = ['tiles']
    def __init__(self, tiles=None):
        if tiles is None:
            # Standard Azul bag: 20 of each color
            self.tiles = [Tile.BLUE]*20 + [Tile.YELLOW]*20 + [Tile.RED]*20 + [Tile.GREEN]*20 + [Tile.WHITE]*20
        else:
            self.tiles = list(tiles)
        random.shuffle(self.tiles)
        
    def draw(self, n):
        drawn = []
        for _ in range(n):
            if not self.tiles:
                break
            drawn.append(self.tiles.pop())
        return drawn
        
    def refill(self, box_tiles):
        self.tiles.extend(box_tiles)
        random.shuffle(self.tiles)

    def is_empty(self):
        return len(self.tiles) == 0

    def to_dict(self):
        return {'tiles': [int(t) for t in self.tiles]}

    def copy_from(self, other):
        self.tiles = list(other.tiles)


    @classmethod
    def from_dict(cls, data):
        b = cls()
        b.tiles = [Tile(t) for t in data['tiles']]
        return b

class Factory:
    __slots__ = ['tiles']
    def __init__(self):
        self.tiles = []
        
    def fill(self, tiles):
        self.tiles = tiles
        
    def take(self, color):
        """Takes all tiles of the specified color. Returns (taken, remaining)."""
        taken = [t for t in self.tiles if t == color]
        remaining = [t for t in self.tiles if t != color]
        self.tiles = []
        return taken, remaining
        
    def is_empty(self):
        return len(self.tiles) == 0

    def copy_from(self, other):
        self.tiles = list(other.tiles)

    def to_dict(self):
        return {'tiles': [int(t) for t in self.tiles]}

    @classmethod
    def from_dict(cls, data):
        f = cls()
        f.tiles = [Tile(t) for t in data['tiles']]
        return f

class Center:
    __slots__ = ['tiles']
    def __init__(self):
        self.tiles = [Tile.FIRST_PLAYER]
        
    def add(self, tiles):
        self.tiles.extend(tiles)
        
    def take(self, color):
        """Takes all tiles of the specified color, plus the first player token if present. Returns (taken, remaining)."""
        taken = [t for t in self.tiles if t == color]
        remaining = [t for t in self.tiles if t != color]
        
        # Check if first player token is still in center
        if Tile.FIRST_PLAYER in self.tiles:
            taken.append(Tile.FIRST_PLAYER)
            remaining.remove(Tile.FIRST_PLAYER)
            
        self.tiles = remaining
        return taken
        
    def is_empty(self):
        # Empty if only EMPTY tiles are inside, or truly empty. 
        # But actually in Azul, center is empty if no colored tiles are present.
        return not any(t != Tile.FIRST_PLAYER and t != Tile.EMPTY for t in self.tiles)

    def copy_from(self, other):
        self.tiles = list(other.tiles)

    def to_dict(self):
        return {'tiles': [int(t) for t in self.tiles]}

    @classmethod
    def from_dict(cls, data):
        c = cls()
        c.tiles = [Tile(t) for t in data['tiles']]
        return c

class PlayerBoard:
    # Wall colors for each row. 
    # Example for row 0: Blue, Yellow, Red, Green, White
    # But in Azul, the pattern is offset.
    # Row 0: B Y R G W
    # Row 1: W B Y R G
    # Row 2: G W B Y R
    # Row 3: R G W B Y
    # Row 4: Y R G W B
    WALL_PATTERN = [
        [Tile.BLUE, Tile.YELLOW, Tile.RED, Tile.GREEN, Tile.WHITE],
        [Tile.WHITE, Tile.BLUE, Tile.YELLOW, Tile.RED, Tile.GREEN],
        [Tile.GREEN, Tile.WHITE, Tile.BLUE, Tile.YELLOW, Tile.RED],
        [Tile.RED, Tile.GREEN, Tile.WHITE, Tile.BLUE, Tile.YELLOW],
        [Tile.YELLOW, Tile.RED, Tile.GREEN, Tile.WHITE, Tile.BLUE]
    ]

    FLOOR_PENALTIES = [-1, -1, -2, -2, -2, -3, -3]
    __slots__ = ['score', 'pattern_lines', 'wall_mask', 'floor_line']

    def __init__(self):
        self.score = 0
        # Pattern lines: index 0 can hold 1 tile, index 4 can hold 5 tiles.
        # Stored as dictionaries: { 'color': Tile.EMPTY, 'count': 0 }
        self.pattern_lines = [{'color': Tile.EMPTY, 'count': 0} for _ in range(5)]
        
        # Wall is 25-bit mask (5x5). row r, col c -> bit (r*5 + c)
        self.wall_mask = 0
        
        # Floor line holds up to 7 tiles (the first player token and overflows)
        self.floor_line = []

    def clone(self):
        b = PlayerBoard()
        b.score = self.score
        b.pattern_lines = [dict(p) for p in self.pattern_lines]
        b.wall_mask = self.wall_mask
        b.floor_line = list(self.floor_line)
        return b

    @property
    def wall(self):
        """Compatibility property for UI/tests. Returns 2D list."""
        res = [[False for _ in range(5)] for _ in range(5)]
        for r in range(5):
            for c in range(5):
                if (self.wall_mask >> (r * 5 + c)) & 1:
                    res[r][c] = True
        return res

    def to_dict(self):
        return {
            'score': self.score,
            'pattern_lines': [{'color': int(p['color']), 'count': p['count']} for p in self.pattern_lines],
            'wall_mask': self.wall_mask,
            'floor_line': [int(t) for t in self.floor_line]
        }

    def copy_from(self, other):
        self.score = other.score
        for i in range(5):
            self.pattern_lines[i]['color'] = other.pattern_lines[i]['color']
            self.pattern_lines[i]['count'] = other.pattern_lines[i]['count']
        self.wall_mask = other.wall_mask
        self.floor_line = list(other.floor_line)


    @classmethod
    def from_dict(cls, data):
        b = cls()
        b.score = data['score']
        b.pattern_lines = [{'color': Tile(p['color']), 'count': p['count']} for p in data['pattern_lines']]
        b.wall_mask = data.get('wall_mask', 0)
        # Handle migration from old 'wall' list format if needed
        if 'wall' in data:
            for r in range(5):
                for c in range(5):
                    if data['wall'][r][c]:
                        b.wall_mask |= (1 << (r * 5 + c))
        b.floor_line = [Tile(t) for t in data['floor_line']]
        return b

    def add_to_pattern_line(self, line_index, tiles):
        """
        Adds tiles to the specified pattern line (0-4).
        If line_index is -1, it goes straight to the floor.
        Returns the number of tiles that overflowed to the floor.
        """
        if not tiles:
            return 0
            
        # First player token always goes to floor immediately
        first_player_token = False
        if Tile.FIRST_PLAYER in tiles:
            tiles.remove(Tile.FIRST_PLAYER)
            self.add_to_floor([Tile.FIRST_PLAYER])
            if not tiles:
                return 0

        color = tiles[0]

        if line_index == -1:
            self.add_to_floor(tiles)
            return len(tiles)

        line_capacity = line_index + 1
        line = self.pattern_lines[line_index]
        
        if line['count'] == 0:
            line['color'] = color
            
        space_left = line_capacity - line['count']
        added = min(space_left, len(tiles))
        line['count'] += added
        
        overflow = len(tiles) - added
        if overflow > 0:
            overflow_tiles = [color] * overflow
            self.add_to_floor(overflow_tiles)
            
        return overflow

    def add_to_floor(self, tiles):
        """Adds tiles to the floor line, up to the maximum of 7."""
        space_left = 7 - len(self.floor_line)
        added = min(space_left, len(tiles))
        self.floor_line.extend(tiles[:added])
        # Tiles beyond 7 are technically discarded (back to box), but we might need to handle returning them to the box.
        # This will be handled by the GameEngine which checks how many tiles were added.
        return len(tiles) - added

    def can_place_on_pattern_line(self, line_index, color):
        """Checks if a color can be placed on a specific pattern line."""
        if line_index == -1:
            return True # Can always place on floor
            
        line = self.pattern_lines[line_index]
        
        # Check if line is full
        if line['count'] >= line_index + 1:
            return False
            
        # Check if line has a different color
        if line['count'] > 0 and line['color'] != color:
            return False
            
        # Check if color is already on the corresponding wall row
        col = self.WALL_PATTERN[line_index].index(color)
        if (self.wall_mask >> (line_index * 5 + col)) & 1:
            return False
            
        return True
