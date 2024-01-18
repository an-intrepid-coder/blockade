from pygame.locals import *

ability_types = [ 
    "torpedo",
    "missile", # TODO
    "radar", # NOTE: in progress
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
        self.range = 6 # NOTE: tentative
        self.targets_other = True
        self.key_literal = "1"
        self.key_constant = K_1
    
    def draw_str(self):
        return "{}: torpedo (x{})".format(self.key_literal, self.ammo)

class PassiveSonar(Ability):
    def __init__(self): 
        super().__init__()
        self.type = "passive sonar"
        self.range = 12
        self.key_literal = "0" 
        self.key_constant = K_0
    
    def draw_str(self):
        return "{}: passive sonar".format(self.key_literal)

class Radar(Ability):
    def __init__(self):
        super().__init__()
        self.type = "radar"
        self.range = 20
        self.key_literal = "9"
        self.key_constant = K_9
    
    def draw_str(self):
        return "{}: radar".format(self.key_literal)

