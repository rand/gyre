from typing import Dict, Any, List
import time

class PrivateStore:
    def __init__(self):
        self.items: Dict[str, Dict[str,Any]] = {}
    def upsert(self, item:Dict[str,Any]):
        self.items[item["id"]] = item
    def query(self, limit:int=100)->List[Dict[str,Any]]:
        return list(self.items.values())[:limit]
    def get(self, item_id:str)->Dict[str,Any]:
        return self.items.get(item_id)
    def query_session(self, session_id:str, limit:int=50)->List[Dict[str,Any]]:
        out = [item for item in self.items.values() if item.get("session_id")==session_id]
        out.sort(key=lambda i: i.get("timestamp",""), reverse=True)
        return out[:limit]
