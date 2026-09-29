import numpy as np
import pygame as pg
from const import *

O2Concentration = 0.21
CO2Concentration = 0.03
AirAmount = 10000000

O2Amount = O2Concentration * AirAmount
CO2Amount = CO2Concentration * AirAmount

creatureCnt = 0

nutritionMap = []

bioMass = 0
entCnt = 0
