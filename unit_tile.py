import pygame
from constants import *

def unit_tile_circle(color, hollow=False):
    image = pygame.Surface((CELL_SIZE, CELL_SIZE))
    image.set_colorkey(ALPHA_KEY)
    image.fill(ALPHA_KEY)
    if hollow:
        pygame.draw.circle(image, color, (CELL_SIZE // 2, CELL_SIZE // 2), CELL_SIZE // 3, 2)
    else:
        pygame.draw.circle(image, color, (CELL_SIZE // 2, CELL_SIZE // 2), CELL_SIZE // 3)
    return image

def unit_tile_triangle(color, upsidedown=False):
    image = pygame.Surface((CELL_SIZE, CELL_SIZE))
    image.set_colorkey(ALPHA_KEY)
    image.fill(ALPHA_KEY)
    if upsidedown:
        vert = (CELL_SIZE // 2, CELL_SIZE - 1)
        left = (0, 0)
        right = (CELL_SIZE - 1, 0)
    else:
        vert = (CELL_SIZE // 2, 0)
        left = (0, CELL_SIZE - 1)
        right = (CELL_SIZE - 1, CELL_SIZE - 1)
    pygame.draw.polygon(image, color, (vert, left, right))
    image = pygame.transform.scale(image, (int(image.get_width() * .66), int(image.get_height() * .66)))
    base = pygame.Surface((CELL_SIZE, CELL_SIZE))
    base.set_colorkey(ALPHA_KEY)
    base.fill(ALPHA_KEY)
    base.blit(image, (int(image.get_width() * .33), int(image.get_height() * .33)))
    return base

def unit_tile_cross(color): 
    image = pygame.Surface((CELL_SIZE, CELL_SIZE))
    image.set_colorkey(ALPHA_KEY)
    image.fill(ALPHA_KEY) 
    rect_side_a = CELL_SIZE // 4
    rect_side_b = CELL_SIZE
    h_rect = (0, CELL_SIZE // 2 - rect_side_a // 2, CELL_SIZE, rect_side_a)
    v_rect = (CELL_SIZE // 2 - rect_side_a // 2, 0, rect_side_a, CELL_SIZE)
    pygame.draw.rect(image, color, h_rect)
    pygame.draw.rect(image, color, v_rect)
    image = pygame.transform.scale(image, (int(image.get_width() * .66), int(image.get_height() * .66)))
    base = pygame.Surface((CELL_SIZE, CELL_SIZE))
    base.set_colorkey(ALPHA_KEY)
    base.fill(ALPHA_KEY)
    base.blit(image, (int(image.get_width() * .33), int(image.get_height() * .33)))
    return base

def unidentified_unit_tile(entity):
    if entity.name == "freighter":
        return unit_tile_circle("dark gray")
    elif entity.name == "small convoy escort":
        return unit_tile_triangle("dark gray")
    elif entity.name == "escort sub":
        return unit_tile_triangle("dark gray", upsidedown=True)

