from functional import flatten
from euclidean import chebyshev_distance
from constants import *

""" ________Is/Does/Needs/Will Do:
    - Map Generation for: (bearing in mind each tile should represent, like, a square mile or two -- for now, loosely)
        1.) Open Ocean
        2.) Open Ocean and a coastline *
        3.) A huge bay (like, huge) *
        4.) A Huge peninsula *
        5.) Archipelago *
        6.) Inland Sea *

        * Cities, Rivers, Forests, Jagged Coastlines, Land Units, Islands all possible.
"""     

tile_types = ["ocean", "land"] # TODO: more types of land, ocean, rivers, forests, etc.

class Tile:
    def __init__(self, xy_tuple, tile_type):
        self.xy_tuple = xy_tuple
        self.tile_type = tile_type

geography_types = ["open ocean", "coastline", "bay", "peninsula", "archipelago", "inland sea"]

def gen_open_ocean(wh_tuple):
    tiles = []
    for x in range(wh_tuple[0]):
        tiles.append([])
        for y in range(wh_tuple[1]):
            tiles[x].append(Tile((x, y), "ocean"))
    return tiles

def gen_coastline(wh_tuple):
    tiles = gen_open_ocean(wh_tuple)
    # TODO: generate map
    return tiles

def gen_bay(wh_tuple):
    tiles = gen_open_ocean(wh_tuple)
    # TODO: generate map
    return tiles

def gen_peninsula(wh_tuple): 
    tiles = gen_open_ocean(wh_tuple)
    # TODO: generate map
    return tiles

def gen_archipelago(wh_tuple):
    tiles = gen_open_ocean(wh_tuple)
    # TODO: generate map
    return tiles

def gen_inland_sea(wh_tuple):
    tiles = gen_open_ocean(wh_tuple)
    # TODO: generate map
    return tiles

geography_generators = {
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
        self.tiles = geography_generators[geography_type](wh_tuple)

    def get_tile(self, xy_tuple) -> Tile:
        return self.tiles[xy_tuple[0]][xy_tuple[1]]

    def tile_in_bounds(self, xy_tuple) -> bool:
        return xy_tuple[0] >= 0 and xy_tuple[1] >= 0 and xy_tuple[0] < self.wh_tuple[0] and xy_tuple[1] < self.wh_tuple[1]
    
    def all_tiles(self) -> list:
        return flatten(self.tiles)

    def neighbors_of(self, tile_xy) -> list:
        neighbors = []
        for _, v in DIRECTIONS.items():
            target_xy = (tile_xy[0] + v[0], tile_xy[1] + v[1])
            if self.tile_in_bounds(target_xy):
                neighbors.append(self.get_tile(target_xy))
        return neighbors
            
