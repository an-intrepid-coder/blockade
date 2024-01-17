import pygame
from pygame.locals import *
from pygame.math import Vector2
from constants import *
from ability import ShortRangeTorpedo, PassiveSonar, ToggleSpeed
from functional import first
from enum import Enum
from alert_level import AlertLevel
from faction import Faction
from rolls import roll_for_initiative
from euclidean import manhattan_distance

speed_modes = ["normal", "fast"]

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
        }
        self.hp = None
        self.dead = False  
        self.contacts = [] 
        self.next_move_time = 0 
        self.speed = None
        self.speed_mode = "normal"
        self.torpedos_incoming = []
        self.missiles_incoming = []

    def toggle_speed(self):
        if self.speed_mode == "normal":
            self.speed_mode = "fast"
        elif self.speed_mode == "fast":
            self.speed_mode = "normal"

    def can_detect_incoming_torpedos(self):
        return self.has_skill("visual detection") or \
            (self.has_skill("passive sonar") and self.has_ability("passive sonar"))

    def change_hp(self, change):
        hp = self.hp["current"] + change
        if hp < 0: hp = 0
        elif hp > self.hp["max"]: hp = self.hp["max"]
        self.hp["current"] = hp
        if hp == 0:
            self.dead = True

    def has_ability(self, ability_type):
        return any(filter(lambda x: x.type == ability_type, self.abilities))

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
        super().__init__(xy_tuple, Faction.FRIENDLY)
        self.image = pygame.Surface((CELL_SIZE, CELL_SIZE))
        self.image.fill("navy")
        pygame.draw.circle(self.image, "green", (CELL_SIZE // 2, CELL_SIZE // 2), CELL_SIZE // 2)
        self.name = "player" # NOTE: temp name
        self.can_ocean_move = True
        self.player = True
        self.abilities = [ShortRangeTorpedo(), PassiveSonar(), ToggleSpeed()]
        # NOTE: tentative values below
        self.skills["stealth"] = 16
        self.skills["passive sonar"] = 13
        self.skills["torpedo"] = 16
        self.skills["missile"] = 16
        self.skills["radar"] = 15
        self.skills["active sonar"] = 16
        self.skills["evasive maneuvers"] = 14  
        self.skills["periscope"] = 14
        self.hp = {"current": 7, "max": 7} 
        self.alert_level = AlertLevel.PREPARED
        self.speed = {"normal": 30, "fast": 20}

class Freighter(Entity):
    # NOTE: This represents a totally unarmed freighter, and not a Q-ship or anything like that. But I will include
    #       such things later.
    def __init__(self, xy_tuple, faction):
        super().__init__(xy_tuple, faction)
        self.image = pygame.Surface((CELL_SIZE, CELL_SIZE))
        self.image.fill("navy")
        pygame.draw.circle(self.image, "red", (CELL_SIZE // 2, CELL_SIZE // 2), CELL_SIZE // 2)
        self.name = "freighter" 
        self.can_ocean_move = True
        self.alert_level = AlertLevel.PREPARED
        # NOTE: tentative values below
        self.skills["visual detection"] = 6
        self.skills["evasive maneuvers"] = 4
        self.hp = {"current": 5, "max": 5} 
        self.speed = {"normal": 30, "fast": 20}

# TODO: many more unit types

