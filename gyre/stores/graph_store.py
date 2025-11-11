from typing import Dict, Any, List, Optional, Tuple
import networkx as nx
from datetime import datetime

class TemporalGraph:
    def __init__(self):
        self.G = nx.MultiDiGraph()
    def upsert_item(self, item:Dict[str,Any]):
        iid = item["id"]
        self.G.add_node(iid, **item)
        for e in item.get("graph",{}).get("relations",[]):
            self.G.add_edge(iid, e.get("to",""), rel=e.get("rel","related"))
    def neighborhood(self, ids:List[str], hops:int=2)->Dict[str,Any]:
        nb = set()
        for i in ids:
            if i in self.G:
                nb |= set(nx.single_source_shortest_path_length(self.G, i, cutoff=hops).keys())
        sub = self.G.subgraph(nb).copy()
        return nx.node_link_data(sub)
