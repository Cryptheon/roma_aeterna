from roma_aeterna.tools.agent_diagnostics import AgentDiagnostics
from roma_aeterna.engine.loop import SimulationEngine
from roma_aeterna.engine.renderer import Renderer

import threading

engine = SimulationEngine(world, agents)
renderer = Renderer(engine)

# Run diagnostics in a background thread
diag = AgentDiagnostics(engine)
diag_thread = threading.Thread(target=diag.watch, args=(10,), daemon=True)
diag_thread.start()

renderer.run()
