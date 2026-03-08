import pygame
import os
import math
from game.entities import Tile, PlayerBoard
from .constants import *

PANEL_W = 260   # width of right-side stats + log column

# Bright display colours for tile names in the move log
LOG_TILE_COLORS = {
    'BLUE':   (60,  130, 230),
    'YELLOW': (210, 170,  20),
    'RED':    (210,  50,  50),
    'GREEN':  (50,  170,  70),
    'WHITE':  (200, 200, 200),
}

class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self.font       = pygame.font.SysFont('Arial', 24)
        self.small_font = pygame.font.SysFont('Arial', 18)
        self.large_font = pygame.font.SysFont('Arial', 36, bold=True)
        self.tile_images = self._load_images()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def get_layout(self):
        w, h = self.screen.get_size()
        cx, cy = w // 2, h // 2

        min_dim = min(w, h)
        factory_radius = max(80, min(150, int(min_dim * 0.15)))

        pad = 20
        right_edge = w - PANEL_W - pad  # boards must stay left of the panel

        positions = [
            (pad,                                    pad),           # top-left
            (right_edge - BOARD_WIDTH,               pad),           # top-right
            (pad,                                    h - BOARD_HEIGHT - pad),   # bot-left
            (right_edge - BOARD_WIDTH,               h - BOARD_HEIGHT - pad),  # bot-right
        ]

        # Shift center so it avoids the right panel
        center_x = (right_edge) // 2
        return {
            'w': w, 'h': h,
            'factory_center': (center_x, cy),
            'factory_radius': factory_radius,
            'player_positions': positions
        }

    # ------------------------------------------------------------------
    # Asset loading
    # ------------------------------------------------------------------
    def _load_images(self):
        images = {}
        color_map = {
            Tile.BLUE:   'blue.png',
            Tile.YELLOW: 'yellow.png',
            Tile.RED:    'red.png',
            Tile.GREEN:  'green.png',
            Tile.WHITE:  'white.png'
        }
        assets_dir = 'assets/tiles'
        for tile, filename in color_map.items():
            path = os.path.join(assets_dir, filename)
            if os.path.exists(path):
                img = pygame.image.load(path).convert_alpha()
                images[tile] = pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
            else:
                images[tile] = None
        return images

    # ------------------------------------------------------------------
    # Tile drawing
    # ------------------------------------------------------------------
    def draw_tile(self, tile, x, y, size=TILE_SIZE, selected=False):
        rect = pygame.Rect(x, y, size, size)
        if tile in self.tile_images and self.tile_images[tile]:
            img = self.tile_images[tile] if size == TILE_SIZE else pygame.transform.scale(self.tile_images[tile], (size, size))
            self.screen.blit(img, (x, y))
        else:
            color = TILE_COLORS.get(tile, TILE_COLORS[Tile.EMPTY])
            pygame.draw.rect(self.screen, color, rect)

        if tile == Tile.FIRST_PLAYER:
            text = self.small_font.render("1st", True, (0, 0, 0))
            self.screen.blit(text, text.get_rect(center=rect.center))

        if tile != Tile.EMPTY:
            border_color = (255, 255, 255) if selected else (0, 0, 0)
            border_width = 3 if selected else 1
            pygame.draw.rect(self.screen, border_color, rect, border_width)

    # ------------------------------------------------------------------
    # Coloured move-log line renderer
    # ------------------------------------------------------------------
    def _draw_log_line(self, text, x, y):
        """Render a log entry with the colour-name token drawn in its colour."""
        # Format: "P1: RED from factory → Line 3"
        # Split on the tile name token
        tokens = text.split()   # ['P1:', 'RED', 'from', ...]
        cx = x
        for tok in tokens:
            colour_name = tok.strip(':').upper()
            tile_col = LOG_TILE_COLORS.get(colour_name)
            fg = tile_col if tile_col else (50, 40, 30)
            surf = self.small_font.render(tok + ' ', True, fg)
            self.screen.blit(surf, (cx, y))
            cx += surf.get_width()

    # ------------------------------------------------------------------
    # Full game state draw
    # ------------------------------------------------------------------
    def draw_game_state(self, game_state, selected_draft=None, highlighted_line=None,
                        mouse_pos=None, move_log=None, move_log_scroll=0, bag_count=0,
                        tiles_placed=0, bot_stats=None, endgame_proximity=0,
                        hint_move=None, player_names=None):
        self.screen.fill(BG_COLOR)
        layout = self.get_layout()
        w, h = layout['w'], layout['h']

        # ── Top bar ──────────────────────────────────────────────────
        round_text  = self.font.render(f"Round: {game_state.round_number}", True, TEXT_COLOR)
        cur_idx     = game_state.current_player_idx
        name        = (player_names[cur_idx] if player_names and cur_idx < len(player_names)
                       else f"Player {cur_idx + 1}")
        player_text = self.large_font.render(f"{name}'s Turn", True, TEXT_COLOR)

        # Round counter — top-left
        self.screen.blit(round_text, (20, 24))
        # Player turn — top-centre (but respect left round text + right panel)
        centre_x = (w - PANEL_W) // 2
        self.screen.blit(player_text, (centre_x - player_text.get_width() // 2, 10))

        # ── Bottom bar ───────────────────────────────────────────────
        undo_rect = pygame.Rect(20, h - 60, 100, 40)
        pygame.draw.rect(self.screen, (200, 190, 180), undo_rect)
        pygame.draw.rect(self.screen, (100, 90, 80), undo_rect, 2)
        undo_text = self.font.render("Undo", True, TEXT_COLOR)
        self.screen.blit(undo_text, (undo_rect.centerx - undo_text.get_width()//2,
                                     undo_rect.centery - undo_text.get_height()//2))

        hotkey_text = self.small_font.render(
            "ESC: Save & Exit  |  R: Restart  |  Q: Quit  |  Scroll: Move Log", True, TEXT_COLOR)
        self.screen.blit(hotkey_text, (140, h - 48))

        # ── Right-side panel ─────────────────────────────────────────
        panel_x = w - PANEL_W - 8
        panel_y = 55

        # Split panel into stats (top) and move log (bottom 260px)
        log_h    = 260
        stats_h  = h - panel_y - log_h - 12

        # Stats background
        stats_rect = pygame.Rect(panel_x, panel_y, PANEL_W, stats_h)
        pygame.draw.rect(self.screen, (225, 218, 205), stats_rect)
        pygame.draw.rect(self.screen, (160, 148, 130), stats_rect, 2)

        sy = panel_y + 10
        def draw_stat(label, val):
            nonlocal sy
            lbl  = self.small_font.render(label, True, (100, 90, 80))
            vlbl = self.font.render(str(val), True, TEXT_COLOR)
            self.screen.blit(lbl,  (panel_x + 8, sy))
            self.screen.blit(vlbl, (panel_x + 8, sy + 17))
            sy += 42

        draw_stat("Tiles in Bag:",   bag_count)
        draw_stat("Tiles Placed:",   tiles_placed)
        draw_stat("Box (discard):", len(game_state.box))

        # Endgame proximity bar
        ep_lbl = self.small_font.render("Endgame Proximity:", True, (100, 90, 80))
        self.screen.blit(ep_lbl, (panel_x + 8, sy))
        sy += 18
        bar_w = PANEL_W - 16
        bar_rect = pygame.Rect(panel_x + 8, sy, bar_w, 14)
        pygame.draw.rect(self.screen, (180, 170, 160), bar_rect)
        fill_w = int(bar_w * (endgame_proximity / 5.0))
        fill_col = ((220, 80, 80) if endgame_proximity >= 4 else
                    (220, 180, 80) if endgame_proximity >= 3 else (80, 160, 80))
        pygame.draw.rect(self.screen, fill_col, pygame.Rect(panel_x + 8, sy, fill_w, 14))
        pygame.draw.rect(self.screen, (120, 110, 100), bar_rect, 1)
        sy += 28

        # Bot stats
        if bot_stats:
            sep = self.small_font.render("── Bot Stats ──", True, (100, 90, 80))
            self.screen.blit(sep, (panel_x + 8, sy))
            sy += 22
            for pidx, stats in bot_stats.items():
                n = player_names[pidx] if player_names and pidx < len(player_names) else f"P{pidx+1}"
                if stats['type'] == 'minimax':
                    draw_stat(f"{n} Nodes/last:", f"{stats['last_nodes']:,}")
                    draw_stat(f"{n} Nodes/total:", f"{stats['total_nodes']:,}")
                    draw_stat(f"{n} Think (ms):", f"{stats['last_think_ms']:.0f}")
                elif stats['type'] == 'mcts':
                    draw_stat(f"{n} Sims/last:", f"{stats['last_simulations']:,}")
                    draw_stat(f"{n} Sims/total:", f"{stats['total_simulations']:,}")
                    draw_stat(f"{n} Think (ms):", f"{stats['last_think_ms']:.0f}")

        # ── Move log panel ──────────────────────────────────────────
        log_y   = h - log_h - 6
        log_rect = pygame.Rect(panel_x, log_y, PANEL_W, log_h)
        pygame.draw.rect(self.screen, (225, 218, 205), log_rect)
        pygame.draw.rect(self.screen, (160, 148, 130), log_rect, 2)

        log_hdr = self.small_font.render("Move History  (scroll ↕):", True, (100, 90, 80))
        self.screen.blit(log_hdr, (panel_x + 8, log_y + 5))

        line_h = 19
        clip_rect = pygame.Rect(panel_x + 4, log_y + 24, PANEL_W - 8, log_h - 30)
        self.screen.set_clip(clip_rect)
        visible_lines = (log_h - 30) // line_h
        if move_log:
            visible = move_log[move_log_scroll: move_log_scroll + visible_lines]
            for li, entry in enumerate(visible):
                self._draw_log_line(entry, panel_x + 6, log_y + 26 + li * line_h)
        self.screen.set_clip(None)

        # ── Factories & Center ───────────────────────────────────────
        self._draw_factories(game_state.factories, layout, selected_draft)
        self._draw_center(game_state.center, layout, selected_draft)

        # ── Player boards ─────────────────────────────────────────────
        for i, player in enumerate(game_state.players):
            pos  = layout['player_positions'][i % 4]
            pname = (player_names[i] if player_names and i < len(player_names)
                     else f"Player {i+1}")
            self._draw_player_board(player, pname, pos[0], pos[1],
                                    game_state.current_player_idx == i, highlighted_line)

        # ── Selected draft label ──────────────────────────────────────
        if selected_draft:
            src_type, src_idx, color = selected_draft
            info_text = self.font.render(
                f"Selected: {color.name} from {src_type} {src_idx if src_type=='factory' else ''}",
                True, HIGHLIGHT_COLOR)
            self.screen.blit(info_text, (centre_x - info_text.get_width() // 2, 55))

        # ── Hint move overlay ─────────────────────────────────────────
        if hint_move:
            color = hint_move['color']
            line  = hint_move['target_line']
            cur_p = game_state.current_player_idx
            bx, by = layout['player_positions'][cur_p % 4]
            start_y = by + 60
            if line >= 0:
                row_y = start_y + line * (TILE_SIZE + PADDING)
                pygame.draw.rect(self.screen, (255, 220, 0),
                                 pygame.Rect(bx + 10, row_y, 220, TILE_SIZE), 3)
                hint_lbl = self.small_font.render(
                    f"Hint: {color.name} → Line {line+1}", True, (200, 160, 0))
            else:
                hint_lbl = self.small_font.render(
                    f"Hint: {color.name} → Floor", True, (200, 160, 0))
            self.screen.blit(hint_lbl, (bx + 10, by + 40))

        # ── Mouse cursor dot ──────────────────────────────────────────
        if mouse_pos:
            pygame.draw.circle(self.screen, (100, 100, 100), mouse_pos, 5, 2)

    # ------------------------------------------------------------------
    # Factories — flat 2×2 grids
    # ------------------------------------------------------------------
    def _draw_factories(self, factories, layout, selected_draft):
        num = len(factories)
        fcx, fcy = layout['factory_center']
        fradius   = layout['factory_radius']
        angle_step = 2 * math.pi / num
        GAP = 4

        for i, factory in enumerate(factories):
            angle = i * angle_step - math.pi / 2
            fx = int(fcx + fradius * math.cos(angle))
            fy = int(fcy + fradius * math.sin(angle))

            block_w = TILE_SIZE * 2 + GAP
            block_h = TILE_SIZE * 2 + GAP
            bx = fx - block_w // 2
            by = fy - block_h // 2

            bg_rect = pygame.Rect(bx - 4, by - 4, block_w + 8, block_h + 8)
            pygame.draw.rect(self.screen, BOARD_BG, bg_rect, border_radius=6)
            pygame.draw.rect(self.screen, (160, 148, 130), bg_rect, 2, border_radius=6)

            positions = [
                (bx,                   by),
                (bx + TILE_SIZE + GAP, by),
                (bx,                   by + TILE_SIZE + GAP),
                (bx + TILE_SIZE + GAP, by + TILE_SIZE + GAP),
            ]
            for j, tile in enumerate(factory.tiles):
                if j < 4:
                    is_sel = (selected_draft and selected_draft[0] == 'factory'
                              and selected_draft[1] == i and selected_draft[2] == tile)
                    self.draw_tile(tile, positions[j][0], positions[j][1], selected=is_sel)

    # ------------------------------------------------------------------
    # Center — compact native-size grid
    # ------------------------------------------------------------------
    def _draw_center(self, center, layout, selected_draft):
        fcx, fcy = layout['factory_center']
        display_tiles = [(i, t) for i, t in enumerate(center.tiles) if t != Tile.EMPTY]

        if not display_tiles:
            lbl = self.small_font.render("Center", True, (160, 148, 130))
            self.screen.blit(lbl, (fcx - lbl.get_width() // 2, fcy - 10))
            return

        GAP  = 6
        COLS = 4
        rows     = (len(display_tiles) + COLS - 1) // COLS
        total_w  = min(len(display_tiles), COLS) * (TILE_SIZE + GAP) - GAP
        total_h  = rows * (TILE_SIZE + GAP) - GAP
        origin_x = fcx - total_w // 2
        origin_y = fcy - total_h // 2

        bg_rect = pygame.Rect(origin_x - 6, origin_y - 6, total_w + 12, total_h + 12)
        pygame.draw.rect(self.screen, BOARD_BG, bg_rect, border_radius=6)
        pygame.draw.rect(self.screen, (160, 148, 130), bg_rect, 2, border_radius=6)

        for idx, (_orig_i, tile) in enumerate(display_tiles):
            row = idx // COLS
            col = idx % COLS
            x   = origin_x + col * (TILE_SIZE + GAP)
            y   = origin_y + row * (TILE_SIZE + GAP)
            is_sel = (selected_draft and selected_draft[0] == 'center'
                      and selected_draft[2] == tile)
            self.draw_tile(tile, x, y, selected=is_sel)

    # ------------------------------------------------------------------
    # Player board
    # ------------------------------------------------------------------
    def _draw_player_board(self, player, text, x, y, is_current, highlighted_line):
        board_rect = pygame.Rect(x, y, BOARD_WIDTH, BOARD_HEIGHT)
        color = (255, 250, 230) if is_current else BOARD_BG
        pygame.draw.rect(self.screen, color, board_rect)
        pygame.draw.rect(self.screen, (100, 90, 80), board_rect, 4 if is_current else 2)

        name_surf = self.font.render(f"{text}  Score: {player.score}", True, TEXT_COLOR)
        self.screen.blit(name_surf, (x + 10, y + 10))

        start_y   = y + 42           # tighter so floor fits within BOARD_HEIGHT
        pattern_x = x + 200          # right edge of pattern lines (row 5 ends here)
        wall_x    = x + 215          # left edge of wall (small gap after pattern)

        # Pattern Lines (right-aligned inside left half of board)
        for r in range(5):
            line = player.pattern_lines[r]
            for c in range(r + 1):
                tx = pattern_x - c * (TILE_SIZE + PADDING)
                ty = start_y + r * (TILE_SIZE + PADDING)

                if is_current and highlighted_line == r:
                    pygame.draw.rect(self.screen, HIGHLIGHT_COLOR,
                                     (tx - 2, ty - 2, TILE_SIZE + 4, TILE_SIZE + 4), 2)

                pygame.draw.rect(self.screen, (200, 190, 180), (tx, ty, TILE_SIZE, TILE_SIZE))

                # Tiles are placed right-to-left: rightmost slot = index 0
                slot = r - c          # slot 0 is rightmost
                if slot < line['count']:
                    self.draw_tile(line['color'], tx, ty)

        # Wall (5×5)
        for r in range(5):
            for c in range(5):
                tx = wall_x + c * (TILE_SIZE + PADDING)
                ty = start_y + r * (TILE_SIZE + PADDING)
                wall_color = PlayerBoard.WALL_PATTERN[r][c]
                if player.wall[r][c]:
                    self.draw_tile(wall_color, tx, ty)
                else:
                    s = pygame.Surface((TILE_SIZE, TILE_SIZE))
                    s.set_alpha(128)
                    s.fill(TILE_COLORS[wall_color])
                    self.screen.blit(s, (tx, ty))
                    pygame.draw.rect(self.screen, (180, 170, 160),
                                     (tx, ty, TILE_SIZE, TILE_SIZE), 1)

        # Floor Line
        floor_y = start_y + 5 * (TILE_SIZE + PADDING) + 10
        floor_x = x + 10
        floor_text = self.small_font.render("Floor:", True, TEXT_COLOR)
        self.screen.blit(floor_text, (floor_x, floor_y + 10))

        for i in range(7):
            tx = floor_x + 55 + i * (TILE_SIZE + PADDING)
            pygame.draw.rect(self.screen, (200, 190, 180), (tx, floor_y, TILE_SIZE, TILE_SIZE))
            pen_text = self.small_font.render(str(PlayerBoard.FLOOR_PENALTIES[i]), True, ERROR_COLOR)
            self.screen.blit(pen_text, (tx + 8, floor_y + TILE_SIZE + 3))

            if is_current and highlighted_line == -1:
                pygame.draw.rect(self.screen, HIGHLIGHT_COLOR,
                                 (tx - 2, floor_y - 2, TILE_SIZE + 4, TILE_SIZE + 4), 2)

            if i < len(player.floor_line):
                self.draw_tile(player.floor_line[i], tx, floor_y)
