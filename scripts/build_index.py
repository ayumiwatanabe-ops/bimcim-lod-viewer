# -*- coding: utf-8 -*-
"""site/models/*/model.json から models/index.json (入口画面の一覧) を作る
    python build_index.py [siteフォルダ]
"""
import os, sys, json
site = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "site")
mdir = os.path.join(site, "models")
ORDER = ["tunnel", "earthwork", "pcbridge", "boxculvert", "retwall", "conduit", "slope"]
items = []
for mid in sorted(os.listdir(mdir), key=lambda x: (ORDER.index(x) if x in ORDER else 99, x)):
    mj = os.path.join(mdir, mid, "model.json")
    if not os.path.exists(mj): continue
    m = json.load(open(mj, encoding="utf-8"))
    items.append({"id": m["id"], "name": m["name"], "category": m["category"], "description": m["description"], "thumb": f"models/{m['id']}/thumb.jpg"})
json.dump(items, open(os.path.join(mdir, "index.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("index.json:", [i["id"] for i in items])
