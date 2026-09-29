import pygame as pg

WINDOW_SIZE = (1260, 600)
pg.init()
WINDOW_SIZE_ACCEPTED = pg.display.list_modes()
WINDOW_SIZE_FULL = WINDOW_SIZE_ACCEPTED[0]


BACK_GROUND_COLOR = (20, 20, 20)

IMG_PATH = "../pic/"

MAP_SIZE = [2048]

DEFAULT_IMG_SIZES = {
    "grass": (20, 20), 
    "cow": (20, 20),
    }
DEFAULT_SIZES = {
    "grass": 1,
    "cow": 3,
}
DEFAULT_COLORS = {
    "grass": (10, 255, 10, 255),
    "cow": (255, 255, 255, 255),
}
