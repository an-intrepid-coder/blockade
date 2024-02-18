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
from sheets import *
from random import randint

wake_causing_entities = [
    "small convoy escort",
    "freighter",
    "heavy convoy escort",
]

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

class HudAlert:
    def __init__(self, surf):
        self.surf = surf
        self.offset = 32
        self.max_offset = 60  
        self.complete = False

    def update(self):
        self.offset += 1
        if self.offset > self.max_offset:
            self.complete = True

class LaunchedWeapon:
    def __init__(self, eta, launcher, target, wep_range, sheet, cell_size, known=False):
        self.eta = eta
        self.sheet = sheet
        self.launcher = launcher
        self.target = target
        self.range = wep_range
        self.gui_alert = False
        self.known = known
        self.animation_vector = pygame.math.Vector2(((launcher.xy_tuple[0] * cell_size) + 5, \
            (launcher.xy_tuple[1] * cell_size) + 5))
        self.animation_complete = False 
        self.frame_index = 0
        self.num_frames = 4
        self.update_count = 0

    def get_drawn(self, zoomed_out=False):
        if zoomed_out:
            img = self.sheet["zoomed out"]["left"][self.frame_index]
        else:
            img = self.sheet["regular"]["left"][self.frame_index]
        self.frame_index = (self.frame_index + 1) % self.num_frames
        return img

class Torpedo(LaunchedWeapon):
    def __init__(self, eta, launcher, target, wep_range, sheet, cell_size, known=False):
        super().__init__(eta, launcher, target, wep_range, sheet, cell_size, known=known)
        self.speed = 1
        self.launch_updates = 100

class Missile(LaunchedWeapon):
    def __init__(self, eta, launcher, target, wep_range, sheet, cell_size, known=False):
        super().__init__(eta, launcher, target, wep_range, sheet, cell_size, known=known)
        self.speed = 2
        self.launch_updates = 40

class Wake:
    def __init__(self, xy_tuple, entity, eta, orientation, sheet):
        self.xy_tuple = xy_tuple
        self.sheet = sheet
        self.orientation = orientation
        self.frame_count = 0
        self.frame_index = 0
        self.num_frames = 4
        self.eta = eta
        self.entity = entity

    def get_drawn(self, zoomed_out=False):
        if zoomed_out:
            img = self.sheet["zoomed out"][self.orientation][self.frame_index]
        else:
            img = self.sheet["regular"][self.orientation][self.frame_index]
        if self.frame_count == 0:
            self.frame_index = (self.frame_index + 1) % self.num_frames
        self.frame_count = (self.frame_count + 1) % ENTITY_FRAME_INDEX_INCREMENT_FREQ
        return img

class Explosion:
    def __init__(self, xy_tuple, sheet):
        self.xy_tuple = xy_tuple
        self.sheet = sheet
        self.done = False
        self.frame_count = 0
        self.frame_index = 0
        self.num_frames = 6

    def get_drawn(self, zoomed_out=False) -> pygame.Surface:
        if not self.done:
            img = grab_cell_from_sheet(self.sheet, self.frame_index)
        else:
            img = grab_cell_from_sheet(self.sheet, self.num_frames - 1)
        self.frame_count = (self.frame_count + 1) % EXPLOSION_FRAME_INDEX_INCREMENT_FREQ
        if self.frame_count == 0:
            self.frame_index = (self.frame_index + 1) % self.num_frames
        if self.frame_index == self.num_frames - 1:
            self.done = True
        if zoomed_out:
            return pygame.transform.scale(img, (ZOOMED_OUT_CELL_SIZE, ZOOMED_OUT_CELL_SIZE))
        return img

class Entity:
    entities = 0
    def __init__(self, xy_tuple, faction, sheet):
        self.xy_tuple = xy_tuple
        self.faction = faction
        self.id = Entity.entities
        Entity.entities += 1
        self.image = None
        self.image_unidentified = None
        self.image_zoomed_out = None
        self.image_zoomed_out_unidentified = None
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
        self.frame_orientation = "left"
        self.next_ability_time = 0
        self.sheet = sheet
        self.frame_index = 0
        self.frame_count = 0
        self.num_frames = 4

    def get_drawn(self, zoomed_out=False) -> pygame.Surface:
        if isinstance(self, CampaignEntity) or self.identified or self.player:
            frame_sheet = self.sheet
        else:
            frame_sheet = self.unid_sheet
        if zoomed_out:
            img = frame_sheet["zoomed out"][self.frame_orientation][self.frame_index]
        else:
            img = frame_sheet["regular"][self.frame_orientation][self.frame_index]
        if self.frame_count == 0:
            self.frame_index = (self.frame_index + 1) % self.num_frames
        self.frame_count = (self.frame_count + 1) % ENTITY_FRAME_INDEX_INCREMENT_FREQ
        return img

    def on_cooldown(self, tu_passed):
        return self.next_ability_time > tu_passed

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

    def change_hp(self, change) -> int:
        damage_taken = None
        if change < 0:
            damage_taken = abs(change)
        hp = self.hp["current"] + change
        if hp < 0: 
            damage_taken -= abs(0 - hp)
            hp = 0
        elif hp > self.hp["max"]: 
            hp = self.hp["max"]
        self.hp["current"] = hp
        if hp == 0:
            self.dead = True
        return damage_taken

