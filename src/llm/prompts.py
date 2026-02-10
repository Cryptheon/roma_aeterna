COMMON_KNOWLEDGE = """
ROME 161 AD RULES:
1. Hierarchy: Senator > Plebeian > Slave.
2. Currency: Denarius.
3. Law: No weapons in city limits.
"""

def build_prompt(agent, weather):
    return f"""
    [SYSTEM]
    You are {agent.name}, a {agent.role}.
    Weather: {weather.current.name}.
    Stats: Hunger {int(agent.hunger)}/100.
    
    [MEMORY]
    {agent.memory.get_context()}
    
    [TASK]
    Decide next action. Return JSON:
    {{ "thought": "...", "action": "MOVE|TALK|CRAFT|SLEEP", "target": "..." }}
    """
