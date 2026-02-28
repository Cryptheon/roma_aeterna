"""
Rome: Aeterna — Global Configuration
"""

# --- Population ---
N_AGENTS: int = 1                   # Total number of citizens to spawn
NAMED_AGENTS_FIRST: bool = True      # Spawn hand-placed agents before random ones

# --- Display ---
SCREEN_WIDTH: int = 1920
SCREEN_HEIGHT: int = 1080
FPS: int = 30

# --- Map ---
GRID_WIDTH: int = 200
GRID_HEIGHT: int = 150
TILE_SIZE: int = 16

# --- Simulation ---
TPS: int = 10
RANDOM_SEED: int = 753

# --- Camera ---
CAMERA_SPEED: float = 15.0
MIN_ZOOM: float = 0.5
MAX_ZOOM: float = 4.0
DEFAULT_ZOOM: float = 2.0

# --- LLM ---
VLLM_URL: str = "http://localhost:8000/v1"
VLLM_MODEL: str = "Qwen/Qwen3-8B-AWQ" #"Qwen/Qwen3-30B-A3B-GPTQ-Int4" #"Qwen/Qwen3-8B-AWQ" 
LLM_TEMPERATURE: float = 1.5
LLM_MAX_TOKENS: int = 512

# --- Agent Perception ---
PERCEPTION_RADIUS: int = 8          # Tiles an agent can "see"
INTERACTION_RADIUS: float = 2.0     # Tiles within which agents can interact
MAX_INVENTORY_SIZE: int = 12
MEMORY_SHORT_TERM_CAP: int = 20
MEMORY_LONG_TERM_CAP: int = 50

# --- Agent Biology (TUNED: ~3x gentler than before) ---
HUNGER_RATE: float = 0.12           # Was 0.4 — agents no longer starve in 2 minutes
ENERGY_RATE: float = 0.05           # Was 0.25
SOCIAL_RATE: float = 0.15           # Was 0.08
THIRST_RATE: float = 0.10           # Was 0.35 — was the #1 killer
COMFORT_RATE: float = 0.03          # Was 0.05
HEALTH_REGEN_RATE: float = 0.2      # Was 0.1 — faster recovery

# --- Environment ---
DAY_LENGTH_TICKS: int = 2400
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
FIRE_SPREAD_BASE_CHANCE: float = 0.05
RAIN_FIRE_SUPPRESSION: float = 0.5
BUILDING_COLLAPSE_RUBBLE_COST: float = 10.0
FOUNTAIN_HEAL_RATE: float = 0.5
FOOD_SPOIL_RATE: float = 0.001      # Per tick chance of spoilage