class CampaignEntity(Entity):
    def __init__(self, xy_tuple, faction, sheet, hidden=False):
        super().__init__(xy_tuple, faction, sheet)
        self.hidden = hidden

class PlayerCampaignEntity(CampaignEntity):
    def __init__(self, xy_tuple, debug, sheet):
        super().__init__(xy_tuple, "allied", sheet)
        self.name = "PLAYER" # NOTE: temporary value
        self.can_ocean_move = True
        self.player = True
        if debug:
            self.hp = {"current": 2000, "max": 2000}  
        else:
            self.hp = {"current": PLAYER_HP, "max": PLAYER_HP}  
        self.speed = 30
        self.torps = PLAYER_DEFAULT_TORPS
        self.missiles = PLAYER_DEFAULT_MISSILES
        self.orientation = "wait"

class AlliedFleet(CampaignEntity):
    def __init__(self, xy_tuple, sheet):
        super().__init__(xy_tuple, "allied", sheet)
        self.name = "allied fleet"
        self.can_ocean_move = True
        self.hp = 30
        self.speed = 30
        self.engaged = False

    def set_engaged(self, tu=None):
        self.engaged = True

class EnemyFleet(CampaignEntity):
    def __init__(self, xy_tuple, sheet):
        super().__init__(xy_tuple, "enemy", sheet)
        self.name = "enemy fleet"
        self.can_ocean_move = True
        self.hp = 30
        self.speed = 30
        self.engaged = False
        self.engagement_eta = None

    def set_engaged(self, tu=None):
        self.engaged = True
        if tu is not None and self.engagement_eta is None:
            lo, hi = FLEET_ENGAGEMENT_ETA_RANGE
            self.engagement_eta = tu + randint(lo, hi)

class TacticalEntity(Entity): 
    def __init__(self, xy_tuple, faction, sheet, unid_sheet, direction=None, formation=None): 
        super().__init__(xy_tuple, faction, sheet)
        self.unid_sheet = unid_sheet
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
        self.explosion = None

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
        if self.identified or self.player:
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
    def __init__(self, xy_tuple, campaign_entity, sheet): 
        super().__init__(xy_tuple, "allied", sheet, sheet)
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
        self.orientation = "wait"

class EscortSub(TacticalEntity):
    # NOTE: This represents a relatively weak submarine the player might encounter guarding convoys
    def __init__(self, xy_tuple, faction, sheet, unid_sheet, direction=None, formation=None):
        super().__init__(xy_tuple, faction, sheet, unid_sheet, direction=direction, formation=formation)
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
    def __init__(self, xy_tuple, faction, sheet, unid_sheet, direction=None, formation=None):
        super().__init__(xy_tuple, faction, sheet, unid_sheet, direction=direction, formation=formation)
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
    def __init__(self, xy_tuple, faction, sheet, direction=None, formation=None):
        super().__init__(xy_tuple, faction, sheet, sheet, direction=direction, formation=formation)
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
    def __init__(self, xy_tuple, faction, sheet, unid_sheet, direction=None, formation=None):
        super().__init__(xy_tuple, faction, sheet, unid_sheet, direction=direction, formation=formation)
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
    def __init__(self, xy_tuple, faction, sheet, direction=None, formation=None):
        super().__init__(xy_tuple, faction, sheet, sheet, direction=direction, formation=formation)
        self.name = "patrol plane" 
        self.can_ocean_move = True
        self.can_air_move = True
        # NOTE: tentative values below
        self.skills["visual detection"] = 16 
        self.skills["radio"] = 16
        self.skills["radar"] = 16
        self.skills["torpedo"] = 14
        self.hp = {"current": 6, "max": 6} 
        self.speed = 8
        self.abilities = [
            Radar(), 
            ToggleSpeed(),
            ShortRangeTorpedo(ammo=PATROL_PLANE_TORP_AMMO),
            DropSonobuoy(ammo=PATROL_PLANE_SONOBUOY_AMMO),
        ] 
        self.alert_level = AlertLevel.ALERTED
        # NOTE: aircraft are always in fast mode
        self.toggle_speed() 
        self.num_frames = 1

class PatrolHelicopter(TacticalEntity):
    def __init__(self, xy_tuple, faction, mothership, sheet, direction=None, formation=None):
        super().__init__(xy_tuple, faction, sheet, sheet, direction=direction, formation=formation)
        self.name = "patrol helicopter" 
        self.can_ocean_move = True
        self.can_air_move = True
        # NOTE: highly tentative values below
        self.skills["visual detection"] = 16 
        self.skills["radio"] = 15
        self.skills["radar"] = 15
        self.skills["torpedo"] = 14
        self.hp = {"current": 4, "max": 4} 
        self.speed = 10
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
        self.num_frames = 2

class HeavyConvoyEscort(TacticalEntity):
    # NOTE: These are "boss fights", or even to be avoided entirely by the player
    def __init__(self, xy_tuple, faction, sheet, unid_sheet, direction=None, formation=None):
        super().__init__(xy_tuple, faction, sheet, unid_sheet, direction=direction, formation=formation)
        self.name = "heavy convoy escort" 
        self.can_ocean_move = True
        # NOTE: highly tentative values below
        self.skills["visual detection"] = 12
        self.skills["evasive maneuvers"] = 8
        self.skills["radio"] = 14
        self.skills["radar"] = 16
        self.skills["stealth"] = 7
        self.skills["point defense"] = 12
        self.skills["passive sonar"] = 14
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

