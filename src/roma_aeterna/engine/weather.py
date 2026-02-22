"""
Weather & Time System — Day/night cycle, seasonal weather,
and environmental effects that agents can perceive and react to.
"""

import random
from enum import Enum
from typing import Dict, List
from roma_aeterna.config import DAY_LENGTH_TICKS, DAWN_START, DAWN_END, DUSK_START, DUSK_END


class WeatherType(Enum):
    CLEAR = "Clear"
    CLOUDY = "Cloudy"
    RAIN = "Rain"
    STORM = "Storm"
    HEATWAVE = "Heatwave"
    FOG = "Fog"


class TimeOfDay(Enum):
    NIGHT = "night"
    DAWN = "dawn"
    MORNING = "morning"
    MIDDAY = "midday"
    AFTERNOON = "afternoon"
    DUSK = "dusk"
    EVENING = "evening"


class WeatherSystem:
    """Manages weather state, wind, temperature, and day/night cycle."""

    def __init__(self) -> None:
        self.current: WeatherType = WeatherType.CLEAR
        self.duration: int = 100
        self.wind_speed: float = 1.0
        self.wind_direction: str = "west"
        self.temperature: float = 22.0
        self.humidity: float = 0.45

        # Day/night
        self.world_tick: int = 0
        self.day_count: int = 1
        self.time_of_day: TimeOfDay = TimeOfDay.MORNING

    def update(self) -> None:
        """Advance one tick."""
        self.world_tick += 1
        self._update_time_of_day()
        self._update_temperature()

        self.duration -= 1
        if self.duration <= 0:
            self._change_weather()

    def _update_time_of_day(self) -> None:
        """Compute time of day from tick position in the day cycle."""
        cycle_pos = (self.world_tick % DAY_LENGTH_TICKS) / DAY_LENGTH_TICKS

        if cycle_pos < DAWN_START:
            self.time_of_day = TimeOfDay.NIGHT
        elif cycle_pos < DAWN_END:
            self.time_of_day = TimeOfDay.DAWN
        elif cycle_pos < 0.45:
            self.time_of_day = TimeOfDay.MORNING
        elif cycle_pos < 0.55:
            self.time_of_day = TimeOfDay.MIDDAY
        elif cycle_pos < DUSK_START:
            self.time_of_day = TimeOfDay.AFTERNOON
        elif cycle_pos < DUSK_END:
            self.time_of_day = TimeOfDay.DUSK
        elif cycle_pos < 0.90:
            self.time_of_day = TimeOfDay.EVENING
        else:
            self.time_of_day = TimeOfDay.NIGHT

        # Track days
        if self.world_tick % DAY_LENGTH_TICKS == 0 and self.world_tick > 0:
            self.day_count += 1

    def _update_temperature(self) -> None:
        """Temperature varies with time of day and weather."""
        base = 22.0
        # Day/night variance
        if self.time_of_day in (TimeOfDay.NIGHT, TimeOfDay.DAWN):
            base -= 6.0
        elif self.time_of_day == TimeOfDay.MIDDAY:
            base += 5.0
        elif self.time_of_day == TimeOfDay.AFTERNOON:
            base += 3.0

        # Weather effects
        if self.current == WeatherType.HEATWAVE:
            base += 10.0
        elif self.current == WeatherType.RAIN:
            base -= 3.0
        elif self.current == WeatherType.STORM:
            base -= 5.0
        elif self.current == WeatherType.FOG:
            base -= 2.0

        self.temperature = base

    def _change_weather(self) -> None:
        """Transition to new weather state."""
        roll = random.random()
        if roll < 0.40:
            self.current = WeatherType.CLEAR
            self.wind_speed = random.uniform(0.5, 2.0)
        elif roll < 0.55:
            self.current = WeatherType.CLOUDY
            self.wind_speed = random.uniform(1.0, 3.0)
        elif roll < 0.72:
            self.current = WeatherType.RAIN
            self.wind_speed = random.uniform(2.0, 5.0)
        elif roll < 0.82:
            self.current = WeatherType.STORM
            self.wind_speed = random.uniform(5.0, 10.0)
        elif roll < 0.92:
            self.current = WeatherType.HEATWAVE
            self.wind_speed = random.uniform(0.2, 1.0)
        else:
            self.current = WeatherType.FOG
            self.wind_speed = random.uniform(0.1, 0.5)

        self.wind_direction = random.choice(
            ["north", "south", "east", "west",
             "northeast", "northwest", "southeast", "southwest"]
        )
        self.duration = random.randint(50, 250)

    def get_effects(self) -> Dict[str, float]:
        """Return active environmental effect multipliers."""
        effects: Dict[str, float] = {}

        if self.current == WeatherType.STORM:
            effects["energy_drain"] = 1.5
            effects["fire_spread"] = 0.5   # Rain suppresses fire
            effects["visibility"] = 0.6
            effects["wet"] = True
        elif self.current == WeatherType.RAIN:
            effects["fire_spread"] = 0.3
            effects["visibility"] = 0.8
            effects["wet"] = True
        elif self.current == WeatherType.HEATWAVE:
            effects["thirst"] = 2.0
            effects["fire_spread"] = 1.5
            effects["heatwave"] = True
        elif self.current == WeatherType.FOG:
            effects["visibility"] = 0.4

        # Night penalties
        if self.time_of_day in (TimeOfDay.NIGHT, TimeOfDay.EVENING):
            effects["visibility"] = effects.get("visibility", 1.0) * 0.5
            effects["danger"] = 1.5

        return effects

    def get_description(self) -> str:
        """Human-readable weather + time description for agent perception."""
        time_desc = {
            TimeOfDay.NIGHT: "It is deep night. The stars shine above Rome.",
            TimeOfDay.DAWN: "Dawn breaks over the seven hills. The sky turns golden.",
            TimeOfDay.MORNING: "It is morning. The city stirs to life.",
            TimeOfDay.MIDDAY: "The sun is directly overhead. It is midday.",
            TimeOfDay.AFTERNOON: "The afternoon sun casts long shadows.",
            TimeOfDay.DUSK: "Dusk settles over Rome. The sky is painted in reds and purples.",
            TimeOfDay.EVENING: "Evening has come. Torches and oil lamps light the streets.",
        }

        weather_desc = {
            WeatherType.CLEAR: "The sky is clear and blue.",
            WeatherType.CLOUDY: "Clouds drift lazily across the sky.",
            WeatherType.RAIN: "Rain falls steadily on the city, darkening the stone.",
            WeatherType.STORM: "A violent storm rages! Thunder cracks and wind howls.",
            WeatherType.HEATWAVE: "The heat is oppressive. The air shimmers above the stone.",
            WeatherType.FOG: "A thick fog has settled, muffling sounds and hiding distant shapes.",
        }

        parts = [
            f"Day {self.day_count}.",
            time_desc.get(self.time_of_day, ""),
            weather_desc.get(self.current, ""),
            f"Temperature: {self.temperature:.0f}°C.",
        ]

        if self.wind_speed > 3.0:
            parts.append(f"Strong wind blows from the {self.wind_direction}.")

        return " ".join(parts)
