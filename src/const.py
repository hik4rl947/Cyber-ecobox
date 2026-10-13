import pygame as pg

WINDOW_SIZE = (1260, 600)
pg.init()
WINDOW_SIZE_ACCEPTED = pg.display.list_modes()
WINDOW_SIZE_FULL = WINDOW_SIZE_ACCEPTED[0]

BACK_GROUND_COLOR = (20, 20, 20)

IMG_PATH = "../pic/"

MAP_SIZE = [2048]

THEME_PALETTES = {
    "light": {
        "background": (245, 238, 219),
        "panel": (255, 253, 246),
        "panel_border": (54, 147, 132),
        "toolbar": (245, 238, 219),
        "accent": (24, 160, 153),
        "accent_soft": (23, 109, 96),
        "text": (38, 39, 39),
        "text_on_accent": (255, 253, 246),
        "text_muted": (83, 86, 84),
        "grid": (202, 198, 185),
        "button": (238, 232, 216),
        "button_border": (145, 143, 132),
        "red": (154, 45, 40),
        "gold": (236, 169, 59),
        "orange": (240, 103, 52),
        "cyan": (24, 180, 194),
    },
    "dark": {
        "background": (25, 29, 32),
        "panel": (37, 43, 47),
        "panel_border": (66, 130, 124),
        "toolbar": (31, 35, 38),
        "accent": (74, 218, 194),
        "accent_soft": (134, 232, 204),
        "text": (239, 238, 225),
        "text_on_accent": (24, 31, 32),
        "text_muted": (177, 189, 184),
        "grid": (67, 77, 78),
        "button": (52, 60, 63),
        "button_border": (99, 119, 117),
        "red": (177, 61, 53),
        "gold": (246, 185, 75),
        "orange": (246, 121, 66),
        "cyan": (63, 207, 220),
    },
}

# spawning
INITIAL_GRASS_COUNT = 30
GRASS_SPAWN_INTERVAL = 2.0

INITIAL_HERBIVORE_COUNT = 10
INITIAL_CARNIVORE_COUNT = 1


# default settings
DEFAULT_IMG_SIZES = {
    "grass": (20, 20), 
    "cow": (20, 20),
    "lion": (25, 25),
    }
DEFAULT_SIZES = {
    "grass": 1,
    "cow": 3,
    "lion": 4,
}
DEFAULT_COLORS = {
    "grass": (10, 255, 10, 255),
    "cow": (168, 104, 50, 255),
    "lion": (252, 65, 3),
}
OLD_AGES = {
    "grass": 100,
    "cow": 400,
    "lion": 500,
}
MAX_MASS = {
    "grass": 10,
    "cow": 15,
    "lion": 20,
}
BREED_COOLDOWN = {
    "cow": 100,
    "lion": 300,
}
