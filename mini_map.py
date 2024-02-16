import pygame
from constants import *
from functional import *

class MiniMap: 
    def __init__(self, scene, scene_type):
        self.terrain_base_needs_update = False
        self.scene = scene
        self.last_update_tilemap = self.scene.tilemap
        self.tilemap = self.scene.tilemap
        self.terrain_base = self.generate_terrain_base() 
        self.surf = None
        self.update(scene_type)

    def generate_terrain_base(self): 
        surf = pygame.Surface((self.tilemap.wh_tuple[0] * MM_CELL_SIZE, self.tilemap.wh_tuple[1] * MM_CELL_SIZE))
        # draw tilemap
        cities = []
        for x in range(self.tilemap.wh_tuple[0]):
            for y in range(self.tilemap.wh_tuple[1]):
                rect = (x * MM_CELL_SIZE, y * MM_CELL_SIZE, MM_CELL_SIZE, MM_CELL_SIZE)
                center = (rect[0] + rect[2] // 2, rect[1] + rect[3] // 2)
                tile = self.tilemap.get_tile((x, y))
                if tile.tile_type == "ocean":
                    pygame.draw.rect(surf, "navy", rect)
                    if tile.sea_route_node:
                        pygame.draw.circle(surf, "white", center, 1)
                elif tile.tile_type == "land":
                    pygame.draw.rect(surf, LAND_COLOR, rect)
                elif tile.tile_type == "city":
                    cities.append((x, y))
        for tile in cities:
            x, y = tile
            rect = (x * MM_CELL_SIZE, y * MM_CELL_SIZE, MM_CELL_SIZE, MM_CELL_SIZE)
            center = (rect[0] + rect[2] // 2, rect[1] + rect[3] // 2)
            color = faction_to_color[self.tilemap.tiles[x][y].faction]
            pygame.draw.circle(surf, color, center, 5)
            pygame.draw.circle(surf, "black", center, 5, 2)
        return surf

    def generate_final_campaign(self): 
        surf = self.terrain_base.copy()
        # mission rect
        mission_rect = (self.scene.invasion_target.xy_tuple[0] * MM_CELL_SIZE - MISSION_RADIUS * MM_CELL_SIZE, \
            self.scene.invasion_target.xy_tuple[1] * MM_CELL_SIZE - MISSION_RADIUS * MM_CELL_SIZE, \
            (MISSION_RADIUS * 2 + 1) * MM_CELL_SIZE, (MISSION_RADIUS * 2 + 1) * MM_CELL_SIZE)
        pygame.draw.rect(surf, COLOR_MISSION_HIGHLIGHT, mission_rect, 1)
        # draw entities:
        for entity in self.scene.entities:
            if not entity.hidden or entity.player or self.scene.debug:
                rect = (entity.xy_tuple[0] * MM_CELL_SIZE, entity.xy_tuple[1] * MM_CELL_SIZE, MM_CELL_SIZE, \
                    MM_CELL_SIZE) 
                center = (rect[0] + rect[2] // 2, rect[1] + rect[3] // 2)
                color = faction_to_color[entity.faction]
                pygame.draw.circle(surf, color, center, 3)
        scaled = pygame.transform.scale(surf, MINI_MAP_SIZE)
        pygame.draw.rect(scaled, "green", (0, 0, MINI_MAP_SIZE[0], MINI_MAP_SIZE[1]), 1)
        return scaled

    def generate_final_tactical(self): 
        surf = self.terrain_base.copy()
        # draw entities:
        for entity in self.scene.entities:
            in_player_contacts = entity in list(map(lambda x: x.entity, self.scene.player.contacts))
            if in_player_contacts or entity.player or self.scene.debug:
                rect = (entity.xy_tuple[0] * MM_CELL_SIZE, entity.xy_tuple[1] * MM_CELL_SIZE, MM_CELL_SIZE, \
                    MM_CELL_SIZE) 
                contact = first(lambda x: x.entity is entity, self.scene.player.contacts)
                if entity.player \
                    or entity.identified \
                    or self.scene.debug \
                    or (contact is not None and contact.acc >= CONTACT_ACC_ID_THRESHOLD): 
                    color = faction_to_color[entity.faction]
                else:
                    color = "dark gray"
                pygame.draw.rect(surf, color, rect)
        scaled = pygame.transform.scale(surf, MINI_MAP_SIZE)
        pygame.draw.rect(scaled, "green", (0, 0, MINI_MAP_SIZE[0], MINI_MAP_SIZE[1]), 1)
        return scaled

    def update(self, scene_type):
        if self.terrain_base_needs_update:
            self.terrain_base = self.generate_terrain_base()
            self.terrain_base_needs_update = False
        if scene_type == "campaign":
            self.surf = self.generate_final_campaign()
        elif scene_type == "tactical":
            self.surf = self.generate_final_tactical()

