from functional import *
from euclidean import *
from constants import *
from random import choice, randint, randrange, shuffle
import heapq

tile_types = ["ocean", "land", "mountain", "river", "city", "forest"] 

def sorted_by_distance_to(xy_tuple, tiles_ls, distance_fn):
    sorted_ls = []
    entry_count = 0
    for tile in tiles_ls:
        d = distance_fn(xy_tuple, tile.xy_tuple)
        item = [d, entry_count, tile]
        heapq.heappush(sorted_ls, item)
        entry_count += 1
    return sorted_ls 

def is_edge(wh_tuple, xy_tuple) -> bool:
    x, y = xy_tuple
    w, h = wh_tuple
    return x == w - 1 or y == h - 1 or x == 0 or y == 0

def in_bounds(xy_tuple, wh_tuple) -> bool:
    x, y = xy_tuple
    w, h = wh_tuple
    return x >= 0 and y >= 0 and x < h and y < w

def valid_tiles_in_range_of(tiles_ls, xy_tuple, d, manhattan=False) -> list: 
    w, h = len(tiles_ls[0]), len(tiles_ls)
    locs = []
    for x in range(xy_tuple[0] - d, xy_tuple[0] + d + 1):
        for y in range(xy_tuple[1] - d, xy_tuple[1] + d + 1):
            if manhattan:
                valid = in_bounds((x, y), (w, h)) and manhattan_distance((x, y), xy_tuple) <= d
            else:
                valid = in_bounds((x, y), (w, h)) and chebyshev_distance((x, y), xy_tuple) <= d
            if valid:
                locs.append(tiles_ls[x][y])
    return locs 

class Tile:
    def __init__(self, xy_tuple, tile_type):
        self.xy_tuple = xy_tuple
        self.tile_type = tile_type
        self.occupied = False 
        self.mainland = False
        self.coast = False
        self.island = False
        self.contiguous_ocean = False
        self.exclusion_zone = False
        self.faction = None
        self.untakeable_city = False
        self.sea_route_node = False
        self.logistical_sea_route = False
        self.active_front = False

geography_types = ["campaign", "open ocean", "coastline", "bay", "peninsula", "archipelago", "inland sea"]

