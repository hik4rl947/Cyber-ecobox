import math
import random
import general_var as gv
import pygame as pg
import maps as mp
from const import *


class Individual(pg.sprite.Sprite):
    def __init__(self, x, y, type_):
        super().__init__()
        self.nutrition = 0
        self.mass = 1
        self.world_pos = [float(x), float(y)]
        self.pos = self.world_pos
        self.type_ = type_
        self.image = pg.Surface(DEFAULT_IMG_SIZES.get(self.type_, (20, 20)), pg.SRCALPHA)
        self.rect = self.image.get_rect()
        self.local_density = 1
        self.default_color = DEFAULT_COLORS.get(self.type_, (255, 255, 255, 255))
        self.default_size = DEFAULT_SIZES.get(self.type_, 1)
        self.size = self.default_size

    def action(self):
        pass

    def rebuild_visual(self):
        size = DEFAULT_IMG_SIZES.get(self.type_, (20, 20))
        self.image = pg.Surface(size, pg.SRCALPHA)
        self.image.fill((0, 0, 0, 0))
        pg.draw.circle(self.image, self.default_color, (size[0] // 2, size[1] // 2), self.size)
        self.rect = self.image.get_rect()

    def move_world(self, dx, dy):
        self.world_pos[0] += dx
        self.world_pos[1] += dy
        self.pos = self.world_pos

    def get_type(self):
        return self.type_


def calc_distance(a: Individual, b: Individual):
    return math.sqrt((a.pos[0] - b.pos[0]) ** 2 + (a.pos[1] - b.pos[1]) ** 2)


class GrassSpatialIndex:
    CELL_SIZE = 75

    def __init__(self, grasses):
        self.buckets = {}
        self.max_grass_size = 0
        for grass in grasses:
            cell = self._get_cell(grass.world_pos)
            self.buckets.setdefault(cell, []).append(grass)
            self.max_grass_size = max(self.max_grass_size, grass.size)

    @classmethod
    def _get_cell(cls, position):
        return (
            int(position[0] // cls.CELL_SIZE),
            int(position[1] // cls.CELL_SIZE),
        )

    def query(self, position, radius):
        cell_x, cell_y = self._get_cell(position)
        cell_range = math.ceil(radius / self.CELL_SIZE)
        radius_squared = radius * radius
        nearby = []
        for x in range(cell_x - cell_range, cell_x + cell_range + 1):
            for y in range(cell_y - cell_range, cell_y + cell_range + 1):
                for grass in self.buckets.get((x, y), ()):
                    dx = position[0] - grass.world_pos[0]
                    dy = position[1] - grass.world_pos[1]
                    if dx * dx + dy * dy <= radius_squared:
                        nearby.append(grass)
        return nearby

    def remove(self, grass):
        cell = self._get_cell(grass.world_pos)
        bucket = self.buckets.get(cell)
        if bucket and grass in bucket:
            bucket.remove(grass)
            if not bucket:
                del self.buckets[cell]


class HerbivoreSpatialIndex:
    CELL_SIZE = 60

    def __init__(self, herbivores):
        self.buckets = {}
        self.positions = {}
        for herbivore in herbivores:
            position = tuple(herbivore.world_pos)
            self.positions[herbivore] = position
            cell = self._get_cell(position)
            self.buckets.setdefault(cell, []).append((herbivore, position))

    @classmethod
    def _get_cell(cls, position):
        return (
            int(position[0] // cls.CELL_SIZE),
            int(position[1] // cls.CELL_SIZE),
        )

    def query(self, position, radius):
        cell_x, cell_y = self._get_cell(position)
        cell_range = math.ceil(radius / self.CELL_SIZE)
        radius_squared = radius * radius
        nearby = []
        for x in range(cell_x - cell_range, cell_x + cell_range + 1):
            for y in range(cell_y - cell_range, cell_y + cell_range + 1):
                for herbivore, herbivore_position in self.buckets.get((x, y), ()):
                    dx = position[0] - herbivore_position[0]
                    dy = position[1] - herbivore_position[1]
                    if dx * dx + dy * dy <= radius_squared:
                        nearby.append((herbivore, herbivore_position))
        return nearby

    def position_of(self, herbivore):
        return self.positions[herbivore]


def get_local_density(creatures, radius=20):
    creatures = list(creatures)
    buckets = {}
    for creature in creatures:
        species = (type(creature), creature.type_)
        cell = (int(creature.world_pos[0] // radius), int(creature.world_pos[1] // radius))
        buckets.setdefault((species, cell), []).append(creature)

    radius_squared = radius * radius
    for creature in creatures:
        species = (type(creature), creature.type_)
        cell_x = int(creature.world_pos[0] // radius)
        cell_y = int(creature.world_pos[1] // radius)
        density = 0
        for x in range(cell_x - 1, cell_x + 2):
            for y in range(cell_y - 1, cell_y + 2):
                for neighbor in buckets.get((species, (x, y)), ()):
                    dx = creature.world_pos[0] - neighbor.world_pos[0]
                    dy = creature.world_pos[1] - neighbor.world_pos[1]
                    if dx * dx + dy * dy <= radius_squared:
                        density += 1
        creature.local_density = max(1, density)


def get_population_centers(herbivores, radius=300, spatial_index=None):
    herbivores = list(herbivores)
    if radius <= 0:
        return {herbivore: tuple(herbivore.world_pos) for herbivore in herbivores}

    spatial_index = spatial_index or HerbivoreSpatialIndex(herbivores)
    centers = {}
    for herbivore in herbivores:
        position = spatial_index.position_of(herbivore)
        nearby = spatial_index.query(position, radius)
        centers[herbivore] = (
            sum(position[0] for _, position in nearby) / len(nearby),
            sum(position[1] for _, position in nearby) / len(nearby),
        )
    return centers


class Creature(Individual):
    MUTABLE_GENES = {}
    GENE_MUTATION_RATE = 0.1

    def __init__(self, x, y, type_=""):
        super().__init__(x, y, type_)
        self.atp = self.mass
        self.age = 0
        self.speed = 0
        self.gene = {}

    def _inherit_genes(self):
        inherited_genes = self.gene.copy()
        mutation_probability = self.GENE_MUTATION_RATE / max(1, self.default_size)
        for gene, (minimum, maximum) in self.MUTABLE_GENES.items():
            value = inherited_genes.get(gene)
            if not isinstance(value, (int, float)) or random.random() >= mutation_probability:
                continue

            mutation_amplitude = min((maximum - minimum) * 0.1, value - minimum, maximum - value)
            if mutation_amplitude <= 0:
                continue

            inherited_genes[gene] = random.uniform(value - mutation_amplitude, value + mutation_amplitude)
        return inherited_genes

    def breed(self):
        self.mass *= 0.3
        self.atp *= 0.5
        self.nutrition *= 0.2
        self.rebuild_visual()

        angle = random.uniform(0, 2 * math.pi)
        distance = random.uniform(1*self.size, 10*self.size)
        offspring = type(self)(
            self.world_pos[0] + math.cos(angle) * distance,
            self.world_pos[1] + math.sin(angle) * distance,
            self.type_,
        )
        offspring.gene = self._inherit_genes()
        if hasattr(offspring, "speed"):
            offspring.speed = offspring.gene.get("speed", offspring.speed)
        offspring.rebuild_visual()
        offspring.add(*self.groups())
        gv.entCnt += 1
        return offspring

    def die(self):
        gv.entCnt -= 1
        self.kill()

    def aerobic_respiration(self):  # o2 ---> co2
        rate = 1 / (0.2 * self.atp / self.mass+1)
        if self.nutrition > 1.2*self.mass and gv.O2Amount > self.mass:  # 有氧
            self.nutrition -= self.mass*1.2*rate
            self.atp += self.mass*10*rate
            gv.O2Amount -= self.mass*rate
            gv.CO2Amount += self.mass*rate
        elif self.nutrition > self.mass > gv.O2Amount:  # 无氧
            self.nutrition -= self.mass
            self.atp += self.mass*5

    def tick(self, dx, dy):
        self.aerobic_respiration()
        if self.atp < 0:
            self.die()
        self.atp -= self.mass*0.5
        self.age = self.age + 1
        alpha = max(0, min(255, int(255 * self.atp / (3 * self.mass))))
        self.default_color = (self.default_color[0], self.default_color[1],
                              self.default_color[2], alpha)

        
class Producer(Creature):
    def __init__(self, x, y, type_="grass"):
        self.type_ = type_
        super().__init__(x, y, self.type_)
        self.gene = {"energy_converting_rate": 1.35,
                     "best_CO2": 0.035, }
        self.mass = 1
        self.atp = 10
    
    MUTABLE_GENES = {"best_CO2": (0.01, 0.5)}

    def Photosynthesis(self):  # co2 ---> o2
        if gv.CO2Amount <= gv.bioMass or gv.CO2Amount / gv.AirAmount < 0.01:
            self.atp -= self.mass
        if gv.CO2Amount <= 0:
            self.die()
        nutri = mp.get_nutrition_value(int(self.world_pos[0]), int(self.world_pos[1]))
        if nutri > 70:
            delta = math.fabs(gv.CO2Amount / gv.AirAmount - self.gene.get("best_CO2"))
            if delta > 0.15:
                return
            # 近似为二次
            # dnut = nutri/100 * max(0.0, 3 - (delta / 0.1) ** 2) * 1.5
            dnut = nutri/100 * max(0.0, -math.log(5*delta+0.54, math.e)) * 7.5
            self.nutrition += dnut * self.mass / (0.3 * max(1, self.local_density))
            rate = self.gene.get("energy_converting_rate")
            gv.O2Amount += rate * self.mass/10
            gv.CO2Amount -= rate * self.mass/10

    def grow(self):
        if self.nutrition > self.mass*1.5 and self.mass < 10:
            self.mass += 1
            self.atp -= 5
            self.nutrition -= self.mass
            self.size = self.default_size * (1 + int(self.mass * 0.1))
            self.rebuild_visual()
        elif self.mass >= 10 and self.atp > 100:
            self.breed()
        if self.age >= 100:
            self.die()

    def tick(self):
        self.Photosynthesis()
        self.grow()
        super().tick(0, 0)
        
        
class Consumer(Creature):
    def __init__(self, x, y, type_=""):
        super().__init__(x, y, type_)
        self.speed = 1

    def die(self):
        pass
        super().die()

    def tick(self, x, y):
        self.move_world(x, y)
        super().tick(x, y)


class Decomposer(Creature):
    def __init__(self, x, y, type_="decomposer"):
        super().__init__(x, y, type_)
        self.type_ = type_
        self.gene = {"nutrition_to_breed": 10,  # more atp

                     }

    def depositing(self):  # dead ---> nutrition
        pass


class Herbivorous(Consumer):
    POPULATION_RADIUS = 300
    SEPARATION_RADIUS = 30
    BREED_COOLDOWN = 100
    WANDER_DIRECTIONS = ((1, 0), (-1, 0), (0, 1), (0, -1))

    def __init__(self, x, y, type_="cow"):
        super().__init__(x, y, type_)
        self.last_breed_age = None
        self.type_ = type_
        self.gene = {"speed": 1,
                     "min_nutrition_to_eat": 50,
                     "forage_radius": 300}
        self.speed = self.gene.get("speed")
        self.mass = 5
        self.atp = 100
        self.nutrition = 100
        self.size = self.default_size
        self.rebuild_visual()

    MUTABLE_GENES = {"speed": (0.1, 3)}

    def _random_step(self):
        speed = max(0.1, self.speed)
        direction_x, direction_y = random.choice(self.WANDER_DIRECTIONS)
        return direction_x * speed, direction_y * speed

    def _step_towards(self, target):
        dx = target[0] - self.world_pos[0]
        dy = target[1] - self.world_pos[1]
        distance = math.hypot(dx, dy)
        if distance == 0:
            return 0, 0
        speed = max(0.1, self.speed)
        step = min(speed, distance)
        return dx * step / distance, dy * step / distance

    def _weighted_direction(self, target, weight):
        dx = target[0] - self.world_pos[0]
        dy = target[1] - self.world_pos[1]
        distance = math.hypot(dx, dy)
        if distance == 0:
            return 0, 0
        strength = self.speed * weight
        return dx * strength / distance, dy * strength / distance

    def _avoid_predators(self):
        return 0, 0

    def _separation_vector(self, herd_positions):
        repel_x = 0.0
        repel_y = 0.0
        if isinstance(herd_positions, HerbivoreSpatialIndex):
            herd_positions = herd_positions.query(
                self.world_pos,
                self.SEPARATION_RADIUS,
            )
        for herbivore, position in herd_positions:
            if herbivore is self:
                continue
            dx = self.world_pos[0] - position[0]
            dy = self.world_pos[1] - position[1]
            distance_squared = dx * dx + dy * dy
            if distance_squared == 0:
                angle = random.uniform(0, 2 * math.pi)
                repel_x += math.cos(angle)
                repel_y += math.sin(angle)
            elif distance_squared < self.SEPARATION_RADIUS * self.SEPARATION_RADIUS:
                distance = math.sqrt(distance_squared)
                strength = (self.SEPARATION_RADIUS - distance) / self.SEPARATION_RADIUS
                repel_x += dx / distance * strength
                repel_y += dy / distance * strength

        repel_length = math.hypot(repel_x, repel_y)
        if repel_length == 0:
            return 0, 0
        return repel_x / repel_length * self.speed, repel_y / repel_length * self.speed

    def consume(self, grass):
        dnut = grass.nutrition * grass.mass * 0.2
        grass.die()
        self.nutrition += dnut

        if self.nutrition > self.mass * 1.5 and self.mass < 15:
            self.mass += 1
            self.atp -= self.mass
            self.nutrition -= self.mass
            self.size = self.default_size * (1 + int(self.mass * 0.06))
            self.rebuild_visual()

    def move(self, population_center, grasses, herd_positions, predators):
        dx, dy = self._random_step()
        predator_dx, predator_dy = self._avoid_predators()
        dx += predator_dx * self.speed
        dy += predator_dy * self.speed

        if self.nutrition < self.gene.get("min_nutrition_to_eat"):
            forage_radius = self.gene.get("forage_radius")
            if isinstance(grasses, GrassSpatialIndex):
                nearby_grasses = grasses.query(self.world_pos, forage_radius)
            else:
                nearby_grasses = (
                    grass for grass in grasses
                    if calc_distance(self, grass) <= forage_radius
                )
            nearest_grass = min(nearby_grasses, key=lambda grass: calc_distance(self, grass), default=None)
            if nearest_grass is not None:
                forage_dx, forage_dy = self._weighted_direction(nearest_grass.world_pos, 2)
                dx += forage_dx
                dy += forage_dy

        if population_center is not None:
            center_dx, center_dy = self._weighted_direction(population_center, 0.5)
            dx += center_dx
            dy += center_dy

        separation_dx, separation_dy = self._separation_vector(herd_positions)
        dx += separation_dx
        dy += separation_dy
        self.atp -= math.hypot(dx, dy) * self.speed * 0.8
        return dx, dy

    def tick(self, population_center=None, grasses=(), herd_positions=(), predators=()):
        # move
        dx, dy = self.move(population_center, grasses, herd_positions, predators)
        super().tick(dx, dy)

        # consume grass if close enough
        collision_candidates = (
            grasses.query(self.world_pos, self.size + grasses.max_grass_size)
            if isinstance(grasses, GrassSpatialIndex)
            else grasses
        )
        for grass in collision_candidates:
            if calc_distance(self, grass) <= self.size + grass.size:
                self.consume(grass)
                if isinstance(grasses, GrassSpatialIndex):
                    grasses.remove(grass)
                break

        # breed
        cooldown_elapsed = (
            self.last_breed_age is None
            or self.age - self.last_breed_age >= self.BREED_COOLDOWN
        )
        if self.atp >= 500 and self.nutrition >= 50 and cooldown_elapsed:
            self.breed()
            self.last_breed_age = self.age

        if self.age >= 500:
            self.die()


class Carnivore(Consumer):
    def __init__(self, x, y, type_="lion"):
        super().__init__(x, y, type_)
        self.type_ = type_
        self.gene = {"speed": 1.5,
                     "detecting_distance": 300,
                     "max_prey_num": 10,
                     "min_atp_to_prey": 50,
                     "distance_with_same_kind": 300}


class Omnivores(Consumer):
    def __init__(self, x, y, type_="eagle"):
        super().__init__(x, y, type_)
        self.type_ = type_
        self.gene = {"speed": 1,
                     "preference": 0.5}
