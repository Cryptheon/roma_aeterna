from dataclasses import dataclass

@dataclass
class LIFParameters:
    decay_rate: float = 0.1       # How fast urgency fades (The "Leak")
    threshold: float = 100.0      # The "Action Potential" limit
    resting_potential: float = 0.0
    refractory_period: float = 5.0 # Seconds to wait after firing (Mental cooldown)

class LeakyIntegrateAndFire:
    def __init__(self, params: LIFParameters = None):
        self.params = params if params else LIFParameters()
        self.potential = self.params.resting_potential # Current "Urgency"
        self.last_spike_time = -999.0
        self.is_refractory = False

    def update(self, dt, input_current, current_time):
        # 1. Check Refractory Period (Mental Cooldown)
        if current_time - self.last_spike_time < self.params.refractory_period:
            self.potential = self.params.resting_potential
            self.is_refractory = True
            return False

        self.is_refractory = False

        # 2. Leaky Integration Formula: dV/dt = -V/tau + I
        # We simplify to Euler integration: V += (Input - Leak * V) * dt
        leak = self.params.decay_rate * self.potential
        delta_v = (input_current - leak) * dt
        
        self.potential += delta_v
        self.potential = max(0.0, self.potential) # Clamp bottom

        # 3. Check Threshold (Fire)
        if self.potential >= self.params.threshold:
            self.fire(current_time)
            return True
        
        return False

    def fire(self, time):
        self.potential = self.params.resting_potential # Reset
        self.last_spike_time = time