# Generates a very small but very specific map in a variety of possible orientations, with each tile
# representing many more miles^2 than on the tactical maps.
def gen_campaign_map(wh_tuple) -> tuple: 
    w, h = wh_tuple
    orientation = choice(["upright", "upleft", "downright", "downleft"]) 
    if orientation == "upright":
        opposite = (w - 1, 0)
    elif orientation == "upleft":
        opposite = (0, 0)
    elif orientation == "downright":
        opposite = (w - 1, h - 1)
    elif orientation == "downleft":
        opposite = (0, h - 1)
    tiles = []
    mainland_coastal_city_tiles = []
    island_coastal_city_tiles = []
    def neighbors(tile_xy) -> list:
        neighbors = []
        for k, v in DIRECTIONS.items():
            if k == "wait":
                continue
            x, y = tile_xy[0] + v[0], tile_xy[1] + v[1]
            if in_bounds((x, y), wh_tuple):
                neighbors.append(tiles[x][y])
        return neighbors
    # starting with just ocean
    for x in range(w):
        tiles.append([])
        for y in range(h):
            tiles[x].append(Tile((x, y), "ocean"))
            if chebyshev_distance(opposite, (x, y)) < 10:
                tiles[x][y].exclusion_zone = True
    land_margin = min(wh_tuple) // 5
    # anchor point #1
    if orientation == "upright" or orientation == "downright":
        anchor_1_range = (0, land_margin)
    elif orientation == "upleft" or orientation == "downleft":
        anchor_1_range = (w - land_margin, w - 1)
    # anchor point #2
    if orientation == "upright" or orientation == "upleft":
        anchor_2_range = (h - land_margin, h - 1)
    if orientation == "downright" or orientation == "downleft":
        anchor_2_range = (0, land_margin)
    # Bend anchor point 
    if orientation == "upright":
        bend_rect = (0, h - land_margin, land_margin, land_margin)
    elif orientation == "upleft":
        bend_rect = (w - land_margin, h - land_margin, land_margin, land_margin)
    elif orientation == "downright":
        bend_rect = (0, 0, land_margin, land_margin)
    elif orientation == "downleft":
        bend_rect = (w - land_margin, 0, land_margin, land_margin)
    # select anchor points from their ranges
    if orientation == "upright" or orientation == "upleft":
        anchor_point_1 = (randint(anchor_1_range[0], anchor_1_range[1]), 0)
    elif orientation == "downright" or orientation == "downleft":
        anchor_point_1 = (randint(anchor_1_range[0], anchor_1_range[1]), h - 1)
    if orientation == "upright" or orientation == "downright":
        anchor_point_2 = (w - 1, randint(anchor_2_range[0], anchor_2_range[1]))
    elif orientation == "upleft" or orientation == "downleft":
        anchor_point_2 = (0, randint(anchor_2_range[0], anchor_2_range[1]))
    bend_point = (randint(bend_rect[0], bend_rect[0] + bend_rect[2]), randint(bend_rect[1], bend_rect[1] + bend_rect[3]))
    max_walk_deviation = 30 
    # the first walk (vertical)
    if orientation == "upright" or orientation == "upleft":
        walk_start = anchor_point_1
        walk_end = bend_point
    elif orientation == "downright" or orientation == "downleft":
        walk_start = bend_point
        walk_end = anchor_point_1
    current_x = walk_start[0]
    for y in range(walk_start[1], walk_end[1] + 1):
        if y < h:
            if orientation == "upright" or orientation == "downright":
                land_range = range(0, current_x + 1) 
            elif orientation == "upleft" or orientation == "downleft":
                land_range = range(current_x, w) 
            for x in land_range:
                tiles[x][y].tile_type = "land"
                tiles[x][y].mainland = True
            if orientation == "upright" or orientation == "downright":
                if current_x == 0:
                    deviation = randint(0, 2)
                elif current_x == walk_start[0] + max_walk_deviation:
                    deviation = randint(-2, 0)
                else:
                    deviation = randint(-2, 2)
            elif orientation == "upleft" or orientation == "downleft":
                if current_x == walk_start[0] - max_walk_deviation:
                    deviation = randint(0, 2)
                elif current_x == wh_tuple[0] - 1:
                    deviation = randint(-2, 0)
                else:
                    deviation = randint(-2, 2)
            current_x += deviation
            if current_x < 0:
                current_x = 0
            elif current_x >= w:
                current_x = w - 1
    # fill in the corner
    if orientation == "upright" or orientation == "downright":
        fill_range_x = range(0, current_x + 1)
    elif orientation == "upleft" or orientation == "downleft":
        fill_range_x = range(current_x, w)
    if orientation == "upright" or orientation == "upleft":
        fill_range_y = range(walk_end[1], h)
    elif orientation == "downright" or orientation == "downleft":
        fill_range_y = range(0, bend_point[1])
    for x in fill_range_x:
        for y in fill_range_y:
           tiles[x][y].tile_type = "land"
           tiles[x][y].mainland = True
    # the second walk (horizontal)
    if orientation == "upright" or orientation == "downright":
        walk_start = (current_x, bend_point[1])
        walk_end = anchor_point_2
    elif orientation == "upleft" or orientation == "downleft":
        walk_start = anchor_point_2
        walk_end = (current_x, bend_point[1])
    current_y = walk_start[1]
    for x in range(walk_start[0], walk_end[0] + 1):
        if x < wh_tuple[0]:
            if orientation == "upright" or orientation == "upleft":
                land_range = range(current_y, h)
            elif orientation == "downright" or orientation == "downleft":
                land_range = range(0, current_y + 1)
            for y in land_range:
                tiles[x][y].tile_type = "land"
                tiles[x][y].mainland = True
            if orientation == "upright" or orientation == "upleft":
                if current_y == walk_start[1] - max_walk_deviation:
                    deviation = randint(0, 2)
                elif current_y == wh_tuple[1] - 2:
                    deviation = randint(-2, 0)
                else:
                    deviation = randint(-2, 2)
            elif orientation == "downright" or orientation == "downleft":
                if current_y == 0:
                    deviation = randint(0, 2)
                elif current_y == walk_start[1] + max_walk_deviation:
                    deviation = randint(-2, 0)
                else:
                    deviation = randint(-2, 2)
            current_y += deviation
            if current_y < 0:
                current_y = 0
            elif current_y >= h:
                current_y = h - 1
    # A pass to ensure no long stretches of perfectly straight coast, and add extra fuzz
    coastals = []
    for x in range(w):
        for y in range(h):
            nbrs = neighbors((x, y))
            tile = tiles[x][y]
            if tile.tile_type == "land" and any(map(lambda x: x.tile_type == "ocean", nbrs)):
                tiles[x][y].coast = True
                coastals.append(tile)
    touched = [] 
    for tile in coastals:
        nbrs = neighbors(tile.xy_tuple)
        for nbr in nbrs:
            if randint(1, 8) == 1 and nbr not in touched:
                nbr.tile_type = "land"
                nbr.coast = True
                nbr.mainland = True
                touched.append(nbr)
    # contiguity check
    contiguous_ocean = [tiles[opposite[0]][opposite[1]]]
    search = [tiles[opposite[0]][opposite[1]]]
    tiles[opposite[0]][opposite[1]].contiguous_ocean = True
    while len(search) > 0:
        tile = search.pop()
        nbrs = neighbors(tile.xy_tuple)
        for nbr in nbrs:
            if nbr.tile_type == "ocean" and nbr not in contiguous_ocean:
                contiguous_ocean.append(nbr)
                nbr.contiguous_ocean = True
                search.append(nbr)
    for x in range(wh_tuple[0]):
        for y in range(wh_tuple[1]):
            tile = tiles[x][y]
            if tile.tile_type == "ocean" and not tile.contiguous_ocean:
                tile.tile_type = "land"
                tile.mainland = True
    # islands
    for tile in contiguous_ocean:
        if randint(1, 10) < 7 and not tile.exclusion_zone: 
            tile.tile_type = "land"
            tile.island = True 
            tile.contiguous_ocean = False
    passes = 7 
    for _ in range(passes):
        new_land = []
        new_ocean = []
        for x in range(wh_tuple[0]):
            for y in range(wh_tuple[1]):
                if tiles[x][y].island:
                    nbrs = neighbors((x, y))
                    num_land = len(list(filter(lambda x: x.tile_type == "land", nbrs)))
                    borders_mainland = len(list(filter(lambda x: x.mainland, nbrs))) != 0
                    if num_land >= 5 and not borders_mainland: 
                        new_land.append((x, y))
                    elif num_land <= 3 or borders_mainland:
                        new_ocean.append((x, y))
        for xy in new_ocean:
            tiles[xy[0]][xy[1]].tile_type = "ocean"
            tiles[xy[0]][xy[1]].contiguous_ocean = True
            tiles[xy[0]][xy[1]].island = False
        for xy in new_land:
            tiles[xy[0]][xy[1]].tile_type = "land"
            tiles[xy[0]][xy[1]].island = True
            tiles[xy[0]][xy[1]].contiguous_ocean = False
    # final contiguity pass
    start = None
    for tile in contiguous_ocean:
        if first(lambda x: x.mainland, neighbors(tile.xy_tuple)) is not None:
            start = tile.xy_tuple
            break
    for x in range(wh_tuple[0]):
        for y in range(wh_tuple[1]):
            tiles[x][y].contiguous_ocean = False
    contiguous_ocean = [tiles[start[0]][start[1]]]
    search = [tiles[start[0]][start[1]]]
    tiles[start[0]][start[1]].contiguous_ocean = True
    potential_sea_route_end_nodes = []
    sea_route_end_nodes = []
    while len(search) > 0:
        tile = search.pop()
        nbrs = neighbors(tile.xy_tuple)
        for nbr in nbrs:
            if nbr.tile_type == "ocean" and nbr not in contiguous_ocean:
                contiguous_ocean.append(nbr)
                nbr.contiguous_ocean = True
                search.append(nbr)
    for x in range(w):
        for y in range(h):
            tile = tiles[x][y]
            if tile.tile_type == "ocean" and not tile.contiguous_ocean:
                tile.tile_type = "land"
                tile.island = True
    # ensure non-mainland edges free
    for x in range(w):
        for y in range(h):
            tile = tiles[x][y]
            if tile.tile_type == "land" and not tile.mainland and (x == 0 or y == 0 or x == w - 1 or y == h - 1):
                tile.tile_type = "ocean"
                tile.island = False
                tile.contiguous_ocean = True
                tile.contiguous_ocean = True
    # TODO: forests
    # TODO: mountains and mountain ranges
    # TODO: rivers
    # cities 
    coastal_city_locations = [] 
    for x in range(w):
        for y in range(h):
            tile = tiles[x][y]
            if tile.tile_type == "land":
                nbrs = neighbors(tile.xy_tuple)
                borders_ocean = first(lambda x: x.tile_type == "ocean", nbrs) is not None
                if borders_ocean:
                    coastal_city_locations.append(tile)
                    tile.coast = True
                else:
                    tile.coast = False
    shuffle(coastal_city_locations)
    emplaced_cities = 0
    for tile in coastal_city_locations:
        diffusion = randint(COASTAL_CITY_DIFFUSION_RANGE[0], COASTAL_CITY_DIFFUSION_RANGE[1])
        city_too_close = first(lambda x: x.tile_type == "city", valid_tiles_in_range_of(tiles, tile.xy_tuple, \
            diffusion)) is not None
        if not city_too_close:
            tile.tile_type = "city"
            tile.coast = True
            tile.faction = "enemy"
            emplaced_cities += 1
            if tile.mainland:
                mainland_coastal_city_tiles.append(tile)
            elif tile.island:
                island_coastal_city_tiles.append(tile)
    marked_untakeable = 0
    for x in range(w):
        for y in range(h):
            tile = tiles[x][y]
            diffusion = randint(LAND_CITY_DIFFUSION_RANGE[0], LAND_CITY_DIFFUSION_RANGE[1])
            city_too_close = first(lambda x: x.tile_type == "city", valid_tiles_in_range_of(tiles, tile.xy_tuple, \
                diffusion)) is not None
            if tile.tile_type == "land":
                tile.faction = "enemy"
                if not city_too_close and tile.mainland:
                    tile.tile_type = "city"
                    emplaced_cities += 1
                    if marked_untakeable < NUM_UNTAKEABLE_CITIES:
                        tile.untakeable_city = True
    return (tiles, orientation, opposite, mainland_coastal_city_tiles, island_coastal_city_tiles, sea_route_end_nodes)

