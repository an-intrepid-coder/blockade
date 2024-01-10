import pygame
from constants import *
from rolls import roll3d6, roll_torpedo_damage, roll_skill_check, roll_skill_contest
from tile_map import TileMap
from entity import Player, Freighter, AlertLevel
from euclidean import manhattan_distance, chebyshev_distance
from functional import first, flatten
from console import Console
import modifiers
from alert_level import AlertLevel
from faction import Faction
import sort_keys

class SimStateSnapshot:
    pass # TODO

class Game:
    def __init__(self):
        # TODO: a seeding system
        self.running = True
        self.display_changed = True
        self.screen = pygame.display.get_surface() 
        self.screen_wh_cells_tuple = (self.screen.get_width() // CELL_SIZE, self.screen.get_height() // CELL_SIZE)
        self.clock = pygame.time.Clock()
        self.tilemap = []
        self.camera = (0, 0) # TODO: a little more camera hijackery
        self.entities = []
        self.console = Console()
        self.displaying_hud = True # TODO: implement toggle key for this
        self.console_scrolled_up_by = 0 
        self.hud_font = pygame.font.Font(FONT_PATH, HUD_FONT_SIZE)
        self.overlay_sonar = False
        self.targeting_ability = None 
        self.targeting_index = {"current": 0, "max": 0}
        self.sim_snapshots = [] 
        self.player = None
        self.generate_encounter_convoy_attack()

    def snapshot_sim(self): # TODO: implement sim state snapshotting
        pass

    def input_blocked(self):
        return False # NOTE: this will be used later

    def generate_encounter_convoy_attack(self):
        self.tilemap = TileMap(self.screen_wh_cells_tuple, "open ocean")
        # NOTE: will use a very different entity spawning scheme after basic systems fleshed out more
        player = Player((10, 10))
        freighters = [
            Freighter((1, 10), Faction.ENEMY),
            Freighter((0, 8), Faction.ENEMY),
            Freighter((1, 5), Faction.ENEMY),
            Freighter((2, 18), Faction.ENEMY),
            Freighter((23, 1), Faction.ENEMY),
            Freighter((18, 9), Faction.ENEMY),
            Freighter((24, 10), Faction.ENEMY),
            Freighter((4, 11), Faction.ENEMY),
        ]
        self.entities = freighters + [player]
        self.player = player
        self.camera = player.xy_tuple
        # NOTE: For this mission example, at least, the player should go first.
        self.player.initiative = min(list(map(lambda x: x.initiative, self.entities))) - 1
        self.entities.sort(key=sort_keys.initiative)

    def draw_level(self):
        topleft = (self.camera[0] - self.screen_wh_cells_tuple[0] // 2, self.camera[1] - self.screen_wh_cells_tuple[1] // 2)
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

        # draw entities
        entity_cells = []
        for entity in self.entities:
            if str(entity.xy_tuple) in relative_positions.keys():
                rect = relative_positions[str(entity.xy_tuple)]
                entity_cells.append(rect)
                self.screen.blit(entity.image, rect)

        def draw_overlay(radius, color): 
            tiles_in_range = list(filter(lambda x: manhattan_distance(x.xy_tuple, self.player.xy_tuple) <= radius, 
                                         self.tilemap.all_tiles()))
            # filter out land tiles and inaccessible tiles if torpedo attack (TODO)
            if self.targeting_ability is not None:
                if "torpedo" in self.targeting_ability.type:
                    tiles_in_range = list(filter(lambda x: x.tile_type == "ocean", tiles_in_range))
            # lay down overlay:
            affected_cells = list(map(lambda x: relative_positions[str(x.xy_tuple)], tiles_in_range))
            for cell in affected_cells:
                if (cell[0], cell[1]) not in map(lambda x: (x[0], x[1]), entity_cells):
                    surf = pygame.Surface((cell[2], cell[3]), flags=SRCALPHA)
                    surf.fill(color)
                    self.screen.blit(surf, (cell[0], cell[1]))
            # lay down reticule if ability targeting:
            if self.targeting_ability is not None:
                target_cell = relative_positions[str(self.camera)]
                target = (target_cell[0] + CELL_SIZE // 2, target_cell[1] + CELL_SIZE // 2)
                pygame.draw.circle(self.screen, "yellow", target, int(CELL_SIZE * .66), 2)

        # overlays (TODO: a few more)
        if self.targeting_ability is not None:
            draw_overlay(self.targeting_ability.range, HUD_OPAQUE_RED)
        elif self.overlay_sonar: 
            psonar_range = first(lambda x: x.type == "passive sonar", self.player.abilities).range
            draw_overlay(psonar_range, (0, 220, 220, 170))

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

    def draw_hud(self):
        if self.displaying_hud:
            self.draw_console()
            self.draw_abilities()

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

    def run_checks(self):
        self.dead_entity_check()

    def update(self):
        self.handle_events()
        self.run_checks()

    def keyboard_event_changed_display(self) -> bool:
        return not self.input_blocked() and (self.moved() \
            or self.console_scrolled() \
            or self.cancel_target_mode() \
            or self.cycle_target() \
            or self.fire_at_target() \
            or self.used_ability())

    def used_ability(self):
        ability_key = self.ability_key_pressed()
        if ability_key:
            self.player_uses_ability(ability_key)    
            return True
        return False

    def moved(self):
        move_key = self.movement_key_pressed()
        if move_key and not self.targeting_ability:
            if self.move_entity(self.player, KEY_TO_DIRECTION[move_key]):
                self.camera = self.player.xy_tuple
                return True
        return False

    def fire_at_target(self) -> bool:
        # NOTE: It is ensured that the selected weapon has ammo before it gets to this point
        if pygame.key.get_pressed()[K_f] and self.targeting_ability is not None:
            target = self.targets(self.player, self.targeting_ability.type)[self.targeting_index["current"]]
            if "torpedo" in self.targeting_ability.type:
                self.sim_event_torpedo_attack(self.player, target, self.targeting_ability.range)
                # NOTE: this will appear again in enemy routines, and will take torpedo range in a different way
            # TODO: missiles and more
            self.reset_target_mode()
            return True
        return False

    # NOTE: This is the basic unit of "game action". Breaking these into too many more sub-functions smaller than this
    #       would calcify everything and require a bunch of functions that take way too many parameters. It is best if
    #       they are self-contained like this, in one pot of mild spaghetti, as a sequence of events. But I'll continue
    #       to look out for more ways of doing it. There will be a lot of functions like this, as each "game action"
    #       will be pretty custom. But there will be a limited number of them. 
    # TODO: Preface all SimEvent-like "game action" functions like this with some kind of convention. sim_event_<fn>, etc.
    def sim_event_torpedo_attack(self, launcher, target, torp_range):
        # NOTE: This covers attacks both from and against the player
        # NOTE: For now, all torps behave the same aside from their range. But eventually some will do more damage
        #       or be stealthier, at which point this function gets a few extra steps.
        self.push_to_console_if_player("TORPEDO ATTACK: {} ---> {}".format(launcher.name, target.name), \
            [launcher, target])
        self.display_changed = True
        # Initial launch:
        launcher.raise_alert_level(AlertLevel.ENGAGED)
        launched = self.skill_check_launch_torpedo(self.player)
        if launched <= 0:
            # target detection:
            if target.can_detect_incoming_torpedos():
                target_detects = self.skill_check_detect_incoming_torpedo(launcher, target)
                if target_detects <= 0: 
                    # TODO: (eventually a table of additional effects based on margin of success)
                    target.raise_alert_level(AlertLevel.ENGAGED)
            # nearby observer detection:
            for entity in list(filter(lambda x: x not in [target, launcher], self.entities)): 
                if entity.can_detect_incoming_torpedos():
                    detected = self.skill_check_detect_nearby_torpedo_launch(launcher, target, entity) 
                    if detected <= 0:
                        # TODO: (eventually a table of additional effects based on margin of success)
                        entity.raise_alert_level(AlertLevel.ALERTED)
            # evasion and damage:
            if target_detects <= 0 and target.is_mobile():
                self.push_to_console_if_player("{} takes evasive action!".format(target.name), [launcher, target])
                evaded = self.skill_check_evade_incoming_torpedo(launcher, target) # TODO
                if evaded <= 0 and target_detects <= 0:
                    # TODO: (eventually a table of effects based on margin of victory)
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

            self.targeting_ability.ammo -= 1
            
        else:
            # TODO: a number of positive margin effects, from nothing to a jam to a misfire or worse
            self.push_to_console_if_player("torpedo fails to launch!", [launcher])

    def skill_check_launch_torpedo(self, launcher) -> int:
        bonus = modifiers.torpedo_launch_is_routine
        result = roll_skill_check(launcher, "torpedo", mods=[bonus])
        self.push_to_console_if_player("[{}] Skill Check (launch torpedo): {}".format(launcher.name, result), [launcher])
        return result

    def skill_check_detect_incoming_torpedo(self, launcher, target) -> int:
        # NOTE: Covers both visual and sonar. Uses the most effective of either roll for the target.
        detected_visual, detected_sonar = False, False
        # NOTE: It is ensured before calling this function that at least one of these skills is present
        if target.has_skill("visual detection"):
            # NOTE: This should include player and other subs using periscopes, when up, at some point. Which is a 
            #       separate skill.
            penalty = modifiers.torpedo_is_relatively_hard_to_spot
            detected_visual = roll_skill_check(target, "visual detection", mods=[target.alert_level.value, penalty])
            self.push_to_console_if_player("[{}] Skill Check (visually detect torpedo): {}".format(target.name, \
                detected_visual), [target])
        if target.has_skill("passive sonar") and target.has_ability("passive sonar"):
            bonus = modifiers.noisy_torpedo_bonus_to_passive_sonar_detection
            detected_sonar = roll_skill_check(target, "passive sonar", mods=[target.alert_level.value, bonus])
            self.push_to_console_if_player("[{}] Skill Check (detect torpedo via sonar): {}".format(target.name, \
                detected_sonar), [target])
        if (detected_visual or detected_sonar): 
            winner = min([detected_visual, detected_sonar])
            return winner
        return FAIL_DEFAULT

    def skill_check_detect_nearby_torpedo_launch(self, launcher, target, observer) -> int:
        # NOTE: Covers both visual and passive sonar. Uses the most effective of either roll for the target.
        witness = manhattan_distance(launcher.xy_tuple, observer.xy_tuple) <= RANGE_VISUAL_DETECTION \
            or manhattan_distance(target.xy_tuple, observer.xy_tuple) <= RANGE_VISUAL_DETECTION
        if witness:
            detected_visual, detected_sonar = False, False
            if observer.has_skill("visual detection"):
                penalty = modifiers.torpedo_is_relatively_hard_to_spot
                detected_visual = roll_skill_check(observer, "visual detection", mods=[observer.alert_level.value, \
                    penalty])
                self.push_to_console_if_player("[{}] Skill Check (visually detect torpedo): {}".format(observer.name, \
                    detected_visual), [observer])
            if observer.has_skill("passive sonar") and observer.has_ability("passive sonar"):
                bonus = modifiers.noisy_torpedo_bonus_to_passive_sonar_detection
                detected_sonar = roll_skill_check(observer, "passive sonar", mods=[observer.alert_level.value, bonus])
                self.push_to_console_if_player("[{}] Skill Check (detect torpedo via sonar): {}".format(observer.name, \
                    detected_sonar), [observer])
            if detected_visual or detected_sonar: 
                return min([detected_visual, detected_sonar])
        return FAIL_DEFAULT

    def skill_check_evade_incoming_torpedo(self, launcher, target) -> int:
        bonus = modifiers.pilot_torpedo_against_engaged_target_is_challenging(target.alert_level)
        penalty = modifiers.torpedo_evasion_is_challenging
        contest = roll_skill_contest(launcher, target, "torpedo", "evasive maneuvers", mods_a=[bonus], mods_b=[penalty])
        result = contest["roll"]
        if contest["entity"] is launcher:
            result *= -1
        self.push_to_console_if_player("[{}] Skill Contest (evade torpedo): {}".format(target.name, result), [target]) 
        return result

    def push_to_console_if_player(self, msg, entities):
        if any(filter(lambda x: x.player, entities)):
            self.console.push(msg)
            self.display_changed = True

    def cycle_target(self) -> bool:
        if pygame.key.get_pressed()[K_TAB] and self.targeting_ability is not None:
            targets = self.targets(self.player, self.targeting_ability.type)
            self.targeting_index["current"] = (self.targeting_index["current"] + 1) % self.targeting_index["max"]
            self.camera = targets[self.targeting_index["current"]].xy_tuple
            return True
        return False

    def reset_target_mode(self):
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
            if "missile" in ability.type:
                # can go over land
                in_range = manhattan_distance(entity.xy_tuple, self.player.xy_tuple) <= ability.range
            elif "torpedo" in ability.type:
                # can't go over land (TODO: BFS through water, taking range into account w/ the turns)
                #  ^-- will be same as missiles for first test tho (NOTE)
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
            #self.console.push("{}".format(self.targeting_index))
            return True

    def player_uses_ability(self, key_constant): # NOTE: in progress
        ability_type = list(filter(lambda y: y[0] == key_constant,
            map(lambda x: (x.key_constant, x.type), self.player.abilities)
        ))[0][1] # haha, maybe. awesome. Now we're talkin'. What the heck would I call this, generically? I think it's
                 # kinda unique.
        if ability_type == "short range torpedo":
            if self.enter_target_mode(ability_type):
                self.console.push("target mode: 'f' to fire, TAB to cycle, ESC to return")
        elif ability_type == "passive sonar":
            self.overlay_sonar = not self.overlay_sonar
            self.console.push("displaying passive sonar range: {}".format(self.overlay_sonar))
        # TODO: the rest of 'em

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

    def movement_key_pressed(self): # returns Key constant or False (TODO: type hinting when can be multiple types?)
        if pygame.key.get_pressed()[K_h]: # TODO: I can do a thing with this (refactor if-else chain*)
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
        if self.entity_can_move(entity, direction):
            entity.xy_tuple = (
                entity.xy_tuple[0] + DIRECTIONS[direction][0], 
                entity.xy_tuple[1] + DIRECTIONS[direction][1]
            )
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

