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
    return math.hypot(a.pos[0] - b.pos[0], a.pos[1] - b.pos[1])


def distance_squared(a, b):
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return dx * dx + dy * dy


def get_cell(position, cell_size):
    return (
        int(position[0] // cell_size),
        int(position[1] // cell_size),
    )


def iter_neighbor_cells(position, radius, cell_size):
    cell_x, cell_y = get_cell(position, cell_size)
    cell_range = math.ceil(radius / cell_size)
    for x in range(cell_x - cell_range, cell_x + cell_range + 1):
        for y in range(cell_y - cell_range, cell_y + cell_range + 1):
            yield x, y


class GrassSpatialIndex:
    CELL_SIZE = 75

    def __init__(self, grasses):
        self.buckets = {}
        self.max_grass_size = 0
        for grass in grasses:
            cell = get_cell(grass.world_pos, self.CELL_SIZE)
            self.buckets.setdefault(cell, []).append(grass)
            self.max_grass_size = max(self.max_grass_size, grass.size)

    def query(self, position, radius):
        radius_squared = radius * radius
        nearby = []
        for x, y in iter_neighbor_cells(position, radius, self.CELL_SIZE):
            for grass in self.buckets.get((x, y), ()):
                if distance_squared(position, grass.world_pos) <= radius_squared:
                    nearby.append(grass)
        return nearby

    def nearest(self, position, radius):
        radius_squared = radius * radius
        nearest_grass = None
        nearest_distance_squared = radius_squared
        cell_x, cell_y = get_cell(position, self.CELL_SIZE)
        max_ring = math.ceil(radius / self.CELL_SIZE)

        for ring in range(max_ring + 1):
            for offset_x in range(-ring, ring + 1):
                for offset_y in range(-ring, ring + 1):
                    if ring and abs(offset_x) != ring and abs(offset_y) != ring:
                        continue

                    cell = (cell_x + offset_x, cell_y + offset_y)
                    for grass in self.buckets.get(cell, ()):
                        distance_sq = distance_squared(position, grass.world_pos)
                        if distance_sq <= radius_squared and (
                            nearest_grass is None or distance_sq < nearest_distance_squared
                        ):
                            nearest_grass = grass
                            nearest_distance_squared = distance_sq

            if nearest_grass is not None:
                left = (cell_x - ring) * self.CELL_SIZE
                right = (cell_x + ring + 1) * self.CELL_SIZE
                top = (cell_y - ring) * self.CELL_SIZE
                bottom = (cell_y + ring + 1) * self.CELL_SIZE
                unsearched_distance = min(
                    position[0] - left,
                    right - position[0],
                    position[1] - top,
                    bottom - position[1],
                )
                if nearest_distance_squared <= unsearched_distance * unsearched_distance:
                    break

        return nearest_grass

    def remove(self, grass):
        cell = get_cell(grass.world_pos, self.CELL_SIZE)
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
            cell = get_cell(position, self.CELL_SIZE)
            self.buckets.setdefault(cell, []).append((herbivore, position))

    def query(self, position, radius):
        radius_squared = radius * radius
        nearby = []
        for x, y in iter_neighbor_cells(position, radius, self.CELL_SIZE):
            for herbivore, herbivore_position in self.buckets.get((x, y), ()):
                if distance_squared(position, herbivore_position) <= radius_squared:
                    nearby.append((herbivore, herbivore_position))
        return nearby

    def position_of(self, herbivore):
        return self.positions[herbivore]


def get_local_density(creatures, radius=20):
    creatures = list(creatures)
    buckets = {}
    for creature in creatures:
        species = (type(creature), creature.type_)
        cell = get_cell(creature.world_pos, radius)
        buckets.setdefault((species, cell), []).append(creature)

    radius_squared = radius * radius
    for creature in creatures:
        species = (type(creature), creature.type_)
        cell_x, cell_y = get_cell(creature.world_pos, radius)
        density = 0
        for x in range(cell_x - 1, cell_x + 2):
            for y in range(cell_y - 1, cell_y + 2):
                for neighbor in buckets.get((species, (x, y)), ()):
                    if distance_squared(creature.world_pos, neighbor.world_pos) <= radius_squared:
                        density += 1
        creature.local_density = max(1, density)


def find_nearest_grass(position, grasses, radius):
    if isinstance(grasses, GrassSpatialIndex):
        return grasses.nearest(position, radius)

    nearby = []
    for grass in grasses:
        if distance_squared(position, grass.world_pos) <= radius * radius:
            nearby.append(grass)
    if not nearby:
        return None
    return min(nearby, key=lambda grass: distance_squared(position, grass.world_pos))


def get_grass_collision_candidates(grasses, position, radius):
    if isinstance(grasses, GrassSpatialIndex):
        return grasses.query(position, radius)
    return [
        grass
        for grass in grasses
        if distance_squared(position, grass.world_pos) <= radius * radius
    ]


def get_population_centers(herbivores, radius=300, spatial_index=None):
    herbivores = list(herbivores)
    if radius <= 0:
        return {herbivore: tuple(herbivore.world_pos) for herbivore in herbivores}

    spatial_index = spatial_index or HerbivoreSpatialIndex(herbivores)
    centers = {}
    for herbivore in herbivores:
        position = spatial_index.position_of(herbivore)
        nearby = spatial_index.query(position, radius)
        if not nearby:
            centers[herbivore] = position
            continue

        centers[herbivore] = (
            sum(nearby_pos[0] for _, nearby_pos in nearby) / len(nearby),
            sum(nearby_pos[1] for _, nearby_pos in nearby) / len(nearby),
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
        self.is_dead = False

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

    def is_old(self):
        oldAge = OLD_AGES.get(self.type_)
        if self.age > oldAge:
            self.atp -= self.age-oldAge

    def die(self):
        if not self.is_dead:
            self.is_dead = True
            gv.lifespan_stats.setdefault(self.type_, []).append(
                (gv.simulation_time, self.age)
            )
            gv.entCnt -= 1
            self.kill()

    def aerobic_respiration(self):  # o2 ---> co2
        rate = 1 / (0.3 * self.atp / self.mass+1)
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
        self.is_old()
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
        maxMass = MAX_MASS.get(self.type_)
        if self.nutrition > self.mass*1.5 and self.mass < maxMass:
            self.mass += 1
            self.atp -= self.mass
            self.nutrition -= self.mass
            self.size = self.default_size * (1 + int(self.mass * 0.1))
            self.rebuild_visual()
        elif self.mass >= maxMass and self.atp > 100:
            self.breed()

    def tick(self):
        self.Photosynthesis()
        self.grow()
        super().tick(0, 0)
        
        
class Consumer(Creature):
    WANDER_DIRECTIONS = ((1, 0), (-1, 0), (0, 1), (0, -1))

    def __init__(self, x, y, type_=""):
        super().__init__(x, y, type_)
        self.speed = 1
        self.last_breed_age = None

    def die(self):
        super().die()

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

    def consume(self, item):
        dnut = item.nutrition * item.mass * 0.3
        item.die()
        self.nutrition += dnut

        if self.nutrition > self.mass * 1.5 and self.mass < MAX_MASS.get(self.type_):
            self.mass += 1
            self.atp -= self.mass
            self.nutrition -= self.mass
            self.size = self.default_size * (1 + int(self.mass * 0.06))
            self.rebuild_visual()

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

    def __init__(self, x, y, type_="cow"):
        super().__init__(x, y, type_)

        self.type_ = type_
        self.gene = {"speed": 1,
                     "min_nutrition_to_eat": 50,
                     "forage_radius": 300,
                     "predator_detection_distance": 150}
        self.speed = self.gene.get("speed")
        self.mass = 5
        self.atp = 100
        self.nutrition = 100
        self.size = self.default_size
        self.rebuild_visual()

    MUTABLE_GENES = {"speed": (0.1, 3)}

    def _weighted_direction(self, target, weight):
        dx = target[0] - self.world_pos[0]
        dy = target[1] - self.world_pos[1]
        distance = math.hypot(dx, dy)
        if distance == 0:
            return 0, 0
        strength = self.speed * weight
        return dx * strength / distance, dy * strength / distance

    def _avoid_predators(self, predators=()):
        flee_x = 0.0
        flee_y = 0.0
        detection_distance = self.gene.get("predator_detection_distance", 150)
        if detection_distance <= 0:
            return 0, 0
        detection_distance_squared = detection_distance * detection_distance
        for predator in predators:
            dx = self.world_pos[0] - predator.world_pos[0]
            dy = self.world_pos[1] - predator.world_pos[1]
            distance_squared = dx * dx + dy * dy
            if distance_squared > detection_distance_squared:
                continue
            if distance_squared == 0:
                angle = random.uniform(0, 2 * math.pi)
                flee_x += math.cos(angle)
                flee_y += math.sin(angle)
                continue

            distance = math.sqrt(distance_squared)
            strength = (detection_distance - distance) / detection_distance
            flee_x += dx / distance * strength
            flee_y += dy / distance * strength

        flee_length = math.hypot(flee_x, flee_y)
        if flee_length == 0:
            return 0, 0
        return flee_x / flee_length, flee_y / flee_length

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

    def move(self, population_center, grasses, herd_positions, predators):
        dx, dy = self._random_step()
        predator_dx, predator_dy = self._avoid_predators(predators)
        dx += predator_dx * self.speed
        dy += predator_dy * self.speed

        if self.nutrition < self.gene.get("min_nutrition_to_eat"):
            forage_radius = self.gene.get("forage_radius")
            nearest_grass = find_nearest_grass(self.world_pos, grasses, forage_radius)
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
        dx, dy = self.move(population_center, grasses, herd_positions, predators)
        super().tick(dx, dy)

        collision_radius = self.size + getattr(grasses, "max_grass_size", 0)
        collision_candidates = get_grass_collision_candidates(grasses, self.world_pos, collision_radius)
        for grass in collision_candidates:
            if calc_distance(self, grass) <= self.size + grass.size:
                self.consume(grass)
                if isinstance(grasses, GrassSpatialIndex):
                    grasses.remove(grass)
                break

        breedingCD = (
            self.last_breed_age is None
            or self.age - self.last_breed_age >= BREED_COOLDOWN.get(self.type_)
        )
        if self.atp >= 300 and self.nutrition >= 100 and breedingCD:
            self.breed()
            self.last_breed_age = self.age


class Carnivore(Consumer):
    def __init__(self, x, y, type_="lion"):
        super().__init__(x, y, type_)
        self.type_ = type_
        self.gene = {"speed": 2.0,
                     "detecting_distance": 500,
                     "min_nutrition_to_hunt": 125,
                     "max_prey_num": 10,
                     "distance_with_same_kind": 300}
        self.speed = self.gene.get("speed")
        self.mass = 7
        self.atp = 400
        self.nutrition = 200
        self.size = self.default_size
        self.rebuild_visual()

    def _nearest_prey(self, herbivores):
        detecting_distance = self.gene.get("detecting_distance")
        detecting_distance_squared = detecting_distance * detecting_distance
        prey = (
            herbivore for herbivore in herbivores
            if not getattr(herbivore, "is_dead", False)
            and distance_squared(self.world_pos, herbivore.world_pos) <= detecting_distance_squared
        )
        return min(
            prey,
            key=lambda herbivore: distance_squared(self.world_pos, herbivore.world_pos),
            default=None,
        )

    def tick(self, herbivores=()):
        prey = None
        if self.nutrition <= self.gene.get("min_nutrition_to_hunt"):
            prey = self._nearest_prey(herbivores)

        if prey is None:
            dx, dy = self._random_step()
        else:
            dx, dy = self._step_towards(prey.world_pos)
        self.atp -= math.hypot(dx, dy) * self.speed * 0.6
        super().tick(dx, dy)

        if prey is not None and calc_distance(self, prey) <= self.size + prey.size:
            self.consume(prey)

        # breed
        breedingCD = (
                self.last_breed_age is None
                or self.age - self.last_breed_age >= BREED_COOLDOWN.get(self.type_)
        )
        if self.atp >= 600 and self.nutrition >= 70 and breedingCD:
            self.breed()
            self.last_breed_age = self.age


class Omnivores(Consumer):
    def __init__(self, x, y, type_="eagle"):
        super().__init__(x, y, type_)
        self.type_ = type_
        self.gene = {"speed": 1,
                     "preference": 0.5}
