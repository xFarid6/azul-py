import pygame
import sys
import argparse
from game.engine import GameEngine
from ui.renderer import Renderer
from ui.input import InputManager
from ui.constants import WINDOW_WIDTH, WINDOW_HEIGHT, FPS
from bots import MinimaxBot, MCTSBot

class AzulGame:
    def __init__(self, bot=None):
        pygame.init()
        pygame.display.set_caption("Azul Python")
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        
        # Init engine for 2 players
        self.engine = GameEngine(num_players=2)
        
        # Init bots
        self.bot = bot # e.g., MinimaxBot(player_idx=1)
        
        # Init UI
        self.renderer = Renderer(self.screen)
        self.input_manager = InputManager(self.engine)
        
    def run(self):
        running = True
        while running:
            # Check bot turn
            is_bot_turn = self.bot and self.engine.state.current_player_idx == self.bot.player_idx and not self.engine.game_over
            
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                # Only handle human input if it's a human's turn
                if not self.engine.game_over and not is_bot_turn:
                    self.input_manager.handle_event(event)
                    
            if is_bot_turn:
                # Optionally draw some "Bot Thinking..." UI here
                move = self.bot.get_best_move(self.engine)
                if move:
                    self.engine.execute_move(move)
                    
            # Check for hover/highlight
            pos = pygame.mouse.get_pos()
            highlighted_line = self.input_manager._get_line_click(pos)
                    
            # Render
            self.renderer.draw_game_state(
                self.engine.state, 
                selected_draft=self.input_manager.selected_draft,
                highlighted_line=highlighted_line if self.input_manager.selected_draft else None
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
        p1_score = self.engine.state.players[0].score
        p2_score = self.engine.state.players[1].score
        
        scores = small_font.render(f"Player 1: {p1_score}  -  Player 2: {p2_score}", True, (255, 255, 255))
        self.screen.blit(scores, (WINDOW_WIDTH//2 - scores.get_width()//2, WINDOW_HEIGHT//2))
        
        if p1_score > p2_score:
            winner = "Player 1 Wins!"
        elif p2_score > p1_score:
            winner = "Player 2 Wins!"
        else:
            winner = "It's a Tie!"
            
        win_text = font.render(winner, True, (0, 255, 0))
        self.screen.blit(win_text, (WINDOW_WIDTH//2 - win_text.get_width()//2, WINDOW_HEIGHT//2 + 50))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Play Azul")
    parser.add_argument('--bot', choices=['none', 'minimax', 'mcts'], default='none', help="Choose opponent bot")
    args = parser.parse_args()
    
    selected_bot = None
    if args.bot == 'minimax':
        selected_bot = MinimaxBot(player_idx=1, max_depth=2) # Keep depth low for responsiveness
    elif args.bot == 'mcts':
        selected_bot = MCTSBot(player_idx=1, iterations=100)
        
    app = AzulGame(bot=selected_bot)
    app.run()
