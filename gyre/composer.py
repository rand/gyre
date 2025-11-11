from typing import Dict, List, Any, Tuple
from .cpp import BLUEPRINT_SLOTS


def truncate(text: str, max_tokens: int) -> str:
    if len(text.split()) <= max_tokens:
        return text
    tokens = text.split()
    return " ".join(tokens[:max_tokens])


def compose(slot_specs: List[Dict[str, Any]], fragments: Dict[str, str]) -> Dict[str, Any]:
    bp = {"slots": []}
    caps = {s["name"]: s["max_tokens"] for s in slot_specs}
    for slot in BLUEPRINT_SLOTS:
        if slot not in caps or slot not in fragments:
            continue
        content = truncate(fragments[slot], caps[slot])
        bp["slots"].append({"name": slot, "content": content, "tokens": len(content.split())})
    return bp
