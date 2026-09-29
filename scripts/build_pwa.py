# -*- coding: utf-8 -*-
"""site/ を PWA (ホーム画面に追加・オフライン動作) にするための付属ファイルを生成する。
    python scripts/build_pwa.py [site_dir]
  生成物: vendor/ (three.js ローカルコピー), icons/, manifest.json, sw.js (全モデルを事前キャッシュ)
  build_pages.py の後に実行する (index.html のハッシュを sw.js のバージョンに含めるため)。
"""
import os, sys, json, hashlib, shutil
here = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "..", "site"))
VENDOR = os.path.join(here, "vendor")

# --- three.js をローカルへ (CDN 不要にする) ---
dst = os.path.join(SITE, "vendor")
os.makedirs(os.path.join(dst, "jsm", "controls"), exist_ok=True)
os.makedirs(os.path.join(dst, "jsm", "loaders"), exist_ok=True)
os.makedirs(os.path.join(dst, "jsm", "utils"), exist_ok=True)
shutil.copy(os.path.join(VENDOR, "three.module.js"), os.path.join(dst, "three.module.js"))
shutil.copy(os.path.join(VENDOR, "OrbitControls.js"), os.path.join(dst, "jsm", "controls", "OrbitControls.js"))
shutil.copy(os.path.join(VENDOR, "GLTFLoader.js"), os.path.join(dst, "jsm", "loaders", "GLTFLoader.js"))
shutil.copy(os.path.join(VENDOR, "BufferGeometryUtils.js"), os.path.join(dst, "jsm", "utils", "BufferGeometryUtils.js"))

# --- アイコン ---
from PIL import Image, ImageDraw, ImageFont
def icon(size, path, radius_ratio=0.22, bg=(30, 38, 46)):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = int(size * radius_ratio)
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=r, fill=bg + (255,))
    # トンネル断面 (馬蹄形) をオレンジで
    cx, cy = size / 2, size * 0.50
    w = size * 0.30; h = size * 0.30
    d.pieslice((cx - w, cy - h - w * 0.15, cx + w, cy + w - h * 0.15), 180, 360, fill=(217, 102, 28, 255))
    d.rectangle((cx - w, cy - h * 0.5, cx + w, cy + h * 0.55), fill=(217, 102, 28, 255))
    iw = w * 0.62; ih = h * 0.62
    d.pieslice((cx - iw, cy - ih - iw * 0.1, cx + iw, cy + iw - ih * 0.1), 180, 360, fill=bg + (255,))
    d.rectangle((cx - iw, cy - ih * 0.5, cx + iw, cy + h * 0.55), fill=bg + (255,))
    try: f = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", int(size * 0.20))
    except Exception: f = ImageFont.load_default()
    t = "LOD"; bb = d.textbbox((0, 0), t, font=f)
    d.text((cx - (bb[2] - bb[0]) / 2, size * 0.68), t, font=f, fill=(255, 255, 255, 255))
    im.save(path)
os.makedirs(os.path.join(SITE, "icons"), exist_ok=True)
icon(192, os.path.join(SITE, "icons", "icon-192.png"))
icon(512, os.path.join(SITE, "icons", "icon-512.png"))
icon(180, os.path.join(SITE, "icons", "apple-touch-icon.png"), radius_ratio=0.0)   # iOS が角丸を付ける

# --- manifest ---
manifest = {
    "name": "BIM/CIM 詳細度サンプルビューア", "short_name": "詳細度ビューア",
    "description": "国交省 BIM/CIM活用ガイドラインの詳細度100〜500を、工種別の汎用3Dモデルで比較",
    "start_url": "./", "scope": "./", "display": "standalone", "orientation": "any",
    "background_color": "#1E262E", "theme_color": "#1E262E", "lang": "ja",
    "icons": [{"src": "icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
              {"src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}],
}
json.dump(manifest, open(os.path.join(SITE, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# --- 事前キャッシュ一覧とバージョン ---
def rel(p): return os.path.relpath(p, SITE).replace("\\", "/")
core, models = ["./", "./index.html", "./manifest.json"], []
for root, _, files in os.walk(SITE):
    for f in files:
        p = os.path.join(root, f); r = rel(p)
        if r.startswith(("vendor/", "icons/")): core.append("./" + r)
        elif r == "models/index.json" or (r.startswith("models/") and f == "thumb.jpg"): core.append("./" + r)
        elif r.startswith("models/") and f.endswith((".glb", ".json", ".png")): models.append("./" + r)
core = sorted(set(core)); models = sorted(models)
h = hashlib.sha1()
for u in core + models:
    if u == "./": continue
    p = os.path.join(SITE, u[2:])
    h.update(u.encode()); h.update(hashlib.sha1(open(p, "rb").read()).digest())
version = h.hexdigest()[:10]
total_mb = sum(os.path.getsize(os.path.join(SITE, u[2:])) for u in models) / 1e6

sw = """/* BIM/CIM 詳細度サンプルビューア service worker (build_pwa.py が生成)
   初回表示後にモデルをまとめてキャッシュし、以後はオフライン (機内モード・地下) でも動く。 */
const VERSION = '%(version)s';
const CACHE = 'bimcim-lod-' + VERSION;
const CORE = %(core)s;
const MODELS = %(models)s;
const TOTAL_MB = %(total_mb).0f;

async function broadcast(msg){ for (const c of await self.clients.matchAll({ includeUncontrolled: true })) c.postMessage(msg); }

self.addEventListener('install', e => {
  e.waitUntil((async () => {
    const c = await caches.open(CACHE);
    for (const u of CORE){ try{ await c.put(u, await fetch(new Request(u, { cache: 'reload' }))); }catch(err){ /* 1件失敗しても続行 */ } }
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k !== CACHE) await caches.delete(k);
    await self.clients.claim();
    precacheModels();
  })());
});

let precaching = false;
async function precacheModels(){
  if (precaching) return; precaching = true;
  try{
    const c = await caches.open(CACHE);
    let done = 0;
    for (const u of MODELS){
      if (!(await c.match(u))){
        try{ const r = await fetch(new Request(u, { cache: 'reload' })); if (r.ok) await c.put(u, r); else throw new Error(u); }
        catch(err){ await broadcast({ type: 'precache-error', done, total: MODELS.length }); return; }
      }
      done++; await broadcast({ type: 'precache', done, total: MODELS.length, mb: TOTAL_MB });
    }
    await broadcast({ type: 'precache-done', total: MODELS.length, mb: TOTAL_MB });
  } finally { precaching = false; }
}

self.addEventListener('message', e => { if (e.data === 'precache') precacheModels(); });

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.origin !== location.origin) return;              // three.js は同梱なので外部は素通し (フォント等)
  e.respondWith((async () => {
    const c = await caches.open(CACHE);
    const hit = await c.match(e.request, { ignoreSearch: true });
    if (hit) return hit;
    try{
      const r = await fetch(e.request);
      if (r.ok && url.pathname.startsWith(new URL(self.registration.scope).pathname)) c.put(e.request, r.clone());
      return r;
    }catch(err){
      if (e.request.mode === 'navigate'){ const idx = await c.match('./index.html'); if (idx) return idx; }
      throw err;
    }
  })());
});
""" % dict(version=version, core=json.dumps(core, ensure_ascii=False), models=json.dumps(models, ensure_ascii=False, indent=0), total_mb=total_mb)
open(os.path.join(SITE, "sw.js"), "w", encoding="utf-8", newline="\n").write(sw)
print(f"sw.js version={version} core={len(core)} models={len(models)} ({total_mb:.0f} MB)")
