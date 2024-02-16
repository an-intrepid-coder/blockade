import pygame
from constants import *

def grab_cell_from_sheet(sheet, index, orientation="left", zoomed_out=False) -> pygame.Surface:
    def get_final_clip(xy_tuple) -> pygame.Surface:
        final = pygame.Surface((CELL_SIZE, CELL_SIZE), flags=SRCALPHA)
        rect = (xy_tuple[0], xy_tuple[1], CELL_SIZE, CELL_SIZE)
        final.blit(surf, (0, 0), area=rect)
        return final
    surf = pygame.Surface((CELL_SIZE, CELL_SIZE), flags=SRCALPHA)
    rect = (index * CELL_SIZE, 0, CELL_SIZE, CELL_SIZE)
    surf.blit(sheet, (0, 0), area=rect)
    if orientation == "right":
        final = pygame.transform.flip(surf, True, False) 
    elif orientation == "left":
        final = surf
    elif orientation == "up":
        final = pygame.transform.rotate(surf, -90)
    elif orientation == "down":
        final = pygame.transform.rotate(surf, 90)
    elif orientation == "upright":
        surf = pygame.transform.rotate(surf, -135)
        final = get_final_clip((surf.get_width() - CELL_SIZE - 5, surf.get_height() - CELL_SIZE - 5))
    elif orientation == "upleft":
        surf = pygame.transform.rotate(surf, -45)
        final = get_final_clip((surf.get_width() - CELL_SIZE - 5, surf.get_height() - CELL_SIZE - 5))
    elif orientation == "downright":
        surf = pygame.transform.rotate(surf, 135)
        final = get_final_clip((surf.get_width() - CELL_SIZE - 5, surf.get_height() - CELL_SIZE - 5))
    elif orientation == "downleft":
        surf = pygame.transform.rotate(surf, 45)
        final = get_final_clip((surf.get_width() - CELL_SIZE - 5, surf.get_height() - CELL_SIZE - 5))
    if zoomed_out:
        return pygame.transform.scale(final, (ZOOMED_OUT_CELL_SIZE, ZOOMED_OUT_CELL_SIZE))
    return final