# Tactical Maps 

def gen_open_ocean(wh_tuple) -> list:
    tiles = []
    for x in range(wh_tuple[0]):
        tiles.append([])
        for y in range(wh_tuple[1]):
            tiles[x].append(Tile((x, y), "ocean"))
    return tiles

def gen_coastline(wh_tuple) -> list:
    tiles = gen_open_ocean(wh_tuple)
    # TODO: generate map
    return tiles

def gen_bay(wh_tuple) -> list:
    tiles = gen_open_ocean(wh_tuple)
    # TODO: generate map
    return tiles

def gen_peninsula(wh_tuple) -> list: 
    tiles = gen_open_ocean(wh_tuple)
    # TODO: generate map
    return tiles

def gen_archipelago(wh_tuple) -> list:
    tiles = gen_open_ocean(wh_tuple)
    # TODO: generate map
    return tiles

def gen_inland_sea(wh_tuple) -> list:
    tiles = gen_open_ocean(wh_tuple)
    # TODO: generate map
    return tiles

geography_generators = {
    "campaign": gen_campaign_map,
    "open ocean": gen_open_ocean,
    "coastline": gen_coastline,
    "bay": gen_bay,
    "peninsula": gen_peninsula,
    "archipelago": gen_archipelago,
    "inland sea": gen_inland_sea,
} 

