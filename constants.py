from os import path
from pygame.locals import *

WAIT_TU_COST = 5 # for now

# NOTE: physics not entirely to scale, and a bit game-ified

TORPEDO_RANGE = 6
TORPEDO_SPEED = 20
TORPEDO_LAUNCH_COST_BASE = 30

PASSIVE_SONAR_RANGE = 12

ACTIVE_SONAR_RANGE = 8
ACTIVE_SONAR_TIME_COST = 5

RADAR_RANGE = 20

# NOTE: Missiles can target contacts in another unit's radar umbrella
MISSILE_RANGE = 30
MISSILE_SPEED = 6  
MISSILE_LAUNCH_COST_BASE = 50 # NOTE: tentative 

POINT_DEFENSE_RANGE = 10  # NOTE: tentative

# NOTE: this will eventually vary by ship type.
#       for now, all capped at effectively 30% speed boost
MOMENTUM_CAP = 6
MOMENTUM_FACTOR = .05
FAST_MODE_BONUS = 2

VERSION = "0.0.0"

FONT_PATH = path.abspath(path.join(path.dirname(__file__), "./sansation/Sansation-Regular.ttf"))
WINDOW_ICON_PATH = path.abspath(path.join(path.dirname(__file__), "./window_icon.png"))

FPS = 60

HUD_FONT_SIZE = 15

CONSOLE_LINES = 6

CELL_SIZE = 32 

RANGE_VISUAL_DETECTION = 2

FAIL_DEFAULT = 99

DIRECTIONS = { 
    "up": (0, -1), 
    "down": (0, 1), 
    "left": (-1, 0), 
    "right": (1, 0), 
    "wait": (0, 0),
    "upleft": (-1, -1), 
    "upright": (1, -1), 
    "downleft": (-1, 1), 
    "downright": (1, 1),
}

KEY_TO_DIRECTION = {
    K_h: "left",  
    K_j: "down",
    K_k: "up",
    K_l: "right", 
    K_y: "upleft",
    K_u: "upright",
    K_b: "downleft",
    K_n: "downright",
    K_PERIOD: "wait",
}

HUD_OPAQUE_BLACK = (0, 0, 0, 170)
HUD_OPAQUE_RED = (255, 0, 0, 170)
ALPHA_KEY = (249, 249, 249)

speed_modes = ["normal", "fast"]

factions = ["allied", "enemy", "neutral"]
faction_to_color = {"allied": "cyan", "neutral": "green", "enemy": "red"} 

stealth_levels = ["hidden", "caution", "alert"]

