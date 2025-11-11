from typing import Dict, Any

def inject_system_prefix(session_id:str, text:str)->Dict[str,Any]:
    """Stub: prepend a system patch into next OpenAI turn (Realtime or Chat).
    Wire to your gateway that owns the session stream.
    """
    return {"session_id": session_id, "method": "system_prefix", "payload": text}
