import pygame
from constants import *

def unit_tile_circle(color, hollow=False, small=False):
    if small:
        cell_size = ZOOMED_OUT_CELL_SIZE
    else:
        cell_size = CELL_SIZE
    image = pygame.Surface((cell_size, cell_size))
    image.set_colorkey(ALPHA_KEY)
    image.fill(ALPHA_KEY)
    if hollow:
        pygame.draw.circle(image, color, (cell_size // 2, cell_size // 2), cell_size // 3, 4)
    else:
        pygame.draw.circle(image, color, (cell_size // 2, cell_size // 2), cell_size // 3)
    return image

def unit_tile_triangle(color, upsidedown=False, small=False):
    if small:
        cell_size = ZOOMED_OUT_CELL_SIZE
    else:
        cell_size = CELL_SIZE
    image = pygame.Surface((cell_size, cell_size))
    image.set_colorkey(ALPHA_KEY)
    image.fill(ALPHA_KEY)
    if upsidedown:
        vert = (cell_size // 2, cell_size - 1)
        left = (0, 0)
        right = (cell_size - 1, 0)
    else:
        vert = (cell_size // 2, 0)
        left = (0, cell_size - 1)
        right = (cell_size - 1, cell_size - 1)
    pygame.draw.polygon(image, color, (vert, left, right))
    image = pygame.transform.scale(image, (int(image.get_width() * .66), int(image.get_height() * .66)))
    base = pygame.Surface((cell_size, cell_size))
    base.set_colorkey(ALPHA_KEY)
    base.fill(ALPHA_KEY)
    base.blit(image, (int(image.get_width() * .33), int(image.get_height() * .33)))
    return base

def unit_tile_cross(color, small=False): 
    if small:
        cell_size = ZOOMED_OUT_CELL_SIZE
    else:
        cell_size = CELL_SIZE
    image = pygame.Surface((cell_size, cell_size))
    image.set_colorkey(ALPHA_KEY)
    image.fill(ALPHA_KEY) 
    rect_side_a = cell_size // 4
    rect_side_b = cell_size
    h_rect = (0, cell_size // 2 - rect_side_a // 2, cell_size, rect_side_a)
    v_rect = (cell_size // 2 - rect_side_a // 2, 0, rect_side_a, cell_size)
    pygame.draw.rect(image, color, h_rect)
    pygame.draw.rect(image, color, v_rect)
    image = pygame.transform.scale(image, (int(image.get_width() * .66), int(image.get_height() * .66)))
    base = pygame.Surface((cell_size, cell_size))
    base.set_colorkey(ALPHA_KEY)
    base.fill(ALPHA_KEY)
    base.blit(image, (int(image.get_width() * .33), int(image.get_height() * .33)))
    return base

def unidentified_unit_tile(entity, small=False):
    if entity.name == "freighter":
        if small:
            return unit_tile_circle("dark gray", small=True)
        else:
            return unit_tile_circle("dark gray")
    elif entity.name == "small convoy escort":
        if small:
            return unit_tile_triangle("dark gray", small=True)
        else:
            return unit_tile_triangle("dark gray")
    elif entity.name == "escort sub":
        if small:
            return unit_tile_triangle("dark gray", upsidedown=True, small=True)
        else:
            return unit_tile_triangle("dark gray", upsidedown=True)

