from rolls import *
from loading_screen import loading_screen
from tile_map import *
from entity import *
from euclidean import manhattan_distance, chebyshev_distance
from functional import *
from console import *
import modifiers
from alert_level import AlertLevel
import sort_keys
from random import choice, randint, shuffle, randrange
from unit_tile import *
import time
import heapq
from mission import *
from mini_map import MiniMap
from calendar import Calendar
from pygame.math import Vector2
from camera import *

class Scene:
    def __init__(self, game):
        self.display_changed = True
        self.game = game
        self.debug = game.debug
        self.log_sim_events = game.log_sim_events
        self.log_ai_routines = game.log_ai_routines
        self.pathfinding_perf = game.pathfinding_perf
        self.screen = game.screen
        self.screen_wh_cells_tuple = game.screen_wh_cells_tuple
        self.screen_wh_cells_tuple_zoomed_out = game.screen_wh_cells_tuple_zoomed_out
        self.tilemap = None
        self.camera = Camera((0, 0))
        self.entities = []
        self.moving_entities = []
        self.console = Console()
        self.displaying_hud = True 
        self.console_scrolled_up_by = 0 
        self.hud_font = pygame.font.Font(FONT_PATH, HUD_FONT_SIZE)
        self.hud_font_bold = pygame.font.Font(BOLD_FONT_PATH, HUD_FONT_SIZE)
        self.observation_index = 0
        self.time_units_passed = 0
        self.processing = False  
        self.mini_map = None 
        self.displaying_mini_map = False 
        self.displaying_briefing_splash = True
        self.displaying_big_splash = False
        self.hud_swapped = False
        self.help_splash = None
        self.displaying_help_splash = False
        self.paused = True
        pygame.time.set_timer(self.game.QUIT_CHECK_RESET_CONFIRM, CONFIRM_RESET_TICK_MS)
     
    def processing_event_dependency_working(self, event_type) -> bool:
        dep = first(lambda x: x[0] == event_type, list(self.processing_events.values()))[3]
        if dep is not None:
            return self.processing_events[dep][2]
        return False
        
    def set_processing_event_working(self, name):
        self.processing_events[name][2] = True

    def set_processing_event_done(self, name):
        self.processing_events[name][2] = False

    def processing_event_is_working(self, name) -> bool:
        return self.processing_events[name][2]
 
    def is_processing_event(self, event_type, name) -> bool:
        return name in self.events.keys() and self.events[name][0] == event_type

    def get_processing_event_fn(self, event_type):
        return first(lambda x: x[0] == event_type, list(self.processing_events.values()))[1] 

    def get_processing_event_type(self, name):
        return self.processing_events[name][0]

    def quit_check_reset_confirm(self):
        self.game.exit_game_confirm = False

    def reset_observation_index(self):
        self.observation_index = 0
        self.set_processing_event_done("reset_observation_index")

    def moved(self) -> bool:
        move_key = self.movement_key_pressed()
        if move_key and KEY_TO_DIRECTION[move_key] != "wait" and self.shift_pressed():
            self.move_camera(KEY_TO_DIRECTION[move_key])
            return True 
        elif move_key and KEY_TO_DIRECTION[move_key] == "wait" and self.ctrl_pressed():
            self.camera.set(self.player.xy_tuple)
            return True
        elif move_key: 
            self.player.orientation = KEY_TO_DIRECTION[move_key]
            return True
        return False

    def generate_big_splash_txt_surf(self, lines) -> pygame.Surface:
        surf = pygame.Surface(BIG_SPLASH_SIZE)
        line_height = HUD_FONT_SIZE + 1
        width = surf.get_width()
        for line in range(len(lines)):
            txt = lines[line]
            line_surface = self.hud_font.render(txt, True, "white")
            x = width // 2 - line_surface.get_width() // 2
            surf.blit(line_surface, (x, line * line_height))
        pygame.draw.rect(surf, "green", (0, 0, BIG_SPLASH_SIZE[0], BIG_SPLASH_SIZE[1]), 1)
        return surf

    def escape_pressed(self):
        if pygame.key.get_pressed()[K_ESCAPE]:
            if isinstance(self, TacticalScene) and self.targeting_ability:
                self.reset_target_mode()
            self.camera.set(self.player.xy_tuple)
            self.displaying_mini_map = False
            self.display_changed = True
            self.displaying_big_splash = False
            self.displaying_briefing_splash = False
            self.displaying_help_splash = False
            if isinstance(self, CampaignScene) and self.game_over:
                self.game.running = False 
            return True
        return False

    def djikstra_map_distance_to(self, xy_tuple, valid_tile_types=["ocean"], land_buffer=False) -> list:
        def fitness_function(tile):
            if tile.tile_type not in valid_tile_types: 
                return INVALID_DJIKSTRA_SCORE
            score = manhattan_distance(tile.xy_tuple, xy_tuple)
            if land_buffer:
                score += self.tilemap.land_buffer_mod(tile.xy_tuple)
            return score
        djikstra_map = [list(map(lambda tile: fitness_function(tile), col)) for col in self.tilemap.tiles]
        return djikstra_map

    def update_mini_map(self):  
        if isinstance(self, CampaignScene):
            scene_type = "campaign"
        if isinstance(self, TacticalScene):
            scene_type = "tactical"
        if self.time_units_passed % UPDATE_MINI_MAP_TU_FREQ == 0:
            self.mini_map.update(scene_type)
        self.set_processing_event_done("update_mini_map")

    # Gets the shortest available route     
    def shortest_path(self, start_loc, end_loc, djikstra_map, valid_tile_types=["ocean"]) -> list:   
        tiles_searched = 0
        traceback_start, traceback_end = None, None
        if self.pathfinding_perf:
            start = time.process_time_ns()
        def print_end_time(start, tiles_searched, found, msg=None):
            end = time.process_time_ns()
            tot = end - start
            if found:
                traceback_tot = traceback_end - traceback_start
            player_neighbors = list(map(lambda x: x.xy_tuple, self.tilemap.neighbors_of(self.player.xy_tuple)))
            player_surrounded = len(list(filter(lambda x: x.xy_tuple in player_neighbors, self.entities))) == 8
            start_entity = first(lambda x: x.xy_tuple == start_loc, self.entities)
            start_neighbors = list(map(lambda x: x.xy_tuple, self.tilemap.neighbors_of(start_loc)))
            start_entity_surrounded = len(list(filter(lambda x: x.xy_tuple in start_neighbors, self.entities))) == 8
            if end_loc is not None:
                next_to_target = chebyshev_distance(start_loc, end_loc) == 1
                distance = manhattan_distance(start_loc, end_loc)
                end_entity = first(lambda x: x.xy_tuple == end_loc, self.entities)
            print("__profiling shortest_entity_path()") 
            print("\ttiles_searched: {}".format(tiles_searched)) 
            print("\ttot: {}ns".format(tot)) 
            if found:
                print("\tsearch: {}ns".format(traceback_start - start))
                print("\ttraceback: {}ns".format(traceback_tot)) 
            if end_loc is not None:
                print("\tdistance: {}".format(distance)) 
            print("\tfound: {}".format(found))
            if start_entity is not None:
                print("\tstart_entity: {}".format(start_entity.name))
                print("\tstart_entity_id: {}".format(start_entity.id))
                print("\tstart_entity surrounded: {}".format(start_entity_surrounded))
            if end_loc is not None and end_entity is not None:
                print("\tend_entity: {}".format(end_entity.name))
            if end_loc is not None:
                print("\tplayer surrounded: {}".format(player_surrounded))
                print("\tnext_to_target: {}".format(next_to_target))
            if msg is not None:
                print("\tmsg: {}".format(msg))
       
        if end_loc is not None: 
            # edge case (1) of target surrounded and searching entity not among the surrounders
            end_neighbors = list(map(lambda x: x.xy_tuple, self.tilemap.neighbors_of(end_loc)))
            end_entity_surrounded = len(list(filter(lambda x: x.xy_tuple in end_neighbors, self.entities))) == 8
            start_entity = first(lambda x: x.xy_tuple == start_loc, self.entities)
            if end_entity_surrounded and start_entity.xy_tuple not in end_neighbors:
                if self.pathfinding_perf:
                    print_end_time(start, tiles_searched, False, msg="edge case (1)") 
                return None 
            # edge case (2) of target being next to entity
            next_to_target = chebyshev_distance(start_loc, end_loc) == 1
            if next_to_target:
                if self.pathfinding_perf:
                    print_end_time(start, tiles_searched, False, msg="edge case (2)") 
                return None 

        def get_traceback(ls, goal) -> list:  
            def loc(node):
                return node[2]["loc"]
            def via(node):
                return node[2]["via"]
            nonlocal traceback_start, traceback_end
            traceback_start = time.process_time_ns() 
            current = goal
            traceback = [loc(goal)]
            while loc(current) is not start_loc: 
                for node in ls:                     
                    if loc(node) == via(current):
                        if loc(node) is not start_loc:
                            traceback.append(loc(node))
                        current = node
                        break
            traceback.reverse()
            if self.pathfinding_perf:
                traceback_end = time.process_time_ns()
                print_end_time(start, tiles_searched, True) 
            return traceback 

        def sorted_by_score(ls):
            new_ls = []
            entry_count = 0
            for tile in ls:
                x, y = tile.xy_tuple
                score = djikstra_map[x][y]
                item = [score, entry_count, tile]
                entry_count += 1
                heapq.heappush(new_ls, item)
            return list(map(lambda x: x[2], new_ls))

        w, h = self.tilemap.wh_tuple 
        x0, y0 = start_loc
        seen = []
        visited = []
        seen_bools = [[False for _ in range(h)] for _ in range(w)]
        visited_bools = [[False for _ in range(h)] for _ in range(w)]
        seen_count = 1
        start_score = djikstra_map[x0][y0]
        visited_bools[x0][y0] = True
        start_node = [start_score, 0, {"loc": start_loc, "via": None}]
        heapq.heappush(seen, start_node)
        visited.append(start_node)
        while len(seen) > 0:  
            node = heapq.heappop(seen)
            x1, y1 = node[2]["loc"]
            neighbors = list(filter(lambda x: djikstra_map[x.xy_tuple[0]][x.xy_tuple[1]] != INVALID_DJIKSTRA_SCORE, \
                sorted_by_score(self.tilemap.neighbors_of((x1, y1))))) 
            tile = first(lambda x: visited_bools[x.xy_tuple[0]][x.xy_tuple[1]] == False, neighbors) 
            if tile is not None: 
                x2, y2 = tile.xy_tuple
                seen_count += 1
                tiles_searched += 1
                score = djikstra_map[x2][y2]
                if tile.occupied:
                    score = INVALID_DJIKSTRA_SCORE 
                new_node = {"loc": (x2, y2), "via": (x1, y1)}
                full_node = [score, seen_count, new_node]
                if not visited_bools[x2][y2]:
                    visited.append(full_node)
                visited_bools[x2][y2] = True
                heapq.heappush(seen, full_node) 
                if end_loc is None:
                    if is_edge((w, h), (x2, y2)):
                        return get_traceback(visited, full_node)
                else:
                    if tile.xy_tuple == end_loc:
                        return get_traceback(visited, full_node)
            if any(map(lambda x: visited_bools[x.xy_tuple[0]][x.xy_tuple[1]] == False, neighbors)):
                seen.append(node)
        return None 

    def input_blocked(self):
        # NOTE: later will also block for some pop-up animations and stuff!
        return self.processing

    def get_tail_point(self, entity, center) -> tuple:
        if isinstance(self, TacticalScene):
            if self.zoomed_out:
                cell_size = ZOOMED_OUT_CELL_SIZE
            else:
                cell_size = CELL_SIZE
        else:
            cell_size = CELL_SIZE
        if entity.last_direction == "wait":
            x, y = center
        elif entity.last_direction == "up":
            x, y = center[0], center[1] + cell_size // 2
        elif entity.last_direction == "down":
            x, y = center[0], center[1] - cell_size // 2
        elif entity.last_direction == "left":
            x, y = center[0] + cell_size // 2, center[1]
        elif entity.last_direction == "right":
            x, y = center[0] - cell_size // 2, center[1]
        elif entity.last_direction == "upright":
            x, y = center[0] - cell_size // 2, center[1] + cell_size // 2
        elif entity.last_direction == "upleft":
            x, y = center[0] + cell_size // 2, center[1] + cell_size // 2
        elif entity.last_direction == "downright":
            x, y = center[0] - cell_size // 2, center[1] - cell_size // 2
        elif entity.last_direction == "downleft":
            x, y = center[0] + cell_size // 2, center[1] - cell_size // 2
        return (x, y)

    def draw_big_splash(self, surf):
        x = self.screen.get_width() // 2 - surf.get_width() // 2
        y = 26  
        self.screen.blit(surf, (x, y)) 
        self.display_changed = True
        self.displaying_big_splash = True

    def draw_processing_splash(self):
        surf = self.hud_font.render("...processing...", True, "green", "black") 
        y = 26
        x = self.screen.get_width() // 2 - surf.get_width() // 2
        self.screen.blit(surf, (x, y))
        self.display_changed = True

    def draw(self):
        self.screen.fill("black")
        self.draw_level()
        self.draw_hud()
        self.display_changed = False
        pygame.display.flip()

    def handle_events(self):
        def processing() -> bool:
            return any(map(lambda x: x[2], list(self.processing_events.values())))
        def tactical_scene_update_tick(event_type) -> bool:
            return event.type == self.game.GAME_UPDATE_TICK_TACTICAL \
                and isinstance(self, TacticalScene) \
                and not self.game.campaign_mode \
                and not self.paused \
                and not processing()
        def campaign_scene_update_tick(event_type) -> bool:
            return event.type == self.game.GAME_UPDATE_TICK_CAMPAIGN \
                and isinstance(self, CampaignScene) \
                and self.game.campaign_mode \
                and not self.paused \
                and self.turn_ready() \
                and not processing()
        def launch_processing_events():
            for k in self.processing_events.keys():
                if self.processing_events[k][3] is None \
                    or self.processing_event_dependency_working(self.processing_events[k][0]):
                    self.set_processing_event_working(k)
                    etype = self.get_processing_event_type(k)
                    pygame.event.post(pygame.event.Event(etype)) 
        def is_processing_event(event_type) -> bool:
            valid = list(map(lambda x: x[0], list(self.processing_events.values())))
            return event_type in valid
        for event in pygame.event.get():
            # quit game:
            if event.type == QUIT:
                self.game.running = False
            # window events
            elif event.type == WINDOWFOCUSGAINED:
                self.display_changed = True
            elif event.type == WINDOWMAXIMIZED:
                self.display_changed = True
            elif event.type == WINDOWRESTORED:
                self.display_changed = True
            # Game updates:
            elif tactical_scene_update_tick(event.type):
                launch_processing_events()
            elif campaign_scene_update_tick(event.type):
                launch_processing_events()
            elif is_processing_event(event.type):
                if not self.processing_event_dependency_working(event.type):
                    fn = self.get_processing_event_fn(event.type)
                    if self.game.perfing:
                        self.game.perf_call(fn)
                    else:
                        fn()
                    self.display_changed = True
            elif event.type == self.game.MISSION_OVER_CHECK_RESET_CONFIRM and isinstance(self, TacticalScene):
                self.mission_over_check_reset_confirm()
            elif event.type == self.game.MISSION_OVER_CHECK and isinstance(self, TacticalScene):
                self.mission_over_check()
            elif event.type == self.game.QUIT_CHECK_RESET_CONFIRM:
                self.quit_check_reset_confirm()
            # Keyboard Buttons:
            elif event.type == KEYDOWN and not self.input_blocked(): 
                self.display_changed = self.keyboard_event_changed_display()
        pygame.event.pump() 

    def update(self):
        self.handle_events()
        if isinstance(self, CampaignScene):
            self.encounter_post_check()

    # Moves an entity in a completely random direction
    def entity_ai_random_move(self, entity):
        if self.log_ai_routines:
            print("entity_ai_random_move()")
        direction = choice(list(DIRECTIONS.keys())) 
        self.move_entity(entity, direction)

    def relative_direction(self, from_xy, to_xy, opposite=False): 
        diff = (to_xy[0] - from_xy[0], to_xy[1] - from_xy[1])
        if opposite:
            diff = tuple(map(lambda x: x * -1, diff))
        for k, v in DIRECTIONS.items():
            if v == diff:
                return k
        return "wait"

    def keyboard_event_changed_display(self) -> bool:
        if isinstance(self, TacticalScene):
            if self.mission_over_splash is None and not self.game.campaign_mode:
                return self.moved() \
                    or self.swapped_hud() \
                    or self.toggled_mini_map() \
                    or self.toggled_briefing() \
                    or self.console_scrolled() \
                    or self.escape_pressed() \
                    or self.cycle_target() \
                    or self.toggled_zoom() \
                    or self.fire_at_target() \
                    or self.toggled_hud() \
                    or self.used_ability() \
                    or self.ended_mission() \
                    or self.help_button_pressed() \
                    or self.toggled_pause() \
                    or self.exited_game() 
            elif self.mission_over_splash is not None and not self.game.campaign_mode:
                return self.ended_mission_mode()
        elif isinstance(self, CampaignScene):
            return self.moved() \
                or self.swapped_hud() \
                or self.toggled_mini_map() \
                or self.toggled_briefing() \
                or self.console_scrolled() \
                or self.escape_pressed() \
                or self.cycle_target() \
                or self.toggled_hud() \
                or self.toggled_shipping_heat_map() \
                or self.toggled_danger_points_heat_map() \
                or self.help_button_pressed() \
                or self.toggled_pause() \
                or self.exited_game() 

    def toggled_pause(self) -> bool:
        if pygame.key.get_pressed()[K_p]:
            self.paused = not self.paused
            self.display_changed = True
            self.push_to_console("Paused: {}".format(self.paused))
            return True
        return False

    def toggled_zoom(self) -> bool:
        if pygame.key.get_pressed()[K_z]:
            self.zoomed_out = not self.zoomed_out
            self.display_changed = True
            self.push_to_console("Zoomed Out: {}".format(self.zoomed_out))
            return True
        return False

    def toggled_shipping_heat_map(self) -> bool: 
        if pygame.key.get_pressed()[K_s] and self.shift_pressed():
            self.displaying_shipping_heat_map = not self.displaying_shipping_heat_map
            self.display_changed = True
            self.push_to_console("Displaying shipping heat map: {}".format(self.displaying_shipping_heat_map))
            return True
        return False

    def toggled_danger_points_heat_map(self) -> bool: 
        if pygame.key.get_pressed()[K_d] and self.shift_pressed():
            self.displaying_danger_points_heat_map = not self.displaying_danger_points_heat_map
            self.display_changed = True
            self.push_to_console("Displaying danger zone heat map: {}".format(self.displaying_danger_points_heat_map))
            return True
        return False

    def help_button_pressed(self) -> bool:
        if pygame.key.get_pressed()[K_SLASH] and self.shift_pressed():
            self.help_splash = self.generate_big_splash_txt_surf(self.help_lines())
            self.displaying_help_splash = True
            return True 
        return False

    def help_lines(self) -> list:
        if isinstance(self, TacticalScene):
            lines = [
                "___CONTROLS___", "",
                "[h, k, k, l, y, u, b, n, period]: movement", "",
                "[shift] + [h, k, k, l, y, u, b, n]: camera movement", "",
                "[ctrl + period]: reset camera", "",
                "[TAB]: cycle targets in view", "",
                "[m]: mini map", "",
                "[r]: briefing", "",
                "[z]: toggle zoomed in/out", "",
                "[p]: pause", "",
                "[ctrl + q]: quit game", "",
                "[ctrl + e]: end mission", "",
                "[ctrl + w]: swap hud placement", "",
                "[shift + w]: toggle hud", "",
                "[1, 2, f]: torps, missiles, fire", "",
                "[9, 0]: passive sonar, radar", "",
                "[8]: active sonar", "",
                "[7]: toggle normal/fast speed", "",
                "[left/right brackets, HOME]: scroll console, reset console", "",
            ]
        elif isinstance(self, CampaignScene):
            lines = [
                "___CONTROLS___", "",
                "[h, k, k, l, y, u, b, n, period]: movement", "",
                "[shift] + [h, k, k, l, y, u, b, n]: camera movement", "",
                "[ctrl + period]: reset camera", "",
                "[TAB]: cycle targets in view", "",
                "[m]: mini map", "",
                "[p]: pause", "",
                "[ctrl + q]: quit game", "",
                "[ctrl + w]: swap hud placement", "",
                "[shift + w]: toggle hud", "",
                "[shift + s]: toggle shipping heat map", "",
                "[shift + d]: toggle danger heat map", "",
                "[left/right brackets, HOME]: scroll console, reset console", "",
            ]
        return lines

    def exited_game(self) -> bool:
        if pygame.key.get_pressed()[K_q] and self.ctrl_pressed():
            if self.game.exit_game_confirm: 
                self.game.running = False
            else:
                self.game.exit_game_confirm = True
                self.push_to_console("Exit game? Press again to confirm.")
            return True
        return False

    def swapped_hud(self) -> bool:
        if pygame.key.get_pressed()[K_w] and self.ctrl_pressed():
            self.hud_swapped = not self.hud_swapped
            return True
        return False

    def toggled_mini_map(self) -> bool:
        if pygame.key.get_pressed()[K_m]:
            self.displaying_mini_map = not self.displaying_mini_map
            return True
        return False

    def toggled_briefing(self) -> bool:
        if pygame.key.get_pressed()[K_r]:
            self.displaying_briefing_splash = not self.displaying_briefing_splash
            return True
        return False

    def toggled_hud(self) -> bool:
        if self.shift_pressed() and pygame.key.get_pressed()[K_w]:
            self.displaying_hud = not self.displaying_hud
            return True
        return False  

    def push_to_console_if_player(self, msg, entities, tag="other"):
        if any(filter(lambda x: x.player, entities)):
            self.console.push(Message(msg, tag, self.calendar.clock_string())) 
            self.display_changed = True

    def push_to_console(self, msg, tag="other"):
        self.console.push(Message(msg, tag, self.calendar.clock_string())) 
        self.display_changed = True

    def console_scrolled(self) -> bool:
        valid = False
        if pygame.key.get_pressed()[K_RIGHTBRACKET]:
            if self.console_scrolled_up_by > 0:
                self.console_scrolled_up_by -= 1
                valid = True
        elif pygame.key.get_pressed()[K_LEFTBRACKET]:
            if len(self.console.messages) - (self.console_scrolled_up_by + 1) >= CONSOLE_LINES:
                self.console_scrolled_up_by += 1
                valid = True
        elif pygame.key.get_pressed()[K_HOME]:
            self.console_scrolled_up_by = 0
            valid = True
        return valid

    def movement_key_pressed(self): # returns Key constant or False 
        if pygame.key.get_pressed()[K_h]: 
            return K_h
        elif pygame.key.get_pressed()[K_j]:
            return K_j
        elif pygame.key.get_pressed()[K_k]:
            return K_k
        elif pygame.key.get_pressed()[K_l]:
            return K_l
        elif pygame.key.get_pressed()[K_y]:
            return K_y
        elif pygame.key.get_pressed()[K_u]:
            return K_u
        elif pygame.key.get_pressed()[K_b]:
            return K_b
        elif pygame.key.get_pressed()[K_n]:
            return K_n
        elif pygame.key.get_pressed()[K_PERIOD]:
            return K_PERIOD
        return False

    def shift_pressed(self) -> bool:
        return pygame.key.get_pressed()[K_RSHIFT] or pygame.key.get_pressed()[K_LSHIFT]

    def ctrl_pressed(self) -> bool:
        return pygame.key.get_pressed()[K_RCTRL] or pygame.key.get_pressed()[K_LCTRL]

    def move_camera(self, direction):
        target_xy_tuple = (
            self.camera.xy_tuple[0] + DIRECTIONS[direction][0],
            self.camera.xy_tuple[1] + DIRECTIONS[direction][1]
        )
        if self.tilemap.tile_in_bounds(target_xy_tuple):
            self.camera.set(target_xy_tuple)

    def entity_can_move(self, entity, direction) -> bool:
        target_xy = (entity.xy_tuple[0] + DIRECTIONS[direction][0], entity.xy_tuple[1] + DIRECTIONS[direction][1])
        in_bounds = self.tilemap.tile_in_bounds(target_xy)
        if not in_bounds:
            return False
        tile = self.tilemap.get_tile(target_xy)
        ground_tile = tile.tile_type == "land" or tile.tile_type == "city"
        if not entity.can_land_move and ground_tile:
            return False
        occupied = any(map(lambda x: x.xy_tuple == target_xy, self.entities))
        return entity.is_mobile() and in_bounds and not occupied

    def draw_console(self, tag):
        applicable = list(filter(lambda x: x.tag == tag, self.console.messages))
        line_height = HUD_FONT_SIZE + 1
        num_lines = CONSOLE_LINES
        console_width = int(self.screen.get_width() * .33)
        console_size = (console_width, line_height * num_lines)
        console_surface = pygame.Surface(console_size, flags=SRCALPHA)
        console_surface.fill(HUD_OPAQUE_BLACK)
        pygame.draw.rect(console_surface, "cyan", (0, 0, console_size[0], console_size[1]), 1)
        last = len(applicable) - 1 
        msgs = []
        for line in range(num_lines):
            index = last - line - self.console_scrolled_up_by
            if index >= 0 and index < len(applicable):
                msg = applicable[index]
                if msg.tag == tag:
                    txt = "[{}] {}".format(msg.turn, msg.msg)
                    msgs.append(txt)
        msgs.reverse() 
        for line in range(len(msgs)):
            line_surface = self.hud_font.render(msgs[line], True, "white")
            console_surface.blit(line_surface, (0, line * line_height))
        if self.hud_swapped:
            y = HUD_Y_EGDE_PADDING
        else:
            y = self.screen.get_height() - line_height * num_lines - 3
        if tag == "rolls":
            x = 0
        elif tag == "combat":
            x = console_width + CONSOLE_PADDING
        elif tag == "other":
            x = (console_width + CONSOLE_PADDING) * 2 
        self.screen.blit(console_surface, (x, y)) 

class CampaignScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.calendar = Calendar()
        self.generate_campaign() 
        self.last_repair_check = 0
        self.game_over = False
        self.game_over_splash = None
        self.extra_lives = 1
        self.last_extra_life = 0
        self.displaying_shipping_heat_map = True
        self.displaying_danger_points_heat_map = True
        self.had_encounter = False
        self.accomplished_something = False
        self.player_in_mission_zone = False
        self.displaying_final_splash = False
        self.processing_events = { 
            "run_entity_behavior": [pygame.event.custom_type(), self.run_entity_behavior, False, None],
            "dead_entity_check": [pygame.event.custom_type(), self.dead_entity_check, False, "run_entity_behavior"],
            "game_over_check": [pygame.event.custom_type(), self.game_over_check, False, None],
            "sim_event_run_warsim": [pygame.event.custom_type(), self.sim_event_run_warsim, False, None],
            "sim_event_encounter_check": [pygame.event.custom_type(), self.sim_event_encounter_check, False, \
                "run_entity_behavior"],
            "sim_event_resupply_check": [pygame.event.custom_type(), self.sim_event_resupply_check, False, \
                "run_entity_behavior"],
            "sim_event_repair_check": [pygame.event.custom_type(), self.sim_event_repair_check, False, \
                "run_entity_behavior"],
            "sim_event_extra_lives_check": [pygame.event.custom_type(), self.sim_event_extra_lives_check, False, \
                "run_entity_behavior"],
            "sim_event_danger_points_check": [pygame.event.custom_type(), self.sim_event_danger_points_check, False, \
                "run_entity_behavior"],
            "update_front_lines": [pygame.event.custom_type(), self.update_front_lines, False, "sim_event_run_warsim"],
            "update_mini_map": [pygame.event.custom_type(), self.update_mini_map, False, "sim_event_run_warsim"],
        }
        pygame.time.set_timer(self.game.GAME_UPDATE_TICK_CAMPAIGN, GAME_UPDATE_TICK_MS)
        pygame.time.set_timer(self.game.QUIT_CHECK_RESET_CONFIRM, CONFIRM_RESET_TICK_MS)
        changed_tiles = [tile for tile in self.tilemap.changed_tiles]
        self.master_surface = self.update_master_surface(changed_tiles, reset=True)
        self.master_surface_with_traffic = self.update_master_surface(changed_tiles, reset=True, traffic=True, \
            clear=True)
        self.mini_map = MiniMap(self, "campaign")

    def update_master_surface(self, changed_tiles, reset=False, traffic=False, clear=False):
        if reset:
            changed_tiles = self.tilemap.all_tiles()
            surf = pygame.Surface((self.tilemap.wh_tuple[0] * CELL_SIZE, self.tilemap.wh_tuple[1] * CELL_SIZE))
        elif traffic:
            if len(changed_tiles) > 0:
                surf = self.master_surface_with_traffic.copy()
            else:
                surf = self.master_surface_with_traffic
        else:
            if len(changed_tiles) > 0:
                surf = self.master_surface.copy()
            else:
                surf = self.master_surface
        w, h = self.tilemap.wh_tuple
        for tile in changed_tiles:
            x, y = tile.xy_tuple
            rect = (x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            if tile.tile_type == "ocean":
                pygame.draw.rect(surf, "navy", rect)
                if traffic:
                    traffic_points = self.map_traffic_points[x][y]
                    if traffic_points > 0:
                        alpha = min(OVERLAY_ALPHA_BASE + OVERLAY_ALPHA_INC * traffic_points, 255)
                        tp_surf = pygame.Surface((CELL_SIZE, CELL_SIZE), flags=SRCALPHA)
                        tp_surf.fill(TRAFFIC_OVERLAY_COLOR + [alpha])
                        surf.blit(tp_surf, (rect[0], rect[1]))
            elif tile.tile_type == "land":
                pygame.draw.rect(surf, "olive", rect) 
            elif tile.tile_type == "city":
                pygame.draw.rect(surf, faction_to_color[tile.faction], rect) 
                pygame.draw.rect(surf, "black", rect, 6) 
            pygame.draw.rect(surf, "gray", rect, 1)
        if clear:
            self.tilemap.changed_tiles = []
        if len(changed_tiles) > 0:
            self.display_changed = True
        return surf
 
    def generate_campaign(self):
        self.tilemap = TileMap(CAMPAIGN_MAP_SIZE, "campaign")
        self.orientation = self.tilemap.orientation
        self.player_origin = self.tilemap.player_origin
        self.player = PlayerCampaignEntity(self.player_origin, self.game.debug) 
        self.camera.set(self.player_origin)
        self.entities.append(self.player)
        self.phase = "island"
        self.invasion_target = self.select_invasion_target()
        self.invasion_eta = self.get_invasion_eta() 
        self.briefing_splash = self.generate_big_splash_txt_surf(self.generate_invasion_brief_txt_lines())
        self.mission_tiles = self.get_mission_tiles()
        self.sea_node_distance_map = self.djikstra_map_distance_to_sea_route_end_node()
        for tile in self.tilemap.island_coastal_city_tiles + self.tilemap.mainland_coastal_city_tiles:
            path = self.shortest_path(tile.xy_tuple, None, self.sea_node_distance_map)
            if path is not None: 
                for node in path:
                    tile = self.tilemap.get_tile(node)
                    tile.sea_route_node = True
        for tile in self.tilemap.island_coastal_city_tiles:
            home = choice(list(filter(lambda x: x.tile_type == "ocean", \
                self.tilemap.neighbors_of(choice(self.tilemap.mainland_coastal_city_tiles).xy_tuple))))
            dmap = self.djikstra_map_distance_to(home.xy_tuple)
            path = self.shortest_path(tile.xy_tuple, home.xy_tuple, dmap)
            for node in path:
                tile = self.tilemap.get_tile(node)
                tile.logistical_sea_route = True
        self.map_traffic_points = self.djikstra_map_sea_traffic()
        self.sim_event_place_resupply_vessel() 
        self.active_front_tiles = []
        self.next_front_shift = 0
        self.map_danger_points = self.djikstra_map_danger_points() 
        self.map_fronts = self.map_front_lines()
        self.active_front_line_tiles = []

    def sim_event_increase_danger_zone(self):
        tile = self.tilemap.get_tile(self.player.xy_tuple)
        tile.danger_points += DEFAULT_DANGER_POINTS
        for nbr in self.tilemap.neighbors_of(tile.xy_tuple):
            nbr.danger_points += randint(1, DEFAULT_DANGER_POINTS // 2)
        self.display_changed = True

    def sim_event_place_resupply_vessel(self):
        x, y = self.invasion_target.xy_tuple
        spots = list(filter(lambda x: x.tile_type == "ocean" and not x.coast and \
            self.map_traffic_points[x.xy_tuple[0]][x.xy_tuple[1]] == 0, \
            valid_tiles_in_range_of(self.tilemap.tiles, (x, y), MISSION_RADIUS)))
        origin = choice(spots).xy_tuple
        resupply_vessel = ResupplyVessel(origin)
        self.tilemap.toggle_occupied(origin)
        self.entities.append(resupply_vessel)
        self.push_to_console("ATTN: Resupply Vessel at: {}".format(origin))

    def djikstra_map_sea_traffic(self) -> list:
        w, h = self.tilemap.wh_tuple
        djikstra_map = [] 
        for x in range(w):
            djikstra_map.append([])
            for y in range(h):
                neighbors = self.tilemap.neighbors_of((x, y))
                traffic_points = len(list(filter(lambda z: z.sea_route_node or z.logistical_sea_route, neighbors)))
                djikstra_map[x].append(traffic_points)
        return djikstra_map

    def map_front_lines(self) -> list:
        w, h = self.tilemap.wh_tuple
        front_map = [] 
        active_front_line_tiles = []
        for x in range(w):
            front_map.append([])
            for y in range(h):
                tile = self.tilemap.get_tile((x, y))
                neighbors = self.tilemap.neighbors_of((x, y))
                allied_front = tile.faction == "allied" and any(map(lambda x: x.faction == "enemy", neighbors))
                enemy_front = tile.faction == "enemy" and any(map(lambda x: x.faction == "allied", neighbors))
                if allied_front:
                    front_map[x].append("allied")
                    active_front_line_tiles.append(((x, y), "allied"))
                elif enemy_front:
                    front_map[x].append("enemy")
                    active_front_line_tiles.append(((x, y), "enemy"))
                else:
                    front_map[x].append(False)
        self.active_front_line_tiles = active_front_line_tiles
        return front_map

    def djikstra_map_danger_points(self) -> list:
        w, h = self.tilemap.wh_tuple
        djikstra_map = [] 
        for x in range(w):
            djikstra_map.append([])
            for y in range(h):
                neighbors = self.tilemap.neighbors_of((x, y))
                danger_points = len(list(filter(lambda z: z.danger_points > 0, neighbors)))
                danger_points += self.tilemap.get_tile((x, y)).danger_points
                djikstra_map[x].append(danger_points)
        return djikstra_map

    def djikstra_map_distance_to_sea_route_end_node(self) -> list:
        map_tiles = []
        (w, h) = self.tilemap.wh_tuple
        for x in range(w):
            map_tiles.append([])
            for y in range(h):
                tile = self.tilemap.get_tile((x, y))
                if tile.tile_type != "ocean":
                    score = INVALID_DJIKSTRA_SCORE
                else:
                    score = self.tilemap.distance_from_edge((x, y)) + self.tilemap.land_buffer_mod((x, y))
                map_tiles[x].append(score)
        return map_tiles 

    def get_mission_tiles(self) -> list:
        return valid_tiles_in_range_of(self.tilemap.tiles, self.invasion_target.xy_tuple, MISSION_RADIUS)
     
    def get_invasion_eta(self) -> int:
        diff = randint(INVASION_ETA_RANGE[0], INVASION_ETA_RANGE[1])
        return self.time_units_passed + diff
 
    def generate_invasion_brief_txt_lines(self) -> list:
        if self.phase == "island":
            phase_line = "We are preparating for an invasion of one of the islands!"
        elif self.phase == "mainland":
            phase_line = "We are preparing to invade the mainland holdings of the enemy!" 
        lines = [
            "___THEATER BRIEFING___", "", phase_line,
            "The location of our attack will be in the viscinity of {}.".format(self.invasion_target.xy_tuple),
            "The invasion will commence at around {}.".format(self.calendar.get_eta_str(self.time_units_passed, self.invasion_eta, "campaign")),
            "High command requests you patrol the viscinity in order to attack enemy shipping",
            "and targets of opportunity. Use your own discretion.", "",
            "___NOTES___", "",
            "> Your goal is to survive until the campaign is over. You only take the risks",
            "you choose to take, but to get a high score you will have to take some.", "",
            "> Seek the resupply vessel in the mission area if you need more ammunition.",
            "You can also resupply at friendly ports, once some are taken.", "",
            "> If you take minor damage, find a spot outside the shipping lanes to wait and",
            "do some field repairs. We do not yet control any of the ports in theater.",
            "Once we do, you can get faster repairs by waiting next to one of them.", "",
            "> The enemy has several heavy escort ships which are extremely dangerous to you.",
            "you are best off avoiding them, unless you feel very confident in your approach.", "",
            "> The enemy has a large number of escort submarines. Be wary of submerged contacts.", "",
            "> When attacking convoys within {} tiles of an enemy-controlled port, be wary of the".format(OFFMAP_ASW_ENCOUNTER_RANGE),
            "possibility for ASW patrol planes covering convoy targets.", "",
            "> You gain an Extra Life every {} points. Earn points by destroying freighters!".format(EXTRA_LIFE_THRESHOLD), "",
            "> The green heat map represents shipping lanes. The brighter the green, the bigger", 
            "the risk/reward.", "",
            "> Press '?' for controls (NOTE: The game starts paused. 'p' to unpause).", "",
            "<ESCAPE to continue>",
        ]
        return lines     

    def select_invasion_target(self) -> Tile:
        if self.phase == "island":
            potentials = list(filter(lambda x: x.island and x.coast and x.tile_type == "land" and x.faction == "enemy", \
                self.tilemap.all_tiles()))
            if len(potentials) == 0:
                self.phase = "mainland"
        if self.phase == "mainland":
            potentials = list(filter(lambda x: x.mainland and x.coast and x.faction == "enemy", \
                self.tilemap.all_tiles()))
        return choice(potentials)

    def sim_event_encounter_check(self): 
        if self.time_units_passed % ENCOUNTER_CHECK_TU_FREQ == 0:
            x, y = self.player.xy_tuple
            traffic_points = self.map_traffic_points[x][y]
            danger_points = self.map_danger_points[x][y]
            if roll_shipping_encounter(traffic_points) <= 0:
                self.sim_event_shipping_encounter(traffic_points)
            elif danger_points > 0 and roll_asw_encounter(danger_points) <= 0:
                self.sim_event_asw_encounter(danger_points, traffic_points)
        self.set_processing_event_done("sim_event_encounter_check")

    def sim_event_asw_encounter(self, danger_points, traffic_points):
        if danger_points > 20:
            scale = 3
        else: 
            scale = 2
        mission = AswPatrol(scale, self.encounter_has_offmap_asw(self.player.xy_tuple, traffic_points))
        self.game.scene_tactical_combat.generate_encounter(mission, self.calendar)
        self.game.current_scene = self.game.scene_tactical_combat
        self.game.campaign_mode = False
        self.last_repair_check = self.time_units_passed
        self.had_encounter = True

    def sim_event_shipping_encounter(self, traffic_points):
        loading_screen()
        self.push_to_console("Convoy contact!") 
        if roll_large_encounter(traffic_points):
            scale = 2
        else:
            scale = 1
        mission = ConvoyAttack(scale=scale, \
            subs=self.encounter_has_subs(traffic_points), \
            heavy_escort=self.encounter_has_heavy_escort(traffic_points), \
            offmap_asw=self.encounter_has_offmap_asw(self.player.xy_tuple, traffic_points), \
            neutral_freighters=roll_neutrals_encounter(traffic_points))
        self.game.scene_tactical_combat.generate_encounter(mission, self.calendar) 
        self.game.current_scene = self.game.scene_tactical_combat
        self.game.campaign_mode = False
        self.last_repair_check = self.time_units_passed
        self.had_encounter = True

    def encounter_has_subs(self, traffic_points) -> bool:
        bonus = [modifiers.traffic_points_encounter_mod(traffic_points)]
        if self.game.subs > 0:
            return roll_sub_encounter(traffic_points, mods=bonus)
        return False

    def encounter_has_heavy_escort(self, traffic_points) -> bool:
        mods = [
            modifiers.traffic_points_encounter_mod(traffic_points),
            modifiers.heavy_escort_is_rare
        ]
        if self.game.heavy_escorts > 0:
            return roll_heavy_escort_encounter(traffic_points, mods=mods)
        return False

    def encounter_has_offmap_asw(self, xy_tuple, traffic_points) -> bool:
        bonus = [modifiers.traffic_points_encounter_mod(traffic_points)]
        in_range = valid_tiles_in_range_of(self.tilemap.tiles, xy_tuple, OFFMAP_ASW_ENCOUNTER_RANGE, manhattan=True)
        if any(map(lambda x: x.tile_type == "city" and x.faction == "enemy", in_range)):
            return roll_offmap_asw_encounter(traffic_points, mods=bonus)
        return False

    def encounter_post_check(self):
        if self.had_encounter and self.game.current_scene is self:
            self.game_over_check()
            self.game.encounters_had += 1
            self.map_danger_points = self.djikstra_map_danger_points()
            self.had_encounter = False
            self.display_changed = True
            if self.tilemap.get_tile(self.player.xy_tuple) in self.mission_tiles and self.accomplished_something:
                self.game.encounters_accomplished_something += 1
                self.game.total_score += SCORE_MISSION_ZONE
                self.push_to_console("+{} points for activity in mission zone.".format(SCORE_MISSION_ZONE))
            self.accomplished_something = False
            self.paused = True
            self.push_to_console("Paused: {}".format(self.paused))

    def turn_ready(self) -> bool: 
        return not self.game_over and self.game.current_scene is self and not self.displaying_final_splash

    def update_front_lines(self):
        if self.time_units_passed % UPDATE_FRONT_LINES_CHECK_TU_FREQ == 0:
            self.map_fronts = self.map_front_lines()
        self.set_processing_event_done("update_front_lines")

    def sim_event_danger_points_check(self):
        if self.time_units_passed % DANGER_POINTS_CHECK_TU_FREQ == 0:
            w, h = self.tilemap.wh_tuple
            for x in range(w):
                for y in range(h):
                    self.tilemap.get_tile((x, y)).reduce_danger_points()
            self.map_danger_points = self.djikstra_map_danger_points()
        self.set_processing_event_done("sim_event_danger_points_check")

    def sim_event_extra_lives_check(self):
        if self.time_units_passed % EXTRA_LIVES_CHECK_TU_FREQ == 0:
            if self.last_extra_life + EXTRA_LIFE_THRESHOLD <= self.game.total_score:
                self.extra_lives += 1
                self.last_extra_life = self.game.total_score
                self.push_to_console("Extra Life Granted!")
        self.set_processing_event_done("sim_event_extra_lives_check")

    def sim_event_run_warsim(self):
        def update_next_front_shift():
            if self.phase == "island":
                self.next_front_shift = self.time_units_passed + WARSIM_TILE_CREEP_FREQUENCY_RANGE_ISLAND
            elif self.phase == "mainland":
                self.next_front_shift = self.time_units_passed + WARSIM_TILE_CREEP_FREQUENCY_RANGE_MAINLAND
        if self.time_units_passed % RUN_WARSIM_TU_FREQ == 0:
            if self.invasion_eta <= self.time_units_passed and self.invasion_target.faction == "enemy":
                self.invasion_target.faction = "allied"
                self.push_to_console("Allied landing successful at {}!".format(self.invasion_target.xy_tuple))
                self.active_front_tiles.append(self.invasion_target)
                update_next_front_shift()
                self.set_processing_event_done("sim_event_run_warsim")
                return
            elif self.invasion_eta > self.time_units_passed and self.invasion_target.faction == "enemy":
                self.set_processing_event_done("sim_event_run_warsim")
                return
            if self.time_units_passed >= self.next_front_shift:
                update_next_front_shift()
                targets = []
                for tile in self.active_front_tiles:
                    potentials = list(filter(lambda x: x.tile_type == "land" or x.tile_type == "city", \
                        self.tilemap.neighbors_of(tile.xy_tuple)))
                    for target in potentials:
                        if target not in targets and target.faction == "enemy":
                            targets.append(target)
                for target in targets:
                    surround_bonus = len(list(filter(lambda x: x.faction == "allied", \
                        self.tilemap.neighbors_of(target.xy_tuple))))
                    if target.tile_type == "city":
                        terrain_mod = -3
                    if target.untakeable_city:
                        terrain_mod = FAIL_DEFAULT
                    else:
                        terrain_mod = 0
                    attack_successful = roll_for_front_change([surround_bonus, terrain_mod])
                    if attack_successful:
                        target.faction = "allied"
                        self.tilemap.changed_tiles.append(target)
                        if target.tile_type == "city":
                            self.push_to_console("Allied forces take city at {}!".format(target.xy_tuple))
                            self.game.cities_conquered += 1
                            self.mini_map.terrain_base_needs_update = True
                        self.active_front_tiles.append(target)
                if len(targets) == 0:
                    if self.phase == "island":
                        self.game.islands_conquered += 1
                    self.active_front_tiles = []
                    self.invasion_target = self.select_invasion_target()
                    self.invasion_eta = self.get_invasion_eta()
                    self.briefing_splash = self.generate_big_splash_txt_surf(self.generate_invasion_brief_txt_lines())
                    self.mission_tiles = self.get_mission_tiles()
                    self.displaying_briefing_splash = True
                    resupply_ship = first(lambda x: x.name == "resupply vessel", self.entities)
                    if resupply_ship is not None:
                        self.tilemap.toggle_occupied(resupply_ship.xy_tuple)
                        if resupply_ship in self.entities:
                            self.entities.remove(resupply_ship)
                        self.sim_event_place_resupply_vessel()
        self.set_processing_event_done("sim_event_run_warsim")

    def game_over_check(self):
        if self.time_units_passed % GAME_OVER_CHECK_TU_FREQ == 0:
            game_over = False
            if self.phase == "mainland":
                mainland_tiles = list(filter(lambda x: x.mainland, self.tilemap.all_tiles()))
                total_mainland_tiles = len(mainland_tiles)
                allied_mainland_tiles = len(list(filter(lambda x: x.faction == "allied", mainland_tiles)))
                percent_conquered = allied_mainland_tiles / total_mainland_tiles * 100
                if percent_conquered > VICTORY_THRESHOLD:
                    title_line = "__VICTORY! WAR WON!__"
                    game_over = True
            if self.player.hp["current"] <= 0:
                if self.extra_lives > 0:
                    if not self.sim_event_player_respawn():
                        title_line = "__GAME OVER___"
                        game_over = True
                else:
                    title_line = "__GAME OVER___"
                    game_over = True
            if game_over:
                lines = [
                    "Total Score: {}".format(self.game.total_score), "",
                    "___ASSORTED STATISTICS___",
                    "Freighters Sunk: {}".format(self.game.freighters_sunk),
                    "Small Escorts Sunk: {}".format(self.game.escorts_sunk),
                    "Escort Subs Sunk: {} / {}".format(self.game.subs_sunk, STARTING_SUBS),
                    "Heavy Escorts Sunk: {} / {}".format(self.game.heavy_escorts_sunk, STARTING_HEAVY_ESCORTS),
                    "Neutral Freighters Sunk: {}".format(self.game.neutral_freighters_sunk),
                    "Encounters: {}".format(self.game.encounters_had),
                    "Encounters w/ Retained Stealth: {}".format(self.game.encounters_retained_stealth),
                    "Meaningful Encounters: {}".format(self.game.encounters_accomplished_something),
                    "Meaningful Encounters w/ Retained Stealth: {}".format(self.game.encounters_accomplished_something_retained_stealth),
                    "Times Pursuers Evaded: {}".format(self.game.times_lost_hunters),
                    "Islands Taken: {}".format(self.game.islands_conquered),
                    "Cities/Ports Taken: {}".format(self.game.cities_conquered),
                    "Total Damage Sustained: {}".format(self.game.total_damage_taken),
                    "Torpedos Evaded: {}".format(self.game.torpedos_evaded),
                    "Torpedos Used: {}".format(self.game.torpedos_used),
                    "Missiles Used: {}".format(self.game.missiles_used),
                    "Times Resupplied: {}".format(self.game.times_resupplied),
                    "Extra Lives Used: {}".format(self.game.extra_lives_used),
                ]
                if self.extra_lives > 0 and self.player.hp["current"] <= 0:
                    lines.append("> Un-used extra lives, since no ports were taken.")
                splash_lines = [title_line, ""] + lines + ["", "<ESC to continue>"]
                self.game_over_splash = self.generate_big_splash_txt_surf(splash_lines) 
                self.game_over = True
                self.player_turn_ended = True
                self.display_changed = True
                self.displaying_final_splash = True
        self.set_processing_event_done("game_over_check")

    def sim_event_player_respawn(self) -> bool:
        allied_ports = list(filter(lambda x: x.tile_type == "city" and x.faction == "allied" and x.coast, \
            self.tilemap.all_tiles()))
        if len(allied_ports) == 0:
            return False
        else:
            self.tilemap.toggle_occupied(self.player.xy_tuple)
            spawn = choice(list(filter(lambda x: x.tile_type == "ocean", \
                self.tilemap.neighbors_of(choice(allied_ports).xy_tuple)))).xy_tuple
            self.player.xy_tuple = spawn
            self.camera.set(spawn)
            self.player.hp["current"] = self.player.hp["max"]
            self.tilemap.toggle_occupied(spawn)
            self.push_to_console("You and most of your crew are rescued!")
            self.push_to_console("After being brough back to port and a")
            self.push_to_console("short period of recovery, you've been")
            self.push_to_console("given a new vessel.")
            self.extra_lives -= 1
            self.game.extra_lives_used += 1
            self.update_mini_map()
            return True

    def sim_event_repair_check(self):
        if self.time_units_passed % REPAIR_CHECK_TU_FREQ == 0:
            diff = self.time_units_passed - self.last_repair_check
            hits = diff // PLAYER_REPAIR_FREQUENCY
            if hits > 0 and self.player.hp["current"] < self.player.hp["max"]:
                friendly_ports = first(lambda x: x.tile_type == "city" and x.faction == "allied", \
                    self.tilemap.neighbors_of(self.player.xy_tuple)) is not None
                if friendly_ports:
                    amt = 4 * hits
                else:
                    amt = 1 * hits
                self.player.change_hp(amt)
                self.push_to_console("{} HP repaired in the field!".format(amt))
                self.last_repair_check = self.time_units_passed
        self.set_processing_event_done("sim_event_repair_check")

    def sim_event_resupply_check(self):
        if self.time_units_passed % RESUPPLY_CHECK_TU_FREQ == 0:
            resupply_ship = first(lambda x: x.name == "resupply vessel", self.entities)
            resupply_ship_in_range = resupply_ship is not None and chebyshev_distance(self.player.xy_tuple, \
                resupply_ship.xy_tuple) <= 1
            next_to_city = first(lambda x: x.tile_type == "city" and x.faction == "allied", \
                self.tilemap.neighbors_of(self.player.xy_tuple)) is not None
            needs_ammo = self.player.torps < PLAYER_DEFAULT_TORPS or self.player.missiles < PLAYER_DEFAULT_MISSILES
            if (resupply_ship_in_range or next_to_city) and needs_ammo:
                if resupply_ship_in_range:
                    source = "resupply vessel"
                elif next_to_city:
                    source = "friendly port"
                self.player.torps = PLAYER_DEFAULT_TORPS
                self.player.missiles = PLAYER_DEFAULT_MISSILES
                self.push_to_console("Fresh ammo from {}!".format(source))
                self.game.times_resupplied += 1
        self.set_processing_event_done("sim_event_resupply_check")

    def move_entity(self, entity, direction) -> bool:
        camera_coupled = self.player.xy_tuple == self.camera.xy_tuple
        target_xy_tuple = (
            entity.xy_tuple[0] + DIRECTIONS[direction][0], 
            entity.xy_tuple[1] + DIRECTIONS[direction][1]
        )
        # moving into occupied space
        if direction != "wait" and self.tilemap.occupied(target_xy_tuple):
            self.push_to_console_if_player("occupied tile", [entity])  
            direction = "wait"
        # wait 
        if direction == "wait":
            cost = WAIT_TU_COST
            entity.next_move_time = self.time_units_passed + cost
            entity.last_direction = direction
            if entity.player and camera_coupled:
                self.camera.set(self.player.xy_tuple)
            return True
        # valid movement
        elif self.entity_can_move(entity, direction):
            if entity.player:
                mission_zone = list(map(lambda x: x.xy_tuple, self.mission_tiles))
                if not self.player_in_mission_zone and target_xy_tuple in mission_zone:
                    self.push_to_console("Entering Mission Zone")
                    self.player_in_mission_zone = True
                elif self.player_in_mission_zone and target_xy_tuple not in mission_zone:
                    self.push_to_console("Leaving Mission Zone")
                    self.player_in_mission_zone = False
            self.tilemap.toggle_occupied(entity.xy_tuple)
            self.tilemap.toggle_occupied(target_xy_tuple)
            mover = MovingEntity(entity, entity.xy_tuple, target_xy_tuple)
            self.moving_entities.append(mover)
            entity.xy_tuple = target_xy_tuple
            if entity.player and camera_coupled:
                self.camera.set(self.player.xy_tuple)
            time_unit_cost = entity.get_adjusted_speed()
            if direction in ["upright", "upleft", "downright", "downleft"]:
                time_unit_cost *= 2
            entity.next_move_time = self.time_units_passed + time_unit_cost
            entity.last_direction = direction
            return True
        return False

    def cycle_target(self) -> bool:
        visible_entities = list(filter(lambda x: not x.hidden, self.entities))
        if pygame.key.get_pressed()[K_TAB] and len(visible_entities) > 0: 
            self.observation_index = (self.observation_index + 1) % len(visible_entities)
            self.camera.set(visible_entities[self.observation_index].xy_tuple)
            self.display_changed = True
            return True
        return False

    def run_entity_behavior(self): 
        can_move = list(filter(lambda x: x.next_move_time <= self.time_units_passed \
            and not x.name == "resupply vessel", self.entities))
        for entity in can_move:
            if entity.player:
                self.move_entity(self.player, self.player.orientation) 
        self.time_units_passed += 1
        self.calendar.advance("campaign")
        self.set_processing_event_done("run_entity_behavior")

    def dead_entity_check(self):
        new_entities = list(filter(lambda x: not x.dead, self.entities))
        dead_entities = list(filter(lambda x: x.dead, self.entities))
        if len(new_entities) < len(self.entities):
            self.entities = new_entities
            self.display_changed = True
            for entity in dead_entities:
                self.tilemap.toggle_occupied(entity.xy_tuple)
                if entity.name == "escort sub":
                    self.game.subs -= 1
                elif entity.name == "heavy escort":
                    self.game.heavy_escorts -= 1
        self.set_processing_event_done("dead_entity_check")
 
    def draw_hud(self):
        if self.displaying_hud:
            self.draw_console("other") 
            self.draw_player_stats() 
            self.draw_target_stats() 
        if self.displaying_mini_map and self.mini_map is not None:
            self.draw_big_splash(self.mini_map.surf)
        if self.displaying_briefing_splash:
            self.draw_big_splash(self.briefing_splash)
        elif self.game_over_splash is not None:
            self.draw_big_splash(self.game_over_splash)
        elif self.displaying_help_splash:
            self.draw_big_splash(self.help_splash)

    def draw_target_stats(self):
        target = first(lambda x: not x.player and x.xy_tuple == self.camera.xy_tuple and not x.hidden, self.entities)
        if target is not None:
            target_stats = [
                "Target Name: {}".format(target.name),
                "Distance: {}".format(manhattan_distance(self.player.xy_tuple, target.xy_tuple)),
                "Speed: {} ({})".format(target.speed_mode, target.get_adjusted_speed()),
                "Loc: {}".format(target.xy_tuple),
            ]
            text = self.hud_font.render("  |  ".join(target_stats), True, "white")
            surf = pygame.Surface((text.get_width() + 1, text.get_height() + 1), flags=SRCALPHA)
            surf.fill(HUD_OPAQUE_BLACK)
            pygame.draw.rect(surf, "cyan", (0, 0, surf.get_width(), surf.get_height()), 1)
            surf.blit(text, (1, 1))
            if self.hud_swapped:
                y = self.screen.get_height() - surf.get_height() - HUD_Y_EGDE_PADDING
            else:
                y = HUD_Y_EGDE_PADDING
            pos = (self.screen.get_width() / 2 - surf.get_width() / 2, y)
            self.screen.blit(surf, pos)

    def draw_player_stats(self):
        line_height = HUD_FONT_SIZE + 1
        stats_lines = [
            "Score: {}".format(self.game.total_score),
            "Day: {}".format(self.calendar.day),
            "Time: {}".format(self.calendar.clock_string()),
            "HP: {}/{}".format(self.player.hp["current"], self.player.hp["max"]),
            "Extra Lives: {}".format(self.extra_lives),
            "Loc: {}".format(self.player.xy_tuple),
            "Camera: {}".format(self.camera.xy_tuple),
            "Speed: {} ({})".format(self.player.speed_mode, self.player.get_adjusted_speed()),
            "Traveling: {}".format(DIRECTION_TO_COMPASS[self.player.orientation]),
            "Torpedos: {}".format(self.player.torps),
            "Missiles: {}".format(self.player.missiles),
        ]
        stats_width = int(self.screen.get_width() * .13)
        stats_size = (stats_width, len(stats_lines) * line_height)
        stats_surface = pygame.Surface(stats_size, flags=SRCALPHA)
        stats_surface.fill(HUD_OPAQUE_BLACK)
        pygame.draw.rect(stats_surface, "cyan", (0, 0, stats_size[0], stats_size[1]), 1)
        count_y = 0
        for line in stats_lines:
            text = self.hud_font.render(line, True, "white")
            x = 4
            y = line_height * count_y
            stats_surface.blit(text, (x, y))
            count_y += 1
        if self.hud_swapped:
            y = self.screen.get_height() - stats_surface.get_height() - HUD_Y_EGDE_PADDING
        else:
            y = HUD_Y_EGDE_PADDING
        pos = (self.screen.get_width() - stats_width, y)
        self.screen.blit(stats_surface, pos)

    def draw_level(self, grid_lines=True):
        topleft = (self.camera.xy_tuple[0] - self.screen_wh_cells_tuple[0] // 2, \
            self.camera.xy_tuple[1] - self.screen_wh_cells_tuple[1] // 2)
        area_rect = (topleft[0] * CELL_SIZE, topleft[1] * CELL_SIZE, \
            self.screen_wh_cells_tuple[0] * CELL_SIZE, self.screen_wh_cells_tuple[1] * CELL_SIZE)
        # draw tilemap
        changed_tiles = self.tilemap.changed_tiles
        self.master_surface = self.update_master_surface(changed_tiles)
        self.master_surface_with_traffic = self.update_master_surface(changed_tiles, traffic=True, clear=True)
        if self.displaying_shipping_heat_map:
            self.screen.blit(self.master_surface_with_traffic, (0, 0), area=area_rect)
        else:
            self.screen.blit(self.master_surface, (0, 0), area=area_rect)

        # draw entities:
        if self.debug:
            visible_entites = self.entities
        else:
            visible_entities = list(filter(lambda x: not x.hidden, self.entities))
        for entity in visible_entities:
            mover = first(lambda x: x.entity is entity, self.moving_entities)
            if mover is None:
                x, y = entity.xy_tuple
            else:
                x, y = mover.last
            if x >= 0 and y >= 0 and x < self.tilemap.wh_tuple[0] and y < self.tilemap.wh_tuple[1]:
                if mover is None:
                    rect = ((x - topleft[0]) * CELL_SIZE, (y - topleft[1]) * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                else:
                    origin = Vector2((x - topleft[0]) * CELL_SIZE, (y - topleft[1]) * CELL_SIZE)
                    tx, ty = mover.current
                    target = Vector2((tx - topleft[0]) * CELL_SIZE, (ty - topleft[1]) * CELL_SIZE)
                    actual = origin.move_towards(target, mover.progress * mover.speed)
                    mover.progress += 2
                    rect = (actual[0], actual[1], CELL_SIZE, CELL_SIZE)
                    if target == actual:
                        self.moving_entities.remove(mover)
                img = entity.image
                self.screen.blit(img, rect)
                # a "tail" showing direction came from:
                target = (rect[0] + CELL_SIZE // 2, rect[1] + CELL_SIZE // 2)
                tail_point = self.get_tail_point(entity, target) 
                pygame.draw.line(self.screen, "white", target, tail_point, 2) 
                # reticule if camera on AI unit:
                if entity.xy_tuple == self.camera.xy_tuple and not entity.player:
                    target = (rect[0] + CELL_SIZE // 2, rect[1] + CELL_SIZE // 2)
                    pygame.draw.circle(self.screen, "cyan", target, int(CELL_SIZE * .66), 2)
        for tile in self.active_front_line_tiles:
            x, y = tile[0]
            if x >= 0 and y >= 0 and x < self.tilemap.wh_tuple[0] and y < self.tilemap.wh_tuple[1]:
                rect = ((x - topleft[0]) * CELL_SIZE, (y - topleft[1]) * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                if self.tilemap.get_tile((x, y)).tile_type == "city":
                    color = "black"
                else:
                    color = faction_to_color[tile[1]]
                img = unit_tile_circle(color, hollow=True)
                self.screen.blit(img, rect)

class TacticalScene(Scene):
    def __init__(self, game): 
        super().__init__(game)
        self.tilemap = TileMap(MAP_SIZE, "open ocean")
        self.processing_events = {
            "run_entity_behavior": [pygame.event.custom_type(), self.run_entity_behavior, False, None],
            "stealth_check": [pygame.event.custom_type(), self.stealth_check, False, "run_entity_behavior"],
            "torpedo_arrival_check": [pygame.event.custom_type(), self.torpedo_arrival_check, False, \
                "run_entity_behavior"],
            "missile_arrival_check": [pygame.event.custom_type(), self.missile_arrival_check, False, \
                "run_entity_behavior"],
            "sensor_checks": [pygame.event.custom_type(), self.sensor_checks, False, "run_entity_behavior"],
            "offmap_asw_check": [pygame.event.custom_type(), self.offmap_asw_check, False, "run_entity_behavior"],
            "chase_check": [pygame.event.custom_type(), self.chase_check, False, "run_entity_behavior"],
            "incoming_torp_alert": [pygame.event.custom_type(), self.incoming_torp_alert, False, "run_entity_behavior"],
            "alert_check": [pygame.event.custom_type(), self.alert_check, False, "run_entity_behavior"],
            "update_distance_to_player_map": [pygame.event.custom_type(), self.update_distance_to_player_map, False, \
                "run_entity_behavior"],
            "dead_entity_check": [pygame.event.custom_type(), self.dead_entity_check, False, "run_entity_behavior"],
            "update_mini_map": [pygame.event.custom_type(), self.update_mini_map, False, "run_entity_behavior"],
        }
        pygame.time.set_timer(self.game.GAME_UPDATE_TICK_TACTICAL, GAME_UPDATE_TICK_MS)
        pygame.time.set_timer(self.game.MISSION_OVER_CHECK_RESET_CONFIRM, CONFIRM_RESET_TICK_MS)
        pygame.time.set_timer(self.game.MISSION_OVER_CHECK, MISSION_OVER_TICK_MS)
        changed_tiles = [tile for tile in self.tilemap.changed_tiles]
        self.master_surface = self.update_master_surface(changed_tiles, reset=True)
        self.master_surface_zoomed_out = self.update_master_surface(changed_tiles, reset=True, zoomed_out=True, \
            clear=True)
        self.mini_map = MiniMap(self, "tactical")
        self.psonar_overlay_cell = pygame.Surface((CELL_SIZE, CELL_SIZE), flags=SRCALPHA)
        #self.psonar_overlay_cell.set_colorkey(ALPHA_KEY)
        #self.psonar_overlay_cell.fill(ALPHA_KEY)
        self.psonar_overlay_cell_zoomed_out = pygame.Surface((ZOOMED_OUT_CELL_SIZE, ZOOMED_OUT_CELL_SIZE), \
            flags=SRCALPHA)
        self.psonar_overlay_cell.fill(SONAR_OVERLAY_COLOR)
        self.psonar_overlay_cell_zoomed_out.fill(SONAR_OVERLAY_COLOR)
        self.radar_overlay_cell = pygame.Surface((CELL_SIZE, CELL_SIZE), flags=SRCALPHA)
        self.radar_overlay_cell_zoomed_out = pygame.Surface((ZOOMED_OUT_CELL_SIZE, ZOOMED_OUT_CELL_SIZE), \
            flags=SRCALPHA)
        self.radar_overlay_cell.fill(RADAR_OVERLAY_COLOR)
        self.radar_overlay_cell_zoomed_out.fill(RADAR_OVERLAY_COLOR)
        self.targeting_overlay_cell = pygame.Surface((CELL_SIZE, CELL_SIZE), flags=SRCALPHA)
        self.targeting_overlay_cell_zoomed_out = pygame.Surface((ZOOMED_OUT_CELL_SIZE, ZOOMED_OUT_CELL_SIZE), \
            flags=SRCALPHA)
        self.targeting_overlay_cell.fill(HUD_OPAQUE_RED)
        self.targeting_overlay_cell_zoomed_out.fill(HUD_OPAQUE_RED)
        self.player_sonar_overlay_surface = pygame.Surface(((PASSIVE_SONAR_RANGE * 2 + 1) * CELL_SIZE, \
            (PASSIVE_SONAR_RANGE * 2 + 1) * CELL_SIZE), flags=SRCALPHA)
        self.player_sonar_overlay_surface.set_colorkey(ALPHA_KEY)
        self.player_sonar_overlay_surface.fill(ALPHA_KEY)
        self.player_radar_overlay_surface = pygame.Surface(((RADAR_RANGE * 2 + 1) * CELL_SIZE, \
            (RADAR_RANGE * 2 + 1) * CELL_SIZE), flags=SRCALPHA)
        self.player_radar_overlay_surface.set_colorkey(ALPHA_KEY)
        self.player_radar_overlay_surface.fill(ALPHA_KEY)
        self.player_sonar_overlay_surface_zoomed_out = \
            pygame.Surface(((PASSIVE_SONAR_RANGE * 2 + 1) * ZOOMED_OUT_CELL_SIZE, \
            (PASSIVE_SONAR_RANGE * 2 + 1) * ZOOMED_OUT_CELL_SIZE), flags=SRCALPHA)
        self.player_sonar_overlay_surface_zoomed_out.set_colorkey(ALPHA_KEY)
        self.player_sonar_overlay_surface_zoomed_out.fill(ALPHA_KEY)
        self.player_radar_overlay_surface_zoomed_out = pygame.Surface(((RADAR_RANGE * 2 + 1) * ZOOMED_OUT_CELL_SIZE, \
            (RADAR_RANGE * 2 + 1) * ZOOMED_OUT_CELL_SIZE), flags=SRCALPHA)
        self.player_radar_overlay_surface.set_colorkey(ALPHA_KEY)
        self.player_radar_overlay_surface.fill(ALPHA_KEY)
        self.player_torpedo_range_overlay_surface = pygame.Surface(((TORPEDO_RANGE * 2 + 1) * CELL_SIZE, \
            (TORPEDO_RANGE * 2 + 1) * CELL_SIZE), flags=SRCALPHA)
        self.player_torpedo_range_overlay_surface.set_colorkey(ALPHA_KEY)
        self.player_torpedo_range_overlay_surface.fill(ALPHA_KEY)
        self.player_torpedo_range_overlay_surface_zoomed_out = \
            pygame.Surface(((TORPEDO_RANGE * 2 + 1) * ZOOMED_OUT_CELL_SIZE, \
            (TORPEDO_RANGE * 2 + 1) * ZOOMED_OUT_CELL_SIZE), flags=SRCALPHA)
        self.player_torpedo_range_overlay_surface_zoomed_out.set_colorkey(ALPHA_KEY)
        self.player_torpedo_range_overlay_surface_zoomed_out.fill(ALPHA_KEY)
        self.player_missile_range_overlay_surface_zoomed_out = \
            pygame.Surface(((TORPEDO_RANGE * 2 + 1) * ZOOMED_OUT_CELL_SIZE, \
            (MISSILE_RANGE * 2 + 1) * ZOOMED_OUT_CELL_SIZE), flags=SRCALPHA)
        self.player_missile_range_overlay_surface_zoomed_out.set_colorkey(ALPHA_KEY)
        self.player_missile_range_overlay_surface_zoomed_out.fill(ALPHA_KEY)
        self.player_missile_range_overlay_surface = pygame.Surface(((TORPEDO_RANGE * 2 + 1) * CELL_SIZE, \
            (MISSILE_RANGE * 2 + 1) * CELL_SIZE), flags=SRCALPHA)
        self.player_missile_range_overlay_surface.set_colorkey(ALPHA_KEY)
        self.player_missile_range_overlay_surface.fill(ALPHA_KEY)
        self.enemy_sonar_overlay = pygame.Surface(((PASSIVE_SONAR_RANGE * 2 + 1) * CELL_SIZE, \
            (PASSIVE_SONAR_RANGE* 2 + 1) * CELL_SIZE), flags=SRCALPHA)
        self.enemy_sonar_overlay.set_colorkey(ALPHA_KEY)
        self.enemy_sonar_overlay.fill(ALPHA_KEY)
        self.enemy_sonar_overlay_zoomed_out = pygame.Surface(((PASSIVE_SONAR_RANGE * 2 + 1) * ZOOMED_OUT_CELL_SIZE, \
            (PASSIVE_SONAR_RANGE* 2 + 1) * ZOOMED_OUT_CELL_SIZE), flags=SRCALPHA)
        self.enemy_sonar_overlay_zoomed_out.set_colorkey(ALPHA_KEY)
        self.enemy_sonar_overlay_zoomed_out.fill(ALPHA_KEY)
        overlays = [
            {"overlay": self.player_sonar_overlay_surface, "color": SONAR_OVERLAY_COLOR, \
                "rad": PASSIVE_SONAR_RANGE, "size": CELL_SIZE},
            {"overlay": self.player_torpedo_range_overlay_surface, "color": HUD_OPAQUE_RED, \
                "rad": TORPEDO_RANGE, "size": CELL_SIZE},
            {"overlay": self.player_radar_overlay_surface, "color": RADAR_OVERLAY_COLOR, "rad": RADAR_RANGE, \
                "size": CELL_SIZE},
            {"overlay": self.player_missile_range_overlay_surface, "color": HUD_OPAQUE_RED, \
                "rad": MISSILE_RANGE, "size": CELL_SIZE},
            {"overlay": self.player_radar_overlay_surface_zoomed_out, "color": RADAR_OVERLAY_COLOR, \
                "rad": RADAR_RANGE, "size": ZOOMED_OUT_CELL_SIZE},
            {"overlay": self.player_sonar_overlay_surface_zoomed_out, "color": SONAR_OVERLAY_COLOR, \
                "rad": PASSIVE_SONAR_RANGE, "size": ZOOMED_OUT_CELL_SIZE},
            {"overlay": self.player_torpedo_range_overlay_surface_zoomed_out, \
                "color": HUD_OPAQUE_RED, "rad": TORPEDO_RANGE, "size": ZOOMED_OUT_CELL_SIZE},
            {"overlay": self.player_missile_range_overlay_surface_zoomed_out, \
                "color": HUD_OPAQUE_RED, "rad": MISSILE_RANGE, "size": ZOOMED_OUT_CELL_SIZE},
            {"overlay": self.enemy_sonar_overlay, "color": ENEMY_SONAR_OVERLAY_COLOR, "rad": PASSIVE_SONAR_RANGE, \
                "size": CELL_SIZE},
            {"overlay": self.enemy_sonar_overlay_zoomed_out, "color": ENEMY_SONAR_OVERLAY_COLOR, \
                "rad": PASSIVE_SONAR_RANGE, "size": ZOOMED_OUT_CELL_SIZE},
        ]
        for overlay in overlays: 
            print(overlay)
            w = overlay["overlay"].get_width() // overlay["size"]
            h = overlay["overlay"].get_height() // overlay["size"]
            origin = (w // 2, h // 2) 
            for x in range(w):
                for y in range(h):
                    if manhattan_distance(origin, (x, y)) <= overlay["rad"] and (x, y) != origin:
                        rect = (x * overlay["size"], y * overlay["size"], overlay["size"], overlay["size"])
                        pygame.draw.rect(overlay["overlay"], overlay["color"], rect)

    def update_master_surface(self, changed_tiles, reset=False, zoomed_out=False, clear=False):
        if zoomed_out:
            cell_size = ZOOMED_OUT_CELL_SIZE
        else:
            cell_size = CELL_SIZE
        if reset:
            changed_tiles = self.tilemap.all_tiles()
            surf = pygame.Surface((self.tilemap.wh_tuple[0] * cell_size, self.tilemap.wh_tuple[1] * cell_size))
        elif zoomed_out: 
            if len(changed_tiles) > 0:
                surf = self.master_surface_zoomed_out.copy()
            else:
                surf = self.master_surface_zoomed_out
        else: 
            if len(changed_tiles) > 0:
                surf = self.master_surface.copy()
            else:
                surf = self.master_surface
        w, h = self.tilemap.wh_tuple
        for tile in changed_tiles:
            x, y = tile.xy_tuple
            rect = (x * cell_size, y * cell_size, cell_size, cell_size)
            if tile.tile_type == "ocean":
                pygame.draw.rect(surf, "navy", rect)
            elif tile.tile_type == "land":
                pygame.draw.rect(surf, "olive", rect) 
            if not zoomed_out:
                pygame.draw.rect(surf, "gray", rect, 1)
        if clear:
            self.tilemap.changed_tiles = []
        if len(changed_tiles) > 0:
            self.display_changed = True
        return surf
 
    def mission_over_check_reset_confirm(self):
        self.mission_over_confirm = False

    def update_distance_to_player_map(self):
        if self.player_moved:
            self.map_distance_to_player = self.djikstra_map_distance_to(self.player.xy_tuple)
            self.player_moved = False
        self.set_processing_event_done("update_distance_to_player_map")

    def generate_encounter(self, mission, calendar):
        self.paused = True
        self.mission = mission
        self.calendar = calendar
        self.mission_tiles = []
        self.sonobuoy_count = 0
        self.sonobuoys = []
        self.overlay_sonar = False
        self.overlay_radar = False
        self.targeting_ability = None 
        self.targeting_index = {"current": 0, "max": 0}
        self.offmap_asw_eta = None 
        player_origin = (MAP_SIZE[0] // 2, MAP_SIZE[1] // 2) 
        scale = mission.scale
        freighters = mission.freighters
        escorts = mission.escorts
        subs = mission.subs
        heavy_escort = mission.heavy_escort
        offmap_asw = mission.offmap_asw
        neutral_freighters = mission.neutral_freighters
        num_freighters, num_escorts, num_subs, num_neutral_freighters = 0, 0, 0, 0
        for pop in range(scale):
            if escorts:
                num_escorts += randint(SMALL_CONVOY_ESCORTS_PER_SCALE[0], SMALL_CONVOY_ESCORTS_PER_SCALE[1])
            if subs:
                num_subs += randint(ESCORT_SUBS_PER_SCALE[0], ESCORT_SUBS_PER_SCALE[1])
            if freighters:
                num_freighters += randint(FREIGHTERS_PER_SCALE[0], FREIGHTERS_PER_SCALE[1])
        # NOTE: neutral freighters don't influence enemy spawning fuzz, nor is their population determined by scale.
        if neutral_freighters:
            num_neutral_freighters += randint(1, 10)
        fuzz_val = sum([num_escorts, num_freighters, num_subs]) + ENEMY_SPAWN_FUZZ_BASE
        traveling = choice(list(filter(lambda x: x != "wait", DIRECTIONS.keys())))
        origin = (self.tilemap.wh_tuple[0] // 2, self.tilemap.wh_tuple[1] // 2)
        def fuzzed_spawn(origin, spawn_ls, entity, fuzz):
            while True:
                x = randint(-fuzz, fuzz)
                y = randint(-fuzz, fuzz)
                spawn = (origin[0] + x, origin[1] + y)
                if first(lambda x: x.xy_tuple == spawn, spawn_ls) is None:
                    entity.xy_tuple = spawn
                    spawn_ls.append(entity)
                    self.tilemap.toggle_occupied(spawn)
                    break
        def random_spawn(spawn_ls, entity):
            while True:
                spawn = (randrange(0, self.tilemap.wh_tuple[0]), randrange(0, self.tilemap.wh_tuple[1]))
                if first(lambda x: x.xy_tuple == spawn, spawn_ls) is None:
                    entity.xy_tuple = spawn
                    spawn_ls.append(entity)
                    self.tilemap.toggle_occupied(spawn)
                    break
        def spawn_player(spawn_ls, player):
            player_offset_fuzz = randint(-3, 6)
            player_offset = 24 + player_offset_fuzz
            if "up" in traveling:
                player.xy_tuple = (player.xy_tuple[0], player.xy_tuple[1] - player_offset)
            if "down" in traveling:
                player.xy_tuple = (player.xy_tuple[0], player.xy_tuple[1] + player_offset)
            if "left" in traveling:
                player.xy_tuple = (player.xy_tuple[0] - player_offset, player.xy_tuple[1])
            if "right" in traveling:
                player.xy_tuple = (player.xy_tuple[0] + player_offset, player.xy_tuple[1])
            self.player = player
            self.camera.set(player.xy_tuple)
            spawn_ls.append(player)
            self.tilemap.toggle_occupied(player.xy_tuple)
        units = []
        for _ in range(num_escorts):
            fuzzed_spawn(origin, units, SmallConvoyEscort(origin, "enemy", direction=traveling), fuzz_val)
        for _ in range(num_freighters):
            fuzzed_spawn(origin, units, Freighter(origin, "enemy", direction=traveling), fuzz_val)
        for _ in range(num_subs):
            fuzzed_spawn(origin, units, EscortSub(origin, "enemy", direction=traveling), fuzz_val)
        # NOTE: Heavy Escorts are rare and not affected by scale pop
        if heavy_escort:
            fuzzed_spawn(origin, units, HeavyConvoyEscort(origin, "enemy", direction=traveling), fuzz_val)
        # chasers
        if escorts:
            num_escort_chasers = scale * SMALL_CONVOY_ESCORT_CHASERS_PER_SCALE
            escort_chasers = list(filter(lambda x: x.name == "small convoy escort", units))[:num_escort_chasers]
            for escort in escort_chasers:
                escort.chaser = True
        if subs:
            num_sub_chasers = randint(ESCORT_SUB_CHASERS[0], ESCORT_SUB_CHASERS[1])
            sub_chasers = list(filter(lambda x: x.name == "escort sub", units))[:num_sub_chasers]
            for sub in sub_chasers:
                sub.chaser = True
        # offmap asw planes
        if offmap_asw:
            self.offmap_asw_eta = randint(OFFMAP_ASW_ETA_RANGE[0], OFFMAP_ASW_ETA_RANGE[1]) 
        # player
        spawn_player(units, PlayerSub(player_origin, self.game.scene_campaign_map.player))
        for _ in range(num_neutral_freighters):
            direction = choice(list(filter(lambda x: x != "wait", DIRECTIONS.keys())))
            random_spawn(units, Freighter(origin, "neutral", direction=direction))
        self.entities = units
        shuffle(self.entities)
        # special case of ASW Patrol
        if isinstance(mission, AswPatrol):
            for unit in units:
                unit.chaser = True
                unit.contacts.append(Contact(self.player, 100))
        self.map_distance_to_player = self.djikstra_map_distance_to(self.player.xy_tuple)
        self.player_last_known_xy = None
        self.map_distance_to_player_last_known = None
        self.player_in_enemy_contacts = False
        self.mission_over = False
        self.mission_over_confirm = False
        self.mission_over_splash = None
        self.briefing_splash = self.generate_big_splash_txt_surf(mission.briefing_lines)
        self.starting_damage = self.player.hp["max"] - self.player.hp["current"]
        self.zoomed_out = False
        self.player_moved = False

    def used_ability(self) -> bool:
        ability_key = self.ability_key_pressed()
        if ability_key:
            self.player_uses_ability(ability_key)    
            return True
        return False

    def skill_check_to_str(self, result) -> str:
        r_str = "failure"
        if result <= 0:
            r_str = "success"
        r_str = r_str + " by {}".format(abs(result))
        return r_str

    def mission_over_check(self):
        if self.mission_over:
            if self.player in self.entities:
                hp = self.player.hp["current"]
            else:
                hp = 0
            score_lines = self.mission.assessment_lines(hp + self.starting_damage)
            splash_lines = ["___MISSION COMPLETE___", ""] + score_lines + ["", "<ESC to continue>"]
            self.mission_over_splash = self.generate_big_splash_txt_surf(splash_lines) 
            self.display_changed = True

    def offmap_asw_check(self):  
        def fuzz(axis) -> int:
            if axis == "vertical":
                offset = self.tilemap.wh_tuple[1] // 3
            elif axis == "horizontal":
                offset = self.tilemap.wh_tuple[0] // 3
            return randint(-offset, offset)
        if self.time_units_passed % OFFMAP_ASW_CHECK_TU_FREQ == 0:
            on_map = first(lambda x: x.name == "patrol plane", self.entities) is not None
            if not on_map and self.offmap_asw_eta == OFFMAP_ASW_CLEAR:
                self.offmap_asw_eta = self.time_units_passed + randint(OFFMAP_ASW_ETA_RANGE[0], OFFMAP_ASW_ETA_RANGE[1])
            elif not on_map \
                and self.offmap_asw_eta is not None \
                and self.offmap_asw_eta > 0 \
                and self.time_units_passed >= self.offmap_asw_eta:
                traveling = choice(list(filter(lambda x: x != "wait", DIRECTIONS.keys())))
                x, y = self.tilemap.wh_tuple[0] // 2, self.tilemap.wh_tuple[1] // 2
                if "up" in traveling:
                    y = self.tilemap.wh_tuple[1] - 1
                    x += fuzz("horizontal")
                if "down" in traveling:
                    y = 0
                    x += fuzz("horizontal")
                if "left" in traveling:
                    x = self.tilemap.wh_tuple[0] - 1
                    y += fuzz("vertical")
                if "right" in traveling:
                    x = 0
                    y += fuzz("vertical")
                plane = PatrolPlane((x, y), "enemy", traveling)
                plane.next_move_time = self.time_units_passed + 10 
                self.entities.append(plane)
        self.set_processing_event_done("offmap_asw_check")

    def stealth_check(self):
        if self.mission.stealth_retained and self.player_in_enemy_contacts:
            self.mission.stealth_retained = False
        self.set_processing_event_done("stealth_check")

    def player_debug_mode_contacts(self):
        self.player.contacts = list(map(lambda x: Contact(x, 100), filter(lambda x: not x.player, self.entities)))

    def move_entity(self, entity, direction) -> bool:
        camera_coupled = self.player.xy_tuple == self.camera.xy_tuple
        target_xy_tuple = (
            entity.xy_tuple[0] + DIRECTIONS[direction][0], 
            entity.xy_tuple[1] + DIRECTIONS[direction][1]
        )
        # despawn AI units moving off-map
        if not self.tilemap.tile_in_bounds(target_xy_tuple) and not entity.player:
            if entity in self.entities:
                self.entities.remove(entity)
                self.tilemap.toggle_occupied(entity.xy_tuple)
                self.player.contacts = list(filter(lambda x: x.entity is not entity, self.player.contacts))
                if entity.name == "patrol plane":
                    self.offmap_asw_eta = OFFMAP_ASW_CLEAR 
                return
        # moving into occupied space
        if direction != "wait" and self.tilemap.occupied(target_xy_tuple):
            self.push_to_console_if_player("suspicious noises in this direction", [entity])  
            direction = "wait"
        # wait and long wait
        if direction == "wait":
            cost = WAIT_TU_COST
            entity.next_move_time = self.time_units_passed + cost
            entity.momentum = max(entity.momentum - 2, 0)
            entity.last_direction = direction
            if entity.player and camera_coupled:
                self.camera.set(self.player.xy_tuple)
            return True
        # valid movement
        elif self.entity_can_move(entity, direction):
            self.tilemap.toggle_occupied(entity.xy_tuple)
            self.tilemap.toggle_occupied(target_xy_tuple)
            if entity in list(map(lambda x: x.entity, self.player.contacts)) or entity.player:
                mover = MovingEntity(entity, entity.xy_tuple, target_xy_tuple) 
                self.moving_entities.append(mover) 
            entity.xy_tuple = target_xy_tuple
            if entity.player and camera_coupled:
                self.camera.set(self.player.xy_tuple)
            time_unit_cost = entity.get_adjusted_speed()
            if direction in ["upright", "upleft", "downright", "downleft"]:
                time_unit_cost *= 2
            entity.next_move_time = self.time_units_passed + time_unit_cost
            if entity.last_direction == direction and entity.speed_mode == "fast":
                entity.momentum = min(entity.momentum + 1 + FAST_MODE_BONUS, MOMENTUM_CAP + FAST_MODE_BONUS)
            elif entity.last_direction == direction:
                entity.momentum = min(entity.momentum + 1, MOMENTUM_CAP)
            else:
                entity.momentum = max(entity.momentum - 2, 0)
            entity.last_direction = direction
            return True
        return False

    def cycle_target(self) -> bool:
        if pygame.key.get_pressed()[K_TAB] and self.targeting_ability is not None:
            targets = self.targets(self.player, self.targeting_ability.type)
            self.targeting_index["current"] = (self.targeting_index["current"] + 1) % self.targeting_index["max"]
            self.camera.set(targets[self.targeting_index["current"]].xy_tuple)
            self.display_changed = True
            return True
        elif pygame.key.get_pressed()[K_TAB] and len(self.player.contacts) > 0: 
            self.observation_index = (self.observation_index + 1) % len(self.player.contacts)
            self.camera.set(self.player.contacts[self.observation_index].entity.xy_tuple)
            self.display_changed = True
            return True
        return False

    def reset_target_mode(self):
        self.targeting_ability = None
        self.targeting_index = {"current": 0, "max": 0}
        self.camera.set(self.player.xy_tuple)
        self.display_changed = True

    def ability_key_pressed(self): # Returns key constant or False
        ability_keys = list(map(lambda x: x.key_constant, self.player.abilities))
        for key in ability_keys:
            if pygame.key.get_pressed()[key]:
                return key
        return False
 
    def player_uses_ability(self, key_constant): 
        ability_type = list(filter(lambda y: y[0] == key_constant,
            map(lambda x: (x.key_constant, x.type), self.player.abilities)
        ))[0][1] 
        if ability_type == "torpedo" or ability_type == "missile":
            if self.enter_target_mode(ability_type):
                self.push_to_console("target mode: 'f' to fire, TAB to cycle, ESC to return", tag="combat")
        elif ability_type == "passive sonar":
            self.overlay_sonar = not self.overlay_sonar
            self.push_to_console("displaying passive sonar range: {}".format(self.overlay_sonar))
        elif ability_type == "radar":
            self.overlay_radar = not self.overlay_radar
            radar = self.player.get_ability("radar")
            radar.emerged_to_transmit = not radar.emerged_to_transmit
            self.push_to_console("using radar and displaying range: {}".format(self.overlay_radar))
        elif ability_type == "toggle speed":
            self.player.toggle_speed()
            self.push_to_console("speed mode is now: {}".format(self.player.speed_mode))
        elif ability_type == "active sonar":
            self.push_to_console("using active sonar!")
            self.sim_event_entity_conducts_asonar_detection(self.player)

    def targets(self, entity, ability_type):
        ability = entity.get_ability(ability_type)
        if ability is None:
            return []
        def valid_target(entity):
            if first(lambda x: x.entity is entity, self.player.contacts) is None:
                return False
            if "missile" in ability.type:
                # can go over land
                in_range = manhattan_distance(entity.xy_tuple, self.player.xy_tuple) <= ability.range
            elif "torpedo" in ability.type:
                # TODO: contiguous water targeting only
                in_range = manhattan_distance(entity.xy_tuple, self.player.xy_tuple) <= ability.range
            return in_range and (not entity.player)
        return list(filter(valid_target, self.entities))

    def enter_target_mode(self, ability_type):
        ability = self.player.get_ability(ability_type)
        targets = self.targets(self.player, ability_type)
        if ability.ammo <= 0:
            self.push_to_console("out of ammo!", tag="combat") 
            return False
        elif len(targets) == 0:
            self.push_to_console("no valid targets in range ({})!".format(ability.range), tag="combat") 
            return False
        else:
            self.targeting_ability = ability
            self.camera.set(targets[self.targeting_index["current"]].xy_tuple)
            self.targeting_index["max"] = len(targets)
            self.display_changed = True
            return True

    def ended_mission_mode(self, forced=False) -> bool:
        if pygame.key.get_pressed()[K_ESCAPE] or forced:
            self.game.current_scene = self.game.scene_campaign_map
            self.game.total_score += self.mission.calculate_score(self.player.hp["current"])
            self.game.campaign_mode = True
            self.game.scene_campaign_map.player.torps = self.player.get_ability("torpedo").ammo
            self.game.scene_campaign_map.player.missiles = self.player.get_ability("missile").ammo
            if self.mission.danger_increased():
                self.game.scene_campaign_map.sim_event_increase_danger_zone()
            if self.mission.accomplished_something():
                self.game.scene_campaign_map.accomplished_something = True
                if self.mission.stealth_retained:
                    self.game.encounters_accomplished_something_retained_stealth += 1
            if self.mission.stealth_retained:
                self.game.encounters_retained_stealth += 1
            return True
        return False

    def fire_at_target(self) -> bool:
        # NOTE: It is ensured that the selected weapon has ammo before it gets to this point
        if pygame.key.get_pressed()[K_f] and self.targeting_ability is not None:
            if self.player.on_cooldown(self.time_units_passed):
                eta_str = self.calendar.get_eta_str(self.time_units_passed, self.player.next_ability_time, "tactical")
                self.push_to_console("Next Ability Time: {}".format(eta_str)) 
                return True
            target = self.targets(self.player, self.targeting_ability.type)[self.targeting_index["current"]]
            if target.submersible and self.targeting_ability.type == "missile":
                self.push_to_console("can't target submerged vessels with missiles!", tag="combat")
                self.reset_target_mode()
                return True
            if self.targeting_ability.type == "torpedo":
                self.sim_event_torpedo_launch(self.player, target, self.targeting_ability.range)
            elif self.targeting_ability.type == "missile" and not target.submersible:
                self.sim_event_missile_launch(self.player, target, self.targeting_ability.range) 
            self.reset_target_mode()
            return True
        return False

    def sim_event_missile_launch(self, launcher, target, missile_range): 
        if self.log_sim_events:
            print("sim_event_missile_launch({})".format([launcher.name, target.name]))
        # NOTE: This covers attacks both from and against the player
        self.display_changed = True
        launcher.raise_alert_level(AlertLevel.ENGAGED)
        launched = self.skill_check_launch_missile(launcher)
        if launched <= 0:
            if launcher.player:
                self.game.missiles_used += 1
            # detection:
            for entity in list(filter(lambda x: x.faction != launcher.faction, self.entities)):
                if entity.can_detect_incoming_missiles():
                    detected = self.skill_check_detect_nearby_missile(launcher, target, entity) 
                    if detected <= 0:
                        if entity is target:
                            entity.raise_alert_level(AlertLevel.ENGAGED)
                        else:
                            entity.raise_alert_level(AlertLevel.ALERTED)
                        is_new_contact = launcher not in list(map(lambda x: x.entity, entity.contacts))
                        if is_new_contact:
                            new_contact = [Contact(launcher, 100)]
                            self.sim_event_propagate_new_contacts(entity, new_contact)
            # launch:
            distance = manhattan_distance(launcher.xy_tuple, target.xy_tuple)
            eta = self.time_units_passed + MISSILE_SPEED * distance
            eta_str = self.calendar.get_eta_str(self.time_units_passed, eta, "tactical")
            target.missiles_incoming.append(LaunchedWeapon(eta, launcher, target, missile_range))
            self.push_to_console_if_player("MISSILE LAUNCHED! (eta: {})".format(eta_str), [launcher], \
                tag="combat")
            self.targeting_ability.change_ammo(-1)
        else:
            self.push_to_console_if_player("missile fails to launch!", [launcher], tag="combat")
        # NOTE: a good or bad roll has a significant effect on the time cost of both successful and failed launches
        time_cost = max(MISSILE_LAUNCH_COST_BASE + (launched * 2), 0)
        if launcher.player:
            launcher.next_ability_time = self.time_units_passed + time_cost
        else:
            launcher.next_move_time = self.time_units_passed + time_cost

    def sim_event_torpedo_launch(self, launcher, target, torp_range):
        if self.log_sim_events:
            print("sim_event_torpedo_launch({})".format([launcher.name, target.name]))
        # NOTE: This covers attacks both from and against the player
        self.display_changed = True
        launcher.raise_alert_level(AlertLevel.ENGAGED)
        launched = self.skill_check_launch_torpedo(launcher)
        if launched <= 0:
            if launcher.player:
                self.game.torpedos_used += 1
            is_known = False
            # target detection:
            if target.can_detect_incoming_torpedos():
                target_detects = self.skill_check_detect_nearby_torpedo(launcher, target, target)
                if target_detects <= 0: 
                    target.raise_alert_level(AlertLevel.ENGAGED)
                    is_known = True  
            # nearby observer detection:
            for entity in list(filter(lambda x: x not in [target, launcher], self.entities)):
                if entity.can_detect_incoming_torpedos():
                    detected = self.skill_check_detect_nearby_torpedo(launcher, target, entity) 
                    if detected <= 0:
                        entity.raise_alert_level(AlertLevel.ALERTED)
            distance = manhattan_distance(launcher.xy_tuple, target.xy_tuple)
            eta = self.time_units_passed + TORPEDO_SPEED * distance
            eta_str = self.calendar.get_eta_str(self.time_units_passed, eta, "tactical")
            target.torpedos_incoming.append(LaunchedWeapon(eta, launcher, target, torp_range, known=is_known))
            self.push_to_console_if_player("TORPEDO LAUNCHED! (eta: {})".format(eta_str), [launcher], \
                tag="combat")
            torps = launcher.get_ability("torpedo")
            torps.change_ammo(-1)
        else:
            self.push_to_console_if_player("torpedo fails to launch!", [launcher], tag="combat")
        # NOTE: a good or bad roll has a significant effect on the time cost of both successful and failed launches
        time_cost = max(TORPEDO_LAUNCH_COST_BASE + (launched * 2), 0)
        if launcher.player:
            launcher.next_ability_time = self.time_units_passed + time_cost
        else:
            launcher.next_move_time = self.time_units_passed + time_cost

    def skill_check_evade_incoming_torpedo(self, torp) -> int:
        launcher, target = torp.launcher, torp.target
        contact = first(lambda x: x.entity is target, launcher.contacts)
        if contact is None:
            acc = ORPHANED_TORPEDO_DEFAULT
        else:
            acc = contact.acc
        bonus = [modifiers.pilot_torpedo_alert_mod(target.alert_level)]
        if target.speed_mode == "fast":
            bonus.append(modifiers.fast_mode_torpedo_evasion_bonus)
        penalty = []
        if not torp.known:
            penalty.append(modifiers.unknown_torpedo_evasion_penalty)
        acc_pen = -((100 - acc) // 10)
        contest = roll_skill_contest(launcher, target, "torpedo", "evasive maneuvers", mods_a=bonus, mods_b=penalty)
        result = contest["roll"]
        if contest["entity"] is launcher:
            result *= -1
        self.push_to_console_if_player("[{}] Skill Contest (evade torpedo): {}".format(target.name, result), [target], \
            tag="rolls")
        return result

    def sim_event_missile_arrival(self, missile): 
        if self.log_sim_events:
            print("sim_event_missile_arrival({})".format([missile.launcher.name, missile.target.name]))
        # countermeasures and damage
        launcher, target = missile.launcher, missile.target
        roller, intercepted  = None, False
        point_defenders = list(filter(lambda x: x.faction == target.faction \
            and manhattan_distance(x.xy_tuple, target.xy_tuple) <= POINT_DEFENSE_RANGE \
            and not x.player \
            and x.has_skill("point defense") \
            and x.has_ability("radar") and x.has_skill("radar") \
            and (self.skill_check_detect_nearby_missile(launcher, target, x) <= 0 \
                or x.alert_level == AlertLevel.ENGAGED), self.entities))
        apply(lambda x: x.raise_alert_level(AlertLevel.ENGAGED), point_defenders)
        target_detects = target in point_defenders
        bonus = len(point_defenders)
        if not target_detects:
            penalty = -6
        else:
            penalty = 0
        if target.has_skill("point defense"):
            roller = target
        elif len(point_defenders) > 0:
            roller = choice(point_defenders)
        if roller is not None:
            missile_intercepted = roll_skill_contest(launcher, roller, "missile", "point defense", \
                mods_b=[bonus, penalty])
            if missile_intercepted["entity"] is target and missile_intercepted["roll"] <= 0:
                target.missiles_incoming.remove(missile)
                self.push_to_console_if_player("{}'s missile intercepted!".format(launcher.name), [launcher, target], \
                    tag="combat")
                intercepted = True
        if not intercepted and not target.dead:
            dmg = roll_missile_damage()
            # TODO: (eventually a table of effects for damage rolls that are very high or low)
            target.change_hp(-dmg)
            if target.dead:
                dmg_msg = "{} destroyed by missile!".format(target.name)
                if target.player:
                    self.mission.player_fate = "Destroyed by {}'s missile!".format(launcher.name)
            else:
                dmg_msg = "{} takes {} damage from a missile! ({} / {})".format(target.name, dmg, \
                    target.hp["current"], target.hp["max"])
            self.push_to_console_if_player(dmg_msg, [launcher, target], tag="combat")
        target.raise_alert_level(AlertLevel.ENGAGED)

    def sim_event_torpedo_arrival(self, torp): 
        if self.log_sim_events:
            print("sim_event_torpedo_arrival({})".format([torp.launcher.name, torp.target.name]))
        # evasion, misses/technical failures, and damage
        launcher, target = torp.launcher, torp.target
        evaded = self.skill_check_evade_incoming_torpedo(torp)
        if evaded <= 0:
            if torp.known:
                msg = "{}'s torpedo is evaded by {}!".format(launcher.name, target.name)
            else:
                msg = "{}'s torpedo miss vs. {}!".format(launcher.name, target.name)
            self.push_to_console_if_player(msg, [launcher, target], tag="combat")
            if target.player:
                self.game.torpedos_evaded += 1
        elif not target.dead:
            target.raise_alert_level(AlertLevel.ENGAGED)
            dmg = roll_torpedo_damage()
            # TODO: (eventually a table of effects for damage rolls that are very high or low)
            taken = target.change_hp(-dmg)
            if target.player:
                self.game.total_damage_taken += taken
            if target.dead:
                dmg_msg = "{} destroyed by torpedo!".format(target.name, dmg)
                if target.player:
                    self.mission.player_fate = "Destroyed by {}'s torpedo!".format(launcher.name)
            else:
                dmg_msg = "{} takes {} damage from a torpedo! ({} / {})".format(target.name, dmg, \
                    target.hp["current"], target.hp["max"])
            self.push_to_console_if_player(dmg_msg, [launcher, target], tag="combat")

    def skill_check_visually_detect_contact(self, observer) -> int:
        # NOTE: may eventually take target as a parameter for some things
        result = roll_skill_check(observer, "visual detection", mods=[observer.alert_level.value])
        if result <= 0:
            # NOTE: under normal circumstances, this roll is hidden from the player so they can't count contacts based
            #       on it alone.
            #self.push_to_console_if_player("[{}] Skill Check (visual detection): {}".format(observer.name, \
            #    self.skill_check_to_str(result)), [observer], tag="rolls")
            return result
        return FAIL_DEFAULT

    def skill_check_radio_outgoing(self, sender) -> int:
        result = roll_skill_check(sender, "radio")
        if result <= 0:
            self.push_to_console_if_player("[{}] Skill Check (radio send): {}".format(sender.name, \
                result), [sender], tag="rolls")
            return result
        return FAIL_DEFAULT

    def skill_check_radio_incoming(self, receiver, sent_result) -> int:
        mods = [receiver.alert_level.value, abs(sent_result)]
        result = roll_skill_check(receiver, "radio", mods=mods)
        if result <= 0:
            return result
        return FAIL_DEFAULT

    def skill_check_detect_asonar_contact(self, observer, target) -> int:
        observer_mods = [
            modifiers.sonar_distance_mod(observer, target) // 2,
            observer.alert_level.value,
        ]
        target_mods = [modifiers.stealth_asonar_penalty]
        if target.speed_mode == "fast":
            target_mods.append(modifiers.fast_mode_stealth_penalty)
        contest = roll_skill_contest(observer, target, "active sonar", "stealth", mods_a=observer_mods, \
            mods_b=target_mods)
        result, winner = contest["roll"], contest["entity"]
        # NOTE: under normal circumstances, this roll is hidden from the player so they can't count contacts based
        #       on it alone.
        #self.push_to_console_if_player("[{}] Skill Contest (active sonar detection): {}".format(observer.name, \
        #    result), [observer], tag="rolls")
        if winner is observer and result <= 0:
            return result
        return FAIL_DEFAULT

    def skill_check_detect_psonar_contact(self, observer, target) -> int:
        observer_mods = [
            modifiers.moving_psonar_mod(observer, target),
            observer.alert_level.value,
            modifiers.sonar_distance_mod(observer, target),
        ]
        target_mods = []
        if target.speed_mode == "fast":
            target_mods.append(modifiers.fast_mode_stealth_penalty)
        contest = roll_skill_contest(observer, target, "passive sonar", "stealth", mods_a=observer_mods, \
            mods_b=target_mods)
        result, winner = contest["roll"], contest["entity"]
        # NOTE: under normal circumstances, this roll is hidden from the player so they can't count contacts based
        #       on it alone.
        #self.push_to_console_if_player("[{}] Skill Contest (passive sonar detection): {}".format(observer.name, \
        #    result), [observer], tag="rolls")
        if winner is observer and result <= 0:
            return result
        return FAIL_DEFAULT

    def skill_check_detect_radar_contact(self, observer, target) -> int:
        # NOTE: may eventually take target as a parameter for some things
        result = roll_skill_check(observer, "radar", mods=[observer.alert_level.value])
        if result <= 0:
            # NOTE: under normal circumstances, this roll is hidden from the player so they can't count contacts based
            #       on it alone.
            #self.push_to_console_if_player("[{}] Skill Check (radar detection): {}".format(observer.name, \
            #    self.skill_check_to_str(result)), [observer], tag="rolls")
            return result
        return FAIL_DEFAULT

    def skill_check_launch_torpedo(self, launcher) -> int:
        result = roll_skill_check(launcher, "torpedo")
        self.push_to_console_if_player("[{}] Skill Check (launch torpedo): {}".format(launcher.name, \
            self.skill_check_to_str(result)), [launcher], tag="rolls")
        return result

    def skill_check_launch_missile(self, launcher) -> int:
        result = roll_skill_check(launcher, "missile")
        self.push_to_console_if_player("[{}] Skill Check (launch missile): {}".format(launcher.name, \
            self.skill_check_to_str(result)), [launcher], tag="rolls")
        return result

    def skill_check_detect_nearby_missile(self, launcher, target, observer) -> int:
        def witness(r) -> bool:
            return (manhattan_distance(launcher.xy_tuple, observer.xy_tuple) <= r \
                or manhattan_distance(target.xy_tuple, observer.xy_tuple) <= r)
        detected_visual, detected_radar = False, False
        if observer.has_skill("visual detection") and witness(RANGE_VISUAL_DETECTION):
            # NOTE: May include a more fine-grained circumstance for visually detecting incoming torps at some point,
            #       as they are supposed to be closer to modern ones than WW2-style ones.
            detected_visual = roll_skill_check(observer, "visual detection", mods=[observer.alert_level.value])
            if detected_visual <= 0:
                self.push_to_console_if_player("[{}] Skill Check (visually detect missile): {}".format(observer.name, \
                    self.skill_check_to_str(detected_visual)), [observer], tag="rolls")
        if observer.has_skill("radar") and observer.has_ability("radar") and witness(RADAR_RANGE):
            detected_radar = roll_skill_check(observer, "radar", mods=[observer.alert_level.value])
            if detected_radar <= 0:
                self.push_to_console_if_player("[{}] Skill Check (detect torpedo via radar): {}".format(observer.name, \
                    self.skill_check_to_str(detected_radar)), [observer], tag="rolls")
        if detected_visual or detected_radar: 
            return min([detected_visual, detected_radar])
        return FAIL_DEFAULT

    def skill_check_detect_nearby_torpedo(self, launcher, target, observer) -> int:
        # NOTE: Covers both visual and passive sonar. Uses the most effective of either roll for the target.
        def witness(r) -> bool:
            return (manhattan_distance(launcher.xy_tuple, observer.xy_tuple) <= r \
                or manhattan_distance(target.xy_tuple, observer.xy_tuple) <= r)
        detected_visual, detected_sonar = False, False
        if observer.has_skill("visual detection") and witness(RANGE_VISUAL_DETECTION):
            # NOTE: May include a more fine-grained circumstance for visually detecting incoming torps at some point,
            #       as they are supposed to be closer to modern ones than WW2-style ones.
            detected_visual = roll_skill_check(observer, "visual detection", mods=[observer.alert_level.value])
            if detected_visual <= 0:
                self.push_to_console_if_player("[{}] Skill Check (visually detect torpedo): {}".format(observer.name, \
                    self.skill_check_to_str(detected_visual)), [observer], tag="rolls")
        if observer.has_skill("passive sonar") \
            and observer.has_ability("passive sonar") \
            and witness(PASSIVE_SONAR_RANGE):
            bonus = modifiers.noisy_torpedo_bonus_to_passive_sonar_detection
            detected_sonar = roll_skill_check(observer, "passive sonar", mods=[observer.alert_level.value, bonus])
            if detected_sonar <= 0:
                self.push_to_console_if_player("[{}] Skill Check (detect torpedo via sonar): {}".format(observer.name, \
                    self.skill_check_to_str(detected_sonar)), [observer], tag="rolls")
        if detected_visual or detected_sonar: 
            return min([detected_visual, detected_sonar])
        return FAIL_DEFAULT

    def player_being_hunted(self) -> bool:
        chasing = first(lambda x: x.chasing, self.entities) is not None
        return chasing or self.player_in_enemy_contacts

    def ended_mission(self) -> bool:
        if pygame.key.get_pressed()[K_e] and self.ctrl_pressed():
            can_end_mission = not self.player_being_hunted() \
                and len(self.player.torpedos_incoming + self.player.missiles_incoming) == 0
            if self.mission_over_confirm and can_end_mission:
                self.mission_over = True
            elif can_end_mission:
                self.mission_over_confirm = True
                self.push_to_console("End mission? Press again to confirm.")
            elif not can_end_mission:
                self.push_to_console("Can't end mission while being hunted!")
            return True
        return False

    def entity_ai_attempt_to_follow_course(self, entity):
        if self.log_ai_routines:
            print("entity_ai_attempt_to_follow_course()")
        if self.entity_can_move(entity, entity.direction):
            self.move_entity(entity, entity.direction)
        else:
            self.entity_ai_random_move(entity)

    def entity_ai_active_sonar_use(self, entity, sneaky=False) -> bool:
        if self.log_ai_routines:
            print("entity_ai_active_sonar_use()")
        if entity.player and entity.on_cooldown(self.time_units_passed):
            eta_str = self.calendar.get_eta_string(self.time_units_passed, self.player.next_ability_time, "tactical")
            self.push_to_console("Next Ability Time: {}".format(eta_str)) 
            return False
        used_asonar = False
        asonar_target = None
        if entity.alert_level.value >= 1 and len(entity.get_hostile_contacts()) == 0:
            asonar_target = ASONAR_USE_TARGET_ALERTED
        elif not sneaky and len(entity.get_hostile_contacts()) == 0:
            asonar_target = ASONAR_USE_TARGET_UNALERTED + entity.alert_level.value
        if asonar_target is not None:
            asonar_roll = sum(roll3d6())
            if asonar_roll <= asonar_target:
                self.sim_event_entity_conducts_asonar_detection(entity)
                used_asonar = True
        return used_asonar

    def entity_ai_shoot_at_or_close_with_target(self, entity, standoff=None) -> bool:
        if self.log_ai_routines:
            print("entity_ai_shoot_at_or_close_with_target()")
        trange = TORPEDO_RANGE + entity.torp_range_bonus
        torpedo_target = first(lambda x: manhattan_distance(x.entity.xy_tuple, entity.xy_tuple) <= trange, \
            entity.get_hostile_contacts())
        if torpedo_target is not None and entity.get_ability("torpedo").ammo > 0:
            self.sim_event_torpedo_launch(entity, torpedo_target.entity, trange)
            return True
        elif len(entity.get_hostile_contacts()) > 0: 
            closest = entity.get_closest_contact(hostile_only=True) 
            distance = manhattan_distance(closest.entity.xy_tuple, entity.xy_tuple)
            path = self.shortest_path(entity.xy_tuple, closest.entity.xy_tuple, self.map_distance_to_player)
            if path is not None:
                if standoff is not None and distance < entity.standoff:
                    direction = self.relative_direction(entity.xy_tuple, path[0], opposite=True)
                else:
                    direction = self.relative_direction(entity.xy_tuple, path[0])
                self.move_entity(entity, direction)
            else: 
                self.entity_ai_random_move(entity)
            return True
        elif entity.chasing:
            path = self.shortest_path(entity.xy_tuple, self.player_last_known_xy, \
                                      self.map_distance_to_player_last_known)
            if path is not None:
                direction = self.relative_direction(entity.xy_tuple, path[0])
                self.move_entity(entity, direction)
            else:
                self.entity_ai_random_move(entity)
            if chebyshev_distance(entity.xy_tuple, self.player_last_known_xy) <= 1:
                entity.chasing = False
                none_chasing = len(list(filter(lambda x: x.faction == "enemy" and not x.chasing, self.entities))) == 0
                if none_chasing:
                    self.game.times_lost_hunters += 1
            return True
        return False

    def entity_ai_patrol_helicopter(self, entity):
        if self.log_ai_routines:
            print("entity_ai_patrol_helicopter()")
        engaged = self.entity_ai_shoot_at_or_close_with_target(entity)
        no_target = not entity.chasing and len(entity.get_hostile_contacts()) == 0
        out_of_ammo = entity.get_ability("torpedo").ammo <= 0
        if (no_target or out_of_ammo) and not engaged:
            # return path
            path = self.shortest_path(entity.xy_tuple, entity.mothership.xy_tuple, entity.map_to_mothership)
            if path is not None:
                direction = self.relative_direction(entity.xy_tuple, path[0])
                self.move_entity(entity, direction)
        # landing
        can_land = chebyshev_distance(entity.xy_tuple, entity.mothership.xy_tuple) <= 1
        if can_land and not engaged and no_target:
            self.entities.remove(entity)
            player_contact = first(lambda x: x.entity is entity, self.player.contacts)
            if player_contact is not None:
                self.player.contacts.remove(player_contact)
            entity.mothership.get_ability("launch helicopter").change_ammo(1)
        self.entity_ai_drop_sonobuoy(entity)

    def entity_ai_patrol_plane(self, entity): 
        if self.log_ai_routines:
            print("entity_ai_patrol_plane()")
        if not self.entity_ai_shoot_at_or_close_with_target(entity):
            self.entity_ai_attempt_to_follow_course(entity)
        self.entity_ai_drop_sonobuoy(entity)

    def entity_ai_drop_sonobuoy(self, entity):
        if self.log_ai_routines:
            print("entity_ai_drop_sonobuoy()")
        if entity.get_ability("drop sonobuoy").ammo > 0:
            existing_buoys = list(filter(lambda x: x.name == "sonobuoy", self.entities))
            good_spot = all(map(lambda x: manhattan_distance(x.xy_tuple, entity.xy_tuple) > SONOBUOY_DIFFUSION_RANGE, \
                existing_buoys))
            free_tiles = list(filter(lambda x: not x.occupied, self.tilemap.neighbors_of(entity.xy_tuple)))
            will_drop = sum(roll3d6()) <= DROP_SONOBUOY_TARGET
            if len(free_tiles) > 0 and good_spot and will_drop:
                launch_tile = choice(free_tiles).xy_tuple
                sonobuoy = Sonobuoy(launch_tile, "enemy")
                item = [self.sonobuoy_count, sonobuoy]
                self.sonobuoy_count += 1
                heapq.heappush(self.sonobuoys, item)
                if len(self.sonobuoys) > MAX_SONOBUOYS:
                    buoy = heapq.heappop(self.sonobuoys)[1]
                    if buoy in self.entities:
                        self.entities.remove(buoy)
                self.entities.append(sonobuoy)
                self.tilemap.toggle_occupied(launch_tile)
                entity.get_ability("drop sonobuoy").change_ammo(-1)

    def entity_ai_heavy_convoy_escort(self, entity): 
        if self.log_ai_routines:
            print("entity_ai_heavy_convoy_escort()")
        entity.hit_the_gas_if_in_danger()
        heli = entity.get_ability("launch helicopter")
        free_tiles = list(filter(lambda x: not x.occupied, self.tilemap.neighbors_of(entity.xy_tuple)))
        if heli.ammo > 0 and len(free_tiles) > 0 and len(entity.get_hostile_contacts()) > 0:
            launch_tile = choice(free_tiles).xy_tuple
            self.tilemap.toggle_occupied(launch_tile)
            launched_heli = PatrolHelicopter(launch_tile, "enemy", entity)
            launched_heli.map_to_mothership = self.djikstra_map_distance_to(entity.xy_tuple)
            self.entities.append(launched_heli)
            heli.change_ammo(-1)
        if self.entity_ai_active_sonar_use(entity):
            return
        elif self.entity_ai_shoot_at_or_close_with_target(entity, standoff=True):
            return
        self.entity_ai_attempt_to_follow_course(entity)
        if entity.last_xy != entity.xy_tuple:
            launched_heli = first(lambda x: x.name == "patrol helicopter" and x.mothership is entity, self.entities)
            if launched_heli is not None:
                launched_heli.map_to_mothership = self.djikstra_map_distance_to(entity.xy_tuple)
        entity.last_xy = entity.xy_tuple

    def entity_ai_small_convoy_escort(self, entity): 
        if self.log_ai_routines:
            print("entity_ai_small_convoy_escort()")
        entity.hit_the_gas_if_in_danger()
        if self.entity_ai_active_sonar_use(entity):
            return
        elif self.entity_ai_shoot_at_or_close_with_target(entity):
            return
        self.entity_ai_attempt_to_follow_course(entity)

    def entity_ai_escort_sub(self, entity): 
        if self.log_ai_routines:
            print("entity_ai_escort_sub()")
        entity.hit_the_gas_if_in_danger()
        if self.entity_ai_active_sonar_use(entity, sneaky=True):
            return
        elif self.entity_ai_shoot_at_or_close_with_target(entity):
            return
        self.entity_ai_attempt_to_follow_course(entity)

    def entity_ai_freighter(self, entity):
        if self.log_ai_routines:
            print("entity_ai_freighter")
        entity.hit_the_gas_if_in_danger()
        self.entity_ai_attempt_to_follow_course(entity)

    def torpedo_arrival_check(self):
        potential_targets = list(filter(lambda x: len(x.torpedos_incoming) > 0, self.entities))
        def arriving_now(entity):
            return any(map(lambda x: x.eta <= self.time_units_passed, entity.torpedos_incoming))
        targets = list(filter(arriving_now, potential_targets))
        for entity in targets:
            arrived = []
            for torp in entity.torpedos_incoming:
                if torp.eta <= self.time_units_passed:
                    self.sim_event_torpedo_arrival(torp)
                    arrived.append(torp)
            for torp in arrived:
                entity.torpedos_incoming.remove(torp)
        self.set_processing_event_done("torpedo_arrival_check")

    def missile_arrival_check(self): 
        potential_targets = list(filter(lambda x: len(x.missiles_incoming) > 0, self.entities))
        def arriving_now(entity):
            return any(map(lambda x: x.eta <= self.time_units_passed, entity.missiles_incoming))
        targets = list(filter(arriving_now, potential_targets))
        for entity in targets:
            arrived = []
            for missile in entity.missiles_incoming:
                if missile.eta <= self.time_units_passed:
                    self.sim_event_missile_arrival(missile)
                    arrived.append(missile)
            for missile in arrived:
                if missile in entity.missiles_incoming:
                    entity.missiles_incoming.remove(missile)
        self.set_processing_event_done("missile_arrival_check")

    def sensor_checks(self): 
        for contact in list(filter(lambda x: not x.entity.identified, self.player.contacts)):
            if contact.acc >= CONTACT_ACC_ID_THRESHOLD:
                contact.entity.identified = True
                self.push_to_console("{} identified".format(contact.entity.name))
        # NOTE: player-allied surface vessels not in yet
        if self.time_units_passed % SENSOR_CHECKS_TU_FREQ == 0:
            for entity in self.entities:
                new_contacts = []
                if entity.has_skill("visual detection"):
                    new_contacts.extend(self.sim_event_entity_conducts_visual_detection(entity, new_contacts))
                if entity.has_ability("passive sonar") and entity.has_skill("passive sonar"):
                    new_contacts.extend(self.sim_event_entity_conducts_psonar_detection(entity, new_contacts)) 
                    if len(entity.unknown_torpedos()) > 0:
                        self.sim_event_entity_torpedo_detection(entity) 
                if entity.has_ability("radar") and entity.has_skill("radar"):
                    new_contacts.extend(self.sim_event_entity_conducts_radar_detection(entity, new_contacts))
                    if len(entity.missiles_incoming) > 0 and entity.alert_level != AlertLevel.ENGAGED:
                        self.sim_event_entity_missile_detection(entity) 
                self.sim_event_degrade_old_contacts(entity, new_contacts)
                self.sim_event_propagate_new_contacts(entity, new_contacts) 
        self.set_processing_event_done("sensor_checks")

    # Contact accuracy degrades every turn when not actively being sensed
    def sim_event_degrade_old_contacts(self, entity, new_contacts):
        if self.log_sim_events:
            print("sim_event_degrade_old_contacts({})".format(entity.name))
        def in_sensor_range(entity, contact):
            d = manhattan_distance(entity.xy_tuple, contact.entity.xy_tuple)
            sensable = False
            if entity.has_skill("visual detection") and d <= RANGE_VISUAL_DETECTION and not contact.entity.submersible:
                sensable = True
            if entity.has_skill("passive sonar") and entity.has_ability("passive sonar") and d <= PASSIVE_SONAR_RANGE:
                sensable = True
            if entity.has_skill("radar") and entity.has_ability("radar") \
                and (contact.entity.submersible_emitter() or not contact.entity.submersible):
                sensable = True
            return sensable
        for contact in entity.contacts:
            if contact not in new_contacts:
                torp_contact = first(lambda x: x.launcher is entity, contact.entity.torpedos_incoming)
                if torp_contact is None and not in_sensor_range(entity, contact):
                    # NOTE: When targeted by an owned torpedo, contacts don't degrade
                    acc_pen = roll_for_acc_degradation()
                    contact.change_acc(-acc_pen)
                if contact.acc == 0: 
                    entity.contacts.remove(contact)
                    self.push_to_console_if_player("contact with {} lost".format(contact.entity.detected_str()), \
                        [entity])

    def sim_event_propagate_new_contacts(self, entity, new_contacts): 
        if self.log_sim_events:
            print("sim_event_propagate_new_contacts({})".format(entity.name))
        entity.contacts.extend(new_contacts)
        if entity.submersible:
            return 
        sent = self.skill_check_radio_outgoing(entity)
        if sent <= 0:
            receivers = list(filter(lambda x: x is not entity \
                and x.has_skill("radio") \
                and x.faction == entity.faction, self.entities))
            for target in receivers:
                for contact in new_contacts:
                    received = self.skill_check_radio_incoming(target, sent)
                    if received <= 0:
                        # NOTE: I may include some acc degradation based on margin of success later on
                        known = first(lambda x: x.entity is contact.entity, target.contacts)
                        if known is not None: 
                            known.change_acc(roll_for_acc_upgrade())
                        elif known is None:
                            target.contacts.append(contact)

    def sim_event_entity_missile_detection(self, entity): 
        if self.log_sim_events:
            print("sim_event_entity_missile_detection({})".format(entity.name))
        for missile in entity.missiles_incoming:
            launcher, target = missile.launcher, missile.target
            result = self.skill_check_detect_nearby_missile(launcher, target, target)
            if result <= 0:
                entity.raise_alert_level(AlertLevel.ENGAGED)
                break

    def sim_event_entity_torpedo_detection(self, entity): 
        if self.log_sim_events:
            print("sim_event_entity_torpedo_detection({})".format(entity.name))
        for torp in entity.unknown_torpedos(): 
            launcher, target = torp.launcher, torp.target
            result = self.skill_check_detect_nearby_torpedo(launcher, target, target)
            if result <= 0:
                entity.raise_alert_level(AlertLevel.ENGAGED)
                torp.known = True

    def sim_event_entity_conducts_visual_detection(self, entity, new_contacts_ls) -> list:
        if self.log_sim_events:
            print("sim_event_entity_conducts_visual_detection({})".format(entity.name))
        new = list(new_contacts_ls)
        potentials = list(filter(lambda x: x.faction != entity.faction \
            and manhattan_distance(x.xy_tuple, entity.xy_tuple) <= RANGE_VISUAL_DETECTION \
            and x is not entity \
            and not x.submersible, self.entities))
        for target in potentials:
            detected = self.skill_check_visually_detect_contact(entity)
            if detected <= 0:
                # NOTE: for now, successful visual contacts are always 100% acc.
                acc = 100
                new_contact = Contact(target, acc)
                self.push_to_console_if_player("{} visually detected!".format(target.detected_str(), acc), \
                    [entity])
                exists_in_old_contacts = first(lambda x: x.entity is target, entity.contacts)
                exists_in_new_contacts = first(lambda x: x.entity is target, new)
                if exists_in_old_contacts is not None:
                    exists_in_old_contacts.acc = 100
                elif exists_in_new_contacts is not None:
                    exists_in_new_contacts.acc = 100
                else:
                    new.append(new_contact)
        return new

    def sim_event_entity_conducts_asonar_detection(self, entity):
        if self.log_sim_events:
            print("sim_event_entity_conducts_asonar_detection({})".format(entity.name))
        # NOTE: unlike psonar, this is conducted independently of passive sensor_checks() as an action
        new = []
        potentials = list(filter(lambda x: x.faction != entity.faction \
            and manhattan_distance(x.xy_tuple, entity.xy_tuple) <= ACTIVE_SONAR_RANGE \
            and not x.can_air_move \
            and x is not entity, self.entities))
        for target in potentials:
            detected = self.skill_check_detect_asonar_contact(entity, target) 
            if detected <= 0:
                acc = self.initial_sonar_acc(entity, target, detected, active=True)
                new_contact = Contact(target, acc)
                exists_in_old_contacts = first(lambda x: x.entity is target, entity.contacts)
                exists_in_new_contacts = first(lambda x: x.entity is target, new)
                if exists_in_old_contacts is not None:
                    exists_in_old_contacts.change_acc(roll_for_acc_upgrade())
                elif exists_in_new_contacts is not None:
                    exists_in_new_contacts.change_acc(roll_for_acc_upgrade())
                elif exists_in_new_contacts is None and exists_in_old_contacts is None:
                    self.push_to_console_if_player("{} detected via active sonar ({})".format(target.detected_str(), \
                        target.xy_tuple), [entity])
                    new.append(new_contact)
        self.sim_event_propagate_new_contacts(entity, new)
        entity.next_move_time = self.time_units_passed + ACTIVE_SONAR_TIME_COST
        alerted = list(filter(lambda x: x.has_skill("passive sonar") and x.has_ability("passive sonar"), potentials))
        for observer in alerted:
            if observer.faction != entity.faction \
                and entity is not observer \
                and entity not in list(map(lambda x: x.entity, observer.contacts)):
                self.sim_event_propagate_new_contacts(observer, [Contact(entity, 100)])

    def sim_event_entity_conducts_psonar_detection(self, entity, new_contacts_ls) -> list:
        if self.log_sim_events:
            print("sim_event_entity_conducts_psonar_detection({})".format(entity.name))
        new = list(new_contacts_ls)
        potentials = list(filter(lambda x: x.faction != entity.faction \
            and manhattan_distance(x.xy_tuple, entity.xy_tuple) <= PASSIVE_SONAR_RANGE \
            and not x.can_air_move \
            and x is not entity, self.entities))
        for target in potentials:
            detected = self.skill_check_detect_psonar_contact(entity, target)
            if detected <= 0:
                acc = self.initial_sonar_acc(entity, target, detected)
                new_contact = Contact(target, acc)
                exists_in_old_contacts = first(lambda x: x.entity is target, entity.contacts)
                exists_in_new_contacts = first(lambda x: x.entity is target, new)
                if exists_in_old_contacts is not None: 
                    exists_in_old_contacts.change_acc(roll_for_acc_upgrade())
                elif exists_in_new_contacts is not None: 
                    exists_in_new_contacts.change_acc(roll_for_acc_upgrade())
                elif exists_in_new_contacts is None and exists_in_old_contacts is None:
                    self.push_to_console_if_player("{} detected via passive sonar ({})".format(target.detected_str(), \
                        target.xy_tuple), [entity])
                    new.append(new_contact)
        return new

    def initial_sonar_acc(self, entity, target, result, active=False) -> int:
        d = manhattan_distance(entity.xy_tuple, target.xy_tuple)
        acc = CONTACT_ACC_ID_THRESHOLD
        acc -= d * INITIAL_ACC_LOSS_PER_DISTANCE_UNIT
        if target.submersible:
            acc -= INITIAL_ACC_PENALTY_SUBMERSIBLE
        if active:
            acc += INITIAL_ACC_BONUS_ACTIVE
        acc += abs(result) * INITIAL_ACC_BONUS_ROLL_FACTOR
        acc += entity.alert_level.value * INITIAL_ACC_BONUS_ALERT_FACTOR
        if target.speed_mode == "fast":
            acc += INITIAL_ACC_BONUS_FAST_MODE
        if acc < 0:
            acc = 0
        elif acc > CONTACT_ACC_ID_THRESHOLD:
            acc = CONTACT_ACC_ID_THRESHOLD
        return acc

    def sim_event_entity_conducts_radar_detection(self, entity, new_contacts_ls) -> list:
        if self.log_sim_events:
            print("sim_event_entity_conducts_radar_detection({})".format(entity.name))
        if not self.overlay_radar:
            return []
        new = list(new_contacts_ls)
        potentials = list(filter(lambda x: x.faction != entity.faction \
            and manhattan_distance(x.xy_tuple, entity.xy_tuple) <= RADAR_RANGE \
            and (not x.submersible or x.submersible_emitter()) \
            and x is not entity, self.entities))
        for target in potentials:
            detected = self.skill_check_detect_radar_contact(entity, target)
            if detected <= 0:
                # NOTE: for now, successful radar contacts are always 100% acc.
                acc = 100
                new_contact = Contact(target, acc)
                exists_in_old_contacts = first(lambda x: x.entity is target, entity.contacts)
                exists_in_new_contacts = first(lambda x: x.entity is target, new)
                if exists_in_old_contacts is not None: 
                    exists_in_old_contacts.acc = acc
                elif exists_in_new_contacts is not None: 
                    exists_in_new_contacts.acc = acc
                elif exists_in_new_contacts is None and exists_in_old_contacts is None:
                    self.push_to_console_if_player("{} detected via radar ({})".format(target.detected_str(), \
                        target.xy_tuple), [entity])
                    new.append(new_contact)
        return new

    def alert_check(self):
        if self.time_units_passed % ALERT_CHECK_TU_FREQ == 0:
            for entity in self.entities:
                if len(entity.get_hostile_contacts()) > 0:
                    entity.raise_alert_level(AlertLevel.ALERTED)
                elif entity.alert_level == AlertLevel.ENGAGED:
                    entity.alert_level = AlertLevel.ALERTED
        self.set_processing_event_done("alert_check")

    def run_entity_behavior(self): 
        can_move = list(filter(lambda x: x.next_move_time <= self.time_units_passed, self.entities))
        for entity in can_move:
            if entity.name == "small convoy escort":
                self.entity_ai_small_convoy_escort(entity) 
            elif entity.name == "freighter":
                self.entity_ai_freighter(entity)
            elif entity.name == "escort sub":
                self.entity_ai_escort_sub(entity)
            elif entity.name == "heavy convoy escort":
                self.entity_ai_heavy_convoy_escort(entity) 
            elif entity.name == "patrol helicopter":
                self.entity_ai_patrol_helicopter(entity) 
            elif entity.name == "patrol plane":
                self.entity_ai_patrol_plane(entity)
            elif entity.player:
                self.move_entity(self.player, self.player.orientation)
                self.player_moved = True
        self.time_units_passed += 1
        self.calendar.advance("tactical")
        self.set_processing_event_done("run_entity_behavior")

    def dead_entity_check(self):
        new_entities = list(filter(lambda x: not x.dead, self.entities))
        dead_entities = list(filter(lambda x: x.dead, self.entities))
        if len(new_entities) < len(self.entities):
            self.entities = new_entities
            self.player.contacts = list(filter(lambda x: x.entity in new_entities, self.player.contacts)) 
            self.display_changed = True
            for entity in dead_entities:
                self.tilemap.toggle_occupied(entity.xy_tuple)
                if entity.name == "freighter":
                    if entity.faction == "neutral":
                        self.mission.neutral_freighters_sunk += 1
                        self.game.neutral_freighters_sunk += 1
                    else:
                        self.mission.freighters_sunk += 1
                        self.game.freighters_sunk += 1
                elif entity.name == "small convoy escort":
                    self.mission.escorts_sunk += 1
                    self.game.escorts_sunk += 1
                elif entity.name == "escort sub":
                    self.mission.subs_sunk += 1
                    self.game.subs_sunk += 1
                elif entity.name == "heavy convoy escort":
                    self.mission.heavy_escorts_sunk += 1
                    self.game.heavy_escorts_sunk += 1
        if self.player not in self.entities:
            self.mission_over = True 
            self.display_changed = True
        self.set_processing_event_done("dead_entity_check")
 
    def draw_hud(self):
        if self.displaying_hud:
            self.draw_console("rolls")
            self.draw_console("combat")
            self.draw_console("other")
            self.draw_abilities()
            self.draw_player_stats() 
            self.draw_target_stats() 
        if self.displaying_mini_map and self.mini_map is not None:
            self.draw_big_splash(self.mini_map.surf)
        if self.displaying_briefing_splash:
            self.draw_big_splash(self.briefing_splash)
        elif self.mission_over_splash is not None:
            self.draw_big_splash(self.mission_over_splash)
        elif self.displaying_help_splash:
            self.draw_big_splash(self.help_splash)

    def draw_target_stats(self):
        target = first(lambda x: not x.player and x.xy_tuple == self.camera.xy_tuple, self.entities)
        if target is not None:
            contact = first(lambda x: x.entity is target, self.player.contacts)
            if contact is not None:
                target_stats = [
                    "Target Name: {}".format(target.detected_str()),
                    "Distance: {}".format(manhattan_distance(self.player.xy_tuple, target.xy_tuple)),
                    "HP: {}".format(target.dmg_str()),
                    "Speed: {} ({})".format(target.speed_mode, target.get_adjusted_speed()),
                    "Detection: {}%".format(contact.acc),
                    "Loc: {}".format(contact.entity.xy_tuple),
                ]
                text = self.hud_font.render("  |  ".join(target_stats), True, "white")
                surf = pygame.Surface((text.get_width() + 1, text.get_height() + 1), flags=SRCALPHA)
                surf.fill(HUD_OPAQUE_BLACK)
                pygame.draw.rect(surf, "cyan", (0, 0, surf.get_width(), surf.get_height()), 1)
                surf.blit(text, (1, 1))
                if self.hud_swapped:
                    y = self.screen.get_height() - surf.get_height() - HUD_Y_EGDE_PADDING
                else:
                    y = HUD_Y_EGDE_PADDING
                pos = (self.screen.get_width() / 2 - surf.get_width() / 2, y)
                self.screen.blit(surf, pos)

    def draw_player_stats(self):
        line_height = HUD_FONT_SIZE + 1
        stats_lines = [
            "Day: {}".format(self.calendar.day),
            "Time: {}".format(self.calendar.clock_string(seconds=True)),
            "HP: {}/{}".format(self.player.hp["current"], self.player.hp["max"]),
            "Hunted: {}".format(self.player_being_hunted()),
            "Inc. Torps: {}".format(len(self.player.known_torpedos())), 
            "Loc: {}".format(self.player.xy_tuple),
            "Camera: {}".format(self.camera.xy_tuple),
            "Speed: {} ({})".format(self.player.speed_mode, self.player.get_adjusted_speed()),
            "Momentum: {}".format(self.player.momentum),
            "Traveling: {}".format(DIRECTION_TO_COMPASS[self.player.orientation]),
        ]
        stats_width = int(self.screen.get_width() * .13)
        stats_size = (stats_width, len(stats_lines) * line_height)
        stats_surface = pygame.Surface(stats_size, flags=SRCALPHA)
        stats_surface.fill(HUD_OPAQUE_BLACK)
        pygame.draw.rect(stats_surface, "cyan", (0, 0, stats_size[0], stats_size[1]), 1)
        count_y = 0
        for line in stats_lines:
            text = self.hud_font.render(line, True, "white")
            x = 4
            y = line_height * count_y
            stats_surface.blit(text, (x, y))
            count_y += 1
        if self.hud_swapped:
            y = self.screen.get_height() - stats_surface.get_height() - HUD_Y_EGDE_PADDING
        else:
            y = HUD_Y_EGDE_PADDING
        pos = (self.screen.get_width() - stats_width, y)
        self.screen.blit(stats_surface, pos)

    def draw_abilities(self):
        line_height = HUD_FONT_SIZE + 1
        abilities_size = (int(self.screen.get_width() * .1), len(self.player.abilities) * line_height)
        abilities_surface = pygame.Surface(abilities_size, flags=SRCALPHA)
        abilities_surface.fill(HUD_OPAQUE_BLACK)
        pygame.draw.rect(abilities_surface, "cyan", (0, 0, abilities_size[0], abilities_size[1]), 1)
        count_y = 0
        for ability in self.player.abilities:
            text = self.hud_font.render(ability.draw_str(), True, "white")
            x = 4
            y = line_height * count_y
            abilities_surface.blit(text, (x, y)) 
            count_y += 1
        if self.hud_swapped:
            y = self.screen.get_height() - abilities_surface.get_height() - HUD_Y_EGDE_PADDING
        else:
            y = HUD_Y_EGDE_PADDING
        self.screen.blit(abilities_surface, (0, y)) 

    def draw_level(self, grid_lines=True):
        if self.zoomed_out:
            cell_size = ZOOMED_OUT_CELL_SIZE
            wh_tuple = self.screen_wh_cells_tuple_zoomed_out
        else:
            cell_size = CELL_SIZE
            wh_tuple = self.screen_wh_cells_tuple
        topleft = (self.camera.xy_tuple[0] - wh_tuple[0] // 2, self.camera.xy_tuple[1] - wh_tuple[1] // 2)
        area_rect = (topleft[0] * cell_size, topleft[1] * cell_size, wh_tuple[0] * cell_size, wh_tuple[1] * cell_size)
        # draw tilemap
        changed_tiles = self.tilemap.changed_tiles
        self.master_surface = self.update_master_surface(changed_tiles)
        self.master_surface_zoomed_out = self.update_master_surface(changed_tiles, zoomed_out=True, clear=True)
        if self.zoomed_out:
            self.screen.blit(self.master_surface_zoomed_out, (0, 0), area=area_rect)
        else:
            self.screen.blit(self.master_surface, (0, 0), area=area_rect)

        # player overlays  
        torpedo_overlay_to_draw = False
        missile_overlay_to_draw = False
        psonar_overlay_to_draw = False
        radar_overlay_to_draw = False
        if self.targeting_ability is not None:
            if self.targeting_ability.type == "torpedo": 
                torpedo_overlay_pos = ((self.player.xy_tuple[0] - topleft[0] - TORPEDO_RANGE) * cell_size, \
                    (self.player.xy_tuple[1] - topleft[1] - TORPEDO_RANGE) * cell_size)
                torpedo_overlay_to_draw = True
            if self.targeting_ability.type == "missile":
                missile_overlay_pos = ((self.player.xy_tuple[0] - topleft[0] - MISSILE_RANGE) * cell_size, \
                    (self.player.xy_tuple[1] - topleft[1] - MISSILE_RANGE) * cell_size)
                missile_overlay_to_draw = True
        if self.overlay_sonar: 
            psonar_overlay_pos = ((self.player.xy_tuple[0] - topleft[0] - PASSIVE_SONAR_RANGE) * cell_size, \
                (self.player.xy_tuple[1] - topleft[1] - PASSIVE_SONAR_RANGE) * cell_size)
            psonar_overlay_to_draw = True
        if self.overlay_radar:
            radar_overlay_pos = ((self.player.xy_tuple[0] - topleft[0] - RADAR_RANGE) * cell_size, \
                (self.player.xy_tuple[1] - topleft[1] - RADAR_RANGE) * cell_size)
            radar_overlay_to_draw = True
        if torpedo_overlay_to_draw and self.zoomed_out:
            self.screen.blit(self.player_torpedo_range_overlay_surface_zoomed_out, torpedo_overlay_pos)
        elif torpedo_overlay_to_draw:
            self.screen.blit(self.player_torpedo_range_overlay_surface, torpedo_overlay_pos)
        if missile_overlay_to_draw and self.zoomed_out:
            self.screen.blit(self.player_missile_range_overlay_surface_zoomed_out, missile_overlay_pos)
        elif missile_overlay_to_draw:
            self.screen.blit(self.player_missile_range_overlay_surface, missile_overlay_pos)
        if psonar_overlay_to_draw and self.zoomed_out:
            self.screen.blit(self.player_sonar_overlay_surface_zoomed_out, psonar_overlay_pos)
        elif psonar_overlay_to_draw:
            self.screen.blit(self.player_sonar_overlay_surface, psonar_overlay_pos)
        if radar_overlay_to_draw and self.zoomed_out:
            self.screen.blit(self.player_radar_overlay_surface_zoomed_out, radar_overlay_pos)
        elif radar_overlay_to_draw: 
            self.screen.blit(self.player_radar_overlay_surface, radar_overlay_pos)

        # draw enemy sonar overlay layer
        if self.debug:
            player_contacts_entities = self.entities
        else:
            player_contacts_entities = list(map(lambda x: x.entity, self.player.contacts))
        visible_entities = list(filter(lambda x: x in player_contacts_entities, self.entities)) + [self.player]
        for entity in visible_entities:
            contact = first(lambda x: x.entity is entity, self.player.contacts)
            if contact is not None and entity.identified and not entity.player and entity.has_ability("passive sonar"):
                enemy_psonar_overlay_pos = ((entity.xy_tuple[0] - topleft[0] - PASSIVE_SONAR_RANGE) * cell_size, \
                    (entity.xy_tuple[1] - topleft[1] - PASSIVE_SONAR_RANGE) * cell_size)
                if self.zoomed_out:
                    self.screen.blit(self.enemy_sonar_overlay_zoomed_out, enemy_psonar_overlay_pos)
                else:
                    self.screen.blit(self.enemy_sonar_overlay, enemy_psonar_overlay_pos)

        # draw entities:
        for entity in visible_entities:
            mover = first(lambda x: x.entity is entity, self.moving_entities)
            contact = first(lambda x: x.entity is entity, self.player.contacts)
            if mover is None:
                x, y = entity.xy_tuple
            else:
                x, y = mover.last
            if x >= 0 and y >= 0 and x < self.tilemap.wh_tuple[0] and y < self.tilemap.wh_tuple[1]:
                if mover is None:
                    rect = ((x - topleft[0]) * cell_size, (y - topleft[1]) * cell_size, cell_size, cell_size)
                else:
                    origin = Vector2((x - topleft[0]) * cell_size, (y - topleft[1]) * cell_size)
                    tx, ty = mover.current
                    target = Vector2((tx - topleft[0]) * cell_size, (ty - topleft[1]) * cell_size)
                    if self.zoomed_out:
                        actual = origin.move_towards(target, mover.progress * mover.speed)
                        mover.progress += 1
                    else:
                        actual = origin.move_towards(target, mover.progress * mover.speed)
                        mover.progress += 2
                    rect = (actual[0], actual[1], CELL_SIZE, CELL_SIZE)
                    if target == actual:
                        self.moving_entities.remove(mover)
                if entity.player or entity.identified or self.debug:
                    if self.zoomed_out:
                        img = entity.image_zoomed_out
                    else:
                        img = entity.image
                else:
                    if self.zoomed_out:
                        img = entity.image_unidentified_zoomed_out
                    else:
                        img = entity.image_unidentified
                self.screen.blit(img, rect)
                # a "tail" showing direction came from:
                target = (rect[0] + cell_size // 2, rect[1] + cell_size // 2)
                tail_point = self.get_tail_point(entity, target) 
                pygame.draw.line(self.screen, "white", target, tail_point, 2) 
                # marker if currently targeted by a player weapon: 
                torps = list(map(lambda x: x.launcher.player, entity.torpedos_incoming))
                missiles = list(map(lambda x: x.launcher.player, entity.missiles_incoming))
                if any(torps + missiles):
                    pygame.draw.circle(self.screen, COLOR_MISSION_HIGHLIGHT, target, int(cell_size * .66), 4)
                # reticule if camera on AI unit:
                if entity.xy_tuple == self.camera.xy_tuple and not entity.player:
                    target = (rect[0] + cell_size // 2, rect[1] + cell_size // 2)
                    pygame.draw.circle(self.screen, "cyan", target, int(cell_size * .66), 2)
                # acc rating
                if not entity.identified and self.overlay_sonar and contact is not None and not entity.player:
                    if contact.acc < 50:
                        color = "red"
                    elif contact.acc < 80:
                        color = "yellow"
                    else:
                        color = "green"
                    acc_txt = self.hud_font_bold.render("{}".format(contact.acc), True, color, "black")
                    pos = (rect[0] + cell_size // 2 - acc_txt.get_width() // 2,
                           rect[1] + cell_size // 2 - acc_txt.get_height() // 2)
                    self.screen.blit(acc_txt, pos)

    def incoming_torp_alert(self):
        incoming = 0
        etas = []
        for torp in self.player.known_torpedos():
            if not torp.gui_alert:
                incoming += 1
                torp.gui_alert = True
                etas.append(torp.eta)
        if incoming > 0:
            self.push_to_console("{} NEW INCOMING TORPEDOS(s)!".format(incoming), tag="combat")
        for eta in etas:
            eta_str = self.calendar.get_eta_str(self.time_units_passed, eta, "tactical")
            self.push_to_console("Incoming eta: {}".format(eta_str), tag="combat")
        self.set_processing_event_done("incoming_torp_alert")

    def chase_check(self): 
        def chasers_by_distance(units) -> list:
            chasers = []
            for entity in units:
                if entity.chaser:
                    d = manhattan_distance(entity.xy_tuple, self.player_last_known_xy)
                    item = [d, entity.id, entity]
                    heapq.heappush(chasers, item)
            return chasers 
        def currently_chasing(chasers) -> bool:
            for item in chasers:
                entity = item[2]
                if entity.chasing:
                    return True
            return False
        def closest_chaser(chasers) -> Entity:
            for chaser in chasers:
                if chaser[2].name == "patrol helicopter":
                    return chaser[2] 
            return chasers[0][2]
        if self.time_units_passed % CHASE_CHECK_TU_FREQ == 0:
            player_recently_seen = self.player_in_enemy_contacts
            self.player_in_enemy_contacts = False
            enemy_units = list(filter(lambda x: x.faction == "enemy", self.entities))
            enemy_unit_contacts = list(map(lambda x: x.contacts, enemy_units))
            for contact_list in enemy_unit_contacts:
                if self.player in list(map(lambda x: x.entity, contact_list)):
                    self.player_in_enemy_contacts = True
                    self.map_distance_to_player_last_known = self.djikstra_map_distance_to(self.player.xy_tuple)
                    self.player_last_known_xy = self.player.xy_tuple
                    chaser = first(lambda x: x.chasing, self.entities)
                    if chaser is not None:
                        chaser.chasing = False
                    break
            if player_recently_seen and not self.player_in_enemy_contacts:
                # start chase
                if isinstance(self.mission, AswPatrol):
                    new_direction = choice(list(filter(lambda x: x != "wait", DIRECTIONS.keys())))
                    for unit in enemy_units:
                        unit.chasing = True
                        unit.direction = new_direction
                else:
                    chasers = chasers_by_distance(enemy_units)
                    if len(chasers) > 0 and not currently_chasing(chasers):
                        new_chaser = closest_chaser(chasers)
                        new_chaser.chasing = True
        self.set_processing_event_done("chase_check")

