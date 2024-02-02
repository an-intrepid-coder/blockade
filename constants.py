from os import path
from pygame.locals import *

SMALL_CONVOY_ESCORTS_PER_SCALE = (2, 4)
SMALL_CONVOY_ESCORT_CHASERS_PER_SCALE = 1 # tentative
ESCORT_SUBS_PER_SCALE = (1, 3)
ESCORT_SUB_CHASERS = (0, 2)

FREIGHTERS_PER_SCALE = (1, 6)
ENEMY_SPAWN_FUZZ_BASE = 4

INVALID_DJIKSTRA_SCORE = 99999

WAIT_TU_COST = 5 
LONG_WAIT_TU_COST = 100

# NOTE: physics not entirely to scale, and a bit game-ified. All range values tentative, and will
#       continue to evolve with playtesting.

TORPEDO_RANGE = 6
TORPEDO_SPEED = 20
TORPEDO_LAUNCH_COST_BASE = 30
ORPHANED_TORPEDO_DEFAULT = 11
ROCKET_TORP_RANGE_BONUS = 10

PASSIVE_SONAR_RANGE = 19

RADAR_RANGE = 40

ACTIVE_SONAR_RANGE = 19
ACTIVE_SONAR_TIME_COST = 5
ASONAR_USE_TARGET_ALERTED = 9
ASONAR_USE_TARGET_UNALERTED = 5

CONTACT_ACC_ID_THRESHOLD = 100 
INITIAL_ACC_LOSS_PER_DISTANCE_UNIT = 10
INITIAL_ACC_PENALTY_SUBMERSIBLE = 10
INITIAL_ACC_BONUS_ACTIVE = 30
INITIAL_ACC_BONUS_ROLL_FACTOR = 3
INITIAL_ACC_BONUS_ALERT_FACTOR = 5
INITIAL_ACC_BONUS_FAST_MODE = 10

# NOTE: Missiles can target contacts in another unit's radar umbrella
MISSILE_RANGE = 60
MISSILE_SPEED = 3  
MISSILE_LAUNCH_COST_BASE = 50 

POINT_DEFENSE_RANGE = 10  

HEAVY_CONVOY_ESCORT_STANDOFF = 10 # tentative
HEAVY_ESCORT_TORP_AMMO = 60
PATROL_HELICOPTER_TORP_AMMO = 2
DEFAULT_TORP_AMMO = 20
DEFAULT_MISSILE_AMMO = 8
PATROL_PLANE_SONOBUOY_AMMO = 30 # tentative

SONOBUOY_DIFFUSION_RANGE = PASSIVE_SONAR_RANGE - 3
DEFAULT_SONOBUOY_AMMO = 10 # tentative
DROP_SONOBUOY_TARGET = 8 # tentative

OFFMAP_ASW_ETA_RANGE = (200, 600) # tentative
INVASION_ETA_RANGE = (1500, 3000) # tentative

MISSION_RADIUS = 8 # tentative

# NOTE: this will eventually vary by ship type.
MOMENTUM_CAP = 6
MOMENTUM_FACTOR = .05
FAST_MODE_BONUS = 2

VERSION = "0.0.0"

FONT_PATH = path.abspath(path.join(path.dirname(__file__), "./sansation/Sansation-Regular.ttf"))
WINDOW_ICON_PATH = path.abspath(path.join(path.dirname(__file__), "./window_icon.png"))

FPS = 60

MAX_SONOBUOYS = 32 

HUD_FONT_SIZE = 15

CONSOLE_LINES = 8
CONSOLE_PADDING = 4

CELL_SIZE = 32 

RANGE_VISUAL_DETECTION = 2

FAIL_DEFAULT = 99
OFFMAP_ASW_CLEAR = -999

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

HUD_OPAQUE_BLACK = (0, 0, 0, 120)
HUD_OPAQUE_RED = (255, 0, 0, 120)
SONAR_OVERLAY_COLOR = (0, 220, 220, 90)
ENEMY_SONAR_OVERLAY_COLOR = [229, 189, 26]
ENEMY_SONAR_OVERLAY_ALPHA_BASE = 80
ENEMY_SONAR_OVERLAY_ALPHA_INC = 20
RADAR_OVERLAY_COLOR = (220, 220, 220, 90)
ALPHA_KEY = (249, 249, 249)

speed_modes = ["normal", "fast"]

factions = ["allied", "enemy", "neutral"]
faction_to_color = {"allied": "cyan", "neutral": "green", "enemy": "red"} 

MAP_SIZE = (300, 300)
MINI_MAP_SIZE = (640, 640)  
BIG_SPLASH_SIZE = (640, 640)  
MM_CELL_SIZE = 4 
CAMPAIGN_MAP_SIZE = (60, 60)

HUD_Y_EGDE_PADDING = 4

PLAYER_HP = 20

SCORE_FREIGHTER = 100
SCORE_SMALL_CONVOY_ESCORT = 10
SCORE_ESCORT_SUB = 20
SCORE_BOSS = 1000
SCORE_BOSS_PRESENT = 100
SCORE_DIFF_MOD = 20
SCORE_STEALTH_RETAINED = 50
SCORE_HP = -50
SCORE_NEUTRAL_FREIGHTER = -1000

COASTAL_CITY_DIFFUSION_RANGE = (2, 30)
LAND_CITY_DIFFUSION_RANGE = (4, 12)

phases = ["island", "mainland"]

NUM_UNTAKEABLE_CITIES = 3

