from pygame.locals import *
from constants import *

ability_types = [ 
    "torpedo",
    "missile", 
    "radar", 
    "passive sonar",
    "active sonar", # TODO
    "intel report", # TODO
] 

class Ability:
    def __init__(self):
        self.targets_other = False
        self.targets_self = False
        self.range = None

class ToggleSpeed(Ability):
    def __init__(self):  
        self.targets_self = True
        self.type = "toggle speed"
        self.key_literal = "7"
        self.key_constant = K_7

    def draw_str(self):
        return "{}: toggle speed".format(self.key_literal)

class ShortRangeTorpedo(Ability):
    def __init__(self):  
        super().__init__()
        self.type = "torpedo"
        self.ammo = 20 # NOTE: tentative
        self.range = TORPEDO_RANGE # NOTE: tentative
        self.targets_other = True
        self.key_literal = "1"
        self.key_constant = K_1
    
    def draw_str(self):
        return "{}: torpedo (x{})".format(self.key_literal, self.ammo)

class ShortRangeMissile(Ability):
    def __init__(self):
        super().__init__()
        self.type = "missile"
        self.ammo = 8 # NOTE: tentative
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

