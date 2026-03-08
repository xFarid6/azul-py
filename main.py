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
from ui.constants import WINDOW_WIDTH, WINDOW_HEIGHT, FPS
from bots import MinimaxBot, MCTSBot

class AzulGame:
    def __init__(self, screen, clock, num_players=2, bots=None, show_hint=False):
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
        self.move_log_scroll = 0  # scroll offset
        
        # Settings
        self.show_hint = show_hint  # show best move for human players
        
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
                    # Scroll move log
                    self.move_log_scroll = max(0, self.move_log_scroll - event.y)
                    self.move_log_scroll = min(max(0, len(self.move_log) - 12), self.move_log_scroll)
                        
                # Only handle human input if it's a human's turn
                if not self.engine.game_over and not is_bot_turn:
                    moved = self.input_manager.handle_event(event)

            if is_bot_turn:
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
                    
            # Check if a human move was made
            if self.engine.state.current_player_idx != current_p:
                prev_p = current_p
                if not is_bot_turn:
                    # Human made a move, log it from the last selected draft
                    self.tiles_placed += 1
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
                hint_move=hint_move if self.show_hint else None
            )
            
            # Draw game over
            if self.engine.game_over:
                self._draw_game_over()
                
            pygame.display.flip()
            self.clock.tick(FPS)
            
        pygame.quit()
        sys.exit()

    def _draw_game_over(self):
        s = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        self.screen.blit(s, (0, 0))
        
        font = pygame.font.SysFont('Arial', 64, bold=True)
        text = font.render("GAME OVER", True, (255, 200, 0))
        self.screen.blit(text, (WINDOW_WIDTH//2 - text.get_width()//2, WINDOW_HEIGHT//2 - 100))
        
        small_font = pygame.font.SysFont('Arial', 32)
        score_texts = [f"P{i+1}: {p.score}" for i, p in enumerate(self.engine.state.players)]
        scores_str = "  -  ".join(score_texts)
        
        scores = small_font.render(scores_str, True, (255, 255, 255))
        self.screen.blit(scores, (WINDOW_WIDTH//2 - scores.get_width()//2, WINDOW_HEIGHT//2))
        
        # Find winner
        max_score = max(p.score for p in self.engine.state.players)
        winners = [i+1 for i, p in enumerate(self.engine.state.players) if p.score == max_score]
        
        if len(winners) > 1:
            winner_str = "It's a Tie! (" + ", ".join(f"P{w}" for w in winners) + ")"
        else:
            winner_str = f"Player {winners[0]} Wins!"
            
        win_text = font.render(winner_str, True, (0, 255, 0))
        self.screen.blit(win_text, (WINDOW_WIDTH//2 - win_text.get_width()//2, WINDOW_HEIGHT//2 + 50))


def show_startup_screen(screen, clock):
    font = pygame.font.SysFont('Arial', 64, bold=True)
    small_font = pygame.font.SysFont('Arial', 24)
    med_font = pygame.font.SysFont('Arial', 32, bold=True)
    
    options = [
        {"label": "2 Players", "val": 2, "rect": None, "selected": True},
        {"label": "3 Players", "val": 3, "rect": None, "selected": False},
        {"label": "4 Players", "val": 4, "rect": None, "selected": False}
    ]
    
    start_btn = {"rect": None}
    load_btn = {"rect": None}
    chosen_players = 2
    
    rules = [
        "AZUL RULES RECAP:",
        "1. Draft tiles from a Factory or the Center.",
        "2. Place them on one Pattern Line on your board.",
        "3. Overflowing tiles fall to the Floor Line (minus points).",
        "4. At round end, full Pattern Lines move 1 tile to the Wall.",
        "5. Contiguous wall tiles score more points.",
        "6. Game ends when someone completes a horizontal Wall row.",
    ]
    
    while True:
        w, h = screen.get_size()
        screen.fill((240, 235, 225)) # BG_COLOR
        
        # Title
        title = font.render("Azul Python", True, (50, 40, 30))
        screen.blit(title, (w//2 - title.get_width()//2, 50))
        
        # Rules Block
        rules_y = 150
        for i, line in enumerate(rules):
            surf = small_font.render(line, True, (100, 90, 80))
            screen.blit(surf, (w//2 - 250, rules_y + i*30))
            
        # Player Select
        m_pos = pygame.mouse.get_pos()
        sel_y = 400
        for i, opt in enumerate(options):
            rect = pygame.Rect(w//2 - 200 + i*140, sel_y, 120, 50)
            opt['rect'] = rect
            
            color = (200, 190, 180)
            if opt['selected']:
                color = (255, 200, 0)
            elif rect.collidepoint(m_pos):
                color = (220, 210, 200)
                
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, (100, 90, 80), rect, 2)
            
            text = small_font.render(opt['label'], True, (50, 40, 30))
            screen.blit(text, (rect.centerx - text.get_width()//2, rect.centery - text.get_height()//2))
            
        # Start Button
        start_rect = pygame.Rect(w//2 - 220, sel_y + 100, 200, 60)
        start_btn['rect'] = start_rect
        color = (150, 200, 150)
        if start_rect.collidepoint(m_pos):
            color = (130, 180, 130)
            
        pygame.draw.rect(screen, color, start_rect)
        pygame.draw.rect(screen, (50, 100, 50), start_rect, 3)
        
        s_text = med_font.render("START GAME", True, (255, 255, 255))
        screen.blit(s_text, (start_rect.centerx - s_text.get_width()//2, start_rect.centery - s_text.get_height()//2))
        
        # Load Button
        load_rect = pygame.Rect(w//2 + 20, sel_y + 100, 200, 60)
        load_btn['rect'] = load_rect
        color = (150, 150, 200)
        if load_rect.collidepoint(m_pos):
            color = (130, 130, 180)
            
        pygame.draw.rect(screen, color, load_rect)
        pygame.draw.rect(screen, (50, 50, 100), load_rect, 3)
        
        l_text = med_font.render("LOAD GAME", True, (255, 255, 255))
        screen.blit(l_text, (load_rect.centerx - l_text.get_width()//2, load_rect.centery - l_text.get_height()//2))
            
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Player selection
                for opt in options:
                    if opt['rect'] and opt['rect'].collidepoint(event.pos):
                        for o in options: o['selected'] = False
                        opt['selected'] = True
                        chosen_players = opt['val']
                
                # Start game
                if start_btn['rect'] and start_btn['rect'].collidepoint(event.pos):
                    return {"action": "new", "players": chosen_players}
                
                # Load game
                if load_btn['rect'] and load_btn['rect'].collidepoint(event.pos):
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
                    bots_dict[bot_idx] = MCTSBot(player_idx=bot_idx, iterations=100)
                else:
                    bots_dict[bot_idx] = MinimaxBot(player_idx=bot_idx, max_depth=2)
                    
            app = AzulGame(screen=screen, clock=clock, num_players=chosen_players, bots=bots_dict)
            app.engine = engine # override initialized engine with loaded
            app.input_manager.engine = engine
            app.history = []
            app._save_state()
            
        else:
            chosen_players = action_res["players"]
            
            # Initialize dictionary of bots using the chosen player count
            bots_dict = {}
            for i, bot_type in enumerate(args.bots):
                player_idx = i + 1  # P1 (idx 0) remains human, P2 is idx 1, etc.
                if player_idx >= chosen_players:
                    break
                    
                if bot_type == 'minimax':
                    bots_dict[player_idx] = MinimaxBot(player_idx=player_idx, max_depth=2)
                elif bot_type == 'mcts':
                    bots_dict[player_idx] = MCTSBot(player_idx=player_idx, iterations=100)
                    
            app = AzulGame(screen=screen, clock=clock, num_players=chosen_players, bots=bots_dict)
            
        result = app.run()
        if result != "QUIT_TO_MENU":
            break

if __name__ == "__main__":
    main_loop()
