import pygame
from constants import *
from rolls import *
from tile_map import TileMap
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

class SimStateSnapshot:
    pass # TODO

class Game:
    def __init__(self):
        # TODO: a seeding system
        self.running = True
        self.display_changed = True
        self.screen = pygame.display.get_surface() 
        self.screen_wh_cells_tuple = (self.screen.get_width() // CELL_SIZE, self.screen.get_height() // CELL_SIZE)
        self.screen.set_colorkey(ALPHA_KEY)
        self.clock = pygame.time.Clock()
        self.tilemap = None
        self.camera = (0, 0) 
        self.entities = []
        self.sonobuoy_count = 0
        self.sonobuoys = []
        self.console = Console()
        self.displaying_hud = True 
        self.console_scrolled_up_by = 0 
        self.hud_font = pygame.font.Font(FONT_PATH, HUD_FONT_SIZE)
        self.overlay_sonar = False
        self.overlay_radar = False
        self.targeting_ability = None 
        self.targeting_index = {"current": 0, "max": 0}
        self.observation_index = 0
        self.sim_snapshots = [] 
        self.time_units_passed = 0
        self.player_turn = 0
        self.player_turn_ended = False
        self.processing = False
        self.debug = False
        self.log_sim_events = False
        self.log_ai_routines = False
        self.pathfinding_perf = False
        self.player_long_wait = False
        self.mini_map = None 
        self.displaying_mini_map = False 
        self.player = None
        self.offmap_asw_eta = None 
        self.mission = ConvoyAttack() 
        self.generate_encounter_convoy_attack(self.mission)
        if self.debug:
            self.player.hp = {"current": 2000, "max": 2000}  
        self.update_mini_map()
        self.map_distance_to_player = self.djikstra_map_distance_to(self.player.xy_tuple)
        self.player_last_known_xy = None
        self.map_distance_to_player_last_known = None
        self.player_in_enemy_contacts = False
        self.map_enemy_sonar_overlay = self.djikstra_map_enemy_sonar()
        self.displaying_briefing_splash = True
        self.displaying_big_splash = False
        self.hud_swapped = False
        self.briefing_splash = self.generate_big_splash_txt_surf(self.mission.briefing_lines) 
        self.mission_over = False
        self.mission_over_confirm = False
        self.mission_over_splash = None
        self.campaign_mode = False
        self.exit_game_confirm = False

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
            chasers = chasers_by_distance(enemy_units)
            if len(chasers) > 0 and not currently_chasing(chasers):
                new_chaser = closest_chaser(chasers)
                new_chaser.chasing = True

    def incoming_torp_alert(self):
        incoming = 0
        for torp in self.player.known_torpedos():
            if not torp.gui_alert:
                incoming += 1
                torp.gui_alert = True
        if incoming > 0:
            self.push_to_console("{} NEW INCOMING TORPEDOS(s)!".format(incoming), tag="combat")

    def djikstra_map_enemy_sonar(self) -> list:
        def valid_tiles_in_range_of(xy_tuple, d) -> list:
            locs = []
            for x in range(xy_tuple[0] - d, xy_tuple[0] + d + 1):
                for y in range(xy_tuple[1] - d, xy_tuple[1] + d + 1):
                    valid = self.tilemap.tile_in_bounds((x, y)) and manhattan_distance((x, y), xy_tuple) <= d
                    if valid:
                        locs.append((x, y))
            return locs 
        djikstra_map = [[0 for y in range(self.tilemap.wh_tuple[1])] for x in range(self.tilemap.wh_tuple[0])]
        player_contact_entities = list(map(lambda x: x.entity, self.player.contacts))
        # NOTE: For now, all enemy units have the same sonar range. 
        enemy_psonar_origins = list(map(lambda x: x.xy_tuple, \
            list(filter(lambda x: x.faction == "enemy" \
            and x in player_contact_entities \
            and x.identified \
            and x.has_ability("passive sonar") \
            and x.has_skill("passive sonar"), self.entities))))
        for origin in enemy_psonar_origins:
            hits = valid_tiles_in_range_of(origin, PASSIVE_SONAR_RANGE)
            for xy_tuple in hits:
                djikstra_map[xy_tuple[0]][xy_tuple[1]] += 1
        return djikstra_map 

    def djikstra_map_distance_to(self, xy_tuple) -> list: 
        valid_tile_types = ["ocean"] # TODO: land units and land tiles
        def fitness_function(tile):
            score = manhattan_distance(tile.xy_tuple, xy_tuple)
            terrain_is_valid = tile.tile_type in valid_tile_types
            if not terrain_is_valid: 
                score = INVALID_DJIKSTRA_SCORE
            return score
        djikstra_map = [list(map(lambda tile: fitness_function(tile), col)) for col in self.tilemap.tiles] 
        return djikstra_map

    def update_mini_map(self):  
        surf = pygame.Surface((self.tilemap.wh_tuple[0] * MM_CELL_SIZE, self.tilemap.wh_tuple[1] * MM_CELL_SIZE))
        # draw tilemap
        for x in range(self.tilemap.wh_tuple[0]):
            for y in range(self.tilemap.wh_tuple[1]):
                rect = (x * MM_CELL_SIZE, y * MM_CELL_SIZE, MM_CELL_SIZE, MM_CELL_SIZE)
                tile = self.tilemap.get_tile((x, y))
                if tile.tile_type == "ocean":
                    pygame.draw.rect(surf, "navy", rect)
                elif tile.tile_type == "land":
                    pygame.draw.rect(surf, "olive", rect)
        # draw entities:
        for entity in self.entities:
            in_player_contacts = entity in list(map(lambda x: x.entity, self.player.contacts))
            if in_player_contacts or entity.player or self.debug:
                rect = (entity.xy_tuple[0] * MM_CELL_SIZE, entity.xy_tuple[1] * MM_CELL_SIZE, MM_CELL_SIZE, \
                    MM_CELL_SIZE) 
                contact = first(lambda x: x.entity is entity, self.player.contacts)
                if entity.player \
                    or entity.identified \
                    or self.debug \
                    or (contact is not None and contact.acc >= CONTACT_ACC_ID_THRESHOLD): 
                    color = faction_to_color[entity.faction]
                else:
                    color = "dark gray"
                pygame.draw.rect(surf, color, rect)
        pygame.draw.rect(surf, "cyan", (0, 0, surf.get_width(), surf.get_height()), 2)
        self.mini_map = pygame.transform.scale(surf, MINI_MAP_SIZE)

    def player_long_wait_check(self):
        if self.player_long_wait: 
            contacts = len(self.player.contacts) > 0
            engaged = self.player.alert_level == AlertLevel.ENGAGED
            eta = self.player.next_move_time <= self.time_units_passed
            if eta or contacts or engaged:
                self.player_long_wait = False
                self.player.next_move_time = self.time_units_passed 

    # Gets the shortest available route 
    def shortest_entity_path(self, start_loc, end_loc, djikstra_map) -> list:  
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
            next_to_target = chebyshev_distance(start_loc, end_loc) == 1
            distance = manhattan_distance(start_loc, end_loc)
            end_entity = first(lambda x: x.xy_tuple == end_loc, self.entities)
            print("__profiling shortest_entity_path()") 
            print("\ttiles_searched: {}".format(tiles_searched)) 
            print("\ttot: {}ns".format(tot)) 
            if found:
                print("\tsearch: {}ns".format(traceback_start - start))
                print("\ttraceback: {}ns".format(traceback_tot)) 
            print("\tdistance: {}".format(distance)) 
            print("\tfound: {}".format(found))
            print("\tstart_entity: {}".format(start_entity.name))
            print("\tstart_entity_id: {}".format(start_entity.id))
            print("\tstart_entity surrounded: {}".format(start_entity_surrounded))
            print("\tend_entity: {}".format(end_entity.name))
            print("\tplayer surrounded: {}".format(player_surrounded))
            print("\tnext_to_target: {}".format(next_to_target))
            if msg is not None:
                print("\tmsg: {}".format(msg))
        
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

        def get_traceback(visited, goal) -> list:  
            nonlocal traceback_start, traceback_end
            traceback_start = time.process_time_ns() 
            current = goal
            traceback = [goal[2]["loc"]]
            while current[2]["loc"] is not start_loc: 
                for node in visited:                     
                    if node[2]["loc"] is current[2]["via"]:
                        if node[2]["loc"] is not start_loc:
                            traceback.append(node[2]["loc"])
                        current = node
                        break
            traceback.reverse()
            if self.pathfinding_perf:
                traceback_end = time.process_time_ns()
                print_end_time(start, tiles_searched, True) 
            return traceback 

        seen = []
        visited = []
        seen_bools = [[False for y in range(self.tilemap.wh_tuple[1])] for x in range(self.tilemap.wh_tuple[0])] 
        seen_count = 1
        start_score = djikstra_map[start_loc[0]][start_loc[1]]
        seen_bools[start_loc[0]][start_loc[1]] = True
        start_node = [start_score, 0, {"loc": start_loc, "via": None}]
        heapq.heappush(seen, start_node)
        visited.append(start_node)
        while len(seen) > 0:  
            node = heapq.heappop(seen)    
            neighbors = self.tilemap.neighbors_of(node[2]["loc"]) 
            tile = first(lambda x: seen_bools[x.xy_tuple[0]][x.xy_tuple[1]] == False, neighbors)
            if tile is not None:
                seen_count += 1
                heapq.heappush(seen, node)
                tiles_searched += 1
                score = djikstra_map[tile.xy_tuple[0]][tile.xy_tuple[1]]
                if tile.occupied:
                    score = INVALID_DJIKSTRA_SCORE 
                new_node = {"loc": tile.xy_tuple, "via": node[2]["loc"]}
                full_node = [score, seen_count, new_node]
                heapq.heappush(seen, full_node)
                visited.append(full_node)
                seen_bools[tile.xy_tuple[0]][tile.xy_tuple[1]] = True
                if tile.xy_tuple == end_loc:
                    return get_traceback(visited, full_node)

        if self.pathfinding_perf:
            dbg_found = end_loc in list(map(lambda x: x[2]["loc"], visited))
            if dbg_found:
                print_end_time(start, tiles_searched, False, msg="FALSE NEGATIVE")
            print_end_time(start, tiles_searched, False)
        return None 

    def snapshot_sim(self): # TODO: implement sim state snapshotting
        pass

    def input_blocked(self):
        # NOTE: later will also block for some pop-up animations and stuff!
        return self.processing

    def generate_encounter_convoy_attack(self, mission):
        scale = mission.scale
        freighters = mission.freighters
        escorts = mission.escorts
        subs = mission.subs
        heavy_escort = mission.heavy_escort
        offmap_asw = mission.offmap_asw
        neutral_freighters = mission.neutral_freighters
        self.tilemap = TileMap(MAP_SIZE, "open ocean")
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
        def spawn_player(spawn_ls):
            player_offset_fuzz = randint(-3, 6)
            player_offset = 24 + player_offset_fuzz
            player = PlayerSub(origin) 
            if "up" in traveling:
                player.xy_tuple = (player.xy_tuple[0], player.xy_tuple[1] - player_offset)
            if "down" in traveling:
                player.xy_tuple = (player.xy_tuple[0], player.xy_tuple[1] + player_offset)
            if "left" in traveling:
                player.xy_tuple = (player.xy_tuple[0] - player_offset, player.xy_tuple[1])
            if "right" in traveling:
                player.xy_tuple = (player.xy_tuple[0] + player_offset, player.xy_tuple[1])
            self.player = player
            self.camera = player.xy_tuple
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
        spawn_player(units) 
        for _ in range(num_neutral_freighters):
            direction = choice(list(filter(lambda x: x != "wait", DIRECTIONS.keys())))
            random_spawn(units, Freighter(origin, "neutral", direction=direction))
        self.entities = units

    def draw_level(self, grid_lines=True):
        topleft = (self.camera[0] - self.screen_wh_cells_tuple[0] // 2, \
            self.camera[1] - self.screen_wh_cells_tuple[1] // 2)
        relative_positions = {}

        # draw tilemap
        count_x, count_y = 0, 0 
        for x in range(topleft[0], topleft[0] + self.screen_wh_cells_tuple[0]):
            for y in range(topleft[1], topleft[1] + self.screen_wh_cells_tuple[1]):
                rect = (count_x * CELL_SIZE, count_y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                relative_positions[str((x, y))] = rect
                if x >= 0 and y >= 0 and x < self.tilemap.wh_tuple[0] and y < self.tilemap.wh_tuple[1]:
                    tile = self.tilemap.get_tile((x, y))
                    if tile.tile_type == "ocean":
                        pygame.draw.rect(self.screen, "navy", rect)
                        sonar_layers = self.map_enemy_sonar_overlay[x][y]
                        if sonar_layers > 0:
                            alpha = ENEMY_SONAR_OVERLAY_ALPHA_BASE + ENEMY_SONAR_OVERLAY_ALPHA_INC * sonar_layers
                            surf = pygame.Surface((CELL_SIZE, CELL_SIZE), flags=SRCALPHA)
                            surf.fill(ENEMY_SONAR_OVERLAY_COLOR + [alpha])
                            self.screen.blit(surf, (rect[0], rect[1]))
                    elif tile.tile_type == "land":
                        pygame.draw.rect(self.screen, "olive", rect)
                else:
                    pygame.draw.rect(self.screen, "black", rect)
                if grid_lines:
                    pygame.draw.rect(self.screen, "gray", rect, 1)
                count_y += 1
            count_x += 1
            count_y = 0

        def draw_overlay(origin, radius, color): 
            tiles_in_range = list(filter(lambda x: manhattan_distance(x.xy_tuple, origin) <= radius \
                and x.xy_tuple != origin and str(x.xy_tuple) in relative_positions.keys(), \
                self.tilemap.all_tiles()))
            # filter out land tiles and inaccessible tiles if torpedo attack (TODO)
            if self.targeting_ability is not None:
                if "torpedo" in self.targeting_ability.type:
                    tiles_in_range = list(filter(lambda x: x.tile_type == "ocean", tiles_in_range))
            # lay down overlay:
            affected_cells = list(map(lambda x: relative_positions[str(x.xy_tuple)], tiles_in_range))
            for cell in affected_cells:
                if (cell[0], cell[1]) != self.player.xy_tuple:      
                    surf = pygame.Surface((cell[2], cell[3]), flags=SRCALPHA)
                    surf.fill(color)
                    self.screen.blit(surf, (cell[0], cell[1]))

        # player overlays 
        if self.targeting_ability is not None:
            draw_overlay(self.player.xy_tuple, self.targeting_ability.range, HUD_OPAQUE_RED)
        else:
            # NOTE: These sensor overlays may overlap
            if self.overlay_sonar: 
                psonar_range = first(lambda x: x.type == "passive sonar", self.player.abilities).range
                draw_overlay(self.player.xy_tuple, psonar_range, SONAR_OVERLAY_COLOR)
            if self.overlay_radar:
                radar_range = first(lambda x: x.type == "radar", self.player.abilities).range
                draw_overlay(self.player.xy_tuple, radar_range, RADAR_OVERLAY_COLOR)

        # draw entities:
        for entity in self.entities:
            on_screen = str(entity.xy_tuple) in relative_positions.keys()
            in_player_contacts = entity in list(map(lambda x: x.entity, self.player.contacts))
            if on_screen and (in_player_contacts or entity.player or self.debug):
                rect = relative_positions[str(entity.xy_tuple)]
                # contact identification:
                contact = first(lambda x: x.entity is entity, self.player.contacts)
                if entity.player \
                    or entity.identified \
                    or self.debug \
                    or (contact is not None and contact.acc >= CONTACT_ACC_ID_THRESHOLD): 
                    img = entity.image
                    if not entity.identified:
                        entity.identified = True
                        if not entity.player:
                            self.push_to_console("{} identified".format(entity.name))
                elif entity.submersible:
                    img = unit_tile_triangle("dark gray", upsidedown=True)
                else:
                    img = unit_tile_circle("dark gray")
                self.screen.blit(img, rect)
                if not entity.identified and self.overlay_sonar:
                    acc_txt = self.hud_font.render("{}".format(contact.acc), "black", True, "white")
                    pos = (rect[0] + CELL_SIZE // 2 - acc_txt.get_width() // 2,
                           rect[1] + CELL_SIZE // 2 - acc_txt.get_height() // 2)
                    self.screen.blit(acc_txt, pos)
                # a "tail" showing direction came from:
                target = (rect[0] + CELL_SIZE // 2, rect[1] + CELL_SIZE // 2)
                tail_point = self.get_tail_point(entity, target) 
                pygame.draw.line(self.screen, "white", target, tail_point, 2) 
                # marker if currently targeted by a player weapon: 
                torps = list(map(lambda x: x.launcher.player, entity.torpedos_incoming))
                missiles = list(map(lambda x: x.launcher.player, entity.missiles_incoming))
                if any(torps + missiles):
                    pygame.draw.circle(self.screen, "yellow", target, int(CELL_SIZE * .66), 4)
                # reticule if camera on AI unit:
                if entity.xy_tuple == self.camera and not entity.player:
                    target_cell = relative_positions[str(self.camera)]
                    target = (target_cell[0] + CELL_SIZE // 2, target_cell[1] + CELL_SIZE // 2)
                    pygame.draw.circle(self.screen, "cyan", target, int(CELL_SIZE * .66), 2)

    def get_tail_point(self, entity, center) -> tuple:
        if entity.last_direction == "wait":
            x, y = center
        elif entity.last_direction == "up":
            x, y = center[0], center[1] + CELL_SIZE // 2
        elif entity.last_direction == "down":
            x, y = center[0], center[1] - CELL_SIZE // 2
        elif entity.last_direction == "left":
            x, y = center[0] + CELL_SIZE // 2, center[1]
        elif entity.last_direction == "right":
            x, y = center[0] - CELL_SIZE // 2, center[1]
        elif entity.last_direction == "upright":
            x, y = center[0] - CELL_SIZE // 2, center[1] + CELL_SIZE // 2
        elif entity.last_direction == "upleft":
            x, y = center[0] + CELL_SIZE // 2, center[1] + CELL_SIZE // 2
        elif entity.last_direction == "downright":
            x, y = center[0] - CELL_SIZE // 2, center[1] - CELL_SIZE // 2
        elif entity.last_direction == "downleft":
            x, y = center[0] + CELL_SIZE // 2, center[1] - CELL_SIZE // 2
        return (x, y)

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

    def draw_player_stats(self):
        line_height = HUD_FONT_SIZE + 1
        stats_lines = [
            "Turn: {}".format(self.player_turn),
            "Time: {}".format(self.time_units_passed),
            "HP: {}/{}".format(self.player.hp["current"], self.player.hp["max"]),
            "Hunted: {}".format(self.player_being_hunted()),
            "Inc. Torps: {}".format(len(self.player.known_torpedos())), 
            "Loc: {}".format(self.player.xy_tuple),
            "Camera: {}".format(self.camera),
            "Speed: {} ({})".format(self.player.speed_mode, self.player.get_adjusted_speed()),
            "Momentum: {}".format(self.player.momentum),
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

    def draw_target_stats(self):
        target = first(lambda x: not x.player and x.xy_tuple == self.camera, self.entities)
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

    def draw_hud(self):
        if self.displaying_hud:
            self.draw_console("rolls")
            self.draw_console("combat")
            self.draw_console("other")
            self.draw_abilities()
            self.draw_player_stats() 
            self.draw_target_stats() 
        if self.displaying_mini_map and self.mini_map is not None:
            self.draw_big_splash(self.mini_map)
        if self.displaying_briefing_splash:
            self.draw_big_splash(self.briefing_splash)
        elif self.mission_over_splash is not None:
            self.draw_big_splash(self.mission_over_splash)

    def draw_big_splash(self, surf):
        x = self.screen.get_width() // 2 - surf.get_width() // 2
        y = 26  
        self.screen.blit(surf, (x, y)) 
        self.display_changed = True
        self.displaying_big_splash = True

    def draw(self):
        self.screen.fill("black")
        self.draw_level()
        self.draw_hud()
        self.display_changed = False
        pygame.display.flip()

    def handle_events(self):
        for event in pygame.event.get():
            # quit game:
            if event.type == QUIT:
                self.running = False
            # Keyboard Buttons
            elif event.type == KEYDOWN and not self.input_blocked(): 
                self.display_changed = self.keyboard_event_changed_display()
        pygame.event.pump() 

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
                    else:
                        self.mission.freighters_sunk += 1
                elif entity.name == "small convoy escort":
                    self.mission.escorts_sunk += 1
                elif entity.name == "escort sub":
                    self.mission.subs_sunk += 1
                elif entity.name == "heavy convoy escort":
                    self.mission.heavy_escorts_sunk += 1
        if self.player not in self.entities:
            self.mission_over = True 
            self.display_changed = True
            self.mission_over_check() 
    
    def run_entity_behavior(self): 
        while True: 
            can_move = list(filter(lambda x: x.next_move_time <= self.time_units_passed, self.entities))
            player_turn = any(map(lambda x: x.player, can_move))
            if player_turn:
                break
            if not player_turn and len(can_move) > 0:
                shuffle(can_move)
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
            self.time_units_passed += 1 

    # Moves an entity in a completely random direction
    def entity_ai_random_move(self, entity):
        if self.log_ai_routines:
            print("entity_ai_random_move()")
        direction = choice(list(DIRECTIONS.keys())) 
        self.move_entity(entity, direction)

    def relative_direction(self, from_xy, to_xy, opposite=False): # TODO: put direction-related stuff in own file
        diff = (to_xy[0] - from_xy[0], to_xy[1] - from_xy[1])
        if opposite:
            diff = tuple(map(lambda x: x * -1, diff))
        for k, v in DIRECTIONS.items():
            if v == diff:
                return k
        return "wait"

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
            path = self.shortest_entity_path(entity.xy_tuple, closest.entity.xy_tuple, self.map_distance_to_player) 
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
            path = self.shortest_entity_path(entity.xy_tuple, self.player_last_known_xy, \
                self.map_distance_to_player_last_known) 
            if path is not None:
                direction = self.relative_direction(entity.xy_tuple, path[0])
                self.move_entity(entity, direction)
            else:
                self.entity_ai_random_move(entity)
            if chebyshev_distance(entity.xy_tuple, self.player_last_known_xy) <= 1:
                entity.chasing = False
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
            path = self.shortest_entity_path(entity.xy_tuple, entity.mothership.xy_tuple, entity.map_to_mothership) 
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

    def sensor_checks(self): 
        # NOTE: player-allied surface vessels not in yet
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
            # NOTE: submersible entities will propagate contacts only when exposed to do so via an antenna, at
            #       some point.
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
        for entity in self.entities:
            if len(entity.get_hostile_contacts()) > 0:
                entity.raise_alert_level(AlertLevel.ALERTED)
            elif entity.alert_level == AlertLevel.ENGAGED:
                entity.alert_level = AlertLevel.ALERTED

    def keyboard_event_changed_display(self) -> bool:
        if self.mission_over_splash is None and not self.campaign_mode:
            return self.moved() \
                or self.swapped_hud() \
                or self.toggled_mini_map() \
                or self.toggled_briefing() \
                or self.console_scrolled() \
                or self.escape_pressed() \
                or self.cycle_target() \
                or self.fire_at_target() \
                or self.toggled_hud() \
                or self.used_ability() \
                or self.ended_mission() \
                or self.exited_game() 
        elif self.mission_over_splash is not None and not self.campaign_mode:
            return self.ended_mission_mode()

    def exited_game(self) -> bool:
        if pygame.key.get_pressed()[K_q] and self.ctrl_pressed():
            if self.exit_game_confirm: 
                self.running = False
            else:
                self.exit_game_confirm = True
                self.push_to_console("Exit game? Press again to confirm.")
            return True
        return False

    def player_being_hunted(self) -> bool:
        chasing = first(lambda x: x.chasing, self.entities) is not None
        return chasing or self.player_in_enemy_contacts

    def ended_mission(self) -> bool:
        if pygame.key.get_pressed()[K_e] and self.ctrl_pressed():
            can_end_mission = not self.player_being_hunted()
            if self.mission_over_confirm and can_end_mission:
                self.mission_over = True
            elif can_end_mission:
                self.mission_over_confirm = True
                self.push_to_console("End mission? Press again to confirm.")
            elif not can_end_mission:
                self.push_to_console("Can't end mission while being hunted!")
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

    def used_ability(self) -> bool:
        ability_key = self.ability_key_pressed()
        if ability_key:
            self.player_uses_ability(ability_key)    
            return True
        return False

    def moved(self) -> bool:
        move_key = self.movement_key_pressed()
        if move_key and KEY_TO_DIRECTION[move_key] != "wait" and self.shift_pressed():
            self.move_camera(KEY_TO_DIRECTION[move_key])
            return True 
        elif move_key and KEY_TO_DIRECTION[move_key] == "wait" and self.ctrl_pressed():
            self.camera = self.player.xy_tuple
            return True
        if move_key and not self.targeting_ability:
            if self.move_entity(self.player, KEY_TO_DIRECTION[move_key]):
                self.player_turn += 1
                self.player_turn_ended = True
                return True
        return False

    def fire_at_target(self) -> bool:
        # NOTE: It is ensured that the selected weapon has ammo before it gets to this point
        if pygame.key.get_pressed()[K_f] and self.targeting_ability is not None:
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
            self.player_turn += 1
            self.player_turn_ended = True
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
            target.missiles_incoming.append(LaunchedWeapon(eta, launcher, target, missile_range))
            self.push_to_console_if_player("MISSILE LAUNCHED! (eta: {})".format(eta), [launcher], \
                tag="combat")
            self.targeting_ability.change_ammo(-1)
        else:
            self.push_to_console_if_player("missile fails to launch!", [launcher], tag="combat")
        # NOTE: a good or bad roll has a significant effect on the time cost of both successful and failed launches
        time_cost = max(MISSILE_LAUNCH_COST_BASE + (launched * 2), 0)
        launcher.next_move_time = self.time_units_passed + time_cost

    def sim_event_torpedo_launch(self, launcher, target, torp_range):
        if self.log_sim_events:
            print("sim_event_torpedo_launch({})".format([launcher.name, target.name]))
        # NOTE: This covers attacks both from and against the player
        self.display_changed = True
        launcher.raise_alert_level(AlertLevel.ENGAGED)
        launched = self.skill_check_launch_torpedo(launcher)
        if launched <= 0:
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
            target.torpedos_incoming.append(LaunchedWeapon(eta, launcher, target, torp_range, known=is_known))
            self.push_to_console_if_player("TORPEDO LAUNCHED! (eta: {})".format(eta), [launcher], \
                tag="combat")
            torps = launcher.get_ability("torpedo")
            torps.change_ammo(-1)
        else:
            self.push_to_console_if_player("torpedo fails to launch!", [launcher], tag="combat")
        # NOTE: a good or bad roll has a significant effect on the time cost of both successful and failed launches
        time_cost = max(TORPEDO_LAUNCH_COST_BASE + (launched * 2), 0)
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
        elif not target.dead:
            target.raise_alert_level(AlertLevel.ENGAGED)
            dmg = roll_torpedo_damage()
            # TODO: (eventually a table of effects for damage rolls that are very high or low)
            target.change_hp(-dmg)
            if target.dead:
                dmg_msg = "{} destroyed by torpedo!".format(target.name, dmg)
                if target.player:
                    self.mission.player_fate = "Destroyed by {}'s torpedo!".format(launcher.name)
            else:
                dmg_msg = "{} takes {} damage from a torpedo! ({} / {})".format(target.name, dmg, \
                    target.hp["current"], target.hp["max"])
            self.push_to_console_if_player(dmg_msg, [launcher, target], tag="combat")

    def skill_check_to_str(self, result) -> str:
        r_str = "failure"
        if result <= 0:
            r_str = "success"
        r_str = r_str + " by {}".format(abs(result))
        return r_str

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

    def push_to_console_if_player(self, msg, entities, tag="other"):
        if any(filter(lambda x: x.player, entities)):
            self.console.push(Message(msg, tag, self.player_turn))
            self.display_changed = True

    def push_to_console(self, msg, tag="other"):
        self.console.push(Message(msg, tag, self.player_turn))
        self.display_changed = True

    def cycle_target(self) -> bool:
        if pygame.key.get_pressed()[K_TAB] and self.targeting_ability is not None:
            targets = self.targets(self.player, self.targeting_ability.type)
            self.targeting_index["current"] = (self.targeting_index["current"] + 1) % self.targeting_index["max"]
            self.camera = targets[self.targeting_index["current"]].xy_tuple
            self.display_changed = True
            return True
        elif pygame.key.get_pressed()[K_TAB] and len(self.player.contacts) > 0: 
            self.observation_index = (self.observation_index + 1) % len(self.player.contacts)
            self.camera = self.player.contacts[self.observation_index].entity.xy_tuple
            self.display_changed = True
            return True
        return False

    def reset_target_mode(self):
        self.targeting_ability = None
        self.targeting_index = {"current": 0, "max": 0}
        self.camera = self.player.xy_tuple
        self.display_changed = True

    def ended_mission_mode(self) -> bool:
        if pygame.key.get_pressed()[K_ESCAPE]:
            self.running = False
            return True
        return False

    def escape_pressed(self):
        if pygame.key.get_pressed()[K_ESCAPE]:
            if self.targeting_ability:
                self.reset_target_mode()
            self.camera = self.player.xy_tuple
            self.displaying_mini_map = False
            self.display_changed = True
            self.displaying_big_splash = False
            self.displaying_briefing_splash = False
            return True
        return False

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
                # TODO" contiguous water targeting only
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
            self.camera = targets[self.targeting_index["current"]].xy_tuple
            self.targeting_index["max"] = len(targets)
            self.display_changed = True
            return True

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
            self.player_turn += 1
            self.player_turn_ended = True

    def ability_key_pressed(self): # Returns key constant or False
        ability_keys = list(map(lambda x: x.key_constant, self.player.abilities))
        for key in ability_keys:
            if pygame.key.get_pressed()[key]:
                return key
        return False
                
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
            self.camera[0] + DIRECTIONS[direction][0], 
            self.camera[1] + DIRECTIONS[direction][1]
        )
        if self.tilemap.tile_in_bounds(target_xy_tuple):
            self.camera = target_xy_tuple

    def move_entity(self, entity, direction) -> bool:
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
            if entity.player and not self.player_long_wait and self.shift_pressed():
                self.player_long_wait = True
                cost = LONG_WAIT_TU_COST
            else:
                cost = WAIT_TU_COST
            entity.next_move_time = self.time_units_passed + cost
            entity.momentum = max(entity.momentum - 2, 0)
            entity.last_direction = direction
            if entity.player:
                self.camera = self.player.xy_tuple
            return True
        # valid movement
        elif self.entity_can_move(entity, direction):
            self.tilemap.toggle_occupied(entity.xy_tuple)
            self.tilemap.toggle_occupied(target_xy_tuple)
            entity.xy_tuple = target_xy_tuple
            if entity.player:
                self.camera = self.player.xy_tuple
            time_unit_cost = entity.get_adjusted_speed()
            if direction in ["upright", "upleft", "downright", "downleft"]:
                time_unit_cost *= 2
            entity.next_move_time = self.time_units_passed + time_unit_cost
            # NOTE: momentum change will get a little more in-depth later on
            if entity.last_direction == direction and entity.speed_mode == "fast":
                entity.momentum = min(entity.momentum + 1 + FAST_MODE_BONUS, MOMENTUM_CAP + FAST_MODE_BONUS)
            elif entity.last_direction == direction:
                entity.momentum = min(entity.momentum + 1, MOMENTUM_CAP)
            else:
                entity.momentum = max(entity.momentum - 2, 0)
            entity.last_direction = direction
            return True
        return False

    def entity_can_move(self, entity, direction) -> bool:
        target_xy = (entity.xy_tuple[0] + DIRECTIONS[direction][0], entity.xy_tuple[1] + DIRECTIONS[direction][1])
        in_bounds = self.tilemap.tile_in_bounds(target_xy)
        occupied = any(map(lambda x: x.xy_tuple == target_xy, self.entities))
        return entity.is_mobile() and in_bounds and not occupied

    def player_debug_mode_contacts(self):
        self.player.contacts = list(map(lambda x: Contact(x, 100), filter(lambda x: not x.player, self.entities)))

    def offmap_asw_check(self):  
        def fuzz(axis) -> int:
            if axis == "vertical":
                offset = self.tilemap.wh_tuple[1] // 3
            elif axis == "horizontal":
                offset = self.tilemap.wh_tuple[0] // 3
            return randint(-offset, offset)
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
            self.entities.append(plane)

    def stealth_check(self):
        if self.mission.stealth_retained and self.player_in_enemy_contacts:
            self.mission.stealth_retained = False

    def turn_based_routines(self):
        self.mission_over_check() 
        if self.player_turn_ended or self.player_long_wait:
            self.observation_index = 0
            self.mission_over_confirm = False
            self.exit_game_confirm = False
            self.processing = True
            self.offmap_asw_check() 
            self.map_distance_to_player = self.djikstra_map_distance_to(self.player.xy_tuple)
            self.chase_check() 
            self.run_entity_behavior() 
            self.incoming_torp_alert()
            self.sensor_checks()
            self.alert_check()
            self.torpedo_arrival_check() 
            self.missile_arrival_check() 
            self.dead_entity_check()
            self.map_enemy_sonar_overlay = self.djikstra_map_enemy_sonar() 
            self.player_long_wait_check() 
            self.stealth_check()  
            if not self.player_long_wait:
                self.update_mini_map() 
                self.player_turn_ended = False
                self.processing = False
            if self.debug:
                self.player_debug_mode_contacts()

    def mission_over_check(self):
        if self.mission_over:
            if self.player in self.entities:
                hp = self.player.hp["current"]
            else:
                hp = 0
            score_lines = self.mission.assessment_lines(hp)
            splash_lines = ["___MISSION COMPLETE___", ""] + score_lines + ["", "<ESC to continue>"]
            self.mission_over_splash = self.generate_big_splash_txt_surf(splash_lines) 

    def update(self):
        self.handle_events()
        self.turn_based_routines()

    def game_loop(self):
        while self.running: 
            self.update()
            if self.display_changed:
                self.draw() 
            self.clock.tick(FPS)

if __name__ == "__main__":
    pygame.init()
    pygame.display.set_caption("Blockade <version {}>".format(VERSION))
    icon = pygame.image.load(WINDOW_ICON_PATH)
    pygame.display.set_icon(icon)
    flags = pygame.FULLSCREEN
    desktop_size = pygame.display.get_desktop_sizes()[0]
    pygame.display.set_mode((desktop_size[0], desktop_size[1]), flags) 
    pygame.mixer.quit()
    game = Game()
    game.game_loop()
    pygame.quit()

