from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

import networkx as nx

class TemporalGraph:
    def __init__(self, path: Path | None = None):
        self.path = path or Path("data") / "graph.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.G = nx.MultiDiGraph()
        self.cache: Dict[str, Dict[str, Any]] = {}
        self._load()

    def upsert_item(self, item: Dict[str, Any]):
        iid = item["id"]
        timestamp = item.get("timestamp") or datetime.now(timezone.utc).isoformat()
        attrs = dict(item)
        attrs.setdefault("valid_from", timestamp)
        attrs.setdefault("valid_to", None)
        self.G.add_node(iid, **attrs)
        for rel in item.get("graph", {}).get("relations", []):
            target = rel.get("to")
            if target:
                self.G.add_edge(iid, target, rel=rel.get("rel", "related"))
        self.cache.clear()
        self._persist()

    def neighborhood(self, ids: List[str], hops: int = 2) -> Dict[str, Any]:
        key = f"{sorted(ids)}:{hops}"
        if key in self.cache:
            return self.cache[key]
        nodes = set()
        for node_id in ids:
            if node_id in self.G:
                nodes |= set(nx.single_source_shortest_path_length(self.G, node_id, cutoff=hops).keys())
        subgraph = self.G.subgraph(nodes).copy()
        data = nx.node_link_data(subgraph)
        self.cache[key] = data
        return data

    def consolidate(self, ttl_hours: int = 24) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=ttl_hours)
        to_remove = []
        for node, attrs in self.G.nodes(data=True):
            valid_from = _parse_ts(attrs.get("valid_from"))
            valid_to = _parse_ts(attrs.get("valid_to")) if attrs.get("valid_to") else None
            if valid_to and valid_to < cutoff:
                to_remove.append(node)
            elif valid_from and valid_from < cutoff:
                to_remove.append(node)
        for node in to_remove:
            self.G.remove_node(node)
        if to_remove:
            self.cache.clear()
            self._persist()
        return len(to_remove)

    def snapshot(self) -> Dict[str, Any]:
        return nx.node_link_data(self.G.copy())

    def _persist(self) -> None:
        data = nx.node_link_data(self.G)
        self.path.write_text(json.dumps(data), encoding="utf-8")

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.G = nx.node_link_graph(data, directed=True, multigraph=True)
        except Exception:
            self.G = nx.MultiDiGraph()


def _parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
