import uuid
import math
from .memory import Memory
from .neuro import LeakyIntegrateAndFire, LIFParameters

class Agent:
    def __init__(self, name, role, x, y):
        self.uid = str(uuid.uuid4())[:8]
        self.name = name
        self.role = role
        self.x = x
        self.y = y
        self.path = []
        self.inventory = []
        
        # --- Biological Drives (Drive Reduction Theory) ---
        # 0 = Satiated/Good, 100 = Desperate/Bad
        self.drives = {
            "hunger": 0.0,
            "energy": 0.0,  # 0 = Energetic, 100 = Exhausted
            "social": 0.0,  # 0 = Content, 100 = Lonely
        }
        
        # --- Cognitive Model (Leaky Integrate-and-Fire) ---
        # The 'Brain' that decides when to trigger an LLM inference
        self.brain = LeakyIntegrateAndFire(
            LIFParameters(
                decay_rate=0.5,      # How fast urgency fades if nothing happens
                threshold=50.0,      # The "Action Potential" limit to wake up
                refractory_period=5.0 # Seconds to wait after acting
            )
        )
        self.current_time = 0.0
        
        # --- State ---
        self.action = "IDLE"
        self.current_thought = "Head empty."
        self.waiting_for_llm = False
        self.memory = Memory()

    def update_biological(self, dt, weather_fx, visible_threats=0):
        """
        Updates internal biology and returns True if the Agent's brain 'fired' (decided to act).
        """
        self.current_time += dt

        # 1. Biological Decay (Metabolism)
        metabolic_rate = 1.0
        
        # Environmental Modifiers
        if "heatwave" in weather_fx: 
            metabolic_rate *= 1.5
        if self.action == "MOVING": 
            metabolic_rate *= 2.0
        
        # Drive Increases (Decay towards chaos)
        self.drives["hunger"] += 0.5 * metabolic_rate * dt
        self.drives["energy"] += 0.3 * metabolic_rate * dt
        self.drives["social"] += 0.1 * dt

        # Clamp Drives to 0-100 range
        for k in self.drives: 
            self.drives[k] = min(100.0, max(0.0, self.drives[k]))

        # 2. Calculate "Input Current" (Urgency to Act)
        input_current = 0.0
        
        # A. Homeostatic Pressure (Needs)
        # Using square to make high needs exponentially more urgent
        input_current += (self.drives["hunger"] / 100.0) ** 2 * 10.0
        input_current += (self.drives["energy"] / 100.0) ** 2 * 5.0
        input_current += (self.drives["social"] / 100.0) ** 2 * 2.0
        
        # B. External Stimuli (Threats)
        # Immediate massive spike for fire/danger
        input_current += visible_threats * 30.0 

        # C. Bias (Boredom)
        # Ensures they eventually do something even if fully satiated
        input_current += 1.0 

        # 3. Update Brain with this current
        # Returns True if potential >= threshold (Spike!)
        should_act = self.brain.update(dt, input_current, self.current_time)
        
        return should_act

    def perceive(self, world, radius=5):
        """
        Generates a natural language description of the surrounding tiles and entities.
        Used as the [PERCEPTION] block in the LLM Prompt.
        """
        visible = []
        
        # 1. Scan Tiles
        min_x, max_x = int(self.x - radius), int(self.x + radius)
        min_y, max_y = int(self.y - radius), int(self.y + radius)
        
        # Clamp to map bounds
        min_x, max_x = max(0, min_x), min(world.width, max_x)
        min_y, max_y = max(0, min_y), min(world.height, max_y)

        for y in range(min_y, max_y):
            for x in range(min_x, max_x):
                tile = world.get_tile(x, y)
                if not tile: continue
                
                # Check for Buildings
                if tile.building:
                    dist = math.sqrt((x - self.x)**2 + (y - self.y)**2)
                    direction = self._get_direction(x, y)
                    
                    # Check for visual effects (Fire/Rubble)
                    status_text = ""
                    if hasattr(tile.building, "components"):
                        # Duck typing check for Flammable component
                        for comp in tile.building.components.values():
                            if getattr(comp, "is_burning", False):
                                status_text = " (BURNING!)"
                                break

                    visible.append(f"- {tile.building.name}{status_text} is {dist:.1f}m {direction}.")

        # 2. Scan for other Agents (In a real engine, use a spatial hash or quadtree)
        # This assumes 'world' has a reference to agents, or we pass agents in.
        # For this snippet, we'll assume the caller might append agent info, 
        # or we return what we found so far.
        
        if not visible:
            return "You see nothing of interest nearby."
        
        return "\n".join(visible)

    def _get_direction(self, tx, ty):
        """Returns cardinal/ordinal direction string relative to self."""
        dx, dy = tx - self.x, ty - self.y
        if dx == 0 and dy == 0: return "here"
        
        angle = math.degrees(math.atan2(dy, dx))
        if angle < 0: angle += 360
        
        # 8-way directional mapping
        dirs = ["East", "South-East", "South", "South-West", 
                "West", "North-West", "North", "North-East"]
        
        # Offset by 22.5 to center the sectors
        idx = int((angle + 22.5) // 45) % 8
        return dirs[idx]

    def move_towards(self, target_tuple, speed):
        """
        Physics interpolation to move the agent.
        Returns True if arrived at the target node.
        """
        tx, ty = target_tuple
        dx, dy = tx - self.x, ty - self.y
        dist = math.sqrt(dx*dx + dy*dy)
        
        if dist < speed:
            self.x, self.y = float(tx), float(ty)
            return True # Arrived
        
        self.x += (dx/dist) * speed
        self.y += (dy/dist) * speed
        return False

    def get_inspection_data(self):
        """Returns a list of strings for the UI hover tooltip."""
        return [
            f"Name: {self.name}",
            f"Role: {self.role}",
            f"--- Drives ---",
            f"Hunger: {int(self.drives['hunger'])}%",
            f"Energy: {int(self.drives['energy'])}%",
            f"Social: {int(self.drives['social'])}%",
            f"--- Brain ---",
            f"Urgency: {int(self.brain.potential)}/{int(self.brain.params.threshold)}",
            f"Action: {self.action}",
            f"Thought: {self.current_thought[:30]}..."
        ]