# -*- coding: utf-8 -*-
"""オフライン版 (1ファイル) ビューアを生成する。
   three.js を data: URL で import map に埋め込み、モデル (GLB/JSON/サムネイル) を base64 で埋め込むので、
   ダブルクリック (file://) で開けてインターネット接続も不要。
    python build_offline.py [siteフォルダ] [出力html] [--only id,id,...]
"""
import os, sys, json, base64
here = os.path.dirname(os.path.abspath(__file__))
args = [a for a in sys.argv[1:] if not a.startswith("--")]
only = None
for a in sys.argv[1:]:
    if a.startswith("--only="): only = a.split("=", 1)[1].split(",")
site = args[0] if len(args) > 0 else os.path.join(here, "..", "site")
out = args[1] if len(args) > 1 else os.path.join(site, "..", "release", "bimcim-lod-viewer_offline.html")
vendor = os.path.join(here, "vendor")

h = open(os.path.join(site, "index.html"), encoding="utf-8").read()

def data_js(path, fix=None):
    src = open(path, "rb").read()
    if fix:   # data: URL のモジュールは相対 import を解決できないので、bare specifier に書き換えて import map で解決する
        for a, b in fix: src = src.replace(a.encode("utf-8"), b.encode("utf-8"))
    return "data:text/javascript;base64," + base64.b64encode(src).decode("ascii")

# 1) import map を data: URL に置換 (OrbitControls/GLTFLoader は 'three' を import するので、両方とも map に載せる)
three = data_js(os.path.join(vendor, "three.module.js"))
orbit = data_js(os.path.join(vendor, "OrbitControls.js"))
gltf = data_js(os.path.join(vendor, "GLTFLoader.js"), fix=[("'../utils/BufferGeometryUtils.js'", "'three/addons/utils/BufferGeometryUtils.js'")])
bgu = data_js(os.path.join(vendor, "BufferGeometryUtils.js"))
im_start = h.index('<script type="importmap">'); im_end = h.index("</script>", im_start) + len("</script>")
importmap = '<script type="importmap">\n' + json.dumps({"imports": {
    "three": three, "three/addons/controls/OrbitControls.js": orbit, "three/addons/loaders/GLTFLoader.js": gltf, "three/addons/utils/BufferGeometryUtils.js": bgu}}) + "\n</script>"
h = h[:im_start] + importmap + h[im_end:]

# 2) モデル資産を埋め込む
embed = {}
idx = json.load(open(os.path.join(site, "models", "index.json"), encoding="utf-8"))
if only: idx = [m for m in idx if m["id"] in only]
embed["models/index.json"] = idx
total = 0
for m in idx:
    mid = m["id"]; d = os.path.join(site, "models", mid)
    for f in ("model.json", "summary.json"):
        embed[f"models/{mid}/{f}"] = json.load(open(os.path.join(d, f), encoding="utf-8"))
    for l in (100, 200, 300, 400, 500):
        b = open(os.path.join(d, f"LOD{l}.glb"), "rb").read(); total += len(b)
        embed[f"models/{mid}/LOD{l}.glb"] = base64.b64encode(b).decode("ascii")
    tp = os.path.join(d, "thumb.jpg")
    if os.path.exists(tp):
        embed[f"models/{mid}/thumb.jpg:uri"] = "data:image/jpeg;base64," + base64.b64encode(open(tp, "rb").read()).decode("ascii")
embed_script = "<script>window.__BIMCIM_EMBED = " + json.dumps(embed, ensure_ascii=False, separators=(",", ":")) + ";</script>\n"
mod_start = h.index('<script type="module">')
h = h[:mod_start] + embed_script + h[mod_start:]

# 3) 外部参照を完全になくす: Google Fonts の link を削除 (PC 標準フォントで表示)。タイトルにオフライン版と明記
import re
h = re.sub(r'<link rel="stylesheet" href="https://fonts\.googleapis\.com[^"]*">\n?', '', h)
h = h.replace("<title>BIM/CIM 詳細度サンプルビューア</title>", "<title>BIM/CIM 詳細度サンプルビューア (オフライン版)</title>", 1)
os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
open(out, "w", encoding="utf-8").write(h)
print(f"written: {os.path.abspath(out)}  {os.path.getsize(out)/1048576:.1f} MB (models raw {total/1048576:.1f} MB, {len(idx)} models)")
