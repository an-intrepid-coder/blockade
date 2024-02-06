import pygame
from pygame.locals import *
from pygame.math import Vector2
from constants import *
from ability import *
from functional import first
from enum import Enum
from alert_level import AlertLevel, random_starting_alert_level
from euclidean import manhattan_distance
import sort_keys
from unit_tile import *

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

    def copy(self):
        return Contact(self.entity, self.acc)

class LaunchedWeapon:
    def __init__(self, eta, launcher, target, wep_range, known=False):
        self.eta = eta
        self.launcher = launcher
        self.target = target
        self.range = wep_range
        self.gui_alert = False
        self.known = known

class Entity:
    entities = 0
    def __init__(self, xy_tuple, faction):
        self.xy_tuple = tuple(xy_tuple)
        self.faction = faction
        self.id = Entity.entities
        Entity.entities += 1
        self.image = None
        self.can_land_move = False
        self.can_ocean_move = False
        self.can_air_move = False
        self.player = False
        self.hp = None
        self.dead = False  
        self.next_move_time = 0 
        self.speed = None
        self.speed_mode = "normal"
        self.momentum = 0
        self.last_direction = "wait"

    def is_mobile(self):
        # NOTE: this is used in the torpedo detection/evasion logic, so it should also account for things like
        #   damaged engines/screws once those are in as some kind of modifier or status effect.
        return self.can_land_move or self.can_ocean_move or self.can_air_move

    def get_adjusted_speed(self): 
        momentum_factor = self.momentum * MOMENTUM_FACTOR
        return max(int(self.speed - (self.speed * momentum_factor)), 0)

    def toggle_speed(self):
        if self.speed_mode == "normal":
            self.speed_mode = "fast"
        elif self.speed_mode == "fast":
            self.speed_mode = "normal"

    def change_hp(self, change):
        hp = self.hp["current"] + change
        if hp < 0: hp = 0
        elif hp > self.hp["max"]: hp = self.hp["max"]
        self.hp["current"] = hp
        if hp == 0:
            self.dead = True

class CampaignEntity(Entity):
    def __init__(self, xy_tuple, faction, hidden=False):
        super().__init__(xy_tuple, faction)
        self.hidden = hidden

class PlayerCampaignEntity(CampaignEntity):
    def __init__(self, xy_tuple, debug):
        super().__init__(xy_tuple, "allied")
        self.name = "PLAYER" # NOTE: temporary value
        self.image = unit_tile_triangle(faction_to_color[self.faction], upsidedown=True)
        self.can_ocean_move = True
        self.player = True
        if debug:
            self.hp = {"current": 2000, "max": 2000}  
        else:
            self.hp = {"current": PLAYER_HP, "max": PLAYER_HP}  
        self.speed = 30
        self.torps = PLAYER_DEFAULT_TORPS
        self.missiles = PLAYER_DEFAULT_MISSILES

class ResupplyVessel(CampaignEntity):
    def __init__(self, xy_tuple):
        super().__init__(xy_tuple, "allied")
        self.name = "resupply vessel"
        self.image = unit_tile_circle(faction_to_color[self.faction])
        self.can_ocean_move = True
        self.hp = 30
        self.speed = 30

class TacticalEntity(Entity): 
    def __init__(self, xy_tuple, faction, direction=None, formation=None): 
        super().__init__(xy_tuple, faction)
        self.chaser = False
        self.chasing = False
        self.alert_level = random_starting_alert_level()
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
        self.contacts = [] 
        self.torpedos_incoming = []
        self.missiles_incoming = []
        self.submersible = False
        self.direction = direction 
        self.identified = False
        # NOTE: For now, mission scope assumes all enemy entities are in a single "formation". But larger mission types
        #       in future versions will require assigning each unit to a specific formation w/ a specific task.
        self.formation = formation
        self.torp_range_bonus = 0
        self.missile_range_bonus = 0
        self.standoff = None
        self.mothership = None

    def dmg_str(self) -> str:
        if self.hp["current"] == self.hp["max"]:
            return "undamaged"
        return "damaged"

    def known_torpedos(self) -> list:
        return list(filter(lambda x: x.known, self.torpedos_incoming))

    def unknown_torpedos(self) -> list:
        return list(filter(lambda x: not x.known, self.torpedos_incoming))

    def hit_the_gas_if_in_danger(self):
        if self.alert_level.value >= 1 and self.speed_mode == "normal":
            self.toggle_speed()

    def detected_str(self) -> str:
        if self.identified:
            name = self.name
        else:
            name = "unidentified unit"
        return name

    def submersible_emitter(self) -> bool:
        if not self.has_ability("radar") or not self.submersible:
            return False
        return self.submersible and self.get_ability("radar").emerged_to_transmit

    def get_closest_contact(self, hostile_only=False):
        closest = None
        minimum = None
        if hostile_only:
            contacts = self.get_hostile_contacts()
        else:
            contacts = self.contacts
        for contact in contacts:
            d = manhattan_distance(self.xy_tuple, contact.entity.xy_tuple)
            if closest is None:
                closest = contact
                minimum = d
            elif d < minimum:
                closest = contact
                minimum = d
        return closest

    def get_hostile_contacts(self):
        return list(filter(lambda x: x.entity.faction != self.faction and x.entity.faction != "neutral", self.contacts))

    def can_detect_incoming_torpedos(self):
        return self.has_skill("visual detection") or \
            (self.has_skill("passive sonar") and self.has_ability("passive sonar"))

    def can_detect_incoming_missiles(self):
        return self.has_skill("visual detection") or (self.has_skill("radar") and self.has_ability("radar"))

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

