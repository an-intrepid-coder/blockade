import pygame
from pygame.locals import *
from pygame.math import Vector2
from constants import *
from ability import *
from functional import first
from enum import Enum
from alert_level import AlertLevel
from rolls import roll_for_initiative
from euclidean import manhattan_distance

class Contact: 
    def __init__(self, entity, acc):
        self.entity = entity
        self.acc = acc

    def change_acc(self, amt):
        self.acc = self.acc + amt
        if self.acc < 0:
            self.acc = 0
        elif self.acc > 100:
            self.acc = 100

class LaunchedWeapon:
    def __init__(self, eta, launcher, target, wep_range):
        self.eta = eta
        self.launcher = launcher
        self.target = target
        self.range = wep_range

class Entity: 
    def __init__(self, xy_tuple, faction): 
        self.faction = faction
        self.xy_tuple = tuple(xy_tuple)
        self.image = None
        self.can_land_move = False
        self.can_ocean_move = False
        self.can_air_move = False
        self.player = False
        self.alert_level = None 
        self.abilities = [] 
        self.skills = {
            # NOTE: A single skill can be used for multiple abilities
            "stealth": None,
            "passive sonar": None,
            "torpedo": None,
            "missile": None,
            "radar": None,
            "active sonar": None,
            "visual detection": None,
            # NOTE: Visual detection refers to a crew observing something from the deck, and not to periscope,
            #       which is a separate skill.
            "evasive maneuvers": None,
            "periscope": None,
            "radio": None,
            # NOTE: there will be more kinds of point defense, and an Ability or two which use it, down the road.
            "point defense": None,
        }
        self.hp = None
        self.dead = False  
        self.contacts = [] 
        self.next_move_time = 0 
        self.speed = None
        self.speed_mode = "normal"
        self.torpedos_incoming = []
        self.missiles_incoming = []
        self.momentum = 0
        self.last_direction = "wait"
        self.submersible = False

    def get_adjusted_speed(self): 
        momentum_factor = self.momentum * MOMENTUM_FACTOR
        return max(int(self.speed - (self.speed * momentum_factor)), 0)

    def toggle_speed(self):
        if self.speed_mode == "normal":
            self.speed_mode = "fast"
        elif self.speed_mode == "fast":
            self.speed_mode = "normal"

    def can_detect_incoming_torpedos(self):
        return self.has_skill("visual detection") or \
            (self.has_skill("passive sonar") and self.has_ability("passive sonar"))

    def can_detect_incoming_missiles(self):
        return self.has_skill("visual detection") or (self.has_skill("radar") and self.has_ability("radar"))

    def change_hp(self, change):
        hp = self.hp["current"] + change
        if hp < 0: hp = 0
        elif hp > self.hp["max"]: hp = self.hp["max"]
        self.hp["current"] = hp
        if hp == 0:
            self.dead = True

    def has_ability(self, ability_type):
        return first(lambda x: x.type == ability_type, self.abilities) is not None

    def get_ability(self, ability_type):
        return first(lambda x: x.type == ability_type, self.abilities)

    def has_skill(self, skill): 
        return self.skills[skill] is not None

    # Raises the alert level to the desired one, if lower. If higher, leaves it as-is.
    def raise_alert_level(self, alert_level):
        if self.alert_level is None:
            return
        if self.alert_level.value < alert_level.value:
            self.alert_level = alert_level

    def is_mobile(self):
        # NOTE: this is used in the torpedo detection/evasion logic, so it should also account for things like
        #   damaged engines/screws once those are in as some kind of modifier or status effect.
        return self.can_land_move or self.can_ocean_move or self.can_air_move

class Player(Entity):
    def __init__(self, xy_tuple): 
        super().__init__(xy_tuple, "allied")
        self.image = pygame.Surface((CELL_SIZE, CELL_SIZE))
        self.image.set_colorkey(ALPHA_KEY)
        self.image.fill(ALPHA_KEY)
        pygame.draw.circle(self.image, faction_to_color[self.faction], (CELL_SIZE // 2, CELL_SIZE // 2), CELL_SIZE // 3)
        self.name = "PLAYER" # NOTE: temporary value
        self.can_ocean_move = True
        self.player = True
        self.abilities = [ShortRangeTorpedo(), PassiveSonar(), ToggleSpeed(), Radar(), ShortRangeMissile()]
        # NOTE: tentative values below
        self.skills["stealth"] = 16
        self.skills["passive sonar"] = 13
        self.skills["torpedo"] = 15
        self.skills["missile"] = 15
        self.skills["radar"] = 14
        self.skills["active sonar"] = 15
        self.skills["evasive maneuvers"] = 14  
        self.skills["periscope"] = 14
        self.skills["radio"] = 15
        self.hp = {"current": 7, "max": 7} 
        self.alert_level = AlertLevel.PREPARED
        self.speed = 30
        self.submersible = True

class Freighter(Entity):
    # NOTE: This represents a totally unarmed freighter, and not a Q-ship or anything like that. But I will include
    #       such things later.
    def __init__(self, xy_tuple, faction):
        super().__init__(xy_tuple, faction)
        self.image = pygame.Surface((CELL_SIZE, CELL_SIZE))
        self.image.set_colorkey(ALPHA_KEY)
        self.image.fill(ALPHA_KEY)
        pygame.draw.circle(self.image, faction_to_color[faction], (CELL_SIZE // 2, CELL_SIZE // 2), CELL_SIZE // 3)
        self.name = "freighter" 
        self.can_ocean_move = True
        self.alert_level = AlertLevel.PREPARED
        # NOTE: tentative values below
        self.skills["visual detection"] = 10
        self.skills["evasive maneuvers"] = 4
        self.skills["radio"] = 11
        self.skills["stealth"] = 5
        self.hp = {"current": 5, "max": 5} 
        self.speed = 35

class Escort(Entity):
    def __init__(self, xy_tuple, faction):
        super().__init__(xy_tuple, faction)
        self.image = pygame.Surface((CELL_SIZE, CELL_SIZE))
        self.image.set_colorkey(ALPHA_KEY)
        self.image.fill(ALPHA_KEY)
        pygame.draw.circle(self.image, faction_to_color[faction], (CELL_SIZE // 2, CELL_SIZE // 2), CELL_SIZE // 3)
        self.name = "escort" 
        self.can_ocean_move = True
        self.alert_level = AlertLevel.PREPARED
        # NOTE: tentative values below
        self.skills["visual detection"] = 12
        self.skills["evasive maneuvers"] = 10
        self.skills["radio"] = 14
        self.skills["radar"] = 13
        self.skills["stealth"] = 8
        self.skills["point defense"] = 10
        self.skills["passive sonar"] = 13
        self.hp = {"current": 10, "max": 10} 
        self.speed = 35
        self.abilities = [Radar(), PassiveSonar()]

# TODO: many more unit types

