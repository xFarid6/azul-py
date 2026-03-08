import pygame
import sys
import argparse
from game.engine import GameEngine
from ui.renderer import Renderer
from ui.input import InputManager
from ui.constants import WINDOW_WIDTH, WINDOW_HEIGHT, FPS
from bots import MinimaxBot, MCTSBot

class AzulGame:
    def __init__(self, screen, clock, num_players=2, bots=None):
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
        
    def run(self):
        running = True
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
                    # Update renderer with new screen reference if needed (Pygame handles it, but good practice)
                    self.renderer.screen = self.screen
                
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        return "QUIT_TO_MENU"
                    elif event.key == pygame.K_r:
                        self.reset()
                        
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # Check undo button
                    h = self.screen.get_height()
                    undo_rect = pygame.Rect(20, h - 60, 100, 40)
                    if undo_rect.collidepoint(event.pos):
                        self._undo()
                        continue
                        
                # Only handle human input if it's a human's turn
                if not self.engine.game_over and not is_bot_turn:
                    moved = self.input_manager.handle_event(event)

            # Inside handle_event, if it returned True or we can just trace state ID changes
            # Wait, our input manager doesn't return anything. We can check if state changed.
                    
            if is_bot_turn:
                # Optionally draw some "Bot Thinking..." UI here
                bot = self.bots[current_p]
                move = bot.get_best_move(self.engine)
                if move:
                    self.engine.execute_move(move)
                    self._save_state()
                    
            # Check if a human move was made (dirty check: if current player changed)
            if self.engine.state.current_player_idx != current_p:
                self._save_state()
                    
            # Check for hover/highlight
            pos = pygame.mouse.get_pos()
            highlighted_line = self.input_manager._get_line_click(pos)
                    
            # Render
            self.renderer.draw_game_state(
                self.engine.state, 
                selected_draft=self.input_manager.selected_draft,
                highlighted_line=highlighted_line if self.input_manager.selected_draft else None,
                mouse_pos=pos
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
        start_rect = pygame.Rect(w//2 - 100, sel_y + 100, 200, 60)
        start_btn['rect'] = start_rect
        color = (150, 200, 150)
        if start_rect.collidepoint(m_pos):
            color = (130, 180, 130)
            
        pygame.draw.rect(screen, color, start_rect)
        pygame.draw.rect(screen, (50, 100, 50), start_rect, 3)
        
        s_text = med_font.render("START GAME", True, (255, 255, 255))
        screen.blit(s_text, (start_rect.centerx - s_text.get_width()//2, start_rect.centery - s_text.get_height()//2))
            
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
                    return chosen_players
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
        chosen_players = show_startup_screen(screen, clock)
        
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
