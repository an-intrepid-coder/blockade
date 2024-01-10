from pygame.locals import *

ability_types = [ # NOTE: I may do away with the various distinctions between ranged types, and rely entirely on the
                  #   range variable in the class. Probably will before implementing missiles.
    "short range torpedo",
    "medium range torpedo",
    "long range torpedo",
    "short range missile",
    "long range missile",
    "short range radar",
    "long range radar",
    "passive sonar",
    "active sonar",
    "intel report", # NOTE: Will show a variety of stats/overlays for a target, based on known intel 
                    #       ^ (maybe a few of these, one for a stat block and one for each overlay) (start w/ stat block)
] 

class Ability:
    def __init__(self):
        self.targets_other = False
        self.targets_self = False
        self.range = None

class ShortRangeTorpedo(Ability):
    def __init__(self):  # NOTE: this is basically a melee attack with limited ammo
        super().__init__()
        self.type = "short range torpedo"
        self.ammo = 20 # NOTE: tentative
        self.range = 3 # NOTE: tentative
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

