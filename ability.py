from pygame.locals import *
from constants import *

ability_types = [ 
    "torpedo",
    "missile", 
    "radar", 
    "passive sonar",
    "active sonar", 
] 

class Ability:
    def __init__(self):
        self.targets_other = False
        self.targets_self = False
        self.range = None
        self.ammo = None

    def change_ammo(self, amt): 
        self.ammo = self.ammo + amt
        if self.ammo < 0:
            self.ammo = 0

# NOTE: In the future, I may allow the player to control some surface vessels and use some of these
#       AI-only abilities.

class DropSonobuoy(Ability):
    def __init__(self, ammo=DEFAULT_SONOBUOY_AMMO):
        self.type = "drop sonobuoy"
        self.ammo = ammo

class LaunchHelicopter(Ability):
    def __init__(self):  
        self.type = "launch helicopter"
        self.ammo = 1

class ToggleSpeed(Ability):
    def __init__(self):  
        self.targets_self = True
        self.type = "toggle speed"
        self.key_literal = "7"
        self.key_constant = K_7

    def draw_str(self):
        return "{}: toggle speed".format(self.key_literal)

class ShortRangeTorpedo(Ability):
    def __init__(self, ammo=DEFAULT_TORP_AMMO):  
        super().__init__()
        self.type = "torpedo"
        self.ammo = ammo
        self.range = TORPEDO_RANGE 
        self.targets_other = True
        self.key_literal = "1"
        self.key_constant = K_1
    
    def draw_str(self):
        return "{}: torpedo (x{})".format(self.key_literal, self.ammo)

class ShortRangeMissile(Ability):
    def __init__(self, ammo=DEFAULT_MISSILE_AMMO):
        super().__init__()
        self.type = "missile"
        self.ammo = ammo
        self.range = MISSILE_RANGE
        self.targets_other = True
        self.key_literal = "2"
        self.key_constant = K_2

    def draw_str(self):
        return "{}: missile (x{})".format(self.key_literal, self.ammo)

class PassiveSonar(Ability):
    def __init__(self): 
        super().__init__()
        self.type = "passive sonar"
        self.range = PASSIVE_SONAR_RANGE
        self.key_literal = "0" 
        self.key_constant = K_0
    
    def draw_str(self):
        return "{}: passive sonar".format(self.key_literal)

class ActiveSonar(Ability):
    def __init__(self):
        super().__init__()
        self.type = "active sonar"
        self.range = ACTIVE_SONAR_RANGE
        self.key_literal = "8"
        self.key_constant = K_8

    def draw_str(self):
        return "{}: active sonar".format(self.key_literal)

class Radar(Ability):
    def __init__(self):
        super().__init__()
        self.type = "radar"
        self.range = RADAR_RANGE
        self.key_literal = "9"
        self.key_constant = K_9
        self.emerged_to_transmit = False
    
    def draw_str(self):
        return "{}: radar".format(self.key_literal)

