import pygame as pg

WINDOW_SIZE = (1260, 600)
pg.init()
WINDOW_SIZE_ACCEPTED = pg.display.list_modes()
WINDOW_SIZE_FULL = WINDOW_SIZE_ACCEPTED[0]

BACK_GROUND_COLOR = (20, 20, 20)

IMG_PATH = "../pic/"

MAP_SIZE = [2048]

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
    "lion": (252, 90, 3),
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
