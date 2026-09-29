# -*- coding: utf-8 -*-
"""viewer/index.html (Artifact 用の断片HTML) から GitHub Pages 用の完全な index.html を生成する。
    python scripts/build_pages.py [出力パス]      # 既定: site/index.html
  - three.js の importmap を CDN から同梱の vendor/ に切替 (オフライン動作・PWA 用)
  - manifest / iOS ホーム画面用メタ / service worker 登録を追加
"""
import os, sys
here = os.path.dirname(os.path.abspath(__file__))
src = os.path.join(here, "..", "viewer", "index.html")
dst = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "..", "site", "index.html")
h = open(src, encoding="utf-8").read()
h = h.replace('<meta charset="utf-8">\n', '')
h = h.replace('"three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js"', '"three": "./vendor/three.module.js"')
h = h.replace('"three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"', '"three/addons/": "./vendor/jsm/"')
assert './vendor/jsm/' in h and './vendor/three.module.js' in h, 'importmap の書換に失敗'
i = h.index('</style>') + len('</style>')
head_extra = ('<link rel="manifest" href="manifest.json">\n'
              '<meta name="theme-color" content="#1E262E">\n'
              '<meta name="apple-mobile-web-app-capable" content="yes">\n'
              '<meta name="mobile-web-app-capable" content="yes">\n'
              '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">\n'
              '<meta name="apple-mobile-web-app-title" content="詳細度ビューア">\n'
              '<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">\n'
              '<link rel="icon" type="image/png" sizes="192x192" href="icons/icon-192.png">\n')
pwa = r"""
<style>
  .pwa-toast{position:fixed;left:50%;bottom:calc(14px + env(safe-area-inset-bottom,0px));transform:translateX(-50%);z-index:60;max-width:min(92vw,520px);
    background:#1E262E;color:#fff;border:1px solid #3a4652;border-radius:12px;padding:10px 14px;font-size:13px;line-height:1.5;box-shadow:0 6px 20px rgba(0,0,0,.35);display:flex;gap:10px;align-items:center}
  .pwa-toast[hidden]{display:none}
  .pwa-toast b{color:#FFB366}
  .pwa-toast button{margin-left:auto;border:0;background:#2f3b47;color:#fff;border-radius:8px;padding:6px 10px;font-size:12px;cursor:pointer;white-space:nowrap}
  .pwa-toast .ic{width:22px;height:22px;flex:none;display:inline-block;vertical-align:middle}
</style>
<script>
// ---- PWA: ホーム画面に追加 / オフライン用キャッシュ (build_pages.py が付加) ----
(function(){
  if (!('serviceWorker' in navigator) || !/^https?:$/.test(location.protocol)) return;
  const toast = document.createElement('div'); toast.className = 'pwa-toast'; toast.hidden = true; document.body.appendChild(toast);
  let hideTimer = null;
  function show(html, opts){
    opts = opts || {}; clearTimeout(hideTimer); toast.hidden = false;
    toast.innerHTML = html + (opts.close ? '<button type="button" data-x>閉じる</button>' : '');
    const x = toast.querySelector('[data-x]'); if (x) x.addEventListener('click', ()=>{ toast.hidden = true; if (opts.onClose) opts.onClose(); });
    if (opts.ms) hideTimer = setTimeout(()=>{ toast.hidden = true; }, opts.ms);
  }
  const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  const standalone = window.matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
  let hadController = !!navigator.serviceWorker.controller;
  navigator.serviceWorker.register('./sw.js').then(reg => { if (reg.active) reg.active.postMessage('precache'); }).catch(()=>{});
  navigator.serviceWorker.addEventListener('controllerchange', ()=>{ if (hadController) location.reload(); hadController = true; });
  let precacheDone = false;
  navigator.serviceWorker.addEventListener('message', ev => {
    const m = ev.data || {};
    if (m.type === 'precache' && m.done < m.total && !precacheDone) show(`オフライン用にモデルを保存中… <b>${m.done}/${m.total}</b>（合計約${m.mb}MB）`);
    else if (m.type === 'precache-done' || (m.type === 'precache' && m.done >= m.total)){
      if (precacheDone) return; precacheDone = true;
      let hint = '';
      try{ hint = (isIOS && !standalone && !localStorage.getItem('pwa-hint-shown')) ? '<br>Safari の共有ボタン <svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3v12M8 7l4-4 4 4M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7"/></svg> →「ホーム画面に追加」でアプリのように開けます' : ''; }catch(e){}
      show('<b>保存完了。</b>このページはオフラインでも使えます' + hint, { close: true, ms: hint ? 0 : 6000, onClose: ()=>{ try{ localStorage.setItem('pwa-hint-shown', '1'); }catch(e){} } });
    }
    else if (m.type === 'precache-error') show('オフライン用の保存が途中で止まりました（通信を確認して再読込すると続きから保存します）', { close: true, ms: 8000 });
  });
})();
</script>
"""
doc = ('<!DOCTYPE html>\n<html lang="ja">\n<head>\n<meta charset="utf-8">\n'
       '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
       + head_extra +
       '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)} [hidden]{display:none!important}</style>\n'
       + h[:i] + '\n</head>\n<body>' + h[i:] + pwa + '\n</body>\n</html>\n')
os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
open(dst, "w", encoding="utf-8", newline="\n").write(doc)
print("written:", os.path.abspath(dst), len(doc.encode('utf-8')), "bytes")
