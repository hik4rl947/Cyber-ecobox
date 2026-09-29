import pygame as pg
from const import *


class Move:
    def __init__(self, mapSize):
        self.display_surface = pg.display.get_surface()
        self.all_sprites = CameraGroup(self)
        try:
            self.background_pic = pg.image.load(IMG_PATH + 'nutrition_map.png')
        except (FileNotFoundError, pg.error):
            self.background_pic = pg.Surface((1, 1))
            self.background_pic.fill("green")
        self.camera_scale_ratio = 1
        self.camera_sizex, self.camera_sizey = self.display_surface.get_size()
        self.camerax = int(self.camera_sizex / 2)
        self.cameray = int(self.camera_sizey / 2)
        self.mapSize = MAP_SIZE[mapSize]

    def _draw_background(self):
        if self.background_pic is None:
            return

        view_left = max(0, int(self.camerax - self.camera_sizex / 2))
        view_top = max(0, int(self.cameray - self.camera_sizey / 2))
        view_right = min(self.mapSize, int(self.camerax + self.camera_sizex / 2))
        view_bottom = min(self.mapSize, int(self.cameray + self.camera_sizey / 2))

        crop_rect = (view_left, view_top, max(1, view_right - view_left), max(1, view_bottom - view_top))
        background = self.background_pic.subsurface(crop_rect)

        if self.camera_scale_ratio != 1:
            background = pg.transform.smoothscale(background, (
                int(background.get_width() * self.camera_scale_ratio),
                int(background.get_height() * self.camera_scale_ratio)
            ))

        dest_x = int(self.camera_sizex / 2 - (self.camerax - view_left))
        dest_y = int(self.camera_sizey / 2 - (self.cameray - view_top))
        self.display_surface.blit(background, (dest_x, dest_y))

    def clamp_camera(self):
        half_width = self.camera_sizex / 2
        half_height = self.camera_sizey / 2
        self.camerax = max(half_width, min(self.camerax, self.mapSize - half_width))
        self.cameray = max(half_height, min(self.cameray, self.mapSize - half_height))

    def world_to_screen(self, x, y):
        return (
            int(x - self.camerax + self.camera_sizex / 2),
            int(y - self.cameray + self.camera_sizey / 2),
        )

    def update_size(self):
        self.camera_sizex, self.camera_sizey = self.display_surface.get_size()
        self.clamp_camera()

    def run(self, dt):
        self.display_surface.fill("green")
        self.display_surface = pg.display.get_surface()
        self._draw_background()
        self.all_sprites.customDraw()
        self.all_sprites.update(dt)


class CameraGroup(pg.sprite.Group):
    def __init__(self, camera=None):
        super().__init__()
        self.display_surface = pg.display.get_surface()
        self.camera = camera

    def _is_visible(self, rect):
        width, height = self.display_surface.get_size()
        return rect.right >= 0 and rect.left <= width and rect.bottom >= 0 and rect.top <= height

    def customDraw(self):
        for sprite in self.sprites():
            if self.camera is not None and hasattr(sprite, "world_pos"):
                if not hasattr(sprite, "rect"):
                    sprite.rect = sprite.image.get_rect()
                screen_x, screen_y = self.camera.world_to_screen(*sprite.world_pos)
                sprite.rect.center = (screen_x, screen_y)
                if not self._is_visible(sprite.rect):
                    continue
            self.display_surface.blit(sprite.image, sprite.rect)