class PlayerSub(TacticalEntity):
    def __init__(self, xy_tuple, campaign_entity): 
        super().__init__(xy_tuple, "allied")
        self.image = unit_tile_triangle(faction_to_color[self.faction], upsidedown=True)
        self.can_ocean_move = True
        self.name = campaign_entity.name
        self.player = True
        self.abilities = [
            ShortRangeTorpedo(ammo=campaign_entity.torps), 
            PassiveSonar(), 
            ActiveSonar(),
            ToggleSpeed(), 
            Radar(), 
            ShortRangeMissile(ammo=campaign_entity.missiles)
        ]
        # NOTE: tentative values below
        self.skills["stealth"] = 18 
        self.skills["passive sonar"] = 13
        self.skills["torpedo"] = 15
        self.skills["missile"] = 15
        self.skills["radar"] = 14
        self.skills["active sonar"] = 17
        self.skills["evasive maneuvers"] = 14  
        self.skills["periscope"] = 14
        self.skills["radio"] = 15
        self.hp = campaign_entity.hp
        self.alert_level = AlertLevel.PREPARED
        self.speed = campaign_entity.speed
        self.submersible = True
        self.abilities.sort(key=sort_keys.abilities)

class EscortSub(TacticalEntity):
    # NOTE: This represents a relatively weak submarine the player might encounter guarding convoys
    def __init__(self, xy_tuple, faction, direction=None, formation=None):
        super().__init__(xy_tuple, faction, direction=direction, formation=formation)
        self.image = unit_tile_triangle(faction_to_color[self.faction], upsidedown=True)
        self.name = "escort sub"  
        self.can_ocean_move = True
        self.abilities = [
            ShortRangeTorpedo(), 
            PassiveSonar(), 
            ToggleSpeed(),
            ActiveSonar(),
        ]
        # NOTE: tentative values below
        self.skills["stealth"] = 14
        self.skills["passive sonar"] = 11
        self.skills["torpedo"] = 12
        self.skills["active sonar"] = 12
        self.skills["evasive maneuvers"] = 12
        self.skills["periscope"] = 12
        self.skills["radio"] = 12
        self.hp = {"current": 7, "max": 7} 
        self.speed = 35
        self.submersible = True

class Freighter(TacticalEntity):
    # NOTE: This represents a totally unarmed freighter, and not a Q-ship or anything like that. But I will include
    #       such things later.
    def __init__(self, xy_tuple, faction, direction=None, formation=None):
        super().__init__(xy_tuple, faction, direction=direction, formation=formation)
        self.image = unit_tile_circle(faction_to_color[self.faction])
        self.name = "freighter" 
        self.can_ocean_move = True
        # NOTE: tentative values below
        self.skills["visual detection"] = 10
        self.skills["evasive maneuvers"] = 4
        self.skills["radio"] = 11
        self.skills["stealth"] = 5
        self.hp = {"current": 5, "max": 5} 
        self.speed = 35
        self.abilities = [
            ToggleSpeed(),
        ]

class Sonobuoy(TacticalEntity):
    def __init__(self, xy_tuple, faction, direction=None, formation=None):
        super().__init__(xy_tuple, faction, direction=direction, formation=formation)
        self.image = unit_tile_circle(faction_to_color[self.faction], hollow=True)
        self.name = "sonobuoy" 
        self.identified = True
        self.can_ocean_move = True
        # NOTE: tentative values below
        self.skills["radio"] = 16
        self.skills["stealth"] = 4
        self.skills["passive sonar"] = 11 # tentative
        self.hp = {"current": 4, "max": 4} 
        self.speed = FAIL_DEFAULT
        self.abilities = [
            PassiveSonar(), 
        ] 

