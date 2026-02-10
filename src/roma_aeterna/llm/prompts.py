def build_prompt(agent, world, weather):
    # 1. Gather Perception
    visuals = agent.perceive(world, radius=6)
    
    return f"""
    [SYSTEM]
    You are {agent.name}, a {agent.role} in Ancient Rome (161 AD).
    Your goal is to survive, socialize, and fulfill your duties.
    
    [STATUS]
    Health: {int(agent.health)}/100
    Hunger: {int(agent.hunger)}/100
    Energy: {int(agent.energy)}/100
    Weather: {weather.current.name}
    
    [PERCEPTION]
    (What you see in your immediate vicinity)
    {visuals}
    
    [MEMORY]
    (Recent events)
    {agent.memory.get_context()}
    
    [CURRENT THOUGHT LOOP]
    Last thought: "{agent.current_thought}"
    
    [TASK]
    Based on your status and perception, decide your next move.
    If you move, choose a relative coordinate (e.g., target is x+1, y-1).
    Valid Actions: MOVE, TALK, CRAFT, IDLE, SLEEP.
    
    Response Format (JSON):
    {{
        "thought": "internal monologue explaining why...",
        "action": "ACTION_NAME",
        "target": [x, y] or "Target Name"
    }}
    """