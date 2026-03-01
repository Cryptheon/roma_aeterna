"""
JSON parser for LLM output.

Handles: think tags, markdown fences, trailing commas, extraction from prose.
"""

import json
import re
from typing import Dict, Optional


def parse_json(text: str) -> Optional[Dict]:
    """Extract and parse a JSON object from raw LLM output."""
    if not text:
        return None

    text = text.strip()

    # Qwen3 often wraps output in <think>...</think> tags — strip those first
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

    # Strip common markdown wrappers
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fallback: extract first JSON object from the text
    # This handles cases where the model adds explanation before/after
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        candidate = text[start:end]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

        # Try fixing common issues: trailing commas, single quotes
        try:
            fixed = re.sub(r',\s*}', '}', candidate)
            fixed = re.sub(r',\s*]', ']', fixed)
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

    return None
