import pygame
from loading_screen import loading_screen
from scene import *
from entity import *
from constants import *
from mission import *

class Game: 
    def __init__(self):
        self.GAME_UPDATE_TICK_TACTICAL = pygame.event.custom_type()
        self.GAME_UPDATE_TICK_CAMPAIGN = pygame.event.custom_type()
        self.MISSION_OVER_CHECK_RESET_CONFIRM = pygame.event.custom_type()
        self.MISSION_OVER_CHECK = pygame.event.custom_type()
        self.QUIT_CHECK_RESET_CONFIRM = pygame.event.custom_type()
        self.running = True
        self.screen = pygame.display.get_surface() 
        self.screen_wh_cells_tuple = (self.screen.get_width() // CELL_SIZE, self.screen.get_height() // CELL_SIZE)
        self.screen_wh_cells_tuple_zoomed_out = (self.screen.get_width() // ZOOMED_OUT_CELL_SIZE, \
            self.screen.get_height() // ZOOMED_OUT_CELL_SIZE)
        self.screen.set_colorkey(ALPHA_KEY)
        self.clock = pygame.time.Clock()
        self.debug = False
        self.log_sim_events = False
        self.log_ai_routines = False
        self.pathfinding_perf = False
        self.scene_campaign_map = CampaignScene(self)
        self.scene_tactical_combat = TacticalScene(self)
        self.current_scene = self.scene_campaign_map 
        self.exit_game_confirm = False
        self.campaign_mode = True
        self.heavy_escorts = STARTING_HEAVY_ESCORTS
        self.subs = STARTING_SUBS
        self.total_score = 0
        self.freighters_sunk = 0
        self.escorts_sunk = 0
        self.subs_sunk = 0
        self.heavy_escorts_sunk = 0
        self.neutral_freighters_sunk = 0
        self.encounters_had = 0
        self.encounters_retained_stealth = 0
        self.encounters_accomplished_something = 0
        self.encounters_accomplished_something_retained_stealth = 0
        self.times_lost_hunters = 0
        self.islands_conquered = 0
        self.cities_conquered = 0
        self.total_damage_taken = 0
        self.torpedos_evaded = 0
        self.torpedos_used = 0
        self.missiles_used = 0
        self.times_resupplied = 0
        self.extra_lives_used = 0
        self.perf_calls = False
        self.perfing = { 
            "total": 0,
            "total campaign proc": 0,
            "total tac proc": 0,
        }

    def perf_call(self, fn): 
        start = pygame.time.get_ticks()
        fn()
        end = pygame.time.get_ticks()
        tot = end - start
        if fn not in self.perfing.keys():
            self.perfing[fn] = {"cumulative": tot, "longest": tot, "shortest": tot}
        else:
            self.perfing[fn]["cumulative"] += tot
            if tot < self.perfing[fn]["shortest"]:
                self.perfing[fn]["shortest"] = tot
            if tot > self.perfing[fn]["longest"]:
                self.perfing[fn]["longest"] = tot
        procs = list(map(lambda x: x[1], self.current_scene.processing_events.values()))
        if fn in procs:
            if isinstance(self.current_scene, TacticalScene):
                self.perfing["total tac proc"] += tot
            elif isinstance(self.current_scene, CampaignScene):
                self.perfing["total campaign proc"] += tot
 
    def game_loop(self):
        while self.running: 
            if self.perfing:
               self.perf_call(self.current_scene.update)
            else:
                self.current_scene.update()
            if self.current_scene.display_changed:
                if self.perfing:
                    self.perf_call(self.current_scene.draw)
                else:
                    self.current_scene.draw() 
            self.clock.tick(FPS)
        if self.perf_calls:
            self.perfing["total"] = pygame.time.get_ticks()
            print("____Perf Logs by Function:")
            for k, v in self.perfing.items():
                if k != "total" and k != "total campaign proc" and k != "total tac proc":
                    print("\t{}".format(k))
                    print("\t\t% of total time: {}%".format(v["cumulative"] / self.perfing["total"] * 100))
                    print("\t\tshortest: {}".format(v["shortest"]))
                    print("\t\tlongest: {}".format(v["longest"]))
            print("\tcampaign proc: {}%".format(self.perfing["total campaign proc"] / self.perfing["total"] * 100))
            print("\ttac proc: {}%".format(self.perfing["total tac proc"] / self.perfing["total"] * 100))

if __name__ == "__main__":
    pygame.init()
    pygame.display.set_caption("Blockade <version {}>".format(VERSION))
    icon = pygame.image.load(WINDOW_ICON_PATH)
    pygame.display.set_icon(icon)
    flags = pygame.FULLSCREEN
    desktop_size = pygame.display.get_desktop_sizes()[0]
    pygame.display.set_mode((desktop_size[0], desktop_size[1]), flags) 
    pygame.mixer.quit()
    pygame.mouse.set_visible(False)
    loading_screen()
    game = Game()
    game.game_loop()
    pygame.quit()

