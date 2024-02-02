from functional import *
from euclidean import chebyshev_distance
from constants import *
from random import choice, randint, randrange, shuffle

tile_types = ["ocean", "land", "mountain", "river", "city", "forest"] 

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
        self.distance_from_mainland = 0 # TODO
        self.island_number = 0 # TODO

geography_types = ["campaign", "open ocean", "coastline", "bay", "peninsula", "archipelago", "inland sea"]

# Generates a very small but very specific map in a variety of possible orientations, with each tile
# representing many more miles^2 than on the tactical maps.
def gen_campaign_map(wh_tuple) -> tuple:  
    elbow = choice(["upright", "upleft", "downright", "downleft"]) # <- rename this to "orientation" TODO
    if elbow == "upright":
        opposite = (wh_tuple[0] - 1, 0)
    elif elbow == "upleft":
        opposite = (0, 0)
    elif elbow == "downright":
        opposite = (wh_tuple[0] - 1, wh_tuple[1] - 1)
    elif elbow == "downleft":
        opposite = (0, wh_tuple[1] - 1)
    tiles = []
    def in_bounds(xy_tuple) -> bool:
        return xy_tuple[0] >= 0 and xy_tuple[1] >= 0 and xy_tuple[0] < wh_tuple[0] and xy_tuple[1] < wh_tuple[1]
    def neighbors(tile_xy) -> list:
        neighbors = []
        for k, v in DIRECTIONS.items():
            if k == "wait":
                continue
            x, y = tile_xy[0] + v[0], tile_xy[1] + v[1]
            if in_bounds((x, y)):
                neighbors.append(tiles[x][y])
        return neighbors
    # starting with just ocean
    for x in range(wh_tuple[0]):
        tiles.append([])
        for y in range(wh_tuple[1]):
            tiles[x].append(Tile((x, y), "ocean"))
            if chebyshev_distance(opposite, (x, y)) < 10:
                tiles[x][y].exclusion_zone = True
    land_margin = min(wh_tuple) // 5
    # anchor point #1
    if elbow == "upright" or elbow == "downright":
        anchor_1_range = (0, land_margin)
    elif elbow == "upleft" or elbow == "downleft":
        anchor_1_range = (wh_tuple[0] - land_margin, wh_tuple[0] - 1)
    # anchor point #2
    if elbow == "upright" or elbow == "upleft":
        anchor_2_range = (wh_tuple[1] - land_margin, wh_tuple[1] - 1)
    if elbow == "downright" or elbow == "downleft":
        anchor_2_range = (0, land_margin)
    # Bend anchor point 
    if elbow == "upright":
        bend_rect = (0, wh_tuple[1] - land_margin, land_margin, land_margin)
    elif elbow == "upleft":
        bend_rect = (wh_tuple[0] - land_margin, wh_tuple[1] - land_margin, land_margin, land_margin)
    elif elbow == "downright":
        bend_rect = (0, 0, land_margin, land_margin)
    elif elbow == "downleft":
        bend_rect = (wh_tuple[0] - land_margin, 0, land_margin, land_margin)
    # select anchor points from their ranges
    if elbow == "upright" or elbow == "upleft":
        anchor_point_1 = (randint(anchor_1_range[0], anchor_1_range[1]), 0)
    elif elbow == "downright" or elbow == "downleft":
        anchor_point_1 = (randint(anchor_1_range[0], anchor_1_range[1]), wh_tuple[1] - 1)
    if elbow == "upright" or elbow == "downright":
        anchor_point_2 = (wh_tuple[0] - 1, randint(anchor_2_range[0], anchor_2_range[1]))
    elif elbow == "upleft" or elbow == "downleft":
        anchor_point_2 = (0, randint(anchor_2_range[0], anchor_2_range[1]))
    bend_point = (randint(bend_rect[0], bend_rect[0] + bend_rect[2]), randint(bend_rect[1], bend_rect[1] + bend_rect[3]))
    max_walk_deviation = 30 
    # the first walk (vertical)
    if elbow == "upright" or elbow == "upleft":
        walk_start = anchor_point_1
        walk_end = bend_point
    elif elbow == "downright" or elbow == "downleft":
        walk_start = bend_point
        walk_end = anchor_point_1
    current_x = walk_start[0]
    for y in range(walk_start[1], walk_end[1] + 1):
        if y < wh_tuple[1]:
            if elbow == "upright" or elbow == "downright":
                land_range = range(0, current_x + 1) 
            elif elbow == "upleft" or elbow == "downleft":
                land_range = range(current_x, wh_tuple[0]) 
            for x in land_range:
                tiles[x][y].tile_type = "land"
                tiles[x][y].mainland = True
            if elbow == "upright" or elbow == "downright":
                if current_x == 0:
                    deviation = randint(0, 2)
                elif current_x == walk_start[0] + max_walk_deviation:
                    deviation = randint(-2, 0)
                else:
                    deviation = randint(-2, 2)
            elif elbow == "upleft" or elbow == "downleft":
                if current_x == walk_start[0] - max_walk_deviation:
                    deviation = randint(0, 2)
                elif current_x == wh_tuple[0] - 1:
                    deviation = randint(-2, 0)
                else:
                    deviation = randint(-2, 2)
            current_x += deviation
            if current_x < 0:
                current_x = 0
            elif current_x >= wh_tuple[0]:
                current_x = wh_tuple[0] - 1
    # fill in the corner
    if elbow == "upright" or elbow == "downright":
        fill_range_x = range(0, current_x + 1)
    elif elbow == "upleft" or elbow == "downleft":
        fill_range_x = range(current_x, wh_tuple[0])
    if elbow == "upright" or elbow == "upleft":
        fill_range_y = range(walk_end[1], wh_tuple[1])
    elif elbow == "downright" or elbow == "downleft":
        fill_range_y = range(0, bend_point[1])
    for x in fill_range_x:
        for y in fill_range_y:
           tiles[x][y].tile_type = "land"
           tiles[x][y].mainland = True
    # the second walk (horizontal)
    if elbow == "upright" or elbow == "downright":
        walk_start = (current_x, bend_point[1])
        walk_end = anchor_point_2
    elif elbow == "upleft" or elbow == "downleft":
        walk_start = anchor_point_2
        walk_end = (current_x, bend_point[1])
    current_y = walk_start[1]
    for x in range(walk_start[0], walk_end[0] + 1):
        if x < wh_tuple[0]:
            if elbow == "upright" or elbow == "upleft":
                land_range = range(current_y, wh_tuple[1])
            elif elbow == "downright" or elbow == "downleft":
                land_range = range(0, current_y + 1)
            for y in land_range:
                tiles[x][y].tile_type = "land"
                tiles[x][y].mainland = True
            if elbow == "upright" or elbow == "upleft":
                if current_y == walk_start[1] - max_walk_deviation:
                    deviation = randint(0, 2)
                elif current_y == wh_tuple[1] - 2:
                    deviation = randint(-2, 0)
                else:
                    deviation = randint(-2, 2)
            elif elbow == "downright" or elbow == "downleft":
                if current_y == 0:
                    deviation = randint(0, 2)
                elif current_y == walk_start[1] + max_walk_deviation:
                    deviation = randint(-2, 0)
                else:
                    deviation = randint(-2, 2)
            current_y += deviation
            if current_y < 0:
                current_y = 0
            elif current_y >= wh_tuple[1]:
                current_y = wh_tuple[1] - 1
    # A pass to ensure no long stretches of perfectly straight coast, and add extra fuzz
    coastals = []
    for x in range(wh_tuple[0]):
        for y in range(wh_tuple[1]):
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
    print(len(contiguous_ocean))
    for tile in contiguous_ocean:
        if randint(1, 10) < 7 and not tile.exclusion_zone: # tentative
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
                tile.island = True
    # ensure non-mainland edges free
    for x in range(wh_tuple[0]):
        for y in range(wh_tuple[1]):
            tile = tiles[x][y]
            if tile.tile_type == "land" and not tile.mainland and \
                (x == 0 or \
                y == 0 or \
                x == wh_tuple[0] - 1 or \
                y == wh_tuple[1] - 1):
                tile.tile_type = "ocean"
                tile.island = False
                tile.contiguous_ocean = True
                tile.contiguous_ocean = True
    # TODO: forests
    # TODO: mountains and mountain ranges
    # TODO: rivers
    # cities 
    def valid_tiles_in_range_of(tiles_ls, xy_tuple, d) -> list: 
        locs = []
        for x in range(xy_tuple[0] - d, xy_tuple[0] + d + 1):
            for y in range(xy_tuple[1] - d, xy_tuple[1] + d + 1):
                valid = in_bounds((x, y)) and chebyshev_distance((x, y), xy_tuple) <= d
                if valid:
                    locs.append(tiles[x][y])
        return locs 
    coastal_city_locations = [] 
    for x in range(wh_tuple[0]):
        for y in range(wh_tuple[1]):
            tile = tiles[x][y]
            if tile.tile_type == "land":
                nbrs = neighbors(tile.xy_tuple)
                borders_ocean = first(lambda x: x.tile_type == "ocean", nbrs) is not None
                if borders_ocean:
                    coastal_city_locations.append(tile)
    shuffle(coastal_city_locations)
    emplaced_cities = 0
    for tile in coastal_city_locations:
        diffusion = randint(COASTAL_CITY_DIFFUSION_RANGE[0], COASTAL_CITY_DIFFUSION_RANGE[1])
        city_too_close = first(lambda x: x.tile_type == "city", valid_tiles_in_range_of(tiles, tile.xy_tuple, \
            diffusion)) is not None
        if not city_too_close:
            tile.tile_type = "city"
            tile.coast = True
            emplaced_cities += 1
    marked_untakeable = 0
    for x in range(wh_tuple[0]):
        for y in range(wh_tuple[1]):
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
    # NOTE: ^-- the rest (trade routes, nations, etc.) will be handled in Scene scope. And at some point I'll want to
    #           optimize this by combining some things which are currently handled in separate steps. And extract some
    #           generic functions for drunken walks and cellular automata, for use in other map types. Importantly,
    #           with bounds parameters, so I can use them on bigger maps where big-O will be a serious concern. This is
    #           basically a rough draft. Importantly, this is tightly bounded by a (for now) 60x60 tile campaign map.
    return (tiles, elbow, opposite)

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
            self.tiles, self.orientation, self.player_origin = geography_generators[geography_type](wh_tuple)
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

