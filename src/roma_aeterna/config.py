"""
Rome: Aeterna — Global Configuration
"""

# --- Population ---
N_AGENTS: int = 12                  # Total number of citizens to spawn
NAMED_AGENTS_FIRST: bool = True      # Spawn hand-placed agents before random ones


# --- Display ---
SCREEN_WIDTH: int = 1920
SCREEN_HEIGHT: int = 1080
FPS: int = 60

# --- Map ---
GRID_WIDTH: int = 200
GRID_HEIGHT: int = 150
TILE_SIZE: int = 16

# --- Simulation ---
TPS: int = 100
RANDOM_SEED: int = 753

# --- Camera ---
CAMERA_SPEED: float = 20.0
MIN_ZOOM: float = 0.5
MAX_ZOOM: float = 4.0
DEFAULT_ZOOM: float = 2.0

# --- LLM ---
VLLM_URL: str = "http://localhost:8000/v1"
VLLM_MODEL: str = "Qwen/Qwen3-4B-AWQ" #"Qwen/Qwen3-30B-A3B-GPTQ-Int4" #"Qwen/Qwen3-8B-AWQ" 
LLM_TEMPERATURE: float = 1.2
LLM_MAX_TOKENS: int = 512

# --- Agent Perception ---
PERCEPTION_RADIUS: int = 8          # Tiles an agent can "see"
INTERACTION_RADIUS: float = 2.0     # Tiles within which agents can interact
MAX_INVENTORY_SIZE: int = 12
MEMORY_SHORT_TERM_CAP: int = 20
MEMORY_LONG_TERM_CAP: int = 50

# --- Agent Biology ---
HUNGER_RATE: float = 0.8            # ~10 min to critical from 10
THIRST_RATE: float = 0.9            # Slightly faster than hunger — thirst is more urgent
ENERGY_RATE: float = 0.015           # Tired after ~80 min
SOCIAL_RATE: float = 0.06            # Lonely after ~15 min
COMFORT_RATE: float = 0.02
HEALTH_REGEN_RATE: float = 0.2

# --- Environment ---
DAY_LENGTH_TICKS: int = 36000
DAWN_START: float = 0.20
DAWN_END: float = 0.30
DUSK_START: float = 0.70
DUSK_END: float = 0.80

# --- Rome Biome ---
ROME_LATITUDE: float = 41.9
AMBIENT_TEMP_BASE: float = 22.0
HUMIDITY_BASE: float = 0.45
CYPRESS_DENSITY: float = 0.03
OLIVE_DENSITY: float = 0.02

# --- World Rules ---
FIRE_SPREAD_BASE_CHANCE: float = 0.008
RAIN_FIRE_SUPPRESSION: float = 0.5
BUILDING_COLLAPSE_RUBBLE_COST: float = 10.0
FOUNTAIN_HEAL_RATE: float = 0.5
FOOD_SPOIL_RATE: float = 0.001      # Per tick chance of spoilage

# --- Agent Autopilot ---
MAX_AUTOPILOT_TICKS: int = 300          # Brain fires before forcing an LLM re-evaluation (~3 sec at TPS=100)
CRITICAL_THIRST_THRESHOLD: float = 70.0 # Trigger emergency drink/navigate
CRITICAL_HUNGER_THRESHOLD: float = 70.0 # Trigger emergency eat/navigate
CRITICAL_ENERGY_THRESHOLD: float = 85.0 # Trigger emergency REST
ROUTINE_ENERGY_THRESHOLD: float = 65.0  # Trigger casual REST when idle
ROUTINE_SOCIAL_THRESHOLD: float = 60.0  # Trigger greeting when someone is nearby
HEALTH_CRITICAL_THRESHOLD: float = 25.0 # Use medicine from inventory
PATHFINDING_MAX_STEPS: int = 100         # Greedy path steps — covers ~110 tiles diagonally
PATHFINDING_ROAD_BIAS: float = 0.2      # Cost multiplier for road tiles (lower = preferred)

# --- Combat ---
UNARMED_DAMAGE: float = 5.0             # Base damage when attacking bare-handed
ATTACK_PROXIMITY_RADIUS: float = 2.0   # Tiles within which ATTACK can reach a target
DEAD_REMOVAL_DELAY: int = 3000         # Ticks before corpse is purged (~30s at TPS=100)

