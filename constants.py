from os import path
from pygame.locals import *

TORPEDO_SPEED = 20
TORPEDO_LAUNCH_COST_BASE = 30

VERSION = "0.0.0"

FONT_PATH = path.abspath(path.join(path.dirname(__file__), "./sansation/Sansation-Regular.ttf"))
WINDOW_ICON_PATH = path.abspath(path.join(path.dirname(__file__), "./window_icon.png"))

FPS = 60

HUD_FONT_SIZE = 14

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

