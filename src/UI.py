import pygame as pg
from const import *
import general_var as gv
import maps as mp


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
        self.hover_camera = None
        self.view_tab_rects = {}
        self.species_tab_rects = {}
        self.stat_row_rects = {}
        self.reset_button_rect = pg.Rect(12, 9, 76, 34)
        self.reset_callback = None
        self.hovered_metric = None
        self.pinned_metric = None
        self.chart_rect = None
        self.metric_history = {"O2": [], "CO2": [], "Biomass": [], "EntityCnt": []}
        self.species_metric_history = {"Biomass": {}, "EntityCnt": {}}
        self.species_metric_colors = {}
        self.species_population_history = {}
        self.species_lifespan_history = {}
        self.lifespan_history_sample_time = gv.simulation_time
        self.lifespan_row_rect = None
        self.species_history_elapsed = 0.0
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
        for species_histories in self.species_metric_history.values():
            species_histories.clear()
        self.species_metric_colors.clear()
        self.species_population_history.clear()
        self.species_lifespan_history.clear()
        self.lifespan_history_sample_time = gv.simulation_time
        self.lifespan_row_rect = None
        self.species_history_elapsed = 0.0
        self.history_elapsed = 0.0
        self.hovered_metric = None
        self.pinned_metric = None

    def set_species_source(self, species_source):
        self.species_source = species_source

    def set_hover_camera(self, camera):
        self.hover_camera = camera

    def _get_panel_rect(self):
        width = self.display_surface.get_width()
        height = self.display_surface.get_height()
        return pg.Rect(width - self.panel_width, 0, self.panel_width, height)

    def _panel_left(self):
        return self.display_surface.get_width() - self.panel_width

    def _draw_tab_button(self, rect, label, selected, font, active_background=(55, 105, 125), inactive_background=(48, 48, 48), active_border=(120, 220, 255), inactive_border=(100, 100, 100), text_color=(245, 245, 245)):
        pg.draw.rect(self.display_surface, active_background if selected else inactive_background, rect, border_radius=4)
        pg.draw.rect(self.display_surface, active_border if selected else inactive_border, rect, 1, border_radius=4)
        label_surface = font.render(label, True, text_color)
        self.display_surface.blit(label_surface, label_surface.get_rect(center=rect.center))

    def _draw_stat_row(self, label, value, y):
        text_color = (240, 240, 240)
        label_surface = self.font.render(f"{label}:", True, text_color)
        value_surface = self.font.render(f"{value}", True, (120, 220, 255))

        x = self._panel_left() + self.panel_padding
        self.display_surface.blit(label_surface, (x, y))
        value_x = self.display_surface.get_width() - self.panel_padding - value_surface.get_width()
        self.display_surface.blit(value_surface, (value_x, y))
        self.stat_row_rects[label] = pg.Rect(
            x,
            y - 3,
            self.panel_width - self.panel_padding * 2,
            max(label_surface.get_height(), value_surface.get_height()) + 6,
        )

    def _get_species(self):
        if self.species_source is None:
            return {}

        self._prune_lifespan_stats()
        species = {}
        for sprite in self.species_source:
            name = getattr(sprite, "type_", None)
            genes = getattr(sprite, "gene", None)
            if name and isinstance(genes, dict) and genes:
                species.setdefault(str(name), []).append(genes)
        for species_name in gv.lifespan_stats:
            species.setdefault(species_name, [])
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
    def _get_population_averages(individuals):
        totals = {attribute: 0.0 for attribute in ("atp", "nutrition", "mass")}
        counts = {attribute: 0 for attribute in totals}
        for individual in individuals:
            for attribute in totals:
                value = getattr(individual, attribute, None)
                if isinstance(value, (int, float)):
                    totals[attribute] += value
                    counts[attribute] += 1

        return {
            attribute: totals[attribute] / counts[attribute] if counts[attribute] else 0.0
            for attribute in totals
        }

    @staticmethod
    def _prune_lifespan_stats():
        cutoff = gv.simulation_time - 60.0
        for species_name, records in list(gv.lifespan_stats.items()):
            recent_records = [
                record for record in records
                if record[0] >= cutoff
            ]
            if recent_records:
                gv.lifespan_stats[species_name] = recent_records
            else:
                del gv.lifespan_stats[species_name]

    @staticmethod
    def _get_average_lifespan(species_name):
        UI._prune_lifespan_stats()
        stats = gv.lifespan_stats.get(species_name)
        if not stats:
            return None
        return sum(age for _, age in stats) / len(stats)

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
            self._draw_tab_button(
                self.view_tab_rects[view],
                label,
                self.active_view == view,
                self.tab_font,
            )

    def _draw_toolbar(self):
        panel_left = max(0, self.display_surface.get_width() - self.panel_width)
        toolbar_rect = pg.Rect(0, 0, panel_left, self.TOOLBAR_HEIGHT)
        pg.draw.rect(self.display_surface, (30, 34, 35), toolbar_rect)
        pg.draw.line(self.display_surface, (85, 100, 105), toolbar_rect.bottomleft, toolbar_rect.bottomright, 1)
        button_width = min(76, max(0, panel_left - 24))
        self.reset_button_rect = pg.Rect(12, 9, button_width, 34)
        if button_width >= 48:
            self._draw_tab_button(
                self.reset_button_rect,
                "Reset",
                False,
                self.tab_font,
                active_background=(70, 75, 65),
                inactive_background=(70, 75, 65),
                active_border=(150, 175, 130),
                inactive_border=(150, 175, 130),
            )

    @staticmethod
    def _get_overall_metrics(species_counts=None):
        air_amount = max(gv.AirAmount, 1)
        o2_value = gv.O2Amount / air_amount * 100
        co2_value = gv.CO2Amount / air_amount * 100
        return {
            "O2": o2_value,
            "CO2": co2_value,
            "Biomass": gv.bioMass,
            "EntityCnt": sum(species_counts.values()) if species_counts is not None else gv.entCnt,
        }

    def _draw_overall_data(self, metrics):
        self.stat_row_rects = {}
        self._draw_stat_row("O2", f"{metrics['O2']:.2f}%", 72)
        self._draw_stat_row("CO2", f"{metrics['CO2']:.2f}%", 108)
        self._draw_stat_row("Biomass", self._format_scaled_count(metrics["Biomass"]), 144)
        self._draw_stat_row("EntityCnt", f"{metrics['EntityCnt']:.1f}", 180)

    @staticmethod
    def _format_scaled_count(value):
        absolute_value = abs(value)
        if absolute_value >= 1_000_000:
            return f"{value / 1_000_000:.3f}M"
        if absolute_value >= 1_000:
            return f"{value / 1_000:.3f}K"
        return f"{value:.1f}"

    def _get_species_metrics(self):
        species_metrics = {
            "Biomass": {},
            "EntityCnt": {},
        }
        species_metric_colors = getattr(self, "species_metric_colors", None)
        if species_metric_colors is None:
            species_metric_colors = self.species_metric_colors = {}
        for sprite in getattr(self, "species_source", None) or ():
            species_name = getattr(sprite, "type_", None)
            if not species_name:
                continue
            species_name = str(species_name)
            species_metrics["EntityCnt"][species_name] = (
                species_metrics["EntityCnt"].get(species_name, 0) + 1
            )
            mass = getattr(sprite, "mass", None)
            if isinstance(mass, (int, float)):
                species_metrics["Biomass"][species_name] = (
                    species_metrics["Biomass"].get(species_name, 0) + mass
                )

            if species_name not in species_metric_colors:
                color = getattr(sprite, "default_color", DEFAULT_COLORS.get(species_name, (220, 220, 220)))
                species_metric_colors[species_name] = tuple(color[:3])
        return species_metrics

    def _sample_metrics(self, values, species_metrics=None):
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

        if species_metrics is None:
            species_metrics = self._get_species_metrics()

        for metric, current_values in species_metrics.items():
            histories = self.species_metric_history[metric]
            species_names = histories.keys() | current_values.keys()
            for species_name in species_names:
                history = histories.get(species_name)
                if history is None:
                    history = [0.0] * max(0, len(self.metric_history[metric]) - 1)
                    histories[species_name] = history
                history.append(float(current_values.get(species_name, 0)))
                if len(history) > max_samples:
                    del history[:len(history) - max_samples]

    def _sample_lifespan_history(self):
        sample_time = gv.simulation_time
        last_sample_time = getattr(self, "lifespan_history_sample_time", sample_time)
        elapsed = sample_time - last_sample_time
        if elapsed < 0:
            self.lifespan_history_sample_time = sample_time
            return
        if elapsed < self.history_interval:
            return

        self.lifespan_history_sample_time = sample_time
        histories = getattr(self, "species_lifespan_history", None)
        if histories is None:
            histories = self.species_lifespan_history = {}
        max_samples = int(self.history_duration / self.history_interval) + 1
        for species_name in self._get_species():
            average_lifespan = self._get_average_lifespan(species_name)
            if average_lifespan is None:
                histories.pop(species_name, None)
                continue

            history = histories.setdefault(species_name, [])
            history.append(average_lifespan)
            if len(history) > max_samples:
                del history[:len(history) - max_samples]

    def _sample_species_populations(self, dt, species_counts=None):
        self.species_history_elapsed += dt
        if self.species_history_elapsed < self.history_interval:
            return

        self.species_history_elapsed %= self.history_interval
        if species_counts is None:
            species_counts = self._get_species_metrics()["EntityCnt"]

        max_samples = int(self.history_duration / self.history_interval) + 1
        species_names = self.species_population_history.keys() | species_counts.keys()
        for species_name in species_names:
            history = self.species_population_history.setdefault(species_name, [])
            history.append(float(species_counts.get(species_name, 0)))
            if len(history) > max_samples:
                del history[:len(history) - max_samples]

    def _draw_metric_chart(self, metric, panel_rect, history=None, title=None):
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

        if history is None:
            history = self.metric_history[metric]
        title_surface = self.tab_font.render(title or f"{metric} history", True, (220, 235, 240))
        self.display_surface.blit(title_surface, (self.chart_rect.left + 10, self.chart_rect.top + 8))

        species_series = None
        if metric in self.species_metric_history:
            species_series = {
                name: values[-(round(self.chart_visible_duration / self.history_interval) + 1):]
                for name, values in self.species_metric_history[metric].items()
            }
            species_series = {name: values for name, values in species_series.items() if values}

        if species_series is not None and not species_series:
            message = self.detail_font.render("Collecting data...", True, (155, 165, 170))
            self.display_surface.blit(message, message.get_rect(center=self.chart_rect.center))
            return
        if species_series is None and not history:
            message = self.detail_font.render("Collecting data...", True, (155, 165, 170))
            self.display_surface.blit(message, message.get_rect(center=self.chart_rect.center))
            return

        visible_sample_count = round(self.chart_visible_duration / self.history_interval) + 1
        if species_series is None:
            chart_history = history[-visible_sample_count:]
            series = None
            all_values = chart_history
        else:
            species_series = {
                name: values[-visible_sample_count:]
                for name, values in species_series.items()
            }
            series = species_series
            all_values = [value for values in series.values() for value in values]
            chart_history = max(series.values(), key=len)

        minimum = min(all_values)
        maximum = max(all_values)
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
            self.chart_rect.top + (58 if series is not None else 42),
            self.chart_rect.width - y_axis_label_width - 22,
            self.chart_rect.height - (92 if series is not None else 76),
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
            self.display_surface.blit(label_surface, label_surface.get_rect(midtop=(x, graph.bottom + 10)))

        if len(chart_history) < 2:
            message = self.detail_font.render("Collecting data...", True, (155, 165, 170))
            self.display_surface.blit(message, message.get_rect(center=graph.center))
            return

        if series is not None:
            self._draw_species_metric_legend(series)
            for species_name, species_history in series.items():
                self._draw_chart_series(
                    species_history,
                    graph,
                    minimum,
                    value_range,
                    self.species_metric_colors.get(species_name, (220, 220, 220)),
                )
        else:
            self._draw_chart_series(chart_history, graph, minimum, value_range, (90, 210, 235))

    def _draw_chart_series(self, history, graph, minimum, value_range, color):
        if len(history) < 2:
            return
        points = []
        for index, value in enumerate(history):
            x = graph.left + round(index * graph.width / (len(history) - 1))
            y = graph.bottom - round((value - minimum) / value_range * graph.height)
            points.append((x, y))
        pg.draw.lines(self.display_surface, color, False, points, 2)

    def _draw_species_metric_legend(self, series):
        x = self.chart_rect.left + 10
        y = self.chart_rect.top + 32
        right = self.chart_rect.right - 10
        line_height = self.detail_font.get_linesize() + 2
        for species_name in sorted(series):
            label = self._truncate_text(self.detail_font, species_name, 90)
            label_surface = self.detail_font.render(label, True, (220, 230, 235))
            item_width = label_surface.get_width() + 18
            if x + item_width > right:
                x = self.chart_rect.left + 10
                y += line_height
            if y + line_height > self.chart_rect.top + 58:
                break
            color = self.species_metric_colors.get(species_name, (220, 220, 220))
            pg.draw.line(self.display_surface, color, (x, y + line_height // 2), (x + 9, y + line_height // 2), 2)
            self.display_surface.blit(label_surface, (x + 13, y))
            x += item_width

    @staticmethod
    def _format_chart_value(metric, value):
        if metric in ("O2", "CO2"):
            return f"{value:.2f}%"
        if metric in ("EntityCnt", "Population"):
            return f"{value:.0f}"
        if metric == "Biomass":
            return UI._format_scaled_count(value)
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

    @staticmethod
    def _format_hover_value(value):
        if isinstance(value, (int, float)):
            return f"{value:.3g}"
        return str(value)

    def _get_hover_info(self, mouse_pos):
        camera = getattr(self, "hover_camera", None)
        species_source = getattr(self, "species_source", None)
        if camera is None or species_source is None:
            return []

        panel_left = self.display_surface.get_width() - self.panel_width
        if not (0 <= mouse_pos[0] < panel_left and 0 <= mouse_pos[1] < self.display_surface.get_height()):
            return []

        world_x = mouse_pos[0] + camera.camerax - camera.camera_sizex / 2
        world_y = mouse_pos[1] + camera.cameray - camera.camera_sizey / 2
        lines = []
        nutrition_map = getattr(gv, "nutritionMap", None)
        if getattr(nutrition_map, "ndim", 0) >= 2:
            lines.append(f"Nutrition value: {mp.get_nutrition_value(int(world_x), int(world_y)):.1f}")

        hovered_sprite = next(
            (
                sprite
                for sprite in reversed(species_source.sprites())
                if getattr(sprite, "rect", None) is not None
                and sprite.rect.collidepoint(mouse_pos)
            ),
            None,
        )
        if hovered_sprite is None:
            return lines

        species_name = getattr(hovered_sprite, "type_", None)
        if species_name:
            lines.append(f"Species: {species_name}")

        genes = getattr(hovered_sprite, "gene", None)
        if isinstance(genes, dict):
            lines.extend(
                f"{name}: {self._format_hover_value(value)}"
                for name, value in sorted(genes.items())
            )

        for attribute, label in (
            ("atp", "ATP"),
            ("nutrition", "Individual nutrition"),
            ("mass", "Mass"),
            ("age", "Age"),
            ("local_density", "Local density"),
        ):
            value = getattr(hovered_sprite, attribute, None)
            if isinstance(value, (int, float)):
                lines.append(f"{label}: {self._format_hover_value(value)}")

        return lines

    def _draw_hover_info(self):
        lines = self._get_hover_info(pg.mouse.get_pos())
        if not lines:
            return

        padding = 10
        line_height = self.detail_font.get_linesize() + 3
        max_lines = max(1, (self.display_surface.get_height() - padding * 2) // line_height)
        lines = lines[:max_lines]
        text_surfaces = [self.detail_font.render(line, True, (235, 240, 240)) for line in lines]
        width = min(
            self.display_surface.get_width() - padding * 2,
            max(surface.get_width() for surface in text_surfaces) + padding * 2,
        )
        height = len(text_surfaces) * line_height + padding
        panel = pg.Surface((width, height), pg.SRCALPHA)
        panel.fill((20, 24, 26, 220))
        x = padding
        y = self.display_surface.get_height() - height - padding
        self.display_surface.blit(panel, (x, y))
        for index, text_surface in enumerate(text_surfaces):
            self.display_surface.blit(text_surface, (x + padding, y + 5 + index * line_height))

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
            self._draw_tab_button(rect, label, name == self.selected_species, self.tab_font)
            x += width + gap

        return y + tab_height + 14

    def _draw_biology_data(self, panel_rect, species_counts=None):
        self.lifespan_row_rect = None
        species = self._get_species()
        species_names = sorted(species)
        if not species_names:
            self.species_tab_rects = {}
            message = self.detail_font.render("No biological data", True, (180, 180, 180))
            self.display_surface.blit(message, (panel_rect.left + self.panel_padding, 72))
            return

        if self.selected_species not in species:
            self.selected_species = species_names[0]

        if species_counts is None:
            species_counts = self._get_species_metrics()["EntityCnt"]
        population = species_counts.get(self.selected_species, 0)
        heading = self.tab_font.render(f"{self.selected_species}  |  population: {population}", True, (240, 240, 240))
        self.display_surface.blit(heading, (panel_rect.left + self.panel_padding, 68))
        row_y = self._draw_species_tabs(panel_rect, species_names)
        gene_averages = self._get_gene_averages(species[self.selected_species])
        species_individuals = [
            sprite for sprite in (self.species_source or ())
            if getattr(sprite, "type_", None) == self.selected_species
        ]
        population_averages = self._get_population_averages(species_individuals)
        content_x = panel_rect.left + self.panel_padding
        content_width = self.panel_width - self.panel_padding * 2
        chart_bottom = panel_rect.bottom - self.panel_padding
        chart_height = min(210, chart_bottom - 228)
        content_bottom = chart_bottom - chart_height - 8

        row_y += 4
        pg.draw.line(
            self.display_surface,
            (85, 100, 105),
            (content_x, row_y),
            (content_x + content_width, row_y),
            1,
        )
        row_y += 8
        for label, value in (
            ("Avg ATP", f"{population_averages['atp']:.1f}"),
            ("Avg Nutrition", f"{population_averages['nutrition']:.1f}"),
            ("Avg Mass", f"{population_averages['mass']:.1f}"),
        ):
            if row_y + 20 > content_bottom:
                break
            text = self.detail_font.render(f"{label}: {value}", True, (150, 210, 190))
            self.display_surface.blit(text, (content_x, row_y))
            row_y += 22

        average_lifespan = self._get_average_lifespan(self.selected_species)
        lifespan_text = (
            f"{average_lifespan:.1f} ticks" if average_lifespan is not None else "n/a"
        )
        self.lifespan_row_rect = None
        if row_y + 20 <= content_bottom:
            text = self.detail_font.render(
                f"Avg Lifespan: {lifespan_text}",
                True,
                (150, 210, 190),
            )
            self.display_surface.blit(text, (content_x, row_y))
            self.lifespan_row_rect = pg.Rect(
                content_x,
                row_y - 2,
                content_width,
                text.get_height() + 4,
            )
            row_y += 28

        if row_y + 24 <= content_bottom:
            text = self.detail_font.render("Average genes", True, (220, 235, 240))
            self.display_surface.blit(text, (content_x, row_y))
            row_y += 24

        for gene, average in sorted(gene_averages.items()):
            if row_y + 24 > content_bottom:
                return
            value_text = f"{average:.6f}"
            label = self._truncate_text(self.detail_font, f"{gene}: {value_text}", content_width)
            text = self.detail_font.render(label, True, (230, 230, 230))
            self.display_surface.blit(text, (content_x, row_y))
            row_y += 28

    def _draw_species_population_chart(self, panel_rect):
        history = self.species_population_history.get(self.selected_species, [])
        self._draw_metric_chart(
            "Population",
            panel_rect,
            history=history,
            title=f"{self.selected_species} population",
        )

    def _draw_species_lifespan_chart(self, panel_rect):
        history = getattr(self, "species_lifespan_history", {}).get(self.selected_species, [])
        self._draw_metric_chart(
            "Avg Lifespan",
            panel_rect,
            history=history,
            title=f"{self.selected_species} average lifespan",
        )

    def _is_lifespan_row_hovered(self, mouse_pos=None):
        row_rect = getattr(self, "lifespan_row_rect", None)
        if row_rect is None:
            return False
        return row_rect.collidepoint(mouse_pos or pg.mouse.get_pos())

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
        species_metrics = self._get_species_metrics()
        species_counts = species_metrics["EntityCnt"]
        self._sample_species_populations(dt, species_counts)
        self._sample_lifespan_history()
        metrics = self._get_overall_metrics(species_counts)
        self._sample_metrics(metrics, species_metrics)
        self._draw_toolbar()
        panel_rect = self._get_panel_rect()

        pg.draw.rect(self.display_surface, self.panel_color, panel_rect)
        pg.draw.rect(self.display_surface, self.panel_border_color, panel_rect, 2)
        self._draw_view_tabs(panel_rect)
        if self.active_view == "overall":
            self.species_tab_rects = {}
            self._draw_overall_data(metrics)
            self._update_hovered_metric(panel_rect)
            chart_metric = self.pinned_metric or self.hovered_metric
            if chart_metric:
                self._draw_metric_chart(chart_metric, panel_rect)
            else:
                self.chart_rect = None
        else:
            self.chart_rect = None
            self._draw_biology_data(panel_rect, species_counts)
            if self.selected_species is not None:
                if self._is_lifespan_row_hovered():
                    self._draw_species_lifespan_chart(panel_rect)
                else:
                    self._draw_species_population_chart(panel_rect)

        self.update(dt)
        self._draw_hover_info()

    def update_elements(self):
        pass
