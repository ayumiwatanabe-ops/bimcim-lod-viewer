# -*- coding: utf-8 -*-
"""viewer/index.html (Artifact 用の断片HTML) から GitHub Pages 用の完全な index.html を生成する。
    python scripts/build_pages.py            # ../tunnel-lod-viewer/index.html を更新
"""
import os, sys
here = os.path.dirname(os.path.abspath(__file__))
src = os.path.join(here, "..", "viewer", "index.html")
dst = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "..", "site", "index.html")
h = open(src, encoding="utf-8").read()
h = h.replace('<meta charset="utf-8">\n', '')
i = h.index('</style>') + len('</style>')
doc = ('<!DOCTYPE html>\n<html lang="ja">\n<head>\n<meta charset="utf-8">\n'
       '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
       '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)} [hidden]{display:none!important}</style>\n'
       + h[:i] + '\n</head>\n<body>' + h[i:] + '\n</body>\n</html>\n')
open(dst, "w", encoding="utf-8").write(doc)
print("written:", os.path.abspath(dst), len(doc), "bytes")
