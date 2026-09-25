# BIM/CIM 詳細度サンプルビューア / BIM/CIM LOD Sample Viewer

国土交通省「BIM/CIM活用ガイドライン(案) 第1編 共通編」で定義された **詳細度 100 / 200 / 300 / 400 / 500** を、
工種ごとの汎用3Dモデルで実際に切り替えて比較できる Web ビューアです。ブラウザだけで動きます (サーバ不要)。
発注者・受注者の事前協議で「詳細度○○とはどこまで作り込むのか」を実物で確認する用途を想定しています。

> **すべて架空の寸法・線形・地形で作成しており、実案件のデータは含みません。**
> 参考にした図面は一般的な寸法の把握にのみ使用し、契約外の相手に提示できる内容にしています。

## 収録モデル (工種)

| ID | 工種 | 内容 | 主な参考 |
|---|---|---|---|
| `tunnel` | 山岳トンネル | NATM 2車線、延長240m。支保パターン DⅢa/DⅡ/DⅠ、坑門工、非常駐車帯、ロックボルト・鋼製支保工・覆工鉄筋 | ガイドライン共通編 表1-2 (山岳トンネルの例) |
| `earthwork` | 道路土工 (切土・盛土) | 2車線道路 240m。切土 1:1.0 / 盛土 1:1.5、小段、法尻側溝、舗装4層、吹付法枠・植生工、縦排水、ガードレール | 道路土工要綱、道路標準横断図 |
| `pcbridge` | PC橋 (ポステンT桁 2径間) | 橋長61m、T桁5本、逆T式橋台・壁式橋脚、杭、支承・伸縮装置、PC鋼材・配筋 | 道路橋示方書、PC標準設計 |
| `boxculvert` | BOXカルバート (3.0×2.5m) | 延長40m、頂版・側壁・底版・ハンチ、ウイング、取付水路、目地・止水板、配筋 | カルバート工指針 |
| `retwall` | 擁壁 (逆T式 H=5m + 重力式 H=2m) | 延長40m、基礎、目地・止水板、水抜き孔、裏込め・透水マット、配筋、防護柵 | 重力式擁壁一般図、土木構造物標準設計 |
| `conduit` | 電線共同溝 | 管路部240m (電力6条・通信 共用FA方式)、電力/通信ハンドホール、引込管、横断管、地上機器 | 管路配列参考図、土工断面図、HH構造図 |
| `slope` | 法枠工・鉄筋挿入工・かご工 | 切土法面 60m に吹付法枠 300×300 @2.0m、主アンカー、鉄筋挿入工 D19 L=4m、排水孔。法尻にふとんかご3段 | 吹付法枠工・鉄筋挿入工詳細図 |

各モデルは `models/<ID>/` に `LOD100.glb` 〜 `LOD500.glb`、`model.json` (線形・視点・定義文)、`summary.json` (部材一覧)、`thumb.jpg` を持ちます。
IFC4 / DXF / OBJ 形式はサイズが大きいため [Releases](../../releases) に zip で添付しています。

## ビューアの使い方

* 入口画面で工種を選ぶ (URL は `index.html#tunnel` のように `#ID` で直接開けます)
* 上部のボタンで詳細度 100〜500 を切替。右パネルにその詳細度の定義と含まれる部材一覧 (表示/非表示可)
* 左端のアイコン: 視点 / 表示 (ワイヤーフレーム・透過・回転中心の目印・回転方向) / 断面カット / 回転感度 / ピボット / 回転中心 / クリックした点へ寄る
* 右上の ViewCube: ドラッグで回転、面・辺・角をクリックでその方向にスナップ、家アイコンでホーム視点

## 詳細度の定義について

共通定義は国交省ガイドライン共通編 表1-2 の記載です。山岳トンネルの工種別定義文は同表の「山岳トンネルの例」をそのまま使用し、
他の工種は共通定義に基づいて本サンプルでの適用例として記述しています (各 `model.json` の `lod_def`)。
発注者との協議では『3次元モデル成果物作成要領(案)』および各分野編の記載を正としてください。

## ファイル構成

```
index.html            ビューア (入口画面を含む単一ページ, three.js を CDN から読込)
models/index.json     工種一覧
models/<ID>/          各工種のモデル (GLB, model.json, summary.json, thumb.jpg, view_LOD300/400.png)
scripts/lodkit.py     共通ライブラリ (線形・メッシュ・書き出し)
scripts/gen_*.py      工種別の生成スクリプト
scripts/build_index.py, build_pages.py, render_thumbs.py
```

## ローカルで動かす / 再生成する

```bash
python -m http.server 8000        # → http://localhost:8000/
```

```bash
pip install numpy ezdxf ifcopenshell trimesh networkx
python scripts/gen_tunnel.py .    # 各 gen_*.py を実行すると models/<ID>/ に書き出し
python scripts/build_index.py .
```

`gen_*.py` 冒頭のパラメータ (断面・延長・配置) を書き換えれば別条件のサンプルを同じ手順で出力できます。GLB/OBJ は Y-up、DXF/IFC は Z-up です。

## ライセンス・出典

* コードおよびモデル: [MIT License](LICENSE)
* 詳細度の定義文: 国土交通省「BIM/CIM活用ガイドライン(案) 第1編 共通編」(令和4年3月) 表1-2、社会基盤情報標準化委員会「土木分野におけるモデル詳細度標準(案)【改訂版】」(平成30年3月)
* 3D描画: [three.js](https://threejs.org/) (MIT)

---

## English summary

A browser-based viewer that switches between Level of Detail 100–500 (MLIT Japan BIM/CIM Guideline) for seven generic civil-engineering models: mountain tunnel, road earthwork (cut/fill), PC girder bridge, box culvert, retaining walls, utility conduit, and slope protection (shotcrete frame, soil nailing, gabions). All geometry is procedurally generated with fictitious dimensions; no real project data is included. Static site (`index.html` + GLB), three.js from CDN. MIT licensed.
