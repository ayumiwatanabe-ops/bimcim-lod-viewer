/* BIM/CIM 詳細度サンプルビューア service worker (build_pwa.py が生成)
   初回表示後にモデルをまとめてキャッシュし、以後はオフライン (機内モード・地下) でも動く。 */
const VERSION = '4d75314ae3';
const CACHE = 'bimcim-lod-' + VERSION;
const CORE = ["./", "./icons/apple-touch-icon.png", "./icons/icon-192.png", "./icons/icon-512.png", "./index.html", "./manifest.json", "./models/boxculvert/thumb.jpg", "./models/conduit/thumb.jpg", "./models/earthwork/thumb.jpg", "./models/index.json", "./models/pcbridge/thumb.jpg", "./models/retwall/thumb.jpg", "./models/slope/thumb.jpg", "./models/tunnel/thumb.jpg", "./vendor/jsm/controls/OrbitControls.js", "./vendor/jsm/loaders/GLTFLoader.js", "./vendor/jsm/utils/BufferGeometryUtils.js", "./vendor/three.module.js"];
const MODELS = [
"./models/boxculvert/LOD100.glb",
"./models/boxculvert/LOD200.glb",
"./models/boxculvert/LOD300.glb",
"./models/boxculvert/LOD400.glb",
"./models/boxculvert/LOD500.glb",
"./models/boxculvert/model.json",
"./models/boxculvert/summary.json",
"./models/boxculvert/view_LOD300.png",
"./models/boxculvert/view_LOD300_portal.png",
"./models/boxculvert/view_LOD400.png",
"./models/conduit/LOD100.glb",
"./models/conduit/LOD200.glb",
"./models/conduit/LOD300.glb",
"./models/conduit/LOD400.glb",
"./models/conduit/LOD500.glb",
"./models/conduit/model.json",
"./models/conduit/summary.json",
"./models/conduit/view_LOD300.png",
"./models/conduit/view_LOD400.png",
"./models/earthwork/LOD100.glb",
"./models/earthwork/LOD200.glb",
"./models/earthwork/LOD300.glb",
"./models/earthwork/LOD400.glb",
"./models/earthwork/LOD500.glb",
"./models/earthwork/model.json",
"./models/earthwork/summary.json",
"./models/earthwork/view_LOD300.png",
"./models/earthwork/view_LOD400.png",
"./models/pcbridge/LOD100.glb",
"./models/pcbridge/LOD200.glb",
"./models/pcbridge/LOD300.glb",
"./models/pcbridge/LOD400.glb",
"./models/pcbridge/LOD500.glb",
"./models/pcbridge/model.json",
"./models/pcbridge/summary.json",
"./models/pcbridge/view_LOD200.png",
"./models/pcbridge/view_LOD300.png",
"./models/pcbridge/view_LOD400.png",
"./models/retwall/LOD100.glb",
"./models/retwall/LOD200.glb",
"./models/retwall/LOD300.glb",
"./models/retwall/LOD400.glb",
"./models/retwall/LOD500.glb",
"./models/retwall/model.json",
"./models/retwall/summary.json",
"./models/retwall/view_LOD300.png",
"./models/retwall/view_LOD400.png",
"./models/slope/LOD100.glb",
"./models/slope/LOD200.glb",
"./models/slope/LOD300.glb",
"./models/slope/LOD400.glb",
"./models/slope/LOD500.glb",
"./models/slope/model.json",
"./models/slope/summary.json",
"./models/slope/view_LOD300.png",
"./models/slope/view_LOD400.png",
"./models/tunnel/LOD100.glb",
"./models/tunnel/LOD200.glb",
"./models/tunnel/LOD300.glb",
"./models/tunnel/LOD400.glb",
"./models/tunnel/LOD500.glb",
"./models/tunnel/model.json",
"./models/tunnel/summary.json",
"./models/tunnel/view_LOD300.png",
"./models/tunnel/view_LOD400.png"
];
const TOTAL_MB = 56;

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
