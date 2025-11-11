import json, os, random, pathlib

base = pathlib.Path(__file__).resolve().parents[1] / "data" / "train"
base.mkdir(parents=True, exist_ok=True)

def write(name, rows):
    with open(base / name, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r)+"\n")

# Tiny placeholder datasets
write("rank_train.jsonl", [
    {"task_desc":"plan coil-spring conversion","items_json":"[]","budget_tokens":800,"topk":5,"ideal_order_ids":["a","b"]}
])
write("sum_train.jsonl", [
    {"slot_name":"constraints","max_tokens":200,"items_with_citations_json":"[]","target_summary_text":"Keep emissions-compliant."}
])
write("ev_train.jsonl", [
    {"task_desc":"fetch parts","query_plan_json":"{}","realized_reward_delta":0.2}
])
write("red_train.jsonl", [
    {"target_scope":"demo","draft_json":"{}","policy_json":"{}","gold_redacted_json":"{}"}
])
write("blue_train.jsonl", [
    {"task_desc":"assemble","slot_specs_json":"[]","fragments_json":"{}","blueprint_json":"{}"}
])

print("Seeded tiny train datasets in", base)
