import pygame
from scene import *
from entity import *
from constants import *
from mission import *

class Game: 
    def __init__(self):
        self.running = True
        self.screen = pygame.display.get_surface() 
        self.screen_wh_cells_tuple = (self.screen.get_width() // CELL_SIZE, self.screen.get_height() // CELL_SIZE)
        self.screen.set_colorkey(ALPHA_KEY)
        self.clock = pygame.time.Clock()
        self.debug = False
        self.log_sim_events = False
        self.log_ai_routines = False
        self.pathfinding_perf = False
        self.scene_campaign_map = CampaignScene(self)
        self.scene_tactical_combat = None 
        self.current_scene = self.scene_campaign_map 
        self.exit_game_confirm = False
        self.campaign_mode = True
        self.heavy_escorts = 3
        self.subs = 100
        self.total_score = 0

    def game_loop(self):
        while self.running: 
            self.current_scene.update()
            if self.current_scene.display_changed:
                self.current_scene.draw() 
            self.clock.tick(FPS)

def loading_screen():
    title_font = pygame.font.Font(FONT_PATH, TITLE_FONT_SIZE)
    subtitle_font = pygame.font.Font(FONT_PATH, HUD_FONT_SIZE)
    desktop_size = pygame.display.get_desktop_sizes()[0]
    w, h = desktop_size
    screen = pygame.display.get_surface()
    surf = pygame.Surface(desktop_size)
    surf.fill("navy")
    lines = [
        title_font.render("BLOCKADE", True, "white"),
        subtitle_font.render("<version {}>".format(VERSION), True, "white", "black"),
        subtitle_font.render("~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-", True, "white", "black"),
        subtitle_font.render("...loading...".format(VERSION), True, "white", "black"),
        subtitle_font.render("~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-", True, "white", "black"),
    ]
    y = h // 2 - ((len(lines) - 1) * lines[1].get_height() + lines[0].get_height()) // 2 
    for line in lines:
        x = w // 2 - line.get_width() // 2
        surf.blit(line, (x, y))
        if line is lines[0]:
            y += lines[0].get_height()
        else:
            y += lines[1].get_height()
    screen.blit(surf, (0, 0))
    pygame.display.flip()

if __name__ == "__main__":
    pygame.init()
    pygame.display.set_caption("Blockade <version {}>".format(VERSION))
    icon = pygame.image.load(WINDOW_ICON_PATH)
    pygame.display.set_icon(icon)
    flags = pygame.FULLSCREEN
    desktop_size = pygame.display.get_desktop_sizes()[0]
    pygame.display.set_mode((desktop_size[0], desktop_size[1]), flags) 
    pygame.mixer.quit()
    loading_screen()
    game = Game()
    game.game_loop()
    pygame.quit()

