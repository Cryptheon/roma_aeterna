"""
Persistence — Save and load simulation state to/from SQLite.

Handles serialization of:
  - Agents: position, drives, health, memory, relationships, beliefs,
    inventory, status effects, personality, denarii
  - World: damaged/destroyed buildings, ground items, tile modifications
  - Simulation: tick count, weather state, day count

Usage:
    from roma_aeterna.core.persistence import save_game, load_game

    # Save
    save_game(engine, path="saves/autosave.db")

    # Load (returns None if no save exists)
    state = load_game(path="saves/autosave.db")
    if state:
        engine.restore(state)
"""

import sqlite3
import json
import os
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path


SAVE_DIR = "saves"
DEFAULT_SAVE = "autosave.db"
SAVE_VERSION = 1  # Bump when schema changes


# ============================================================
# SERIALIZATION HELPERS
# ============================================================

def _serialize_agent(agent: Any) -> Dict:
    """Convert an agent's full state to a JSON-serializable dict."""
    return {
        "uid": agent.uid,
        "name": agent.name,
        "role": agent.role,
        "x": agent.x,
        "y": agent.y,
        "health": agent.health,
        "max_health": agent.max_health,
        "is_alive": agent.is_alive,
        "denarii": agent.denarii,
        "drives": dict(agent.drives),
        "action": agent.action,
        "current_thought": agent.current_thought,
        "last_speech": agent.last_speech,
        "movement_cooldown": agent.movement_cooldown,
        "interaction_cooldown": agent.interaction_cooldown,
        "current_time": agent.current_time,
        # Personality
        "personality_seed": agent.personality_seed,
        "personal_goals": agent.personal_goals,
        "fears": agent.fears,
        "values": agent.values,
        # Brain
        "brain_potential": agent.brain.potential,
        "brain_last_spike": agent.brain.last_spike_time,
        # Inventory (item names — items are recreated from ITEM_DB on load)
        "inventory": [item.name for item in agent.inventory],
        # Memory
        "memory": _serialize_memory(agent.memory),
        # Status effects
        "status_effects": _serialize_status_effects(agent.status_effects),
    }


def _serialize_memory(memory: Any) -> Dict:
    """Serialize the memory system."""
    return {
        "short_term": [
            {
                "text": m.text,
                "tick": m.tick,
                "importance": m.importance,
                "memory_type": m.memory_type,
                "related_agent": m.related_agent,
                "location": list(m.location) if m.location else None,
                "tags": m.tags,
            }
            for m in memory.short_term
        ],
        "long_term": [
            {
                "text": m.text,
                "tick": m.tick,
                "importance": m.importance,
                "memory_type": m.memory_type,
                "related_agent": m.related_agent,
                "location": list(m.location) if m.location else None,
                "tags": m.tags,
            }
            for m in memory.long_term
        ],
        "relationships": {
            name: {
                "agent_name": rel.agent_name,
                "trust": rel.trust,
                "familiarity": rel.familiarity,
                "last_interaction_tick": rel.last_interaction_tick,
                "interaction_count": rel.interaction_count,
                "notes": rel.notes,
            }
            for name, rel in memory.relationships.items()
        },
        "beliefs": [
            {
                "subject": b.subject,
                "claim": b.claim,
                "confidence": b.confidence,
                "source": b.source,
            }
            for b in memory.beliefs
        ],
        "known_locations": {
            name: list(pos) for name, pos in memory.known_locations.items()
        },
        "preferences": dict(memory.preferences),
    }


def _serialize_status_effects(manager: Any) -> List[Dict]:
    """Serialize active status effects."""
    return [
        {
            "name": e.name,
            "remaining_ticks": e.remaining_ticks,
            "source": e.source,
        }
        for e in manager.active
    ]


