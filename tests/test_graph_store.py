from pathlib import Path

from gyre.stores.graph_store import TemporalGraph


def test_temporal_graph_persists_and_caches(tmp_path):
    path = tmp_path / "graph.json"
    g = TemporalGraph(path)
    g.upsert_item({"id": "node-1", "timestamp": "2025-02-15T00:00:00Z", "graph": {"relations": []}})
    assert path.exists()
    g.neighborhood(["node-1"], hops=1)
    assert g.cache
    reloaded = TemporalGraph(path)
    assert reloaded.neighborhood(["node-1"], hops=1)["nodes"]


def test_temporal_graph_consolidation_and_skills(tmp_path):
    path = tmp_path / "graph.json"
    g = TemporalGraph(path)
    g.upsert_item({"id": "old-node", "valid_from": "2020-01-01T00:00:00Z", "graph": {"relations": []}})
    g.upsert_item({"id": "new-node", "graph": {"relations": []}, "references": 3})
    removed = g.consolidate(ttl_hours=1)
    assert removed >= 1
    promoted = g.promote_skills(min_references=2)
    assert promoted >= 1
    snapshot = g.snapshot()
    assert snapshot["nodes"]
