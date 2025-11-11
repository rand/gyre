from typing import List, Dict, Any
from collections import defaultdict

def lexical_score(q:str, text:str)->float:
    return sum(1 for tok in set(q.lower().split()) if tok in text.lower()) / (len(set(q.split()))+1e-6)

def retrieve(task_desc:str, pool:List[Dict[str,Any]])->List[Dict[str,Any]]:
    # Tiny hybrid stub: lexical score + provided relevance feature
    scored = []
    for it in pool:
        content = it.get("content",{})
        text = content.get("text","") if isinstance(content,dict) else str(content)
        s = 0.6*lexical_score(task_desc, text) + 0.4*it.get("features",{}).get("relevance",0.0)
        it2 = dict(it)
        it2["features"] = {**it.get("features",{}), "relevance": s}
        scored.append(it2)
    scored.sort(key=lambda x: x["features"]["relevance"], reverse=True)
    return scored[:50]
