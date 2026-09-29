import pygame as pg
import sys
from pygame.locals import *
from const import *
from movements import Move
from UI import UI
from maps import *
import general_var as gv
from individual import Herbivorous, Producer, get_local_density
import random


class Game:
    def __init__(self, saving_id, map_size):
        pg.init()
        self.screen = pg.display.set_mode(WINDOW_SIZE, RESIZABLE)
        pg.display.set_caption("生态箱")
        self.clock = pg.time.Clock()
        self.fullScreen = False
        self.pause = False
        self.ui = UI()
        self.bio_update_interval = 1.0 / 10.0
        self.bio_accumulator = 0.0

        if saving_id != "":
            self.nutrition_map_pic = read_map(saving_id)
        else:
            self.nutrition_map_pic = generate("nutrition_map", map_size)
        gv.nutritionMap = np.array(self.nutrition_map_pic)
        self.move = Move(map_size)
        self.biomass = 0.0

    def add_grass_at_mouse(self, mouse_pos):
        screen_width = self.screen.get_width()
        ui_width = getattr(self.ui, "panel_width", 260)
        if mouse_pos[0] >= screen_width - ui_width:
            return

        world_x = self.move.camerax - self.move.camera_sizex / 2 + mouse_pos[0]
        world_y = self.move.cameray - self.move.camera_sizey / 2 + mouse_pos[1]
        grass = Producer(int(world_x), int(world_y))
        self.move.all_sprites.add(grass)
        self.biomass += grass.mass

    def run(self):
        while 1:
            dt = self.clock.tick(30) / 1000.0
            for event in pg.event.get():
                if event.type == QUIT:
                    store_map(self.nutrition_map_pic)
                    # saving status
                    pg.quit()
                    sys.exit()
                if event.type == KEYDOWN:
                    if event.key == K_F11:
                        self.fullScreen = not self.fullScreen
                        if self.fullScreen:
                            window = pg.display.set_mode(WINDOW_SIZE_FULL, RESIZABLE | FULLSCREEN | HWSURFACE)
                        else:
                            window = pg.display.set_mode(WINDOW_SIZE, RESIZABLE)
                    if event.key == K_SPACE:
                        self.move.camera_scale_ratio = 1

                if event.type == MOUSEBUTTONUP:
                    if event.button == 1:
                        self.add_grass_at_mouse(event.pos)
                # if event.type == MOUSEWHEEL:
                #     if event.y == 1 and self.move.camera_scale_ratio < 2:
                #         self.move.camera_scale_ratio += 0.1
                #     if event.y == -1 and self.move.camera_scale_ratio > 0.7:
                #         self.move.camera_scale_ratio -= 0.1

                if event.type == KEYUP:
                    if event.key == K_SPACE:
                        self.pause = not self.pause
                if event.type == VIDEORESIZE:
                    self.move.update_size()

            if not self.pause:
                # camera movement stays frame-based and is independent from biology update tick
                key_pressed = pg.key.get_pressed()
                if key_pressed[K_a] or key_pressed[K_LEFT]:
                    self.move.camerax = max(self.move.camera_sizex/2, self.move.camerax - 2)
                if key_pressed[K_s] or key_pressed[K_DOWN]:
                    self.move.cameray = min(self.move.mapSize-self.move.camera_sizey/2, self.move.cameray + 2)
                if key_pressed[K_d] or key_pressed[K_RIGHT]:
                    self.move.camerax = min(self.move.mapSize-self.move.camera_sizex/2, self.move.camerax + 2)
                if key_pressed[K_w] or key_pressed[K_UP]:
                    self.move.cameray = max(self.move.camera_sizey/2, self.move.cameray - 2)

                self.bio_accumulator += dt
                if self.bio_accumulator >= self.bio_update_interval:
                    sprites = list(self.move.all_sprites)
                    get_local_density(
                        sprite for sprite in sprites
                        if hasattr(sprite, "world_pos") and hasattr(sprite, "mass")
                    )
                    for sprite in sprites:
                        if hasattr(sprite, "tick"):
                            sprite.tick()
                    self.biomass = sum(
                        sprite.mass for sprite in self.move.all_sprites
                        if hasattr(sprite, "mass")
                    )
                    self.bio_accumulator = 0

            self.move.run(dt)
            self.ui.display(dt, self.biomass)
            pg.display.update()


if __name__ == "__main__":
    game = Game("", 0)
    game.run()
