"""
Rome: Aeterna — Global Configuration
"""

import os

# --- Population ---
N_AGENTS: int = 2                  # Total number of citizens to spawn
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
TPS: int = 30
RANDOM_SEED: int = 755

# --- Camera ---
CAMERA_SPEED: float = 20.0
MIN_ZOOM: float = 0.5
MAX_ZOOM: float = 4.0
DEFAULT_ZOOM: float = 2.0

# --- LLM ---
# Which inference backend to use:
#   "openai"  — any OpenAI-compatible endpoint (local vLLM, OpenAI, Mistral, etc.)
#   "gemini"  — Google's native Gemini SDK (pip install google-genai);
#               reads GEMINI_API_KEY from environment automatically.
LLM_PROVIDER: str = os.environ.get("LLM_PROVIDER", "gemini")

# Model identifier (used by both providers).
# OpenAI-compat examples: "Qwen/Qwen3-4B-AWQ", "gpt-4o-mini"
# Gemini examples:        "gemini-2.5-flash", "gemini-2.5-pro", "gemini-flash-lite-latest"
LLM_MODEL: str = os.environ.get("LLM_MODEL", "gemini-flash-lite-latest")

# OpenAI-compatible provider settings (ignored when LLM_PROVIDER="gemini").
LLM_BASE_URL: str = os.environ.get("LLM_BASE_URL", "http://localhost:8000/v1")
LLM_API_KEY: str = os.environ.get("LLM_API_KEY", "vllm")

LLM_TEMPERATURE: float = 0.6
LLM_MAX_TOKENS: int = 512

# Backwards-compatible aliases.
VLLM_URL: str = LLM_BASE_URL
VLLM_MODEL: str = LLM_MODEL

# --- Agent Perception ---
PERCEPTION_RADIUS: int = 8          # Tiles an agent can "see"
INTERACTION_RADIUS: float = 2.0     # Tiles within which agents can interact
MAX_INVENTORY_SIZE: int = 12
MEMORY_SHORT_TERM_CAP: int = 20
MEMORY_LONG_TERM_CAP: int = 50

# --- Agent Biology ---
# All rates are in units/second; they are multiplied by dt in update_biological()
# so they are TPS-independent. At TPS=30 (dt≈0.0333s):
HUNGER_RATE: float = 0.04            # ~29 min to critical (70) from 0; ~25 min from resting (10)
THIRST_RATE: float = 0.05            # ~23 min to critical from 0 — slightly more urgent than hunger
ENERGY_RATE: float = 0.015           # ~94 min to critical (85) from 0 — energy drains slowly
SOCIAL_RATE: float = 0.06            # ~17 min to routine threshold (60) — Romans are social
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
CYPRESS_DENSITY: float = 0.05
OLIVE_DENSITY: float = 0.05

# --- World Rules ---
FIRE_SPREAD_BASE_CHANCE: float = 0.008
RAIN_FIRE_SUPPRESSION: float = 0.5
BUILDING_COLLAPSE_RUBBLE_COST: float = 10.0
FOUNTAIN_HEAL_RATE: float = 0.5
FOOD_SPOIL_RATE: float = 0.002      # Freshness lost per second (×dt); food spoils in ~7.5 min at 22°C

# --- Movement ---
MOVEMENT_TICKS_PER_TILE: int = 15       # Ticks to cross one tile of cost=1.0 terrain at TPS=30
                                        # road=15t (0.5s), grass=30t (1.0s), hill=45t (1.5s); map crossing ~100s

# --- Agent Autopilot ---
MAX_AUTOPILOT_TICKS: int = 40           # Autopilot brain-fires before forcing LLM re-evaluation (~4 min at TPS=30, ~5-10s each fire)
CRITICAL_THIRST_THRESHOLD: float = 70.0 # Trigger emergency drink/navigate
CRITICAL_HUNGER_THRESHOLD: float = 70.0 # Trigger emergency eat/navigate
CRITICAL_ENERGY_THRESHOLD: float = 85.0 # Trigger emergency REST
ROUTINE_ENERGY_THRESHOLD: float = 65.0  # Trigger casual REST when idle
ROUTINE_SOCIAL_THRESHOLD: float = 60.0  # Trigger greeting when someone is nearby
HEALTH_CRITICAL_THRESHOLD: float = 25.0 # Use medicine from inventory
PATHFINDING_MAX_STEPS: int = 100         # Greedy path steps — covers ~110 tiles diagonally
PATHFINDING_ROAD_BIAS: float = 0.6      # Cost multiplier for road tiles (lower = preferred)

