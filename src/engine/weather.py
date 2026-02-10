import random
from enum import Enum

class WeatherType(Enum):
    SUNNY = "Sunny"
    RAIN = "Rain"
    STORM = "Storm"
    HEATWAVE = "Heatwave"

class WeatherSystem:
    def __init__(self):
        self.current = WeatherType.SUNNY
        self.duration = 100
        self.wind_speed = 0.0

    def update(self):
        self.duration -= 1
        if self.duration <= 0:
            self._change_weather()

    def _change_weather(self):
        roll = random.random()
        if roll < 0.6:
            self.current = WeatherType.SUNNY
            self.wind_speed = 1.0
        elif roll < 0.8:
            self.current = WeatherType.RAIN
            self.wind_speed = 3.0
        elif roll < 0.9:
            self.current = WeatherType.STORM
            self.wind_speed = 8.0
        else:
            self.current = WeatherType.HEATWAVE
            self.wind_speed = 0.5
        self.duration = random.randint(50, 200)

    def get_effects(self):
        if self.current == WeatherType.STORM:
            return {"energy_drain": 2.0, "fire_spread": 2.0}
        elif self.current == WeatherType.HEATWAVE:
            return {"thirst": 2.0}
        return {}
