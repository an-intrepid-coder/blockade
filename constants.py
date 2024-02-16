from os import path
from pygame.locals import *

SECONDS_PER_TU_CAMPAIGN = 720
MINUTES_PER_TU_CAMPAIGN = SECONDS_PER_TU_CAMPAIGN // 60
SECONDS_PER_TU_TACTICAL = 12

GAME_UPDATE_TICK_MS = 100
CONFIRM_RESET_TICK_MS = 5000
MISSION_OVER_TICK_MS = 20

STARTING_SUBS = 100
STARTING_HEAVY_ESCORTS = 3

SMALL_CONVOY_ESCORTS_PER_SCALE = (2, 4)
SMALL_CONVOY_ESCORT_CHASERS_PER_SCALE = 1 
ESCORT_SUBS_PER_SCALE = (1, 3)
ESCORT_SUB_CHASERS = (0, 2)

FREIGHTERS_PER_SCALE = (1, 6)
ENEMY_SPAWN_FUZZ_BASE = 4

INVALID_DJIKSTRA_SCORE = 99999

WAIT_TU_COST = 5 
LONG_WAIT_TU_COST = 100

# NOTE: physics not entirely to scale, and a bit game-ified. All range values tentative, and will
#       continue to evolve with playtesting.

TORPEDO_RANGE = 9
TORPEDO_SPEED = 20
TORPEDO_LAUNCH_COST_BASE = 30
ORPHANED_TORPEDO_DEFAULT = 11
ROCKET_TORP_RANGE_BONUS = 10

PASSIVE_SONAR_RANGE = 21

RADAR_RANGE = 41

ACTIVE_SONAR_RANGE = 21
ACTIVE_SONAR_TIME_COST = 30
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
MISSILE_RANGE = 61
MISSILE_SPEED = 3  
MISSILE_LAUNCH_COST_BASE = 50 

POINT_DEFENSE_RANGE = 10  

HEAVY_CONVOY_ESCORT_STANDOFF = 10 
HEAVY_ESCORT_TORP_AMMO = 60
PATROL_HELICOPTER_TORP_AMMO = 2
PATROL_PLANE_TORP_AMMO = 2
DEFAULT_TORP_AMMO = 20
DEFAULT_MISSILE_AMMO = 8
PATROL_PLANE_SONOBUOY_AMMO = 30 

SONOBUOY_DIFFUSION_RANGE = PASSIVE_SONAR_RANGE - 3
DEFAULT_SONOBUOY_AMMO = 10 
DROP_SONOBUOY_TARGET = 8 

OFFMAP_ASW_ETA_RANGE = (200, 600) 
INVASION_ETA_RANGE = (600, 1000) 
WARSIM_TILE_CREEP_FREQUENCY_RANGE_ISLAND = 100
WARSIM_TILE_CREEP_FREQUENCY_RANGE_MAINLAND = 50

MISSION_RADIUS = 12 

# NOTE: this will eventually vary by ship type.
MOMENTUM_CAP = 6
MOMENTUM_FACTOR = .05
FAST_MODE_BONUS = 2

VERSION = "0.0.1"

FONT_PATH = path.abspath(path.join(path.dirname(__file__), "./sansation/Sansation-Regular.ttf"))
BOLD_FONT_PATH = path.abspath(path.join(path.dirname(__file__), "./sansation/Sansation-Bold.ttf"))
WINDOW_ICON_PATH = path.abspath(path.join(path.dirname(__file__), "./window_icon.png"))
ALLIED_CITIES_PATH = path.abspath(path.join(path.dirname(__file__), "./images/AlliedCities.png"))
ENEMY_CITIES_PATH = path.abspath(path.join(path.dirname(__file__), "./images/EnemyCities.png"))
ENEMY_FREIGHTER_PATH = path.abspath(path.join(path.dirname(__file__), "./images/EnemyFreighter.png"))
ESCORT_SUB_PATH = path.abspath(path.join(path.dirname(__file__), "./images/EscortSub.png"))
HEAVY_CONVOY_ESCORT_PATH = path.abspath(path.join(path.dirname(__file__), "./images/HeavyConvoyEscort.png"))
LAND_PATH = path.abspath(path.join(path.dirname(__file__), "./images/Land.png"))
NEUTRAL_FREIGHTER_PATH = path.abspath(path.join(path.dirname(__file__), "./images/NeutralFreighter.png"))
OPEN_OCEAN_PATH = path.abspath(path.join(path.dirname(__file__), "./images/OpenOcean.png"))
PATROL_HELICOPTER_PATH = path.abspath(path.join(path.dirname(__file__), "./images/PatrolHelicopter.png"))
PATROL_PLANE_PATH = path.abspath(path.join(path.dirname(__file__), "./images/PatrolPlane.png"))
PLAYER_SUB_PATH = path.abspath(path.join(path.dirname(__file__), "./images/PlayerSub.png")) 
SMALL_CONVOY_ESCORT_PATH = path.abspath(path.join(path.dirname(__file__), "./images/SmallConvoyEscort.png")) 
SONOBUOY_PATH = path.abspath(path.join(path.dirname(__file__), "./images/Sonobuoy.png")) 
ALLIED_FRONT_LINE_PATH = path.abspath(path.join(path.dirname(__file__), "./images/AlliedFrontLine.png")) 
ENEMY_FRONT_LINE_PATH = path.abspath(path.join(path.dirname(__file__), "./images/EnemyFrontLine.png")) 
SMALL_EXPLOSIONS_PATH = path.abspath(path.join(path.dirname(__file__), "./images/SmallExplosions.png")) 
BIG_EXPLOSION_PATH = path.abspath(path.join(path.dirname(__file__), "./images/BigExplosion.png")) 
UNIDENTIFIED_SURFACE_PATH = path.abspath(path.join(path.dirname(__file__), "./images/UnidentifiedSurface.png")) 
UNIDENTIFIED_SUBMERGED_PATH = path.abspath(path.join(path.dirname(__file__), "./images/UnidentifiedSubmerged.png")) 
LOADING_SCREENSHOT_PATH = path.abspath(path.join(path.dirname(__file__), "./images/Loader.jpg")) 
ALLIED_FLEET_PATH = path.abspath(path.join(path.dirname(__file__), "./images/AlliedFleet.png")) 

