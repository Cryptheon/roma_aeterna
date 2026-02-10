# 🏛️ Rome: Aeterna — Agent-Based Ancient World Simulator

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-active-orange)
![Engine](https://img.shields.io/badge/engine-PyGame%20%2B%20vLLM-purple)

**Rome: Aeterna** is a high-fidelity, 2D top-down simulation of Ancient Rome (c. 161 AD), populated by autonomous AI agents. Unlike traditional game loops, this engine decouples simulation logic from rendering, allowing for complex biological, environmental, and cognitive processes to run asynchronously.

The simulation features a **living ecosystem** where agents possess Theory of Mind, organic navigation based on terrain costs, and physiological needs, all influenced by a dynamic weather and chaos system.

---

## 📑 Table of Contents

- [Features](#-features)
- [System Architecture](#-system-architecture)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage & Controls](#-usage--controls)
- [Project Structure](#-project-structure)
- [Logic & Mechanics](#-logic--mechanics)
- [Contributing](#-contributing)
- [License](#-license)

---

## ✨ Features

### 🧠 Cognitive & Social
- **LLM-Driven Agency**: Agents utilize Large Language Models (via vLLM) to generate internal monologues and complex decision-making (Move, Talk, Craft, Sleep).
- **Theory of Mind**: Agents maintain memory of interactions and develop "Preferences" (Like/Dislike) for items and other agents over time.
- **Asynchronous Thinking**: Heavy LLM inference runs on a dedicated worker thread, ensuring the GUI never freezes while agents "think."

### 🌍 Dynamic World
- **Procedural Generation**: Terrain is generated using multi-octave **Perlin Noise** for elevation and moisture.
- **Organic Infrastructure**: Roads are carved using "Random Walker" algorithms, creating natural, non-grid-aligned city layouts.
- **Chaos Engine**: A physics-based system handling **Fire Propagation** (fuel/burn rate), **Structural Integrity** (collapse risk), and **Weather Events** (Storms, Heatwaves).

### ⚙️ Engine
- **Hybrid CES Architecture**: Uses a Component-Entity-System for world objects (Flammable, Structural, Liquid).
- **Cost-Field Navigation**: Agents use a modified **A* Algorithm** that recognizes terrain costs (e.g., Roads = 1.0, Grass = 2.0, Forest = 4.0), resulting in natural pathing behaviors.
- **Deep Inspection**: A zoomable camera system allows real-time introspection of agent states, inventory, and health via mouse hover.

---

## 🏗 System Architecture

The simulation runs on two primary parallel loops to ensure performance:

1.  **The Render Loop (Main Thread @ 60 FPS)**: Handles PyGame window drawing, input processing (WASD/Zoom), and interpolates agent positions for smooth visuals.
2.  **The Logic Loop (Sim Thread @ 10 TPS)**: Handles biological decay, pathfinding calculations, weather updates, and the Chaos Engine.

**LLM Integration**:
Requests are offloaded to an `LLMWorker` thread. This worker maintains a queue of agents waiting for decisions, batches the context (Memory + Perception), and sends it to the vLLM API.

---

## 🛠 Installation

### Prerequisites
- Python 3.10 or higher.
- A running instance of **vLLM** (or an OpenAI-compatible API endpoint).

### Steps

1.  **Clone the Repository**
    ```bash
    git clone [https://github.com/your-username/rome-aeterna.git](https://github.com/your-username/rome-aeterna.git)
    cd rome-aeterna
    ```

2.  **Create a Virtual Environment**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Start vLLM (Optional but Recommended)**
    If you want the agents to have actual AI intelligence, run a local LLM server:
    ```bash
    python -m venv vllm_env
    source vllm_env/bin/activate
    pip install vllm
    python -m vllm.entrypoints.api_server --model mistralai/Mistral-7B-Instruct-v0.2 --port 8000
    ```

---

## ⚙ Configuration

Global settings can be modified in `config.py`.

| Variable | Default | Description |
| :--- | :--- | :--- |
| `GRID_WIDTH` | 128 | Width of the generated map in tiles. |
| `TILE_SIZE` | 32 | Base pixel size of a single tile at 1.0x zoom. |
| `TPS` | 10 | Ticks Per Second. Controls simulation speed. |
| `RANDOM_SEED` | 753 | Seed for Perlin Noise (753 BC). |
| `VLLM_URL` | `localhost` | URL for the LLM inference server. |

---

## 🎮 Usage & Controls

Run the simulation entry point:

```bash
python main.py
```

### Keyboard & Mouse Controls

| Input | Action |
| :--- | :--- |
| **W, A, S, D** | Pan the camera around the map. |
| **Scroll Wheel** | Zoom In / Zoom Out (0.5x to 3.0x). |
| **Mouse Hover** | Inspect an entity. Hover over an agent to see their Health, Hunger, Role, and current Action. |
| **ESC** | Quit the simulation. |

---

## 📂 Project Structure

```text
rome-aeterna/
├── src/
│   ├── agent/              # Agent Logic
│   │   ├── base.py         # Main Agent Class (Movement, State)
│   │   ├── memory.py       # Theory of Mind & Preferences
│   │   └── status.py       # Status Effects (Wet, Burned)
│   ├── core/               # Core Infrastructure
│   │   ├── logger.py       # Structured Logging System
│   │   └── events.py       # Global Event Bus
│   ├── engine/             # Simulation Physics
│   │   ├── loop.py         # The Tick Orchestrator
│   │   ├── navigation.py   # A* Pathfinding Implementation
│   │   ├── chaos.py        # Fire & Destruction Physics
│   │   └── weather.py      # Climate System
│   ├── gui/                # Visualization
│   │   ├── renderer.py     # PyGame Loop & Drawing
│   │   ├── camera.py       # Coordinate Transformation
│   │   └── assets.py       # Color Palettes & Sprites
│   ├── llm/                # AI Integration
│   │   ├── worker.py       # Async Threading for Inference
│   │   └── prompts.py      # Context Injection Templates
│   └── world/              # Environment
│       ├── generator.py    # Procedural Generation Algorithms
│       ├── map.py          # Grid Data Structures
│       ├── objects.py      # Building/Entity Prefabs
│       └── components.py   # Component System Classes
├── logs/                   # Auto-generated runtime logs
├── config.py               # Global Settings
├── main.py                 # Entry Point
└── requirements.txt        # Python Dependencies
```

---

## 🧠 Logic & Mechanics

### The Chaos Engine (`src/engine/chaos.py`)
The environment is not static.
1.  **Weather**: Runs on a cycle (Sunny -> Rain -> Storm).
2.  **Fire**: Objects with the `Flammable` component have a `fuel` and `burn_rate`. Fire spreads based on wind speed (from Weather) and proximity.
3.  **Collapse**: Objects with the `Structural` component take damage from Fire or Storms. If `hp <= 0`, they turn into Rubble (Difficult Terrain).

### Organic Navigation (`src/engine/navigation.py`)
Agents do not move in straight lines. They calculate the "Cheapest" path.
* **Roads**: Cost 1.0
* **Grass**: Cost 2.0
* **Forest**: Cost 4.0
* **Water/Mountains**: Impassable (Cost 999)

This results in "emergent roads" where agents naturally congregate on paved surfaces, mimicking real human behavior.

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:
1.  Fork the repository.
2.  Create a feature branch (`git checkout -b feature/AmazingFeature`).
3.  Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4.  Push to the branch (`git push origin feature/AmazingFeature`).
5.  Open a Pull Request.

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.

