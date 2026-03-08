import pygame
import sys
import argparse
import json
import os
import datetime
import glob
from game.engine import GameEngine
from ui.renderer import Renderer
from ui.input import InputManager
from ui.constants import WINDOW_WIDTH, WINDOW_HEIGHT, FPS, PANEL_W
from bots import MinimaxBot, MCTSBot

class AzulGame:
    def __init__(self, screen, clock, num_players=2, bots=None, show_hint=False, bot_delay=0.25, player_names=None):
        self.screen = screen
        self.clock = clock
        
        # Init engine for N players
        self.engine = GameEngine(num_players=num_players)
        
        # Init bots dictionary {player_idx: BotInstance}
        self.bots = bots if bots else {}
        
        # Init UI
        self.renderer = Renderer(self.screen)
        self.input_manager = InputManager(self.engine, self.renderer)
        
        # History for undo
        self.history = []
        self._save_state()
        
        # Move log (list of strings describing each move)
        self.move_log = []
        self.move_log_scroll = 0  
        self.stats_scroll = 0     # scroll offset for stats panel
        
        # Settings
        self.show_hint = show_hint
        self.bot_delay = bot_delay
        self.player_names = player_names if player_names else [f"Player {i+1}" for i in range(num_players)]
        
        # Tiles played counter
        self.tiles_placed = 0

    def _save_state(self):
        self.history.append(self.engine.state.clone())

    def _undo(self):
        if len(self.history) > 1:
            self.history.pop() # remove current state
            self.engine.state = self.history[-1].clone()
            self.engine.game_over = False
            
    def reset(self):
        # Full reset while keeping players/bots config
        self.engine = GameEngine(num_players=self.engine.state.num_players)
        self.input_manager.engine = self.engine
        self.history = []
        self._save_state()
        self.move_log = []
        self.move_log_scroll = 0
        self.tiles_placed = 0

    def save_game(self):
        os.makedirs('saves', exist_ok=True)
        filename = f"saves/azul_save_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        data = {
            'engine': self.engine.to_dict(),
            'bots': list(self.bots.keys())
        }
        with open(filename, 'w') as f:
            json.dump(data, f)
        print(f"Game saved to {filename}")
        
    def _log_move(self, move, player_idx):
        src = move['source_type']
        color = move['color'].name
        line = move['target_line']
        target_str = f"Line {line+1}" if line >= 0 else "Floor"
        self.move_log.append(f"P{player_idx+1}: {color} from {src} → {target_str}")
        # Auto-scroll to bottom
        self.move_log_scroll = max(0, len(self.move_log) - 12)
    
    def _get_hint(self):
        """Compute best move for the current human player."""
        current_p = self.engine.state.current_player_idx
        if current_p in self.bots:
            return None  # bot's turn, no hint needed
        from bots import MinimaxBot
        hint_bot = MinimaxBot(player_idx=current_p, max_depth=2)
        return hint_bot.get_best_move(self.engine)

    def run(self):
        running = True
        hint_move = None
        bot_stats = {}  # player_idx -> dict with last stats
        
        while running:
            # Check bot turn
            current_p = self.engine.state.current_player_idx
            is_bot_turn = current_p in self.bots and not self.engine.game_over
            
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                    self.renderer.screen = self.screen
                
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        return "QUIT_TO_MENU"
                    elif event.key == pygame.K_r:
                        self.reset()
                        hint_move = None
                        bot_stats = {}
                    elif event.key == pygame.K_ESCAPE:
                        self.save_game()
                        return "QUIT_TO_MENU"
                        
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # Check undo button
                    h = self.screen.get_height()
                    undo_rect = pygame.Rect(20, h - 60, 100, 40)
                    if undo_rect.collidepoint(event.pos):
                        self._undo()
                        hint_move = None
                        continue
                        
                elif event.type == pygame.MOUSEWHEEL:
                    m_pos = pygame.mouse.get_pos()
                    w_curr, h_curr = self.screen.get_size()
                    panel_x = w_curr - PANEL_W - 8
                    log_h = 260
                    log_y = h_curr - log_h - 6
                    
                    # Log area hover check
                    log_rect = pygame.Rect(panel_x, log_y, PANEL_W, log_h)
                    if log_rect.collidepoint(m_pos):
                        self.move_log_scroll = max(0, self.move_log_scroll - event.y)
                        self.move_log_scroll = min(max(0, len(self.move_log) - 12), self.move_log_scroll)
                    
                    # Stats area hover check
                    stats_y = 55
                    stats_h = h_curr - stats_y - log_h - 20
                    stats_rect = pygame.Rect(panel_x, stats_y, PANEL_W, stats_h)
                    if stats_rect.collidepoint(m_pos):
                        # Scroll stats (pixels)
                        self.stats_scroll = max(0, self.stats_scroll - event.y * 20)
                        # No easy way to know max_scroll without drawing, but let's cap at a reasonable large value or keep as is
                        self.stats_scroll = min(2000, self.stats_scroll)
                        
                # Only handle human input if it's a human's turn
                if not self.engine.game_over and not is_bot_turn:
                    human_move = self.input_manager.handle_event(event)
                    if human_move:
                        self._log_move(human_move, current_p)
                        self.tiles_placed += 1

            if is_bot_turn:
                import time as _time
                bot = self.bots[current_p]
                move = bot.get_best_move(self.engine)
                if move:
                    self._log_move(move, current_p)
                    self.tiles_placed += 1
                    self.engine.execute_move(move)
                    self._save_state()
                    # Record stats
                    if hasattr(bot, 'total_nodes'):
                        bot_stats[current_p] = {
                            'type': 'minimax',
                            'last_nodes': bot.last_nodes,
                            'total_nodes': bot.total_nodes,
                            'last_think_ms': bot.last_think_ms
                        }
                    elif hasattr(bot, 'total_simulations'):
                        bot_stats[current_p] = {
                            'type': 'mcts',
                            'last_simulations': bot.last_simulations,
                            'total_simulations': bot.total_simulations,
                            'last_think_ms': bot.last_think_ms
                        }
                    hint_move = None
                    # If every player is a bot, pause so the user can watch
                    if len(self.bots) == self.engine.state.num_players:
                        _time.sleep(self.bot_delay)
                    
            # Check if a human move was made
            if self.engine.state.current_player_idx != current_p:
                self._save_state()
                hint_move = None  # reset hint on new turn
            
            # Compute hint for human player if enabled
            if self.show_hint and not is_bot_turn and not self.engine.game_over and hint_move is None:
                hint_move = self._get_hint()
                    
            # Check for hover/highlight
            pos = pygame.mouse.get_pos()
            highlighted_line = self.input_manager._get_line_click(pos)
            
            # Bag & tile stats
            bag_count = len(self.engine.state.bag.tiles)
            total_tiles = 100
            placed = self.tiles_placed
            
            # Endgame proximity: any wall row >= 4 filled means close
            max_wall_filled = 0
            for p in self.engine.state.players:
                for r in range(5):
                    filled = sum(1 for c in range(5) if p.wall[r][c])
                    max_wall_filled = max(max_wall_filled, filled)
            endgame_proximity = max_wall_filled  # 0-5 (5 = row complete)
                    
            # Render
            self.renderer.draw_game_state(
                self.engine.state, 
                selected_draft=self.input_manager.selected_draft,
                highlighted_line=highlighted_line if self.input_manager.selected_draft else None,
                mouse_pos=pos,
                move_log=self.move_log,
                move_log_scroll=self.move_log_scroll,
                bag_count=bag_count,
                tiles_placed=placed,
                bot_stats=bot_stats,
                endgame_proximity=endgame_proximity,
                hint_move=hint_move if self.show_hint else None,
                player_names=self.player_names,
                stats_scroll=self.stats_scroll,
                hovered_line=None if self.input_manager.selected_draft else highlighted_line
            )
            
            # Draw game over
            if self.engine.game_over:
                self._draw_game_over()
                
            pygame.display.flip()
            self.clock.tick(FPS)
            
        pygame.quit()
        sys.exit()

    def _draw_game_over(self):
        w, h = self.screen.get_size()
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        self.screen.blit(s, (0, 0))
        
        font = pygame.font.SysFont('Arial', 64, bold=True)
        text = font.render("GAME OVER", True, (255, 200, 0))
        self.screen.blit(text, (w // 2 - text.get_width() // 2, h // 2 - 120))
        
        small_font = pygame.font.SysFont('Arial', 32)
        score_texts = [f"P{i+1}: {p.score}" for i, p in enumerate(self.engine.state.players)]
        scores_str = "  -  ".join(score_texts)
        
        scores = small_font.render(scores_str, True, (255, 255, 255))
        self.screen.blit(scores, (w // 2 - scores.get_width() // 2, h // 2 - 20))
        
        # Find winner
        max_score = max(p.score for p in self.engine.state.players)
        winners = [i+1 for i, p in enumerate(self.engine.state.players) if p.score == max_score]
        
        if len(winners) > 1:
            winner_str = "It's a Tie! (" + ", ".join(f"P{w}" for w in winners) + ")"
        else:
            winner_str = f"Player {winners[0]} Wins!"
            
        win_text = font.render(winner_str, True, (0, 255, 0))
        self.screen.blit(win_text, (w // 2 - win_text.get_width() // 2, h // 2 + 50))
        
        restart_text = small_font.render("Press R to Restart  |  Q for Menu", True, (200, 200, 200))
        self.screen.blit(restart_text, (w // 2 - restart_text.get_width() // 2, h // 2 + 150))


def show_startup_screen(screen, clock):
    font     = pygame.font.SysFont('Arial', 56, bold=True)
    small    = pygame.font.SysFont('Arial', 22)
    med      = pygame.font.SysFont('Arial', 28, bold=True)
    tiny     = pygame.font.SysFont('Arial', 18)

    presets = [
        ("1H  1B", 2, 1, "Human vs. Bot"),
        ("1H  2B", 3, 2, "Human vs. 2 Bots"),
        ("1H  3B", 4, 3, "Human vs. 3 Bots"),
        ("2H  1B", 3, 1, "2 Humans + 1 Bot"),
        ("2H  2B", 4, 2, "2 Humans + 2 Bots"),
        ("2H",     2, 0, "2 Humans"),
        ("3H",     3, 0, "3 Humans"),
        ("4H",     4, 0, "4 Humans"),
        ("2B",     2, 2, "2 Bots only"),
        ("3B",     3, 3, "3 Bots only"),
        ("4B",     4, 4, "4 Bots only"),
    ]
    selected_preset = 0
    speed_options = [("0.1s", 0.1), ("0.25s", 0.25), ("0.5s", 0.5), ("1s", 1.0), ("2s", 2.0)]
    selected_speed = 1
    show_hint = False
    bot_algo  = "minimax" # "minimax" or "mcts"
    load_btn  = {"rect": None}
    start_btn = {"rect": None}
    
    player_names = ["Player 1", "Player 2", "Player 3", "Player 4"]
    active_name_idx = -1
    
    COLS = 4
    PRESET_W, PRESET_H, PRESET_GAP = 140, 56, 8
    rules = [
        "RULES RECAP:",
        "1. Draft a color from a Factory or Center.",
        "2. Place them on a Pattern Line.",
        "3. Overflow goes to the Floor (penalties).",
        "4. Full lines move 1 tile to the Wall.",
        "5. More contiguous tiles = more points.",
        "6. Game ends when a Wall row is complete.",
    ]

    while True:
        w, h = screen.get_size()
        screen.fill((240, 235, 225))
        m_pos = pygame.mouse.get_pos()

        title = font.render("Azul Python", True, (50, 40, 30))
        screen.blit(title, (w // 2 - title.get_width() // 2, 20))

        left_x  = max(30, w // 2 - 460)
        right_x = w // 2 + 10

        ry = 105
        for i, line in enumerate(rules):
            c = (60, 50, 40) if i == 0 else (100, 90, 80)
            s = (med if i == 0 else small).render(line, True, c)
            screen.blit(s, (left_x, ry + i * 28))

        # -- Player Names (left, below rules) --
        ny = ry + len(rules) * 28 + 20
        screen.blit(med.render("Player Names:", True, (60, 50, 40)), (left_x, ny))
        ny += 36
        name_rects = []
        _, np_curr, nb_curr, _ = presets[selected_preset]
        for i in range(np_curr):
            nr = pygame.Rect(left_x, ny + i*40, 220, 32)
            name_rects.append((i, nr))
            bg = (255, 255, 255) if i == active_name_idx else (230, 225, 215)
            pygame.draw.rect(screen, bg, nr, border_radius=4)
            pygame.draw.rect(screen, (100, 90, 80), nr, 2 if i == active_name_idx else 1, border_radius=4)
            
            txt = small.render(player_names[i], True, (50, 40, 30))
            screen.blit(txt, (nr.x + 8, nr.y + 4))

        gy = 100
        ml = med.render("Game Mode:", True, (60, 50, 40))
        screen.blit(ml, (right_x, gy))
        gy += 36

        preset_rects = []
        for idx, (lt, np, nb, desc) in enumerate(presets):
            row = idx // COLS
            col = idx % COLS
            rx  = right_x + col * (PRESET_W + PRESET_GAP)
            ry2 = gy + row * (PRESET_H + PRESET_GAP)
            rect = pygame.Rect(rx, ry2, PRESET_W, PRESET_H)
            preset_rects.append(rect)
            active = idx == selected_preset
            hover  = rect.collidepoint(m_pos)
            if active:
                bg, border = (255, 200, 60), (180, 130, 0)
            elif hover:
                bg, border = (220, 210, 195), (130, 120, 110)
            else:
                bg, border = (205, 195, 182), (150, 138, 125)
            pygame.draw.rect(screen, bg, rect, border_radius=6)
            pygame.draw.rect(screen, border, rect, 2, border_radius=6)
            t1 = med.render(lt, True, (40, 30, 20))
            t2 = tiny.render(desc, True, (80, 70, 60))
            screen.blit(t1, (rect.centerx - t1.get_width()//2, rect.y + 4))
            screen.blit(t2, (rect.centerx - t2.get_width()//2, rect.y + 32))

        rows_used = (len(presets) + COLS - 1) // COLS
        bottom_y  = gy + rows_used * (PRESET_H + PRESET_GAP) + 14

        sl = med.render("Bot Move Delay:", True, (60, 50, 40))
        screen.blit(sl, (right_x, bottom_y))
        bottom_y += 34

        speed_rects = []
        for si, (slbl, _v) in enumerate(speed_options):
            sw = 76
            sx = right_x + si * (sw + 6)
            sr = pygame.Rect(sx, bottom_y, sw, 34)
            speed_rects.append(sr)
            sbg = (100, 165, 240) if si == selected_speed else (195, 208, 228) if sr.collidepoint(m_pos) else (180, 192, 212)
            pygame.draw.rect(screen, sbg, sr, border_radius=5)
            pygame.draw.rect(screen, (70, 100, 155), sr, 2, border_radius=5)
            st = small.render(slbl, True, (15, 15, 55))
            screen.blit(st, (sr.centerx - st.get_width()//2, sr.centery - st.get_height()//2))
        bottom_y += 44

        cb_size = 22
        cb_x, cb_y = right_x, bottom_y
        cb_rect = pygame.Rect(cb_x, cb_y, cb_size, cb_size)
        pygame.draw.rect(screen, (240, 235, 215), cb_rect)
        pygame.draw.rect(screen, (100, 90, 80), cb_rect, 2)
        if show_hint:
            pygame.draw.line(screen, (50, 150, 50), (cb_x+3, cb_y+11), (cb_x+9, cb_y+17), 3)
            pygame.draw.line(screen, (50, 150, 50), (cb_x+9, cb_y+17), (cb_x+19, cb_y+4), 3)
        cb_txt = small.render("Show Best Move Hint (slows game)", True, (50, 40, 30))
        screen.blit(cb_txt, (cb_x + cb_size + 8, cb_y + 2))
        bottom_y += 40

        # -- Bot Algorithm Toggle --
        screen.blit(med.render("Bot Engine:", True, (60, 50, 40)), (right_x, bottom_y))
        bottom_y += 34
        
        algo_rects = []
        for ai, (albl, aval) in enumerate([("Minimax", "minimax"), ("MCTS", "mcts")]):
            aw = 110
            ax = right_x + ai * (aw + 10)
            ar = pygame.Rect(ax, bottom_y, aw, 34)
            algo_rects.append((ar, aval))
            abg = (100, 165, 240) if aval == bot_algo else (195, 208, 228) if ar.collidepoint(m_pos) else (180, 192, 212)
            pygame.draw.rect(screen, abg, ar, border_radius=5)
            pygame.draw.rect(screen, (70, 100, 155), ar, 2, border_radius=5)
            at = small.render(albl, True, (15, 15, 55))
            screen.blit(at, (ar.centerx - at.get_width()//2, ar.centery - at.get_height()//2))
        bottom_y += 50

        btn_y = min(bottom_y + 10, h - 80)
        start_r = pygame.Rect(right_x, btn_y, 178, 54)
        load_r  = pygame.Rect(right_x + 194, btn_y, 178, 54)
        start_btn["rect"] = start_r
        load_btn["rect"]  = load_r

        for btn_r, bcol, blbl in [(start_r, (70, 160, 70), "START GAME"), (load_r, (70, 110, 190), "LOAD GAME")]:
            bg = tuple(max(0, c - 25) for c in bcol) if btn_r.collidepoint(m_pos) else bcol
            pygame.draw.rect(screen, bg, btn_r, border_radius=8)
            pygame.draw.rect(screen, (25, 25, 25), btn_r, 2, border_radius=8)
            bt = med.render(blbl, True, (255, 255, 255))
            screen.blit(bt, (btn_r.centerx - bt.get_width()//2, btn_r.centery - bt.get_height()//2))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                if active_name_idx != -1:
                    if event.key == pygame.K_BACKSPACE:
                        player_names[active_name_idx] = player_names[active_name_idx][:-1]
                    elif event.key == pygame.K_RETURN:
                        active_name_idx = -1
                    elif event.key == pygame.K_TAB:
                        active_name_idx = (active_name_idx + 1) % np_curr
                    else:
                        if len(player_names[active_name_idx]) < 15 and event.unicode.isprintable():
                            player_names[active_name_idx] += event.unicode
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                old_preset = selected_preset
                active_name_idx = -1
                for i, nr in name_rects:
                    if nr.collidepoint(event.pos):
                        active_name_idx = i
                for idx, rect in enumerate(preset_rects):
                    if rect.collidepoint(event.pos):
                        selected_preset = idx
                if selected_preset != old_preset:
                    active_name_idx = -1 # Reset focus if preset changed
                for si, sr in enumerate(speed_rects):
                    if sr.collidepoint(event.pos):
                        selected_speed = si
                if cb_rect.collidepoint(event.pos):
                    show_hint = not show_hint
                for ar, aval in algo_rects:
                    if ar.collidepoint(event.pos):
                        bot_algo = aval
                if start_btn["rect"] and start_btn["rect"].collidepoint(event.pos):
                    _, np, nb, _ = presets[selected_preset]
                    return {"action": "new", "players": np, "num_bots": nb,
                             "show_hint": show_hint, "bot_delay": speed_options[selected_speed][1],
                             "player_names": player_names[:np], "bot_algo": bot_algo}
                if load_btn["rect"] and load_btn["rect"].collidepoint(event.pos):
                    return {"action": "load"}
        clock.tick(60)
def show_load_screen(screen, clock):
    font = pygame.font.SysFont('Arial', 64, bold=True)
    small_font = pygame.font.SysFont('Arial', 24)
    
    os.makedirs('saves', exist_ok=True)
    saves = sorted(glob.glob('saves/*.json'), reverse=True)
    
    while True:
        w, h = screen.get_size()
        screen.fill((240, 235, 225))
        
        title = font.render("Load Game", True, (50, 40, 30))
        screen.blit(title, (w//2 - title.get_width()//2, 50))
        
        m_pos = pygame.mouse.get_pos()
        clicked_save = None
        
        if not saves:
            txt = small_font.render("No saves found.", True, (100, 90, 80))
            screen.blit(txt, (w//2 - txt.get_width()//2, 200))
        else:
            for i, save in enumerate(saves[:10]): # max 10
                rect = pygame.Rect(w//2 - 250, 150 + i*60, 500, 50)
                color = (200, 190, 180)
                if rect.collidepoint(m_pos):
                    color = (220, 210, 200)
                pygame.draw.rect(screen, color, rect)
                pygame.draw.rect(screen, (100, 90, 80), rect, 2)
                
                name = os.path.basename(save)
                txt = small_font.render(name, True, (50, 40, 30))
                screen.blit(txt, (rect.x + 20, rect.centery - txt.get_height()//2))
                
                if rect.collidepoint(m_pos) and pygame.mouse.get_pressed()[0]:
                    clicked_save = save
                    
        # Back button
        back_rect = pygame.Rect(w//2 - 100, h - 100, 200, 50)
        color = (200, 100, 100)
        if back_rect.collidepoint(m_pos):
            color = (220, 120, 120)
        pygame.draw.rect(screen, color, back_rect)
        pygame.draw.rect(screen, (100, 50, 50), back_rect, 2)
        txt = small_font.render("BACK", True, (255, 255, 255))
        screen.blit(txt, (back_rect.centerx - txt.get_width()//2, back_rect.centery - txt.get_height()//2))
        
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if back_rect.collidepoint(event.pos):
                    return None
                if clicked_save:
                    return clicked_save
        clock.tick(60)

def main_loop():
    pygame.init()
    pygame.display.set_caption("Azul Python")
    
    parser = argparse.ArgumentParser(description="Play Azul. CLI bot args are applied AFTER player count is chosen in the UI.")
    parser.add_argument('--bots', type=str, nargs='*', choices=['minimax', 'mcts'], default=[], 
                        help="Specify bots for players starting from P2. E.g., --bots minimax mcts")
    args = parser.parse_args()
    
    # Initialize resizable screen once
    screen = pygame.display.set_mode((1400, 1000), pygame.RESIZABLE)
    clock = pygame.time.Clock()
    
    while True:
        # Show UI to choose players
        action_res = show_startup_screen(screen, clock)
        
        if action_res["action"] == "load":
            save_file = show_load_screen(screen, clock)
            if not save_file:
                continue # go back to startup screen
                
            # Load game logic
            with open(save_file, 'r') as f:
                data = json.load(f)
            
            engine = GameEngine.from_dict(data['engine'])
            chosen_players = engine.state.num_players
            
            bots_dict = {}
            for bot_idx in data['bots']:
                # Simplify: assume if bot was there it's minimax/mcts depending on CLI.
                # If CLI passed nothing, fallback to minimax depth 2
                b_type = 'minimax'
                if args.bots and len(args.bots) >= (bot_idx):
                    b_type = args.bots[bot_idx - 1]
                    
                if b_type == 'mcts':
                    bots_dict[bot_idx] = MCTSBot(player_idx=bot_idx, iterations=1000)
                else:
                    bots_dict[bot_idx] = MinimaxBot(player_idx=bot_idx, max_depth=4)
                    
            app = AzulGame(screen=screen, clock=clock, num_players=chosen_players, bots=bots_dict)
            app.engine = engine # override initialized engine with loaded
            app.input_manager.engine = engine
            app.history = []
            app._save_state()
            
        else:
            chosen_players = action_res["players"]
            num_bots = action_res.get("num_bots", 0)
            bot_delay = action_res.get("bot_delay", 0.25)
            
            # Build bots dict: bots fill slots from the last player down
            # e.g. 2P 1B => bot is P2 (idx 1)
            # e.g. 4P 4B => all 4 are bots
            bots_dict = {}
            bot_type = action_res.get("bot_algo", (args.bots[0] if args.bots else 'minimax'))
            for i in range(num_bots):
                player_idx = chosen_players - num_bots + i  # assign to last N slots
                if bot_type == 'mcts':
                    bots_dict[player_idx] = MCTSBot(player_idx=player_idx, iterations=1000)
                else:
                    bots_dict[player_idx] = MinimaxBot(player_idx=player_idx, max_depth=2)
                    
            app = AzulGame(screen=screen, clock=clock, num_players=chosen_players, bots=bots_dict,
                           show_hint=action_res.get('show_hint', False),
                           bot_delay=bot_delay,
                           player_names=action_res.get("player_names"))
            
        result = app.run()
        if result != "QUIT_TO_MENU":
            break

if __name__ == "__main__":
    main_loop()
