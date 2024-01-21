import pygame
from constants import *
from rolls import *
from tile_map import TileMap
from entity import *
from euclidean import manhattan_distance, chebyshev_distance
from functional import *
from console import Console
import modifiers
from alert_level import AlertLevel
import sort_keys
from random import choice, randint, shuffle

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
        self.camera = (0, 0) # TODO: a little more camera hijackery
        self.entities = []
        self.console = Console()
        self.displaying_hud = True # TODO: implement toggle key for this
        self.console_scrolled_up_by = 0 
        self.hud_font = pygame.font.Font(FONT_PATH, HUD_FONT_SIZE)
        self.overlay_sonar = False
        self.overlay_radar = False
        self.targeting_ability = None 
        self.targeting_index = {"current": 0, "max": 0}
        self.sim_snapshots = [] 
        self.player = None
        self.generate_encounter_small_escorted_convoy_attack()
        self.time_units_passed = 0
        self.player_turn = 0
        self.stealth = "hidden"
        self.player_turn_ended = False

    # Gets the shortest available route 
    def shortest_entity_path(self, start_loc, end_loc, valid_tile_types) -> list:  
        def get_traceback(seen) -> list:  
            current = seen[-1]  
            traceback = [current["loc"]]
            seen.reverse()
            while current["loc"] is not start_loc:
                for node in seen:
                    if node["loc"] is current["via"]:
                        if node["loc"] is not start_loc:
                            traceback.append(node["loc"])
                        current = node
            traceback.reverse()
            return traceback 

        seen = [{"loc": start_loc, "via": None}]
        while True:  
            hits = False
            for node in seen:
                distance = manhattan_distance(node["loc"], end_loc)
                neighbors = self.tilemap.neighbors_of(node["loc"]) 
                for loc in neighbors:
                    not_seen = loc.xy_tuple not in list(map(lambda x: x["loc"], seen))
                    valid_terrain = self.tilemap.get_tile(loc.xy_tuple).tile_type in valid_tile_types
                    closer = manhattan_distance(loc.xy_tuple, end_loc) < distance
                    not_occupied = first(lambda x: x.xy_tuple == loc.xy_tuple, self.entities) is None 
                    goal_reached = loc.xy_tuple == end_loc
                    new_node = {"loc": loc.xy_tuple, "via": node["loc"]}
                    if not_seen and valid_terrain and closer and not_occupied:
                        seen.append(new_node)
                        hits = True
                    if goal_reached:
                        seen.append(new_node)
                        return get_traceback(seen)
            if not hits:
                break
        return None

    def snapshot_sim(self): # TODO: implement sim state snapshotting
        pass

    def input_blocked(self):
        return False # NOTE: this will be used later

    def generate_encounter_small_escorted_convoy_attack(self): # NOTE: In Progress
        self.tilemap = TileMap((200, 200), "open ocean")
        num_escorts, num_freighters = randint(2, 4), randint(3, 8)
        fuzz_val = num_escorts + num_freighters
        traveling = choice(list(DIRECTIONS.keys()))
        origin = (self.tilemap.wh_tuple[0] // 2, self.tilemap.wh_tuple[1] // 2)
        def fuzzed_spawn(origin, spawn_ls, entity, fuzz):
            while True:
                x = randint(-fuzz, fuzz)
                y = randint(-fuzz, fuzz)
                spawn = (origin[0] + x, origin[1] + y)
                if first(lambda x: x.xy_tuple == spawn, spawn_ls) is None:
                    entity.xy_tuple = spawn
                    spawn_ls.append(entity)
                    break
        ai_units = []
        for _ in range(num_escorts):
            fuzzed_spawn(origin, ai_units, SmallConvoyEscort(origin, "enemy", direction=traveling), fuzz_val)
        for _ in range(num_freighters):
            fuzzed_spawn(origin, ai_units, Freighter(origin, "enemy", direction=traveling), fuzz_val)
        player_offset = 20
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
        self.entities = ai_units + [player]

    def draw_level(self):
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
                    elif tile.tile_type == "land":
                        pygame.draw.rect(self.screen, "olive", rect)
                else:
                    pygame.draw.rect(self.screen, "black", rect)
                pygame.draw.rect(self.screen, "gray", rect, 1)
                count_y += 1
            count_x += 1
            count_y = 0

        def draw_overlay(radius, color): 
            tiles_in_range = list(filter(lambda x: manhattan_distance(x.xy_tuple, self.player.xy_tuple) <= radius \
                and x.xy_tuple != self.player.xy_tuple and str(x.xy_tuple) in relative_positions.keys(), \
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
            # lay down reticule if ability targeting:
            if self.targeting_ability is not None:
                target_cell = relative_positions[str(self.camera)]
                target = (target_cell[0] + CELL_SIZE // 2, target_cell[1] + CELL_SIZE // 2)
                pygame.draw.circle(self.screen, "magenta", target, int(CELL_SIZE * .66), 2)

        # overlays (TODO: a few more)
        if self.targeting_ability is not None:
            draw_overlay(self.targeting_ability.range, HUD_OPAQUE_RED)
        else:
            # NOTE: These sensor overlays may overlap
            if self.overlay_sonar: 
                psonar_range = first(lambda x: x.type == "passive sonar", self.player.abilities).range
                draw_overlay(psonar_range, (0, 220, 220, 170))
            if self.overlay_radar:
                radar_range = first(lambda x: x.type == "radar", self.player.abilities).range
                draw_overlay(radar_range, (220, 220, 220, 170))

        # draw entities:
        for entity in self.entities:
            if str(entity.xy_tuple) in relative_positions.keys() \
                and ((entity in list(map(lambda x: x.entity, self.player.contacts))) or entity.player):
                rect = relative_positions[str(entity.xy_tuple)]
                self.screen.blit(entity.image, rect)
                # a "tail" showing direction came from:
                target = (rect[0] + CELL_SIZE // 2, rect[1] + CELL_SIZE // 2)
                tail_point = self.get_tail_point(entity, target) 
                pygame.draw.line(self.screen, "white", target, tail_point, 2) 
                # reticule if currently targeted by a player weapon:
                torps = list(map(lambda x: x.launcher.player, entity.torpedos_incoming))
                missiles = list(map(lambda x: x.launcher.player, entity.missiles_incoming))
                if any(torps + missiles):
                    pygame.draw.circle(self.screen, "yellow", target, int(CELL_SIZE * .66), 2)

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

    def draw_console(self):
        line_height = HUD_FONT_SIZE + 1
        num_lines = CONSOLE_LINES
        console_size = (int(self.screen.get_width() * .4), line_height * num_lines)
        console_surface = pygame.Surface(console_size, flags=SRCALPHA)
        console_surface.fill(HUD_OPAQUE_BLACK)
        pygame.draw.rect(console_surface, "cyan", (0, 0, console_size[0], console_size[1]), 1)
        last = len(self.console.messages) - 1 
        msgs = []
        for line in range(num_lines):
            index = last - line - self.console_scrolled_up_by
            if index >= 0 and index < len(self.console.messages):
                msgs.append(self.console.messages[index])
        msgs.reverse() 
        for line in range(len(msgs)):
            line_surface = self.hud_font.render(msgs[line], True, "white")
            console_surface.blit(line_surface, (0, line * line_height))
        y = self.screen.get_height() - line_height * num_lines - 3
        x = (self.screen.get_width() - console_size[0]) // 2
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
        self.screen.blit(abilities_surface, (0, 0)) 

    def draw_player_stats(self):
        line_height = HUD_FONT_SIZE + 1
        stats_lines = [
            "Turn: {}".format(self.player_turn),
            "Time: {}".format(self.time_units_passed),
            "HP: {}/{}".format(self.player.hp["current"], self.player.hp["max"]),
            "Stealth: {}".format(self.stealth.upper()),
            "Speed: {} ({})".format(self.player.speed_mode, self.player.get_adjusted_speed()),
            "Momentum: {}".format(self.player.momentum),
        ]
        stats_size = (int(self.screen.get_width() * .1), len(stats_lines) * line_height)
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
        pos = (int(self.screen.get_width() * .9), 0)
        self.screen.blit(stats_surface, pos)

    def draw_target_stats(self):
        if self.targeting_ability is not None:
            target = self.targets(self.player, self.targeting_ability.type)[self.targeting_index["current"]]
            contact = first(lambda x: x.entity is target, self.player.contacts)
            target_stats = [
                "Target Name: {}".format(target.name),
                "HP: {}/{}".format(target.hp["current"], target.hp["max"]),
                "Speed: {} ({})".format(target.speed_mode, target.get_adjusted_speed()),
                "Detection: {}%".format(contact.acc),
            ]
            text = self.hud_font.render("  |  ".join(target_stats), True, "white")
            surf = pygame.Surface((text.get_width() + 1, text.get_height() + 1), flags=SRCALPHA)
            surf.fill(HUD_OPAQUE_BLACK)
            pygame.draw.rect(surf, "cyan", (0, 0, surf.get_width(), surf.get_height()), 1)
            surf.blit(text, (1, 1))
            pos = (self.screen.get_width() / 2 - surf.get_width() / 2, 4)
            self.screen.blit(surf, pos)

    def draw_hud(self):
        if self.displaying_hud:
            self.draw_console()
            self.draw_abilities()
            self.draw_player_stats() 
            self.draw_target_stats() 

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
            # Keyboard Buttons (this game will be all buttons, as I want to prepare it for controller input)
            elif event.type == KEYDOWN: 
                self.display_changed = self.keyboard_event_changed_display()

    def dead_entity_check(self):
        new_entities = list(filter(lambda x: not x.dead, self.entities))
        if len(new_entities) < len(self.entities):
            self.entities = new_entities
            self.display_changed = True
        if self.player not in self.entities:
            # NOTE: place-holder
            self.running = False 

    def run_ai_behavior(self): # NOTE: in progress
        while True: 
            can_move = list(filter(lambda x: x.next_move_time <= self.time_units_passed, self.entities))
            if any(map(lambda x: x.player, can_move)):
                break
            shuffle(can_move)
            for entity in can_move:
                if entity.name == "small convoy escort":
                    self.entity_ai_small_convoy_escort(entity) 
                elif entity.name == "freighter":
                    self.move_entity(entity, entity.direction)
            self.time_units_passed += 1
        return

    # Moves an entity in a completely random direction
    def entity_ai_random_move(self, entity):
        direction = choice(list(DIRECTIONS.keys())) 
        self.move_entity(entity, direction)

    def relative_direction(self, from_xy, to_xy): # TODO: put direction-related stuff in own file
        diff = (to_xy[0] - from_xy[0], to_xy[1] - from_xy[1])
        for k, v in DIRECTIONS.items():
            if v == diff:
                return k
        return "wait"

    def entity_ai_small_convoy_escort(self, entity):  # NOTE: In Progress
        torpedo_target = first(lambda x: manhattan_distance(x.entity.xy_tuple, entity.xy_tuple) <= TORPEDO_RANGE, \
            entity.contacts)
        if torpedo_target is not None and entity.get_ability("torpedo").ammo > 0:
            self.sim_event_torpedo_launch(entity, torpedo_target.entity, TORPEDO_RANGE)
        elif len(entity.contacts) > 0:
            closest = entity.get_closest_contact() 
            path = self.shortest_entity_path(entity.xy_tuple, closest.entity.xy_tuple, ["ocean"]) 
            if path is not None:
                self.console.push("<testing entity_ai_convoy_escort CHASE>")
                direction = self.relative_direction(entity.xy_tuple, path[0]) 
                self.move_entity(entity, direction) 
        else:
            self.move_entity(entity, entity.direction)
        if entity.alert_level.value >= 1 and entity.speed_mode == "normal":
            entity.toggle_speed()

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
        # NOTE: missiles not in yet
        for entity in self.entities:
            new_contacts = []
            if entity.has_skill("visual detection"):
                new_contacts.extend(self.sim_event_entity_conducts_visual_detection(entity, new_contacts))
            if entity.has_ability("passive sonar") and entity.has_skill("passive sonar"):
                new_contacts.extend(self.sim_event_entity_conducts_psonar_detection(entity, new_contacts)) 
                if len(entity.torpedos_incoming) > 0 and entity.alert_level != AlertLevel.ENGAGED:
                    self.sim_event_entity_torpedo_detection(entity) 
            if entity.has_ability("radar") and entity.has_skill("radar"):
                new_contacts.extend(self.sim_event_entity_conducts_radar_detection(entity, new_contacts))
                if len(entity.missiles_incoming) > 0 and entity.alert_level != AlertLevel.ENGAGED:
                    self.sim_event_entity_missile_detection(entity) 
            self.sim_event_degrade_old_contacts(entity, new_contacts)
            self.sim_event_propagate_new_contacts(entity, new_contacts) 

    # Contact accuracy degrades every turn by 3d6% when not actively being sensed
    def sim_event_degrade_old_contacts(self, entity, new_contacts):
        for contact in entity.contacts:
            if contact not in new_contacts:
                torp_contact = first(lambda x: x.launcher is entity, contact.entity.torpedos_incoming)
                if torp_contact is None:
                    # NOTE: When targeted by an owned torpedo, contacts don't degrade
                    acc_pen = sum(roll3d6())
                    contact.change_acc(-acc_pen)
                if contact.acc == 0: 
                    entity.contacts.remove(contact)
                    self.push_to_console_if_player("contact with {} lost".format(contact.entity.name), [entity])

    def sim_event_propagate_new_contacts(self, entity, new_contacts): 
        entity.contacts.extend(new_contacts)
        if entity.submersible:
            # NOTE: submersible entities will propagate contacts only when exposed to do so via an antenna, once
            #       that mechanic is implemented.
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
                        if known is not None and known.acc < contact.acc:
                            known.acc = contact.acc
                        elif known is None:
                            target.contacts.append(contact)

    def sim_event_entity_missile_detection(self, entity): 
        for missile in entity.missiles_incoming:
            launcher, target = missile.launcher, missile.target
            result = self.skill_check_detect_nearby_missile(launcher, target, target)
            if result <= 0:
                entity.raise_alert_level(AlertLevel.ENGAGED)
                break

    def sim_event_entity_torpedo_detection(self, entity): 
        for torp in entity.torpedos_incoming:
            launcher, target = torp.launcher, torp.target
            result = self.skill_check_detect_nearby_torpedo(launcher, target, target)
            if result <= 0:
                entity.raise_alert_level(AlertLevel.ENGAGED)
                break

    def sim_event_entity_conducts_visual_detection(self, entity, new_contacts_ls) -> list:
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
                self.push_to_console_if_player("{} visually detected with {}% accuracy!".format(target.name, acc), \
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
        # NOTE: unlike psonar, this is conducted independently of passive sensor_checks() as an action
        new = []
        potentials = list(filter(lambda x: x.faction != entity.faction \
            and manhattan_distance(x.xy_tuple, entity.xy_tuple) <= ACTIVE_SONAR_RANGE \
            and x is not entity, self.entities))
        for target in potentials:
            detected = self.skill_check_detect_asonar_contact(entity, target) 
            if detected <= 0:
                # NOTE: asonar contacts come with a range of accuracy ratings based on roll's margin of success 
                acc = min(80 + 10 * abs(detected), 100)
                new_contact = Contact(target, acc)
                exists_in_old_contacts = first(lambda x: x.entity is target, entity.contacts)
                exists_in_new_contacts = first(lambda x: x.entity is target, new)
                if exists_in_old_contacts is not None and exists_in_old_contacts.acc < acc:
                    exists_in_old_contacts.acc = acc
                elif exists_in_new_contacts is not None and exists_in_new_contacts.acc < acc:
                    exists_in_new_contacts.acc = acc
                elif exists_in_new_contacts is None and exists_in_old_contacts is None:
                    self.push_to_console_if_player("{} detected via active sonar".format(target.name), [entity])
                    new.append(new_contact)
        self.sim_event_propagate_new_contacts(entity, new)
        entity.next_move_time += ACTIVE_SONAR_TIME_COST
        alerted = list(filter(lambda x: x.has_skill("passive sonar") and x.has_ability("passive sonar"), potentials))
        for observer in alerted:
            self.sim_event_propagate_new_contacts(entity, [Contact(entity, 100)])

    def sim_event_entity_conducts_psonar_detection(self, entity, new_contacts_ls) -> list:
        new = list(new_contacts_ls)
        potentials = list(filter(lambda x: x.faction != entity.faction \
            and manhattan_distance(x.xy_tuple, entity.xy_tuple) <= PASSIVE_SONAR_RANGE \
            and x is not entity, self.entities))
        for target in potentials:
            detected = self.skill_check_detect_psonar_contact(entity, target)
            if detected <= 0:
                # NOTE: psonar contacts come with a range of accuracy ratings based on roll's margin of success 
                acc = min(50 + 10 * abs(detected), 100)
                new_contact = Contact(target, acc)
                exists_in_old_contacts = first(lambda x: x.entity is target, entity.contacts)
                exists_in_new_contacts = first(lambda x: x.entity is target, new)
                if exists_in_old_contacts is not None and exists_in_old_contacts.acc < acc:
                    exists_in_old_contacts.acc = acc
                elif exists_in_new_contacts is not None and exists_in_new_contacts.acc < acc:
                    exists_in_new_contacts.acc = acc
                elif exists_in_new_contacts is None and exists_in_old_contacts is None:
                    self.push_to_console_if_player("{} detected via passive sonar".format(target.name), [entity])
                    new.append(new_contact)
        return new

    def sim_event_entity_conducts_radar_detection(self, entity, new_contacts_ls) -> list:
        if not self.overlay_radar:
            return []
        new = list(new_contacts_ls)
        potentials = list(filter(lambda x: x.faction != entity.faction \
            and manhattan_distance(x.xy_tuple, entity.xy_tuple) <= RADAR_RANGE \
            and not x.submersible \
            and x is not entity, self.entities)) + \
            list(filter(lambda x: x.submersible_emitter(), self.entities))
        for target in potentials:
            detected = self.skill_check_detect_radar_contact(entity, target)
            if detected <= 0:
                # NOTE: for now, successful radar contacts are always 100% acc.
                acc = 100
                new_contact = Contact(target, acc)
                exists_in_old_contacts = first(lambda x: x.entity is target, entity.contacts)
                exists_in_new_contacts = first(lambda x: x.entity is target, new)
                if exists_in_old_contacts is not None and exists_in_old_contacts.acc < acc:
                    exists_in_old_contacts.acc = acc
                elif exists_in_new_contacts is not None and exists_in_new_contacts.acc < acc:
                    exists_in_new_contacts.acc = acc
                elif exists_in_new_contacts is None and exists_in_old_contacts is None:
                    self.push_to_console_if_player("{} detected via radar".format(target.name, acc), \
                        [entity])
                    new.append(new_contact)
        return new

    def alert_check(self):
        for entity in self.entities:
            if len(entity.contacts) > 0:
                entity.raise_alert_level(AlertLevel.ALERTED)

    def turn_based_routines(self):
        if self.player_turn_ended:
            self.sensor_checks()
            self.alert_check()
            self.run_ai_behavior() # NOTE: in progress
            self.torpedo_arrival_check() 
            self.missile_arrival_check() 
            self.dead_entity_check()
            self.player_turn_ended = False

    def update(self):
        self.handle_events()
        self.turn_based_routines()

    def keyboard_event_changed_display(self) -> bool:
        return not self.input_blocked() and (self.moved() \
            or self.console_scrolled() \
            or self.cancel_target_mode() \
            or self.cycle_target() \
            or self.fire_at_target() \
            or self.used_ability())

    def used_ability(self) -> bool:
        ability_key = self.ability_key_pressed()
        if ability_key:
            self.player_uses_ability(ability_key)    
            return True
        return False

    def moved(self) -> bool:
        move_key = self.movement_key_pressed()
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
                self.console.push("can't target submerged vessels with missiles!")
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
        # NOTE: This covers attacks both from and against the player
        self.display_changed = True
        launcher.raise_alert_level(AlertLevel.ENGAGED)
        launched = self.skill_check_launch_missile(self.player)
        if launched <= 0:
            # target detection:
            if target.can_detect_incoming_missiles():
                target_detects = self.skill_check_detect_nearby_missile(launcher, target, target)
                if target_detects <= 0: 
                    target.raise_alert_level(AlertLevel.ENGAGED)
            # nearby observer detection:
            for entity in list(filter(lambda x: x not in [target, launcher], self.entities)): 
                if entity.can_detect_incoming_missiles():
                    detected = self.skill_check_detect_nearby_missile(launcher, target, entity) 
                    if detected <= 0:
                        entity.raise_alert_level(AlertLevel.ALERTED)
            distance = manhattan_distance(launcher.xy_tuple, target.xy_tuple)
            eta = self.time_units_passed + MISSILE_SPEED * distance
            target.missiles_incoming.append(LaunchedWeapon(eta, launcher, target, missile_range))
            self.push_to_console_if_player("MISSILE LAUNCHED! (will reach target around: {})".format(eta), [launcher])
            self.targeting_ability.ammo -= 1
        else:
            self.push_to_console_if_player("missile fails to launch!", [launcher])
        # NOTE: a good or bad roll has a significant effect on the time cost of both successful and failed launches
        time_cost = max(MISSILE_LAUNCH_COST_BASE + (launched * 2), 0)
        launcher.next_move_time = self.time_units_passed + time_cost

    def sim_event_torpedo_launch(self, launcher, target, torp_range):
        # NOTE: This covers attacks both from and against the player
        self.display_changed = True
        launcher.raise_alert_level(AlertLevel.ENGAGED)
        launched = self.skill_check_launch_torpedo(launcher)
        if launched <= 0:
            # target detection:
            if target.can_detect_incoming_torpedos():
                target_detects = self.skill_check_detect_nearby_torpedo(launcher, target, target)
                if target_detects <= 0: 
                    target.raise_alert_level(AlertLevel.ENGAGED)
            # nearby observer detection:
            for entity in list(filter(lambda x: x not in [target, launcher], self.entities)): 
                if entity.can_detect_incoming_torpedos():
                    detected = self.skill_check_detect_nearby_torpedo(launcher, target, entity) 
                    if detected <= 0:
                        entity.raise_alert_level(AlertLevel.ALERTED)
            distance = manhattan_distance(launcher.xy_tuple, target.xy_tuple)
            eta = self.time_units_passed + TORPEDO_SPEED * distance
            target.torpedos_incoming.append(LaunchedWeapon(eta, launcher, target, torp_range))
            self.push_to_console_if_player("TORPEDO LAUNCHED! (will reach target around: {})".format(eta), [launcher])
            torps = launcher.get_ability("torpedo")
            torps.ammo -= 1
        else:
            self.push_to_console_if_player("torpedo fails to launch!", [launcher])
        # NOTE: a good or bad roll has a significant effect on the time cost of both successful and failed launches
        time_cost = max(TORPEDO_LAUNCH_COST_BASE + (launched * 2), 0)
        launcher.next_move_time = self.time_units_passed + time_cost

    def skill_check_evade_incoming_torpedo(self, torp) -> int:
        launcher, target = torp.launcher, torp.target
        bonus = modifiers.pilot_torpedo_alert_mod(target.alert_level)
        acc_pen = -((100 - first(lambda x: x.entity is target, launcher.contacts).acc) // 10)
        contest = roll_skill_contest(launcher, target, "torpedo", "evasive maneuvers", mods_a=[bonus])
        result = contest["roll"]
        if contest["entity"] is launcher:
            result *= -1
        self.push_to_console_if_player("[{}] Skill Contest (evade torpedo): {}".format(target.name, result), [target])
        return result

    def sim_event_missile_arrival(self, missile): 
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
                self.push_to_console_if_player("{}'s missile intercepted!".format(launcher.name), [launcher, target])
                intercepted = True
        if not intercepted:
            dmg = roll_missile_damage()
            # TODO: (eventually a table of effects for damage rolls that are very high or low)
            target.change_hp(-dmg)
            if target.dead:
                dmg_msg = "{} takes {} damage from a missile, and is destroyed!".format(target.name, dmg)
            else:
                dmg_msg = "{} takes {} damage from a missile! ({} / {})".format(target.name, dmg, \
                    target.hp["current"], target.hp["max"])
            self.push_to_console_if_player(dmg_msg, [launcher, target])
        target.raise_alert_level(AlertLevel.ENGAGED)

    def sim_event_torpedo_arrival(self, torp): 
        # evasion and damage
        launcher, target = torp.launcher, torp.target
        target_detects = self.skill_check_detect_nearby_torpedo(launcher, target, target) 
        if target_detects <= 0 and target.is_mobile():
            target.raise_alert_level(AlertLevel.ENGAGED)
            self.push_to_console_if_player("{} takes evasive action!".format(target.name), [launcher, target])
            evaded = self.skill_check_evade_incoming_torpedo(torp)
            if evaded <= 0 and target_detects <= 0:
                msg = "{}'s torpedo is evaded by {}!".format(launcher.name, target.name)
                self.push_to_console_if_player(msg, [launcher, target])
            else:
                dmg = roll_torpedo_damage()
                # TODO: (eventually a table of effects for damage rolls that are very high or low)
                target.change_hp(-dmg)
                if target.dead:
                    dmg_msg = "{} takes {} damage from a torpedo, and is destroyed!".format(target.name, dmg)
                else:
                    dmg_msg = "{} takes {} damage from a torpedo! ({} / {})".format(target.name, dmg, \
                        target.hp["current"], target.hp["max"])
                self.push_to_console_if_player(dmg_msg, [launcher, target])

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
            #    self.skill_check_to_str(result)), [observer])
            return result
        return FAIL_DEFAULT

    def skill_check_radio_outgoing(self, sender) -> int:
        result = roll_skill_check(sender, "radio")
        if result <= 0:
            self.push_to_console_if_player("[{}] Skill Check (radio send): {}".format(sender.name, \
                result), [sender])
            return result
        return FAIL_DEFAULT

    def skill_check_radio_incoming(self, receiver, sent_r) -> int:
        result = roll_skill_check(receiver, "radio", mods=[receiver.alert_level.value, sent_r])
        if result <= 0:
            return result
        return FAIL_DEFAULT

    def skill_check_detect_asonar_contact(self, observer, target) -> int:
        mods = [
            modifiers.sonar_distance_mod(observer, target) // 2,
            observer.alert_level.value,
        ]
        contest = roll_skill_contest(observer, target, "active sonar", "stealth", mods_a=mods, \
            mods_b = [modifiers.stealth_asonar_penalty])
        result, winner = contest["roll"], contest["entity"]
        # NOTE: under normal circumstances, this roll is hidden from the player so they can't count contacts based
        #       on it alone.
        #self.push_to_console_if_player("[{}] Skill Contest (active sonar detection): {}".format(observer.name, \
        #    result), [observer])
        if winner is observer and result <= 0:
            return result
        return FAIL_DEFAULT

    def skill_check_detect_psonar_contact(self, observer, target) -> int:
        mods = [
            modifiers.moving_psonar_mod(observer, target),
            observer.alert_level.value,
            modifiers.sonar_distance_mod(observer, target),
        ]
        contest = roll_skill_contest(observer, target, "passive sonar", "stealth", mods_a=mods)
        result, winner = contest["roll"], contest["entity"]
        # NOTE: under normal circumstances, this roll is hidden from the player so they can't count contacts based
        #       on it alone.
        #self.push_to_console_if_player("[{}] Skill Contest (passive sonar detection): {}".format(observer.name, \
        #    result), [observer])
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
            #    self.skill_check_to_str(result)), [observer])
            return result
        return FAIL_DEFAULT

    def skill_check_launch_torpedo(self, launcher) -> int:
        result = roll_skill_check(launcher, "torpedo")
        self.push_to_console_if_player("[{}] Skill Check (launch torpedo): {}".format(launcher.name, \
            self.skill_check_to_str(result)), [launcher])
        return result

    def skill_check_launch_missile(self, launcher) -> int:
        result = roll_skill_check(launcher, "missile")
        self.push_to_console_if_player("[{}] Skill Check (launch missile): {}".format(launcher.name, \
            self.skill_check_to_str(result)), [launcher])
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
                    self.skill_check_to_str(detected_visual)), [observer])
        if observer.has_skill("radar") and observer.has_ability("radar") and witness(RADAR_RANGE):
            detected_radar = roll_skill_check(observer, "radar", mods=[observer.alert_level.value])
            if detected_radar <= 0:
                self.push_to_console_if_player("[{}] Skill Check (detect torpedo via radar): {}".format(observer.name, \
                    self.skill_check_to_str(detected_radar)), [observer])
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
                    self.skill_check_to_str(detected_visual)), [observer])
        if observer.has_skill("passive sonar") and observer.has_ability("passive sonar") and witness(PASSIVE_SONAR_RANGE):
            bonus = modifiers.noisy_torpedo_bonus_to_passive_sonar_detection
            detected_sonar = roll_skill_check(observer, "passive sonar", mods=[observer.alert_level.value, bonus])
            if detected_sonar <= 0:
                self.push_to_console_if_player("[{}] Skill Check (detect torpedo via sonar): {}".format(observer.name, \
                    self.skill_check_to_str(detected_sonar)), [observer])
        if detected_visual or detected_sonar: 
            return min([detected_visual, detected_sonar])
        return FAIL_DEFAULT

    def push_to_console_if_player(self, msg, entities):
        if any(filter(lambda x: x.player, entities)):
            self.console.push(msg)
            self.display_changed = True

    def cycle_target(self) -> bool:
        if pygame.key.get_pressed()[K_TAB] and self.targeting_ability is not None:
            targets = self.targets(self.player, self.targeting_ability.type)
            self.targeting_index["current"] = (self.targeting_index["current"] + 1) % self.targeting_index["max"]
            self.camera = targets[self.targeting_index["current"]].xy_tuple
            self.display_changed = True
            return True
        return False

    def reset_target_mode(self):
        self.display_changed = True
        self.targeting_ability = None
        self.camera = self.player.xy_tuple
        self.targeting_index = {"current": 0, "max": 0}

    def cancel_target_mode(self):
        if pygame.key.get_pressed()[K_ESCAPE] and self.targeting_ability:
            self.reset_target_mode()
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
            self.console.push("out of ammo!") 
            return False
        elif len(targets) == 0:
            self.console.push("no valid targets in range ({})!".format(ability.range)) 
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
                self.console.push("target mode: 'f' to fire, TAB to cycle, ESC to return")
        elif ability_type == "passive sonar":
            self.overlay_sonar = not self.overlay_sonar
            self.console.push("displaying passive sonar range: {}".format(self.overlay_sonar))
        elif ability_type == "radar":
            self.overlay_radar = not self.overlay_radar
            radar = self.player.get_ability("radar")
            radar.emerged_to_transmit = not radar.emerged_to_transmit
            self.console.push("using radar and displaying range: {}".format(self.overlay_radar))
        elif ability_type == "toggle speed":
            self.player.toggle_speed()
            self.console.push("speed mode is now: {}".format(self.player.speed_mode))
        elif ability_type == "active sonar":
            self.console.push("using active sonar!")
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

    def move_entity(self, entity, direction) -> bool:
        target_xy_tuple = (
            entity.xy_tuple[0] + DIRECTIONS[direction][0], 
            entity.xy_tuple[1] + DIRECTIONS[direction][1]
        )
        if not self.tilemap.tile_in_bounds(target_xy_tuple) and not entity.player:
            # NOTE: AI units despawn when moving off-map
            if entity in self.entities:
                self.entities.remove(entity)
        occupied = first(lambda x: x.xy_tuple == target_xy_tuple and entity is not x, self.entities)
        if occupied is not None and occupied not in list(map(lambda x: x.entity, entity.contacts)):
            self.push_to_console_if_player("suspicious noises in this direction {}".format(occupied.name), [entity])  
            direction = "wait"
        if direction == "wait":
            entity.next_move_time = self.time_units_passed + WAIT_TU_COST
            entity.momentum = max(entity.momentum - 2, 0)
            entity.last_direction = direction
            return True
        if self.entity_can_move(entity, direction):
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

