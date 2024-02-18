import pygame
from loading_screen import loading_screen
from scene import *
from entity import *
from constants import *
from mission import *

class Game: 
    def __init__(self):
        self.loader_bg = pygame.image.load(LOADING_SCREENSHOT_PATH)
        self.loader_bg.convert()
        loading_screen(self.loader_bg)
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
        self.perf_calls = True
        self.testing_encounter = False
        self.no_encounters = False
        self.allied_front_line_sheet = pygame.image.load(ALLIED_FRONT_LINE_PATH)
        self.allied_front_line_sheet.convert_alpha()
        self.enemy_front_line_sheet = pygame.image.load(ENEMY_FRONT_LINE_PATH)
        self.enemy_front_line_sheet.convert_alpha()
        self.small_explosions_sheet = pygame.image.load(SMALL_EXPLOSIONS_PATH)
        self.small_explosions_sheet.convert_alpha()
        self.big_explosion_sheet = pygame.image.load(BIG_EXPLOSION_PATH)
        self.big_explosion_sheet.convert_alpha()
        self.allied_cities_sheet = pygame.image.load(ALLIED_CITIES_PATH)
        self.allied_cities_sheet.convert_alpha()
        self.enemy_cities_sheet = pygame.image.load(ENEMY_CITIES_PATH)
        self.enemy_cities_sheet.convert_alpha()
        self.enemy_freighters_sheet = pygame.image.load(ENEMY_FREIGHTER_PATH)
        self.enemy_freighters_sheet.convert_alpha()
        self.unidentified_surface_sheet = pygame.image.load(UNIDENTIFIED_SURFACE_PATH)
        self.unidentified_surface_sheet.convert_alpha()
        self.unidentified_submerged_sheet = pygame.image.load(UNIDENTIFIED_SUBMERGED_PATH)
        self.unidentified_submerged_sheet.convert_alpha()
        self.escort_sub_sheet = pygame.image.load(ESCORT_SUB_PATH)
        self.escort_sub_sheet.convert_alpha()
        self.heavy_convoy_escort_sheet = pygame.image.load(HEAVY_CONVOY_ESCORT_PATH)
        self.heavy_convoy_escort_sheet.convert_alpha()
        self.land_sheet = pygame.image.load(LAND_PATH)
        self.land_sheet.convert_alpha()
        self.neutral_freighters_sheet = pygame.image.load(NEUTRAL_FREIGHTER_PATH)
        self.neutral_freighters_sheet.convert_alpha()
        self.open_ocean_sheet = pygame.image.load(OPEN_OCEAN_PATH)
        self.open_ocean_sheet.convert_alpha()
        self.patrol_helicopter_sheet = pygame.image.load(PATROL_HELICOPTER_PATH)
        self.patrol_helicopter_sheet.convert_alpha()
        self.patrol_plane_sheet = pygame.image.load(PATROL_PLANE_PATH)
        self.patrol_plane_sheet.convert_alpha()
        self.player_sub_sheet = pygame.image.load(PLAYER_SUB_PATH)
        self.player_sub_sheet.convert_alpha()
        self.small_convoy_escort_sheet = pygame.image.load(SMALL_CONVOY_ESCORT_PATH)
        self.small_convoy_escort_sheet.convert_alpha()
        self.sonobuoy_sheet = pygame.image.load(SONOBUOY_PATH)
        self.sonobuoy_sheet.convert_alpha()
        self.allied_fleet_sheet = pygame.image.load(ALLIED_FLEET_PATH)
        self.allied_fleet_sheet.convert_alpha()
        self.craters_sheet = pygame.image.load(CRATERS_PATH)
        self.craters_sheet.convert_alpha()
        self.wake_sheet = pygame.image.load(WAKE_PATH)
        self.wake_sheet.convert_alpha()
        self.torpedo_sheet = pygame.image.load(TORPEDO_PATH)
        self.torpedo_sheet.convert_alpha()
        self.missile_sheet = pygame.image.load(MISSILE_PATH)
        self.missile_sheet.convert_alpha()
        self.smoke_sheet = pygame.image.load(SMOKE_PATH)
        self.smoke_sheet.convert_alpha()
        self.allied_plane_sheet = pygame.image.load(ALLIED_PLANE_PATH)
        self.allied_plane_sheet.convert_alpha()
        self.allied_helicopter_sheet = pygame.image.load(ALLIED_HELICOPTER_PATH)
        self.allied_helicopter_sheet.convert_alpha()
        self.enemy_fleet_sheet = pygame.image.load(ENEMY_FLEET_PATH)
        self.enemy_fleet_sheet.convert_alpha()
        self.entity_sheets = {
            self.escort_sub_sheet: {"frames": 4, "regular": {}, "zoomed out": {}},
            self.heavy_convoy_escort_sheet: {"frames": 4, "regular": {}, "zoomed out": {}},
            self.neutral_freighters_sheet: {"frames": 4, "regular": {}, "zoomed out": {}},
            self.patrol_helicopter_sheet: {"frames": 2, "regular": {}, "zoomed out": {}},
            self.allied_helicopter_sheet: {"frames": 2, "regular": {}, "zoomed out": {}},
            self.patrol_plane_sheet: {"frames": 1, "regular": {}, "zoomed out": {}},
            self.allied_plane_sheet: {"frames": 1, "regular": {}, "zoomed out": {}},
            self.player_sub_sheet: {"frames": 4, "regular": {}, "zoomed out": {}},
            self.sonobuoy_sheet: {"frames": 4, "regular": {}, "zoomed out": {}},
            self.small_convoy_escort_sheet: {"frames": 4, "regular": {}, "zoomed out": {}},
            self.enemy_freighters_sheet: {"frames": 4, "regular": {}, "zoomed out": {}},
            self.unidentified_surface_sheet: {"frames": 4, "regular": {}, "zoomed out": {}},
            self.unidentified_submerged_sheet: {"frames": 4, "regular": {}, "zoomed out": {}},
            self.allied_fleet_sheet: {"frames": 4, "regular": {}, "zoomed out": {}},
            self.enemy_fleet_sheet: {"frames": 4, "regular": {}, "zoomed out": {}},
            self.wake_sheet: {"frames": 4, "regular": {}, "zoomed out": {}},
            self.torpedo_sheet: {"frames": 4, "regular": {}, "zoomed out": {}},
            self.missile_sheet: {"frames": 4, "regular": {}, "zoomed out": {}},
        }
        for sheet in self.entity_sheets.keys():
            for direction in list(filter(lambda x: x != "wait", DIRECTIONS.keys())):
                frames = []
                frames_zoomed_out = []
                for index in range(self.entity_sheets[sheet]["frames"]):
                    frames.append(grab_cell_from_sheet(sheet, index, direction))
                    frames_zoomed_out.append(grab_cell_from_sheet(sheet, index, direction, zoomed_out=True))
                self.entity_sheets[sheet]["regular"][direction] = frames
                self.entity_sheets[sheet]["zoomed out"][direction] = frames_zoomed_out
        self.alert_font = pygame.font.Font(BOLD_FONT_PATH, ALERT_FONT_SIZE)
        self.alerts = {
            "hunted": self.alert_font.render("HUNTED!", True, "red"),
            "incoming": self.alert_font.render("INCOMING TORPEDO!", True, "red"),
            "damaged": self.alert_font.render("DAMAGED!", True, "red"),
            "evaded": self.alert_font.render("EVADED!", True, "yellow"),
            "resupplied": self.alert_font.render("RESUPPLIED!", True, "green"),
            "repaired": self.alert_font.render("REPAIRED!", True, "green"),
            "respawned": self.alert_font.render("NEW SHIP!", True, "green"),
            "cooldown": self.alert_font.render("READY!", True, "yellow"),
        }
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
            self.perfing[fn] = {"cumulative": tot, "longest": tot, "shortest": tot, "num runs": 1}
            if tot >= GAME_UPDATE_TICK_MS - 10:
                self.perfing[fn]["times over"] = 1
            else:
                self.perfing[fn]["times over"] = 0
        else:
            self.perfing[fn]["cumulative"] += tot
            self.perfing[fn]["num runs"] += 1
            if tot < self.perfing[fn]["shortest"]:
                self.perfing[fn]["shortest"] = tot
            if tot > self.perfing[fn]["longest"]:
                self.perfing[fn]["longest"] = tot
            if tot >= GAME_UPDATE_TICK_MS - 10:
                self.perfing[fn]["times over"] += 1
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
                    print("\t\ttime over: {}".format(v["times over"]))
                    average = v["cumulative"] / v["num runs"]
                    print("\t\taverage: {}".format(average))
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
    game = Game()
    game.game_loop()
    pygame.quit()

