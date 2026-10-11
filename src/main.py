import pygame as pg
import sys
from pygame.locals import *
from const import *
from movements import Move
from UI import UI
from maps import *
import general_var as gv
from individual import (
    Carnivore,
    GrassSpatialIndex,
    Herbivorous,
    HerbivoreSpatialIndex,
    Producer,
    get_local_density,
    get_population_centers,
)
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
        self.grass_spawn_elapsed = 0.0

        if saving_id != "":
            self.nutrition_map_pic = read_map(saving_id)
        else:
            self.nutrition_map_pic = generate("nutrition_map", map_size)
        gv.nutritionMap = np.array(self.nutrition_map_pic)
        self.move = Move(map_size)
        self.ui.set_hover_camera(self.move)
        self.ui.set_species_source(self.move.all_sprites)
        self.ui.set_reset_callback(self.reset_simulation)
        self._spawn_initial_population()

    def _spawn_initial_population(self):
        for _ in range(INITIAL_GRASS_COUNT):
            self.spawn_random_grass()

        grass_count = sum(
            isinstance(sprite, Producer) for sprite in self.move.all_sprites
        )
        if grass_count < INITIAL_GRASS_COUNT:
            return False

        for _ in range(INITIAL_HERBIVORE_COUNT):
            cow = Herbivorous(
                random.randrange(self.move.mapSize),
                random.randrange(self.move.mapSize),
            )
            self.move.all_sprites.add(cow)
            gv.entCnt += 1
            gv.bioMass += cow.mass
        return True

    def reset_simulation(self):
        self.move.all_sprites.empty()
        gv.O2Amount = gv.O2Concentration * gv.AirAmount
        gv.CO2Amount = gv.CO2Concentration * gv.AirAmount
        gv.bioMass = 0
        gv.entCnt = 0
        gv.creatureCnt = 0
        self.bio_accumulator = 0.0
        self.grass_spawn_elapsed = 0.0
        self.ui.reset_history()
        self._spawn_initial_population()

    def add_grass_at_world(self, world_x, world_y):
        grass = Producer(int(world_x), int(world_y))
        self.move.all_sprites.add(grass)
        gv.bioMass += grass.mass
        gv.entCnt += 1
        return grass

    def add_grass_at_mouse(self, mouse_pos):
        screen_width = self.screen.get_width()
        ui_width = getattr(self.ui, "panel_width", 260)
        if mouse_pos[0] >= screen_width - ui_width:
            return

        world_x = self.move.camerax - self.move.camera_sizex / 2 + mouse_pos[0]
        world_y = self.move.cameray - self.move.camera_sizey / 2 + mouse_pos[1]
        return self.add_grass_at_world(world_x, world_y)

    def spawn_random_grass(self):
        screen_width = self.screen.get_width()
        screen_height = self.screen.get_height()
        visible_width = max(0, screen_width - self.ui.panel_width)
        visible_top = self.ui.TOOLBAR_HEIGHT
        left = max(0, int(self.move.camerax - self.move.camera_sizex / 2))
        top = max(0, int(self.move.cameray - self.move.camera_sizey / 2 + visible_top))
        right = min(
            self.move.mapSize,
            int(self.move.camerax - self.move.camera_sizex / 2 + visible_width),
        )
        bottom = min(
            self.move.mapSize,
            int(self.move.cameray - self.move.camera_sizey / 2 + screen_height),
        )
        if right <= left or bottom <= top:
            return None

        return self.add_grass_at_world(
            random.randrange(left, right),
            random.randrange(top, bottom),
        )

    def _update_grass_spawning(self, dt):
        self.grass_spawn_elapsed += dt
        while self.grass_spawn_elapsed >= GRASS_SPAWN_INTERVAL:
            self.grass_spawn_elapsed -= GRASS_SPAWN_INTERVAL
            self.spawn_random_grass()

    def _handle_events(self):
        for event in pg.event.get():
            if event.type == QUIT:
                store_map(self.nutrition_map_pic)
                pg.quit()
                sys.exit()
            if event.type == KEYDOWN:
                if event.key == K_F11:
                    self.fullScreen = not self.fullScreen
                    if self.fullScreen:
                        pg.display.set_mode(WINDOW_SIZE_FULL, RESIZABLE | FULLSCREEN | HWSURFACE)
                    else:
                        pg.display.set_mode(WINDOW_SIZE, RESIZABLE)
                if event.key == K_SPACE:
                    self.move.camera_scale_ratio = 1
            elif event.type == MOUSEBUTTONUP:
                if event.button == 1 and not self.ui.handle_event(event):
                    self.add_grass_at_mouse(event.pos)
            elif event.type == MOUSEWHEEL:
                self.ui.handle_event(event)
            elif event.type == KEYUP:
                if event.key == K_SPACE:
                    self.pause = not self.pause
            elif event.type == VIDEORESIZE:
                self.move.update_size()

    def _update_camera(self):
        key_pressed = pg.key.get_pressed()
        if key_pressed[K_a] or key_pressed[K_LEFT]:
            self.move.camerax = max(self.move.camera_sizex / 2, self.move.camerax - 2)
        if key_pressed[K_s] or key_pressed[K_DOWN]:
            self.move.cameray = min(self.move.mapSize - self.move.camera_sizey / 2, self.move.cameray + 2)
        if key_pressed[K_d] or key_pressed[K_RIGHT]:
            self.move.camerax = min(self.move.mapSize - self.move.camera_sizex / 2, self.move.camerax + 2)
        if key_pressed[K_w] or key_pressed[K_UP]:
            self.move.cameray = max(self.move.camera_sizey / 2, self.move.cameray - 2)

    def _advance_simulation(self, dt):
        self._update_grass_spawning(dt)
        self._update_camera()
        self.bio_accumulator += dt
        if self.bio_accumulator < self.bio_update_interval:
            return

        sprites = list(self.move.all_sprites)
        get_local_density(
            sprite for sprite in sprites
            if hasattr(sprite, "world_pos") and hasattr(sprite, "mass")
        )
        herbivores = [sprite for sprite in sprites if isinstance(sprite, Herbivorous)]
        grasses = [sprite for sprite in sprites if isinstance(sprite, Producer)]
        grass_index = GrassSpatialIndex(grasses)
        predators = [sprite for sprite in sprites if isinstance(sprite, Carnivore)]
        herd_index = HerbivoreSpatialIndex(herbivores)
        population_centers = get_population_centers(
            herbivores,
            Herbivorous.POPULATION_RADIUS,
            spatial_index=herd_index,
        )
        for sprite in sprites:
            if isinstance(sprite, Herbivorous):
                sprite.tick(population_centers[sprite], grass_index, herd_index, predators)
            elif hasattr(sprite, "tick"):
                sprite.tick()
        gv.bioMass = sum(
            sprite.mass for sprite in self.move.all_sprites
            if hasattr(sprite, "mass")
        )
        self.bio_accumulator = 0

    def run(self):
        while 1:
            dt = self.clock.tick(30) / 1000.0
            self._handle_events()
            if not self.pause:
                self._advance_simulation(dt)
            self.move.run(dt)
            self.ui.display(dt)
            pg.display.update()


if __name__ == "__main__":
    game = Game("", 0)
    game.run()
