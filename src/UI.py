import pygame as pg
from const import *
import general_var as gv


class UI(pg.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.display_surface = pg.display.get_surface()
        self.panel_width = 460
        self.panel_color = (35, 35, 35)
        self.panel_border_color = (180, 180, 180)
        self.panel_padding = 16
        self.font = pg.font.Font("orbitron-bold.otf", 26)

    def _get_panel_rect(self):
        width = self.display_surface.get_width()
        height = self.display_surface.get_height()
        return pg.Rect(width - self.panel_width, 0, self.panel_width, height)

    def _draw_stat_row(self, label, value, y):
        text_color = (240, 240, 240)
        label_surface = self.font.render(f"{label}:", True, text_color)
        value_surface = self.font.render(f"{value}", True, (120, 220, 255))

        x = self.display_surface.get_width() - self.panel_width + self.panel_padding
        self.display_surface.blit(label_surface, (x, y))
        value_x = self.display_surface.get_width() - self.panel_padding - value_surface.get_width()
        self.display_surface.blit(value_surface, (value_x, y))

    def display(self, dt, biomass):
        panel_rect = self._get_panel_rect()

        pg.draw.rect(self.display_surface, self.panel_color, panel_rect)
        pg.draw.rect(self.display_surface, self.panel_border_color, panel_rect, 2)

        o2_value = gv.O2Amount / gv.AirAmount * 100
        co2_value = gv.CO2Amount / gv.AirAmount * 100
        self._draw_stat_row("O2", f"{o2_value:.2f}%", 24)
        self._draw_stat_row("CO2", f"{co2_value:.2f}%", 60)
        self._draw_stat_row("Biomass", f"{biomass:.1f}", 96)

        # resource info
        #   o2concentration
        #   cursor bio_concentration
        # creature info(if have)
        # page II
        # population   genetic pattern

        self.update(dt)

    def update_elements(self):
        pass
