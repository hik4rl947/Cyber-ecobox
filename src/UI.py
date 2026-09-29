import pygame as pg
from const import *
import general_var as gv


class UI(pg.sprite.Sprite):
    TOOLBAR_HEIGHT = 52

    def __init__(self):
        super().__init__()
        self.display_surface = pg.display.get_surface()
        self.panel_width = 460
        self.panel_color = (35, 35, 35)
        self.panel_border_color = (180, 180, 180)
        self.panel_padding = 16
        self.font = pg.font.Font("orbitron-bold.otf", 26)
        self.tab_font = pg.font.Font("orbitron-bold.otf", 17)
        self.detail_font = pg.font.Font("orbitron-bold.otf", 14)
        self.active_view = "overall"
        self.selected_species = None
        self.species_source = None
        self.view_tab_rects = {}
        self.species_tab_rects = {}
        self.stat_row_rects = {}
        self.reset_button_rect = pg.Rect(12, 9, 76, 34)
        self.reset_callback = None
        self.hovered_metric = None
        self.pinned_metric = None
        self.chart_rect = None
        self.metric_history = {"O2": [], "CO2": [], "Biomass": [], "EntityCnt": []}
        self.history_elapsed = 0.0
        self.history_interval = 0.5
        self.history_duration = 60.0
        self.chart_visible_duration = 20.0
        self.chart_min_duration = 2.5
        self._frame_dt = 0.0

    def set_reset_callback(self, callback):
        self.reset_callback = callback

    def reset_history(self):
        for history in self.metric_history.values():
            history.clear()
        self.history_elapsed = 0.0
        self.hovered_metric = None
        self.pinned_metric = None

    def set_species_source(self, species_source):
        self.species_source = species_source

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
        self.stat_row_rects[label] = pg.Rect(
            x, y - 3, self.panel_width - self.panel_padding * 2, max(label_surface.get_height(), value_surface.get_height()) + 6
        )

    def _get_species(self):
        if self.species_source is None:
            return {}

        species = {}
        for sprite in self.species_source:
            name = getattr(sprite, "type_", None)
            genes = getattr(sprite, "gene", None)
            if name and isinstance(genes, dict) and genes:
                species.setdefault(str(name), []).append(genes)
        return species

    @staticmethod
    def _get_gene_averages(gene_sets):
        totals = {}
        for genes in gene_sets:
            for gene, value in genes.items():
                try:
                    numeric_value = float(value)
                except (TypeError, ValueError):
                    continue
                total, count = totals.get(gene, (0.0, 0))
                totals[gene] = (total + numeric_value, count + 1)

        return {gene: total / count for gene, (total, count) in totals.items()}

    @staticmethod
    def _truncate_text(font, text, max_width):
        if font.size(text)[0] <= max_width:
            return text
        while text and font.size(text + "...")[0] > max_width:
            text = text[:-1]
        return text + "..."

    def _draw_view_tabs(self, panel_rect):
        tab_y = 12
        tab_height = 34
        gap = 8
        tab_width = (self.panel_width - self.panel_padding * 2 - gap) // 2
        self.view_tab_rects = {
            "overall": pg.Rect(panel_rect.left + self.panel_padding, tab_y, tab_width, tab_height),
            "biology": pg.Rect(panel_rect.left + self.panel_padding + tab_width + gap, tab_y, tab_width, tab_height),
        }

        for view, label in (("overall", "Overall"), ("biology", "Biology")):
            rect = self.view_tab_rects[view]
            selected = self.active_view == view
            background = (55, 105, 125) if selected else (48, 48, 48)
            border = (120, 220, 255) if selected else (100, 100, 100)
            pg.draw.rect(self.display_surface, background, rect, border_radius=4)
            pg.draw.rect(self.display_surface, border, rect, 1, border_radius=4)
            text = self.tab_font.render(label, True, (245, 245, 245))
            self.display_surface.blit(text, text.get_rect(center=rect.center))

    def _draw_toolbar(self):
        panel_left = max(0, self.display_surface.get_width() - self.panel_width)
        toolbar_rect = pg.Rect(0, 0, panel_left, self.TOOLBAR_HEIGHT)
        pg.draw.rect(self.display_surface, (30, 34, 35), toolbar_rect)
        pg.draw.line(self.display_surface, (85, 100, 105), toolbar_rect.bottomleft, toolbar_rect.bottomright, 1)
        button_width = min(76, max(0, panel_left - 24))
        self.reset_button_rect = pg.Rect(12, 9, button_width, 34)
        if button_width >= 48:
            pg.draw.rect(self.display_surface, (70, 75, 65), self.reset_button_rect, border_radius=4)
            pg.draw.rect(self.display_surface, (150, 175, 130), self.reset_button_rect, 1, border_radius=4)
            reset_text = self.tab_font.render("Reset", True, (245, 245, 245))
            self.display_surface.blit(reset_text, reset_text.get_rect(center=self.reset_button_rect.center))

    def _draw_overall_data(self):
        air_amount = max(gv.AirAmount, 1)
        o2_value = gv.O2Amount / air_amount * 100
        co2_value = gv.CO2Amount / air_amount * 100
        self.stat_row_rects = {}
        self._draw_stat_row("O2", f"{o2_value:.2f}%", 72)
        self._draw_stat_row("CO2", f"{co2_value:.2f}%", 108)
        self._draw_stat_row("Biomass", f"{gv.bioMass:.1f}", 144)
        self._draw_stat_row("EntityCnt", f"{gv.entCnt:.1f}", 180)
        self._sample_metrics({"O2": o2_value, "CO2": co2_value, "Biomass": gv.bioMass, "EntityCnt": gv.entCnt})

    def _sample_metrics(self, values):
        self.history_elapsed += self._frame_dt
        if self.history_elapsed < self.history_interval:
            return

        self.history_elapsed %= self.history_interval
        max_samples = int(self.history_duration / self.history_interval) + 1
        for metric, value in values.items():
            history = self.metric_history[metric]
            history.append(float(value))
            if len(history) > max_samples:
                del history[:len(history) - max_samples]

    def _draw_metric_chart(self, metric, panel_rect):
        chart_top = 228
        chart_bottom = panel_rect.bottom - self.panel_padding
        chart_height = min(210, chart_bottom - chart_top)
        if chart_height < 90:
            self.chart_rect = None
            return

        self.chart_rect = pg.Rect(
            panel_rect.left + self.panel_padding,
            chart_bottom - chart_height,
            self.panel_width - self.panel_padding * 2,
            chart_height,
        )
        pg.draw.rect(self.display_surface, (27, 31, 33), self.chart_rect, border_radius=3)
        pg.draw.rect(self.display_surface, (85, 100, 105), self.chart_rect, 1, border_radius=3)

        history = self.metric_history[metric]
        title = self.tab_font.render(f"{metric} history", True, (220, 235, 240))
        self.display_surface.blit(title, (self.chart_rect.left + 10, self.chart_rect.top + 8))

        if not history:
            message = self.detail_font.render("Collecting data...", True, (155, 165, 170))
            self.display_surface.blit(message, message.get_rect(center=self.chart_rect.center))
            return

        visible_sample_count = round(self.chart_visible_duration / self.history_interval) + 1
        chart_history = history[-visible_sample_count:]
        minimum = min(chart_history)
        maximum = max(chart_history)
        if maximum == minimum:
            padding = max(abs(maximum) * 0.02, 1.0) / 2
            minimum -= padding
            maximum += padding
        value_range = maximum - minimum
        y_values = (maximum, (minimum + maximum) / 2, minimum)
        y_labels = [self._format_chart_value(metric, value) for value in y_values]
        y_axis_label_width = 68
        graph = pg.Rect(
            self.chart_rect.left + y_axis_label_width + 8,
            self.chart_rect.top + 42,
            self.chart_rect.width - y_axis_label_width - 22,
            self.chart_rect.height - 76,
        )
        if graph.width <= 0 or graph.height <= 0:
            return

        axis_color = (140, 155, 160)
        for fraction, label in zip((0.0, 0.5, 1.0), y_labels):
            y = graph.top + round(graph.height * fraction)
            pg.draw.line(self.display_surface, (58, 68, 72), (graph.left, y), (graph.right, y), 1)
            label_surface = self.detail_font.render(label, True, (175, 185, 190))
            self.display_surface.blit(label_surface, label_surface.get_rect(midright=(graph.left - 8, y)))

        pg.draw.line(self.display_surface, axis_color, graph.bottomleft, graph.topleft, 1)
        pg.draw.line(self.display_surface, axis_color, graph.bottomleft, graph.bottomright, 1)
        elapsed = max(0.0, (len(chart_history) - 1) * self.history_interval)
        time_labels = (f"-{elapsed:.1f}s", f"-{elapsed / 2:.1f}s", "0s")
        for fraction, label in zip((0.0, 0.5, 1.0), time_labels):
            x = graph.left + round(graph.width * fraction)
            pg.draw.line(self.display_surface, axis_color, (x, graph.bottom), (x, graph.bottom + 3), 1)
            label_surface = self.detail_font.render(label, True, (175, 185, 190))
            self.display_surface.blit(label_surface, label_surface.get_rect(midtop=(x, graph.bottom + 4)))

        if len(chart_history) < 2:
            message = self.detail_font.render("Collecting data...", True, (155, 165, 170))
            self.display_surface.blit(message, message.get_rect(center=graph.center))
            return

        points = []
        for index, value in enumerate(chart_history):
            x = graph.left + round(index * graph.width / (len(chart_history) - 1))
            y = graph.bottom - round((value - minimum) / value_range * graph.height)
            points.append((x, y))
        pg.draw.lines(self.display_surface, (90, 210, 235), False, points, 2)

    @staticmethod
    def _format_chart_value(metric, value):
        if metric in ("O2", "CO2"):
            return f"{value:.2f}%"
        if metric == "EntityCnt":
            return f"{value:.0f}"
        return f"{value:.1f}"

    def _update_hovered_metric(self, panel_rect):
        mouse_pos = pg.mouse.get_pos()
        hovered = next(
            (metric for metric, rect in self.stat_row_rects.items() if rect.collidepoint(mouse_pos)),
            None,
        )
        if hovered is not None:
            self.hovered_metric = hovered
        elif self.chart_rect is None or not self.chart_rect.collidepoint(mouse_pos):
            self.hovered_metric = None

    def _draw_species_tabs(self, panel_rect, species_names):
        x = panel_rect.left + self.panel_padding
        y = 106
        max_x = panel_rect.right - self.panel_padding
        tab_height = 30
        gap = 6
        self.species_tab_rects = {}

        for name in species_names:
            label = self._truncate_text(self.tab_font, name, self.panel_width - self.panel_padding * 2 - 20)
            width = min(self.tab_font.size(label)[0] + 20, self.panel_width - self.panel_padding * 2)
            if x + width > max_x:
                x = panel_rect.left + self.panel_padding
                y += tab_height + gap
            rect = pg.Rect(x, y, width, tab_height)
            self.species_tab_rects[name] = rect
            selected = name == self.selected_species
            pg.draw.rect(self.display_surface, (55, 105, 125) if selected else (48, 48, 48), rect, border_radius=3)
            pg.draw.rect(self.display_surface, (120, 220, 255) if selected else (100, 100, 100), rect, 1, border_radius=3)
            text = self.tab_font.render(label, True, (245, 245, 245))
            self.display_surface.blit(text, text.get_rect(center=rect.center))
            x += width + gap

        return y + tab_height + 14

    def _draw_biology_data(self, panel_rect):
        species = self._get_species()
        species_names = sorted(species)
        if not species_names:
            self.species_tab_rects = {}
            message = self.detail_font.render("No biological data", True, (180, 180, 180))
            self.display_surface.blit(message, (panel_rect.left + self.panel_padding, 72))
            return

        if self.selected_species not in species:
            self.selected_species = species_names[0]

        population = len(species[self.selected_species])
        heading = self.tab_font.render(f"{self.selected_species}  |  population: {population}", True, (240, 240, 240))
        self.display_surface.blit(heading, (panel_rect.left + self.panel_padding, 68))
        row_y = self._draw_species_tabs(panel_rect, species_names)
        gene_averages = self._get_gene_averages(species[self.selected_species])
        content_x = panel_rect.left + self.panel_padding
        content_width = self.panel_width - self.panel_padding * 2

        for gene, average in sorted(gene_averages.items()):
            if row_y + 24 > panel_rect.bottom:
                return
            value_text = f"{average:.6f}"
            label = self._truncate_text(self.detail_font, f"{gene}: {value_text}", content_width)
            text = self.detail_font.render(label, True, (230, 230, 230))
            self.display_surface.blit(text, (content_x, row_y))
            row_y += 28

    def handle_event(self, event):
        if event.type == pg.MOUSEWHEEL:
            mouse_pos = getattr(event, "pos", None) or pg.mouse.get_pos()
            if self.chart_rect and self.chart_rect.collidepoint(mouse_pos) and event.y:
                scale = 0.8 if event.y > 0 else 1.25
                self.chart_visible_duration = min(
                    self.history_duration,
                    max(self.chart_min_duration, self.chart_visible_duration * scale),
                )
                return True
            return False

        if event.type != pg.MOUSEBUTTONUP or event.button != 1:
            return False

        if self.reset_button_rect and self.reset_button_rect.collidepoint(event.pos):
            if self.reset_callback:
                self.reset_callback()
            return True

        panel_rect = self._get_panel_rect()
        if panel_rect.collidepoint(event.pos):
            for view, rect in self.view_tab_rects.items():
                if rect.collidepoint(event.pos):
                    self.active_view = view
                    return True

            if self.active_view == "overall":
                for metric, rect in self.stat_row_rects.items():
                    if rect.collidepoint(event.pos):
                        self.pinned_metric = None if self.pinned_metric == metric else metric
                        return True

            if self.active_view == "biology":
                for species, rect in self.species_tab_rects.items():
                    if rect.collidepoint(event.pos):
                        self.selected_species = species
                        return True
                return True

        if event.pos[0] < panel_rect.left and event.pos[1] < self.TOOLBAR_HEIGHT:
            return True
        return False

    def display(self, dt):
        self._frame_dt = dt
        self._draw_toolbar()
        panel_rect = self._get_panel_rect()

        pg.draw.rect(self.display_surface, self.panel_color, panel_rect)
        pg.draw.rect(self.display_surface, self.panel_border_color, panel_rect, 2)
        self._draw_view_tabs(panel_rect)
        if self.active_view == "overall":
            self.species_tab_rects = {}
            self._draw_overall_data()
            self._update_hovered_metric(panel_rect)
            chart_metric = self.pinned_metric or self.hovered_metric
            if chart_metric:
                self._draw_metric_chart(chart_metric, panel_rect)
            else:
                self.chart_rect = None
        else:
            self.chart_rect = None
            self._draw_biology_data(panel_rect)

        self.update(dt)

    def update_elements(self):
        pass
