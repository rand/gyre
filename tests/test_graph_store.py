from gyre.stores.graph_store import TemporalGraph


def test_temporal_graph_upsert_and_neighborhood():
    g = TemporalGraph()
    item = {
        "id": "node-1",
        "graph": {"relations": [{"to": "node-2", "rel": "related"}]},
        "content": {"text": "Denver plan"},
    }
    g.upsert_item(item)
    assert "node-1" in g.G
    data = g.neighborhood(["node-1"], hops=1)
    ids = {node["id"] for node in data["nodes"]}
    assert "node-1" in ids
