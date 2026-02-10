class StatusEffect:
    def __init__(self, name, duration_ticks, stat_modifiers):
        self.name = name
        self.duration = duration_ticks
        self.modifiers = stat_modifiers # {'health': -1.0}
