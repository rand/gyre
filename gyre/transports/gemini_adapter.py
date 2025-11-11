from typing import Dict, Any

def inject_function_result(session_id:str, name:str, result:Dict[str,Any])->Dict[str,Any]:
    """Stub: return a function result to Gemini, carrying structured context."""
    return {"session_id": session_id, "method": "function_result", "name": name, "payload": result}