SEA_TILES_TO_FLIP = 30 
SEA_TILES_TO_FLIP_TU_FREQ = 30 
ENTITY_FRAME_INDEX_INCREMENT_FREQ = 1
EXPLOSION_FRAME_INDEX_INCREMENT_FREQ = 1 
SMALL_EXPLOSIONS_CHECK_TU_FREQ = 2 
EXPLOSION_CHECK_TU_FREQ = 10

FPS = 60

MAX_SONOBUOYS = 32 

HUD_FONT_SIZE = 15
TITLE_FONT_SIZE = 32

CONSOLE_LINES = 8
CONSOLE_PADDING = 4

CELL_SIZE = 32 
ZOOMED_OUT_CELL_SIZE = 16

RANGE_VISUAL_DETECTION = 2

FAIL_DEFAULT = 99
OFFMAP_ASW_CLEAR = -919754

SENSOR_CHECKS_TU_FREQ = 20
ALERT_CHECK_TU_FREQ = 21
CHASE_CHECK_TU_FREQ = 30
OFFMAP_ASW_CHECK_TU_FREQ = 60
UPDATE_MINI_MAP_TU_FREQ = 5

GAME_OVER_CHECK_TU_FREQ = 3
RUN_WARSIM_TU_FREQ = 20
ENCOUNTER_CHECK_TU_FREQ = 21
RESUPPLY_CHECK_TU_FREQ = 22
REPAIR_CHECK_TU_FREQ = 23
EXTRA_LIVES_CHECK_TU_FREQ = 24
DANGER_POINTS_CHECK_TU_FREQ = 25
UPDATE_FRONT_LINES_CHECK_TU_FREQ = 26

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

DIRECTION_TO_COMPASS = {
    "up": "N",
    "down": "S",
    "left": "W", 
    "right": "E", 
    "wait": "-",
    "upleft": "NW", 
    "upright": "NE", 
    "downleft": "SW", 
    "downright": "SE",
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
LAND_COLOR = (19, 149, 26)
ENEMY_SONAR_OVERLAY_COLOR = (40, 89, 0, 40)
TRAFFIC_OVERLAY_COLOR = [0, 220, 0]
OVERLAY_ALPHA_BASE = 80  
OVERLAY_ALPHA_INC = 20  
RADAR_OVERLAY_COLOR = (220, 220, 220, 90)
ALPHA_KEY = (249, 249, 249)

speed_modes = ["normal", "fast"]

factions = ["allied", "enemy", "neutral"]
faction_to_color = {"allied": "cyan", "neutral": "green", "enemy": "red"} 

MAP_SIZE = (300, 300)
MINI_MAP_SIZE = (640, 640)  
BIG_SPLASH_SIZE = (640, 640)  
MM_CELL_SIZE = 4 
CAMPAIGN_MAP_SIZE = (80, 80)

HUD_Y_EGDE_PADDING = 4

PLAYER_HP = 20

# all scores tentative
EXTRA_LIFE_THRESHOLD = 3000
SCORE_FREIGHTER = 100
SCORE_SMALL_CONVOY_ESCORT = 10
SCORE_ESCORT_SUB = 50
SCORE_BOSS = EXTRA_LIFE_THRESHOLD // 2
SCORE_BOSS_PRESENT = 100
SCORE_DIFF_MOD = 20
SCORE_STEALTH_RETAINED = 50
SCORE_HP = -30
SCORE_NEUTRAL_FREIGHTER = -1000
SCORE_ASW_PATROL_SURVIVAL = 500
SCORE_ASW_PATROL_WITH_PLANES = 100
SCORE_MISSION_ZONE = 200

COASTAL_CITY_DIFFUSION_RANGE = (2, 30)
LAND_CITY_DIFFUSION_RANGE = (4, 12)

phases = ["island", "mainland"]

NUM_UNTAKEABLE_CITIES = 3

COLOR_MISSION_HIGHLIGHT = (255, 255, 0)

OFFMAP_ASW_ENCOUNTER_RANGE = 3 

PLAYER_DEFAULT_TORPS = 40
PLAYER_DEFAULT_MISSILES = 12
PLAYER_REPAIR_FREQUENCY = 50 

VICTORY_THRESHOLD = 60 

RESPAWN_TU_COST = 3000

