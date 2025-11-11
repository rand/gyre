import json, os, random, pathlib

base = pathlib.Path(__file__).resolve().parents[1] / "data" / "train"
base.mkdir(parents=True, exist_ok=True)

def write(name, rows):
    with open(base / name, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r)+"\n")

# Tiny placeholder datasets
write("rank_train.jsonl", [])
write("sum_train.jsonl", [])
write("ev_train.jsonl", [])
write("red_train.jsonl", [])
write("blue_train.jsonl", [])

print("Seeded tiny train datasets in", base)