# --- Legionary Formation ---
LEGIONARY_GROUP_RADIUS: float = 14.0   # Move toward unit if farther than this
LEGIONARY_LONE_THRESHOLD: float = 6.0  # Close enough; no action needed

# --- Animals ---
WOLF_PACK_RADIUS: float = 18.0
WOLF_ATTACK_RANGE: float = 2
WOLF_NIGHT_AGGRO_RADIUS: float = 14.0
WOLF_DAY_AGGRO_RADIUS: float = 3.0
WOLF_DAMAGE: float = 15.0
DOG_DAMAGE: float = 8.0
BOAR_AGGRO_RADIUS: float = 4.0
BOAR_DAMAGE: float = 20.0

# --- Combat ---
UNARMED_DAMAGE: float = 5.0             # Base damage when attacking bare-handed
ATTACK_PROXIMITY_RADIUS: float = 2.0   # Tiles within which ATTACK can reach a target
DEAD_REMOVAL_DELAY: int = 900          # Ticks before corpse is purged (~30s at TPS=30)

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
WAGE_INTERVAL: int = 6000           # Ticks between wage payments (~3.3 min at TPS=30)
RESTOCK_INTERVAL: int = 500         # Ticks between market restocks (~17s at TPS=30)
MARKET_CAPACITY: int = 20           # Max items a market holds
PRICE_VARIANCE_MIN: float = 0.8     # Lower bound of per-restock price randomisation
PRICE_VARIANCE_MAX: float = 1.2     # Upper bound of per-restock price randomisation
SCARCITY_PRICE_MULTIPLIER: float = 1.1  # Price increase when stock hits 1 unit

# --- Fire & Chaos ---
FIRE_BURN_THRESHOLD: float = 5.0    # Fire exposure score that causes Burns
FIRE_SMOKE_THRESHOLD: float = 2.0   # Fire exposure score that causes Smoke Inhalation
FIRE_INTENSITY_CAP: float = 20.0    # Max fire intensity a burning object can reach
SMOKE_AGE_THRESHOLD: int = 900      # Ticks of no refresh before smoke clears (~30s at TPS=30)

# --- Simulation ---
AUTOSAVE_INTERVAL: int = 6000       # Ticks between autosaves (~3.3 min at TPS=30)
LLM_BATCH_SIZE: int = 64            # Max agents processed per LLM batch

# --- LIF Urgency ---
LIF_BASELINE_URGENCY: float = 0.6   # Constant floor; drives dominate above this
LIF_ENV_FIRE_WEIGHT: float = 0.5    # Scales fire proximity urgency (intensity / dist * weight)
LIF_ENV_NIGHT_URGENCY: float = 1.0  # Flat urgency added when outdoors at night
LIF_ENV_UPDATE_INTERVAL: int = 20   # Ticks between environmental urgency scans (~0.67s at TPS=30)

# --- Prompt Context Sizes ---
PROMPT_RECENT_MEMORIES_N: int = 32      # Recent memories shown to agent per LLM call
PROMPT_IMPORTANT_MEMORIES_N: int = 16    # Important long-term memories shown
PROMPT_DECISION_HISTORY_N: int = 16     # Recent actions shown in history
PROMPT_STATE_TRENDS_N: int = 16          # Drive snapshots shown in trends
PROMPT_ENV_INTERVAL: int = 3            # Show full verbose environment every N LLM calls
PROMPT_OUTCOMES_N: int = 16              # Events shown in the chronological outcome log
DECISION_THOUGHT_TRUNCATE: int = 512    # Max chars for thought in decision history
DECISION_SPEECH_TRUNCATE: int = 256     # Max chars for speech in decision history
