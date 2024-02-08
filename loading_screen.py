import pygame
from constants import *

def loading_screen():
    title_font = pygame.font.Font(FONT_PATH, TITLE_FONT_SIZE)
    subtitle_font = pygame.font.Font(FONT_PATH, HUD_FONT_SIZE)
    desktop_size = pygame.display.get_desktop_sizes()[0]
    w, h = desktop_size
    screen = pygame.display.get_surface()
    surf = pygame.Surface(desktop_size)
    surf.fill("navy")
    lines = [
        title_font.render("BLOCKADE", True, "white", "black"),
        title_font.render("", True, "white", "black"),
        subtitle_font.render("<version {}>".format(VERSION), True, "white", "black"),
        title_font.render("", True, "white", "black"),
        title_font.render("", True, "white", "black"),
        subtitle_font.render("~-~-~-~-~-~-~-___SECTOR 34 GAMES___~-~-~-~-~-~-~-", True, "white", "black"),
        subtitle_font.render("...loading...".format(VERSION), True, "white", "black"),
        subtitle_font.render("~-~-~-~-<roguelike + subsim = awesome>~-~-~-~-~-~", True, "white", "black"),
    ]
    y = h // 2 - ((len(lines) - 1) * lines[1].get_height() + lines[0].get_height()) // 2 
    for line in lines:
        x = w // 2 - line.get_width() // 2
        surf.blit(line, (x, y))
        if line is lines[0]:
            y += lines[0].get_height()
        else:
            y += lines[1].get_height()
    screen.blit(surf, (0, 0))
    pygame.display.flip()