def _serialize_weather(weather: Any) -> Dict:
    """Serialize weather state."""
    return {
        "current": weather.current.value,
        "duration": weather.duration,
        "wind_speed": weather.wind_speed,
        "wind_direction": weather.wind_direction,
        "temperature": weather.temperature,
        "humidity": weather.humidity,
        "world_tick": weather.world_tick,
        "day_count": weather.day_count,
        "time_of_day": weather.time_of_day.value,
    }


def _serialize_world_damage(world: Any) -> List[Dict]:
    """Serialize tile modifications (rubble, removed buildings, ground items).

    We only save tiles that differ from their generated state.
    """
    damage: List[Dict] = []

    for y in range(world.height):
        for x in range(world.width):
            tile = world.get_tile(x, y)
            if not tile:
                continue

            effects = getattr(tile, "effects", [])
            ground_items = getattr(tile, "ground_items", [])

            # Track tiles with rubble, removed buildings, or ground items
            has_rubble = "rubble" in effects
            has_ground_items = len(ground_items) > 0

            if has_rubble or has_ground_items:
                entry = {"x": x, "y": y}
                if has_rubble:
                    entry["rubble"] = True
                    entry["terrain_type"] = tile.terrain_type
                    entry["movement_cost"] = tile.movement_cost
                if has_ground_items:
                    entry["ground_items"] = [item.name for item in ground_items]
                damage.append(entry)

    return damage


def _serialize_destroyed_objects(world: Any) -> List[str]:
    """Track which named objects have been destroyed.

    On load, we remove these from the freshly generated world.
    """
    # We need to compare against the original object list.
    # Since we can't easily diff, we store the names of objects
    # that currently exist so we can remove any extras on load.
    return [obj.name for obj in world.objects]


# ============================================================
# DESERIALIZATION HELPERS
# ============================================================

def _restore_agent(agent: Any, data: Dict) -> None:
    """Restore an agent's state from saved data."""
    agent.x = data["x"]
    agent.y = data["y"]
    agent.health = data["health"]
    agent.max_health = data["max_health"]
    agent.is_alive = data["is_alive"]
    agent.denarii = data["denarii"]
    agent.drives = data["drives"]
    agent.action = data["action"]
    agent.current_thought = data["current_thought"]
    agent.last_speech = data.get("last_speech", "")
    agent.movement_cooldown = data.get("movement_cooldown", 0)
    agent.interaction_cooldown = data.get("interaction_cooldown", 0)
    agent.current_time = data.get("current_time", 0.0)

    # Personality
    agent.personality_seed = data.get("personality_seed", {})
    agent.personal_goals = data.get("personal_goals", [])
    agent.fears = data.get("fears", [])
    agent.values = data.get("values", [])

    # Brain
    agent.brain.potential = data.get("brain_potential", 0.0)
    agent.brain.last_spike_time = data.get("brain_last_spike", -999.0)

    # Inventory
    agent.inventory = []
    try:
        from roma_aeterna.world.items import ITEM_DB
        for item_name in data.get("inventory", []):
            item = ITEM_DB.create_item(item_name)
            if item:
                agent.inventory.append(item)
    except Exception:
        pass

    # Memory
    _restore_memory(agent.memory, data.get("memory", {}))

    # Status effects
    _restore_status_effects(agent.status_effects, data.get("status_effects", []))


