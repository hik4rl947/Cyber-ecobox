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


def get_local_density(creatures, radius=50):
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


class Creature(Individual):
    def __init__(self, x, y, type_=""):
        super().__init__(x, y, type_)
        self.atp = self.mass
        self.age = 0
        self.speed = 0
        self.gene = {}

    def breed(self):
        self.mass *= 0.3
        self.atp *= 0.5
        self.nutrition *= 0.2
        self.rebuild_visual()

        angle = random.uniform(0, 2 * math.pi)
        distance = random.uniform(10, 30)
        offspring = type(self)(
            self.world_pos[0] + math.cos(angle) * distance,
            self.world_pos[1] + math.sin(angle) * distance,
            self.type_,
        )
        offspring.gene = self.gene.copy()
        offspring.rebuild_visual()
        offspring.add(*self.groups())
        return offspring

    def die(self):
        self.kill()

    def aerobic_respiration(self):  # o2 ---> co2
        if self.nutrition > self.mass and gv.O2Amount > self.mass:  #有氧
            self.nutrition -= self.mass*1.2
            self.atp += self.mass*10
            gv.O2Amount -= self.mass
            gv.CO2Amount += self.mass
        elif self.nutrition > self.mass > gv.O2Amount:  #无氧
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
        self.gene = {"energy_converting_rate": 2.6,
                     "best_CO2": 0.04, }
        self.mass = 1
        self.atp = 10

    def Photosynthesis(self):  # co2 ---> o2
        if gv.CO2Amount <= gv.bioMass or gv.CO2Amount / gv.AirAmount < 0.01:
            pass
        if mp.get_nutrition_value(int(self.world_pos[0]), int(self.world_pos[1])) > 100:
            delta = math.fabs(gv.CO2Amount / gv.AirAmount - self.gene.get("best_CO2"))
            if delta > 0.25:
                return
            # 近似为二次
            dnut = max(0.0, 3 - (delta / 0.1) ** 2) * 1.5
            self.nutrition += dnut * self.mass / (0.5 * max(1, self.local_density))
            rate = self.gene.get("energy_converting_rate")
            gv.O2Amount += dnut * rate * self.mass/10
            gv.CO2Amount -= dnut * rate * self.mass/10

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
    def __init__(self, x, y, type_="cow"):
        super().__init__(x, y, type_)
        self.type_ = type_
        self.gene = {"speed": 1,
                     "min_atp_to_eat": 50}
        self.mass = 5
        self.atp = 100
        self.nutrition = 100
        self.size = self.default_size
        self.rebuild_visual()

    def _random_step(self):
        speed = max(1, int(self.gene.get("speed", 1)))
        axis = random.choice([0, 1])
        dx, dy = 0, 0
        if axis == 0:
            dx = random.choice([-speed, speed])
        else:
            dy = random.choice([-speed, speed])
        return dx, dy

    def tick(self, *args):
        dx, dy = self._random_step()
        self.move_world(dx, dy)
        self.age += 1

    def update(self, dt):
        self.tick(dt)


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