class TileMap:
    def __init__(self, wh_tuple, geography_type):
        self.wh_tuple = wh_tuple
        self.geography_type = geography_type
        if geography_type == "campaign":
            self.tiles, self.orientation, self.player_origin, self.mainland_coastal_city_tiles, \
                self.island_coastal_city_tiles, self.sea_route_end_nodes = geography_generators[geography_type](wh_tuple)
        else:
            self.tiles = geography_generators[geography_type](wh_tuple)

    def get_tile(self, xy_tuple) -> Tile:
        return self.tiles[xy_tuple[0]][xy_tuple[1]]

    def tile_in_bounds(self, xy_tuple) -> bool:
        return xy_tuple[0] >= 0 and xy_tuple[1] >= 0 and xy_tuple[0] < self.wh_tuple[0] and xy_tuple[1] < self.wh_tuple[1]
    
    def all_tiles(self) -> list:
        return flatten(self.tiles)

    def neighbors_of(self, tile_xy) -> list:
        neighbors = []
        for k, v in DIRECTIONS.items():
            if k == "wait":
                continue
            target_xy = (tile_xy[0] + v[0], tile_xy[1] + v[1])
            if self.tile_in_bounds(target_xy):
                neighbors.append(self.get_tile(target_xy))
        return neighbors

    def toggle_occupied(self, xy_tuple):
        if self.tile_in_bounds(xy_tuple):
            self.tiles[xy_tuple[0]][xy_tuple[1]].occupied = not self.tiles[xy_tuple[0]][xy_tuple[1]].occupied

    def occupied(self, xy_tuple) -> bool:
        if not self.tile_in_bounds(xy_tuple):
            return False
        return self.tiles[xy_tuple[0]][xy_tuple[1]].occupied 

    def land_buffer_mod(self, xy_tuple) -> int:
        level = 1
        while True:
            tiles_in_level = valid_tiles_in_range_of(self.tiles, xy_tuple, level)
            for tile in tiles_in_level:
                if tile.tile_type != "ocean":
                    return -level
            level += 1

    def distance_from_edge(self, xy_tuple) -> int:
        x, y = xy_tuple
        w, h = self.wh_tuple
        return min([x, y, w - 1 - x, h - 1 - y])
        