def _restore_memory(memory: Any, data: Dict) -> None:
    """Restore memory from saved data."""
    from roma_aeterna.agent.memory import MemoryEntry, Relationship, Belief

    memory.short_term = []
    for m in data.get("short_term", []):
        memory.short_term.append(MemoryEntry(
            text=m["text"],
            tick=m["tick"],
            importance=m["importance"],
            memory_type=m.get("memory_type", "event"),
            related_agent=m.get("related_agent"),
            location=tuple(m["location"]) if m.get("location") else None,
            tags=m.get("tags", []),
        ))

    memory.long_term = []
    for m in data.get("long_term", []):
        memory.long_term.append(MemoryEntry(
            text=m["text"],
            tick=m["tick"],
            importance=m["importance"],
            memory_type=m.get("memory_type", "event"),
            related_agent=m.get("related_agent"),
            location=tuple(m["location"]) if m.get("location") else None,
            tags=m.get("tags", []),
        ))

    memory.relationships = {}
    for name, rel_data in data.get("relationships", {}).items():
        memory.relationships[name] = Relationship(
            agent_name=rel_data["agent_name"],
            trust=rel_data["trust"],
            familiarity=rel_data["familiarity"],
            last_interaction_tick=rel_data.get("last_interaction_tick", 0),
            interaction_count=rel_data.get("interaction_count", 0),
            notes=rel_data.get("notes", []),
        )

    memory.beliefs = []
    for b in data.get("beliefs", []):
        memory.beliefs.append(Belief(
            subject=b["subject"],
            claim=b["claim"],
            confidence=b.get("confidence", 0.5),
            source=b.get("source", "unknown"),
        ))

    memory.known_locations = {
        name: tuple(pos) for name, pos in data.get("known_locations", {}).items()
    }

    memory.preferences = data.get("preferences", {})


def _restore_status_effects(manager: Any, data: List[Dict]) -> None:
    """Restore active status effects from saved data."""
    from roma_aeterna.agent.status_effects import create_effect

    manager.active = []
    for effect_data in data:
        effect = create_effect(
            effect_data["name"].lower().replace(" ", "_"),
            source=effect_data.get("source", "save"),
        )
        if effect:
            effect.remaining_ticks = effect_data["remaining_ticks"]
            manager.active.append(effect)


def _restore_weather(weather: Any, data: Dict) -> None:
    """Restore weather state."""
    from roma_aeterna.engine.weather import WeatherType, TimeOfDay

    weather.current = WeatherType(data["current"])
    weather.duration = data["duration"]
    weather.wind_speed = data["wind_speed"]
    weather.wind_direction = data["wind_direction"]
    weather.temperature = data["temperature"]
    weather.humidity = data.get("humidity", 0.45)
    weather.world_tick = data["world_tick"]
    weather.day_count = data["day_count"]
    weather.time_of_day = TimeOfDay(data["time_of_day"])


def _restore_world_damage(world: Any, damage: List[Dict]) -> None:
    """Re-apply tile damage to a freshly generated world."""
    for entry in damage:
        x, y = entry["x"], entry["y"]
        tile = world.get_tile(x, y)
        if not tile:
            continue

        if entry.get("rubble"):
            tile.terrain_type = entry.get("terrain_type", "mountain")
            tile.movement_cost = entry.get("movement_cost", 8.0)
            tile.building = None
            if not hasattr(tile, "effects"):
                tile.effects = []
            if "rubble" not in tile.effects:
                tile.effects.append("rubble")

        if entry.get("ground_items"):
            try:
                from roma_aeterna.world.items import ITEM_DB
                if not hasattr(tile, "ground_items"):
                    tile.ground_items = []
                for item_name in entry["ground_items"]:
                    item = ITEM_DB.create_item(item_name)
                    if item:
                        tile.ground_items.append(item)
            except Exception:
                pass


def _restore_destroyed_objects(world: Any, surviving_names: List[str]) -> None:
    """Remove objects that were destroyed in the saved game."""
    surviving_set = set(surviving_names)
    world.objects = [obj for obj in world.objects if obj.name in surviving_set]


# ============================================================
# PUBLIC API
# ============================================================