# --- Proximity / Interaction Ranges ---
NEARBY_AGENT_RADIUS: float = 5.0        # TRADE, BUY proximity, social checks
WORKING_PROXIMITY: float = 8.0          # Near-workplace threshold for wage payment
INSPECT_OBJECT_RADIUS: float = 15.0     # Max range to INSPECT a building/object
INSPECT_AGENT_RADIUS: float = 10.0      # Max range to INSPECT another agent

# --- Action Drive Costs ---
REST_ENERGY_REDUCTION: int = 5          # Energy recovered per REST tick
SLEEP_ENERGY_REDUCTION: int = 15        # Energy recovered per SLEEP tick
SLEEP_COMFORT_REDUCTION: int = 5        # Comfort recovered per SLEEP tick

# --- Memory Importance Thresholds ---
MEMORY_PROMOTION_IMPORTANCE: float = 3.0    # Evicted short-term → long-term if >= this
MEMORY_IMMEDIATE_LT_IMPORTANCE: float = 5.0 # Skip short-term, go straight to long-term
GOSSIP_IMPORTANCE_THRESHOLD: float = 2.5    # Added to gossip buffer if >= this
GOSSIP_BUFFER_CAP: int = 10                 # Max entries in gossip buffer

# --- Events ---
MAX_GOSSIP_HOPS: int = 3            # How many retelling hops before gossip stops spreading
EVENT_HISTORY_CAP: int = 200        # Max events retained in event bus history
GOSSIP_IMPORTANCE_DECAY: float = 0.7 # Importance multiplier per gossip hop

# --- Economy ---
WAGE_INTERVAL: int = 6000           # Ticks between wage payments (~1 min at TPS=100)
RESTOCK_INTERVAL: int = 500         # Ticks between market restocks (~5 sec at TPS=100)
MARKET_CAPACITY: int = 20           # Max items a market holds
PRICE_VARIANCE_MIN: float = 0.8     # Lower bound of per-restock price randomisation
PRICE_VARIANCE_MAX: float = 1.2     # Upper bound of per-restock price randomisation
SCARCITY_PRICE_MULTIPLIER: float = 1.1  # Price increase when stock hits 1 unit

# --- Fire & Chaos ---
FIRE_BURN_THRESHOLD: float = 5.0    # Fire exposure score that causes Burns
FIRE_SMOKE_THRESHOLD: float = 2.0   # Fire exposure score that causes Smoke Inhalation
FIRE_INTENSITY_CAP: float = 20.0    # Max fire intensity a burning object can reach
SMOKE_AGE_THRESHOLD: int = 3000     # Ticks of no refresh before smoke clears (~30 sec)

# --- Simulation ---
AUTOSAVE_INTERVAL: int = 18000      # Ticks between autosaves (~3 min at TPS=100)
LLM_BATCH_SIZE: int = 64            # Max agents processed per LLM batch

# --- LIF Urgency ---
LIF_BASELINE_URGENCY: float = 0.6   # Constant floor; drives dominate above this
LIF_ENV_FIRE_WEIGHT: float = 0.5    # Scales fire proximity urgency (intensity / dist * weight)
LIF_ENV_NIGHT_URGENCY: float = 1.0  # Flat urgency added when outdoors at night
LIF_ENV_UPDATE_INTERVAL: int = 20   # Ticks between environmental urgency scans (~0.2s)

# --- Prompt Context Sizes ---
PROMPT_RECENT_MEMORIES_N: int = 32      # Recent memories shown to agent per LLM call
PROMPT_IMPORTANT_MEMORIES_N: int = 16    # Important long-term memories shown
PROMPT_DECISION_HISTORY_N: int = 16     # Recent actions shown in history
PROMPT_STATE_TRENDS_N: int = 16          # Drive snapshots shown in trends
PROMPT_ENV_INTERVAL: int = 3            # Show full verbose environment every N LLM calls
PROMPT_OUTCOMES_N: int = 8              # Events shown in the chronological outcome log
DECISION_THOUGHT_TRUNCATE: int = 512    # Max chars for thought in decision history
DECISION_SPEECH_TRUNCATE: int = 256     # Max chars for speech in decision history