class SmallConvoyEscort(TacticalEntity):
    def __init__(self, xy_tuple, faction, direction=None, formation=None):
        super().__init__(xy_tuple, faction, direction=direction, formation=formation)
        self.image = unit_tile_triangle(faction_to_color[self.faction])
        self.name = "small convoy escort" 
        self.can_ocean_move = True
        # NOTE: tentative values below
        self.skills["visual detection"] = 12
        self.skills["evasive maneuvers"] = 11
        self.skills["radio"] = 14
        self.skills["radar"] = 14
        self.skills["stealth"] = 8
        self.skills["point defense"] = 10
        self.skills["passive sonar"] = 13
        self.skills["torpedo"] = 13
        self.skills["active sonar"] = 14
        self.hp = {"current": 10, "max": 10} 
        self.speed = 35
        self.abilities = [
            Radar(), 
            PassiveSonar(), 
            ToggleSpeed(),
            ShortRangeTorpedo(),
            ActiveSonar(),
        ] 

class PatrolPlane(TacticalEntity):
    def __init__(self, xy_tuple, faction, direction=None, formation=None):
        super().__init__(xy_tuple, faction, direction=direction, formation=formation)
        self.image = unit_tile_cross(faction_to_color[self.faction])
        self.name = "patrol plane" 
        self.can_ocean_move = True
        self.can_air_move = True
        # NOTE: tentative values below
        self.skills["visual detection"] = 16 
        self.skills["radio"] = 16
        self.skills["radar"] = 16
        self.skills["torpedo"] = 14
        self.hp = {"current": 6, "max": 6} 
        self.speed = 10
        self.abilities = [
            Radar(), 
            ToggleSpeed(),
            ShortRangeTorpedo(),
            DropSonobuoy(ammo=PATROL_PLANE_SONOBUOY_AMMO),
        ] 
        self.alert_level = AlertLevel.ALERTED
        # NOTE: aircraft are always in fast mode
        self.toggle_speed() 

class PatrolHelicopter(TacticalEntity):
    def __init__(self, xy_tuple, faction, mothership, direction=None, formation=None):
        super().__init__(xy_tuple, faction, direction=direction, formation=formation)
        self.image = unit_tile_cross(faction_to_color[self.faction])
        self.name = "patrol helicopter" 
        self.can_ocean_move = True
        self.can_air_move = True
        # NOTE: highly tentative values below
        self.skills["visual detection"] = 16 
        self.skills["radio"] = 15
        self.skills["radar"] = 15
        self.skills["torpedo"] = 14
        self.hp = {"current": 4, "max": 4} 
        self.speed = 12 
        self.mothership = mothership
        self.map_to_mothership = None
        self.abilities = [
            Radar(), 
            ToggleSpeed(),
            ShortRangeTorpedo(ammo=PATROL_HELICOPTER_TORP_AMMO),
            DropSonobuoy(),
        ] 
        self.chaser = True
        self.alert_level = AlertLevel.ALERTED
        # NOTE: aircraft are always in fast mode
        self.toggle_speed() 
        # NOTE: patrol helicopters begin with good copies of all mothership contacts
        self.contacts = [contact.copy() for contact in mothership.contacts] 

class HeavyConvoyEscort(TacticalEntity):
    # NOTE: These are "boss fights", or even to be avoided entirely by the player
    def __init__(self, xy_tuple, faction, direction=None, formation=None):
        super().__init__(xy_tuple, faction, direction=direction, formation=formation)
        self.image = unit_tile_triangle(faction_to_color[self.faction])
        self.name = "heavy convoy escort" 
        self.can_ocean_move = True
        # NOTE: highly tentative values below
        self.skills["visual detection"] = 12
        self.skills["evasive maneuvers"] = 8
        self.skills["radio"] = 14
        self.skills["radar"] = 16
        self.skills["stealth"] = 7
        self.skills["point defense"] = 12
        self.skills["passive sonar"] = 13
        self.skills["torpedo"] = 15
        self.skills["active sonar"] = 14
        self.hp = {"current": 30, "max": 30} 
        self.speed = 35
        self.abilities = [
            Radar(), 
            PassiveSonar(), 
            ToggleSpeed(),
            ShortRangeTorpedo(ammo=HEAVY_ESCORT_TORP_AMMO),
            ActiveSonar(),
            LaunchHelicopter(),
        ] 
        self.torp_range_bonus = ROCKET_TORP_RANGE_BONUS
        self.standoff = HEAVY_CONVOY_ESCORT_STANDOFF
        self.last_xy = None