def save_game(engine: Any, path: Optional[str] = None) -> str:
    """Save the full simulation state to SQLite.

    Args:
        engine: The SimulationEngine instance.
        path: Optional save file path. Defaults to saves/autosave.db.

    Returns:
        The path the save was written to.
    """
    if path is None:
        os.makedirs(SAVE_DIR, exist_ok=True)
        path = os.path.join(SAVE_DIR, DEFAULT_SAVE)

    # Ensure parent directory exists
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    # Remove old save
    if os.path.exists(path):
        os.remove(path)

    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    # --- Schema ---
    cursor.execute("""
        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE agents (
            uid TEXT PRIMARY KEY,
            data TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE world_damage (
            id INTEGER PRIMARY KEY,
            data TEXT
        )
    """)

    # --- Metadata ---
    meta = {
        "save_version": SAVE_VERSION,
        "tick_count": engine.tick_count,
        "weather": _serialize_weather(engine.weather),
        "surviving_objects": [obj.name for obj in engine.world.objects],
    }
    cursor.execute(
        "INSERT INTO metadata VALUES (?, ?)",
        ("simulation", json.dumps(meta)),
    )

    # --- Agents ---
    for agent in engine.agents:
        agent_data = _serialize_agent(agent)
        cursor.execute(
            "INSERT INTO agents VALUES (?, ?)",
            (agent.uid, json.dumps(agent_data)),
        )

    # --- World Damage ---
    damage = _serialize_world_damage(engine.world)
    cursor.execute(
        "INSERT INTO world_damage VALUES (?, ?)",
        (1, json.dumps(damage)),
    )

    conn.commit()
    conn.close()

    print(f"[SAVE] Game saved to {path} (tick {engine.tick_count}, "
          f"{len(engine.agents)} agents)")

    return path


def load_game(engine: Any, path: Optional[str] = None) -> bool:
    """Load simulation state from SQLite into an existing engine.

    The engine should already have a freshly generated world and agents
    (same as a new game). This function overwrites their state with
    saved data.

    Args:
        engine: The SimulationEngine instance (with fresh world + agents).
        path: Optional save file path. Defaults to saves/autosave.db.

    Returns:
        True if a save was loaded, False if no save file exists.
    """
    if path is None:
        path = os.path.join(SAVE_DIR, DEFAULT_SAVE)

    if not os.path.exists(path):
        return False

    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    try:
        # --- Metadata ---
        cursor.execute("SELECT value FROM metadata WHERE key = 'simulation'")
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False

        meta = json.loads(row[0])

        # Version check
        if meta.get("save_version", 0) != SAVE_VERSION:
            print(f"[SAVE] Warning: save version mismatch "
                  f"(save={meta.get('save_version')}, current={SAVE_VERSION})")

        engine.tick_count = meta["tick_count"]

        # Weather
        _restore_weather(engine.weather, meta["weather"])

        # Destroyed objects
        _restore_destroyed_objects(
            engine.world, meta.get("surviving_objects", [])
        )

        # --- World Damage ---
        cursor.execute("SELECT data FROM world_damage WHERE id = 1")
        row = cursor.fetchone()
        if row:
            damage = json.loads(row[0])
            _restore_world_damage(engine.world, damage)

        # --- Agents ---
        # Build lookup: uid -> agent
        agent_map = {a.uid: a for a in engine.agents}
        # Also by name (in case UIDs changed between runs)
        name_map = {a.name: a for a in engine.agents}

        cursor.execute("SELECT uid, data FROM agents")
        for uid, data_json in cursor.fetchall():
            data = json.loads(data_json)
            # Try UID match first, then name match
            agent = agent_map.get(uid) or name_map.get(data.get("name"))
            if agent:
                _restore_agent(agent, data)

        conn.close()

        print(f"[SAVE] Game loaded from {path} (tick {engine.tick_count}, "
              f"day {engine.weather.day_count})")

        return True

    except Exception as e:
        conn.close()
        print(f"[SAVE] Error loading save: {e}")
        return False


def has_save(path: Optional[str] = None) -> bool:
    """Check if a save file exists."""
    if path is None:
        path = os.path.join(SAVE_DIR, DEFAULT_SAVE)
    return os.path.exists(path)


def delete_save(path: Optional[str] = None) -> None:
    """Delete a save file."""
    if path is None:
        path = os.path.join(SAVE_DIR, DEFAULT_SAVE)
    if os.path.exists(path):
        os.remove(path)
        print(f"[SAVE] Deleted {path}")
