from typing import Dict, Any

def inject_message(session_id:str, text:str)->Dict[str,Any]:
    """Stub: add a message or file to the next Anthropic turn. For Computer Use,
    convert to a 'note' the agent will immediately read."""
    return {"session_id": session_id, "method": "message", "payload": text}
