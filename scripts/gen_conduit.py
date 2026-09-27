# -*- coding: utf-8 -*-
"""電線共同溝 詳細度別サンプル
   歩道下の管路部 240m + 特殊部 (電力/通信ハンドホール)、引込管、横断管、地上機器。
   参考: 管路配列参考図 (電力 単管路方式 φ100/φ125、通信 共用FA方式 ボディ管φ200+FA管φ150+φ75)、土工断面図、HH構造図 の一般的な寸法。実案件の平面線形・特殊部位置は使用していない。
"""
import sys, os, math
import numpy as np
from lodkit import *

A = Alignment([("S", 100.0), ("C", 300.0, 80.0), ("S", 60.0)])   # 管路中心線 (歩道内)
L = A.length
Y_ROAD = 3.0          # 管路中心から車道側 (右) へ歩道幅
Z_GL = 0.0            # 歩道面
COVER = 0.6           # 土被り
# 管路配列 (局所座標: y 右+, z 上+ ; 電力: 3列×2段 φ100/125, 通信: ボディ管φ200 + FA管φ150 + 副管φ75×3)
POWER = [(-0.55 + 0.2 * i, Z_GL - COVER - 0.10 - 0.2 * j, 0.05 if j == 0 else 0.0625, f"電力管 {'φ100' if j == 0 else 'φ125'}") for j in range(2) for i in range(3)]
COMM = [(0.30, Z_GL - COVER - 0.25, 0.10, "通信 ボディ管 φ200"), (0.30, Z_GL - COVER - 0.08, 0.075, "通信 FA管 φ150"),
        (0.55, Z_GL - COVER - 0.12, 0.0375, "通信 副管 φ75"), (0.55, Z_GL - COVER - 0.22, 0.0375, "通信 副管 φ75"), (0.55, Z_GL - COVER - 0.32, 0.0375, "通信 副管 φ75")]
TRENCH = (-0.75, 0.75, Z_GL - COVER - 0.55, Z_GL)   # y0, y1, z0, z1
HH_P = [40.0, 120.0, 200.0]      # 電力ハンドホール位置
HH_C = [70.0, 150.0, 230.0]      # 通信ハンドホール位置
SERVICE = [25.0, 55.0, 95.0, 135.0, 175.0, 215.0]   # 引込管 (民地側=左)
CROSS_AT = 120.0                  # 横断管 (車道横断)
rng = np.random.default_rng(11)

def rect(y0, y1, z0, z1): return np.array([[y0, z0], [y1, z0], [y1, z1], [y0, z1]])

def build_parts():
    parts = []
    C = dict(walk=(0.72, 0.72, 0.70, 0.45), road=(0.30, 0.30, 0.32, 0.55), curb=(0.80, 0.80, 0.78), trench=(0.66, 0.60, 0.48), sand=(0.85, 0.80, 0.62),
             power=(0.85, 0.30, 0.20), comm=(0.20, 0.45, 0.85), sub=(0.45, 0.70, 0.90), hh=(0.78, 0.78, 0.74), lid=(0.35, 0.35, 0.38),
             sheet=(0.95, 0.85, 0.20), sym=(0.2, 0.6, 0.9, 0.35), box100=(0.3, 0.55, 0.95, 0.35), marker=(0.95, 0.2, 0.2, 0.7),
             rebar=(0.70, 0.20, 0.15), cable=(0.15, 0.15, 0.15), equip=(0.55, 0.60, 0.55), fitting=(0.6, 0.6, 0.65))
    sts = stations(0, L, 2.0)
    # 道路 (参考): 歩道 / 縁石 / 車道 / 民地側境界
    parts.append(Part("歩道 (参考)", "道路", sweep(A, lambda s: rect(-1.5, 1.5, Z_GL - 0.19, Z_GL), sts), C["walk"], 100, "歩道 (幅3.0m) — 参考表示"))
    parts.append(Part("歩車道境界ブロック (参考)", "道路", sweep(A, lambda s: rect(1.5, 1.65, Z_GL - 0.3, Z_GL + 0.05), sts), C["curb"], 100, "参考表示"))
    parts.append(Part("車道 (参考)", "道路", sweep(A, lambda s: rect(1.65, 12.0, Z_GL - 0.35, Z_GL - 0.15), sts), C["road"], 100, "参考表示"))

    # ---------- LOD100 ----------
    parts.append(Part("管路ルート (中心線)", "線形", tube_along(np.array([A.frame(s)[0] + [0, 0, 0.3] for s in sts]), 0.12, 6), (0.9, 0.1, 0.1), 100, "電線共同溝のルート"))
    parts.append(Part("管路部 範囲ボックス", "概略形状", box_local(A, 0, L, -1.0, 1.0, Z_GL - 1.5, Z_GL + 0.2), C["box100"], 100, "管路の概略範囲", lod_max=100))
    for s in HH_P + HH_C:
        nm = "電力" if s in HH_P else "通信"
        parts.append(Part(f"特殊部位置マーカー ({nm}HH No.{s:.0f})", "概略形状", cylinder(A.frame(s)[0] + [0, 0, -2.0], A.frame(s)[0] + [0, 0, 1.5], 0.3, 10), C["marker"], 100, "特殊部の位置", lod_max=100))

    # ---------- LOD200: 標準断面のスイープ ----------
    parts.append(Part("管路部 (掘削断面 1.5×1.15m を一体化)", "管路部", sweep(A, lambda s: rect(*TRENCH), sts), C["trench"], 200, "管路部の標準断面をスイープした概略形状", lod_max=200))
    for s in HH_P + HH_C:
        nm = "電力" if s in HH_P else "通信"
        parts.append(Part(f"{nm}ハンドホール (概形 No.{s:.0f})", "特殊部", box_local(A, s - 1.2, s + 1.2, -0.9, 0.9, Z_GL - 2.0, Z_GL), C["hh"], 200, "特殊部の概形", lod_max=200))

    # ---------- LOD300: 外形 ----------
    for y, z, r, nm in POWER + COMM:   # 管条ごとの管路 = 主構造 → 外形は詳細度300で正確に
        col = C["power"] if "電力" in nm else (C["comm"] if "ボディ" in nm or "FA" in nm else C["sub"])
        parts.append(Part(f"{nm} (y={y:+.2f})", "管路 (条別)", sweep(A, lambda s, y=y, z=z, r=r: np.array([[y + r * math.cos(t), z + r * math.sin(t)] for t in np.linspace(0, 2 * math.pi, 10, endpoint=False)]), sts), col, 300, "管条ごとの外形 (管径・配列が正確)"))
    parts.append(Part("管路基礎 (砂 t=10cm) / 埋戻し砂", "土工", sweep(A, lambda s: rect(TRENCH[0], TRENCH[1], TRENCH[2], Z_GL - COVER + 0.05), sts), C["sand"], 300, "管路の砂基礎・砂埋戻し"))
    parts.append(Part("埋戻し (掘削断面)", "土工", sweep(A, lambda s: rect(*TRENCH), sts), (0.66, 0.60, 0.48, 0.45), 300, "管路部の掘削・埋戻し範囲 (半透明)"))
    parts.append(Part("歩道舗装復旧 (t=19cm)", "舗装", sweep(A, lambda s: rect(TRENCH[0] - 0.1, TRENCH[1] + 0.1, Z_GL - 0.19, Z_GL + 0.01), sts), (0.60, 0.60, 0.58), 300, "舗装復旧範囲"))
    for s in HH_P + HH_C:
        p = s in HH_P; nm = "電力" if p else "通信"; iw, il, ih = (1.2, 2.0, 1.6) if p else (1.0, 1.6, 1.4); t = 0.2
        zb = Z_GL - ih - 2 * t - 0.15; m = Mesh()
        m.add(box_local(A, s - il / 2 - t, s + il / 2 + t, -iw / 2 - t, iw / 2 + t, zb, zb + t))                         # 底版
        m.add(box_local(A, s - il / 2 - t, s - il / 2, -iw / 2 - t, iw / 2 + t, zb + t, Z_GL - 0.15 - t))                # 側壁 (起点側)
        m.add(box_local(A, s + il / 2, s + il / 2 + t, -iw / 2 - t, iw / 2 + t, zb + t, Z_GL - 0.15 - t))                # 側壁 (終点側)
        m.add(box_local(A, s - il / 2, s + il / 2, -iw / 2 - t, -iw / 2, zb + t, Z_GL - 0.15 - t))                       # 側壁 (民地側)
        m.add(box_local(A, s - il / 2, s + il / 2, iw / 2, iw / 2 + t, zb + t, Z_GL - 0.15 - t))                         # 側壁 (車道側)
        for a, b in ((s - il / 2 - t, s - 0.4), (s + 0.4, s + il / 2 + t)): m.add(box_local(A, a, b, -iw / 2 - t, iw / 2 + t, Z_GL - 0.15 - t, Z_GL - 0.15))   # 頂版 (開口 0.8×0.8 付き)
        for a, b in ((-iw / 2 - t, -0.4), (0.4, iw / 2 + t)): m.add(box_local(A, s - 0.4, s + 0.4, a, b, Z_GL - 0.15 - t, Z_GL - 0.15))
        parts.append(Part(f"{nm}ハンドホール 躯体 (内空 {il}×{iw}×{ih}m, 壁厚{t*100:.0f}cm, No.{s:.0f})", "特殊部", m, C["hh"], 300, "底版・側壁・頂版 (開口付き) の外形が正確な現場打ち躯体"))
        parts.append(Part(f"{nm}ハンドホール 基礎 (均しコン・砕石, No.{s:.0f})", "特殊部", box_local(A, s - il / 2 - t - 0.2, s + il / 2 + t + 0.2, -iw / 2 - t - 0.2, iw / 2 + t + 0.2, Z_GL - ih - 2 * t - 0.45, Z_GL - ih - 2 * t - 0.15), C["sand"], 300, "基礎"))
        parts.append(Part(f"{nm}ハンドホール 蓋位置記号 (No.{s:.0f})", "記号", box_local(A, s - 0.5, s + 0.5, -0.4, 0.4, Z_GL - 0.02, Z_GL + 0.05), C["sym"], 300, "鉄蓋の位置 (記号)。詳細度400で実形状", lod_max=300))
    for s in SERVICE:
        m = Mesh()
        for k in range(2):
            path = np.array([A.to_world(s + 0.1 * k, [[y, Z_GL - COVER - 0.15 - 0.1 * k]])[0] for y in np.linspace(-0.55, -4.0, 8)])
            m.add(tube_along(path, 0.0375, 8))
        parts.append(Part(f"引込管 φ75 ×2 (No.{s:.0f})", "引込管", m, C["sub"], 300, "民地への引込管 (外形)"))
        parts.append(Part(f"引込管 民地側端末 位置記号 (No.{s:.0f})", "記号", box_local(A, s - 0.3, s + 0.3, -4.3, -3.7, Z_GL - COVER - 0.5, Z_GL + 0.05), C["sym"], 300, "引込管端末 (立上り・接続部) の位置を記号で表示。詳細度400で実形状", lod_max=300))
    m = Mesh()
    for k in range(4):
        path = np.array([A.to_world(CROSS_AT + 0.12 * (k - 1.5), [[y, Z_GL - 1.15]])[0] for y in np.linspace(0.7, 12.0, 12)])
        m.add(tube_along(path, 0.05, 8))
    parts.append(Part("横断管 φ100 ×4 (車道横断, 深さ1.0m)", "管路 (条別)", m, C["power"], 300, "横断管の外形"))
    parts.append(Part("横断管 埋戻し範囲 (車道部 開削)", "土工", box_local(A, CROSS_AT - 0.6, CROSS_AT + 0.6, 0.7, 12.0, Z_GL - 1.5, Z_GL - 0.35), (0.66, 0.60, 0.48, 0.45), 300, "車道横断部の掘削・埋戻し範囲 (半透明)"))
    parts.append(Part("地上機器 台座 (変圧器, No.120)", "地上機器", box_local(A, CROSS_AT - 1.1, CROSS_AT + 1.1, -1.4, -0.4, Z_GL - 0.6, Z_GL + 0.2), C["hh"], 300, "地上機器の基礎台座"))
    parts.append(Part("地上機器 外形 (変圧器)", "地上機器", box_local(A, CROSS_AT - 0.9, CROSS_AT + 0.9, -1.3, -0.5, Z_GL + 0.2, Z_GL + 1.5), C["equip"], 300, "地上機器の外形"))

    # ---------- LOD400: 各管条・蓋・配筋・金物 ----------
    m = Mesh(); n = 0     # 管継手 (ソケット): 4m 定尺ごと
    for y, z, r, nm in POWER + COMM:
        for s in np.arange(4.0, L, 4.0):
            if any(abs(s - hh) < 1.5 for hh in HH_P + HH_C): continue
            m.add(sweep(A, lambda ss, y=y, z=z, r=r: np.array([[y + (r + 0.012) * math.cos(t), z + (r + 0.012) * math.sin(t)] for t in np.linspace(0, 2 * math.pi, 10, endpoint=False)]), np.array([s - 0.08, s + 0.08]))); n += 1
    parts.append(Part(f"管継手 (ソケット, 4m 定尺ごと, {n}箇所)", "管路 (条別)", m, C["fitting"], 400, "管の継手部"))
    m = Mesh(); n = 0     # ダクトスペーサ: 2m 間隔
    for s in np.arange(1.0, L, 2.0):
        if any(abs(s - hh) < 1.5 for hh in HH_P + HH_C): continue
        m.add(box_local(A, s - 0.02, s + 0.02, -0.70, -0.30, Z_GL - COVER - 0.50, Z_GL - COVER + 0.0))
        m.add(box_local(A, s - 0.02, s + 0.02, 0.15, 0.65, Z_GL - COVER - 0.42, Z_GL - COVER + 0.02)); n += 1
    parts.append(Part(f"ダクトスペーサ (@2m, {n}箇所)", "管路 (条別)", m, C["fitting"], 400, "管路の間隔保持材"))
    parts.append(Part("埋設シート (注意標示)", "附属", sweep(A, lambda s: rect(-0.6, 0.6, Z_GL - 0.35, Z_GL - 0.34), sts), C["sheet"], 400, "埋設標示シート"))
    for s in HH_P + HH_C:
        p = s in HH_P; nm = "電力" if p else "通信"; iw, il, ih = (1.2, 2.0, 1.6) if p else (1.0, 1.6, 1.4); t = 0.2
        parts.append(Part(f"{nm}ハンドホール 鉄蓋 600角 (No.{s:.0f})", "特殊部", box_local(A, s - 0.35, s + 0.35, -0.35, 0.35, Z_GL - 0.15, Z_GL + 0.0), C["lid"], 400, "鉄蓋の実形状"))
        parts.append(Part(f"{nm}ハンドホール 蓋受枠・調整コン (No.{s:.0f})", "特殊部", box_local(A, s - 0.5, s + 0.5, -0.5, 0.5, Z_GL - 0.15, Z_GL - 0.0), C["hh"], 400, "蓋受枠"))
        # 配筋 (壁: 縦筋 D13@200, 横筋 D13@200 両面)
        m = Mesh(); n = 0
        for yy in (-iw / 2 - t / 2, iw / 2 + t / 2):
            for ss in np.arange(s - il / 2 - t / 2, s + il / 2 + t / 2 + 0.01, 0.2):
                m.add(tube_along(A.to_world(ss, [[yy, Z_GL - ih - 2 * t - 0.1], [yy, Z_GL - 0.2]]), 0.0065, 4)); n += 1
            for zz in np.arange(Z_GL - ih - 2 * t - 0.05, Z_GL - 0.2, 0.2):
                m.add(tube_along(np.array([A.to_world(ss, [[yy, zz]])[0] for ss in np.linspace(s - il / 2 - t / 2, s + il / 2 + t / 2, 6)]), 0.0065, 4)); n += 1
        for zz in (Z_GL - ih - 2 * t - 0.1, Z_GL - ih - t - 0.1):
            for ss in np.arange(s - il / 2 - t / 2, s + il / 2 + t / 2 + 0.01, 0.2):
                m.add(tube_along(A.to_world(ss, [[-iw / 2 - t / 2, zz], [iw / 2 + t / 2, zz]]), 0.0065, 4)); n += 1
        parts.append(Part(f"{nm}ハンドホール 配筋 D13@200 ({n}本, No.{s:.0f})", "配筋", m, C["rebar"], 400, "特殊部の配筋"))
        # 立金物・ケーブル受金物
        m = Mesh()
        for yy in (-iw / 2 + 0.05, iw / 2 - 0.05):
            for ss in (s - il / 2 + 0.3, s + il / 2 - 0.3):
                m.add(box_at(A.to_world(ss, [[yy, Z_GL - ih / 2 - 0.35]])[0], (0.05, 0.05, ih - 0.3), A.frame(ss)[1], A.frame(ss)[2], [0, 0, 1.0]))
                for zz in np.linspace(Z_GL - ih - 0.1, Z_GL - 0.6, 3):
                    m.add(box_at(A.to_world(ss, [[yy - np.sign(yy) * 0.15, zz]])[0], (0.05, 0.3, 0.03), A.frame(ss)[1], A.frame(ss)[2], [0, 0, 1.0]))
        parts.append(Part(f"{nm}ハンドホール 立金物・ケーブル受金物 (No.{s:.0f})", "特殊部", m, C["fitting"], 400, "内部金物"))
    for s in SERVICE:     # 引込管 端末: 民地側の立上り管と防護管
        m = Mesh()
        for k in range(2):
            p0 = A.to_world(s + 0.1 * k, [[-4.0, Z_GL - COVER - 0.15 - 0.1 * k]])[0]
            m.add(cylinder(p0, p0 + [0, 0, COVER + 0.15 + 0.1 * k + 0.6], 0.0375, 8))
        m.add(box_local(A, s - 0.15, s + 0.25, -4.15, -3.85, Z_GL - 0.05, Z_GL + 0.6))
        parts.append(Part(f"引込管 端末 (立上り管・防護管, No.{s:.0f})", "引込管", m, C["sub"], 400, "引込管端末の実形状"))
    m = Mesh()            # 地上機器への立上り管 φ100 ×2
    for k in range(2):
        p0 = A.to_world(CROSS_AT - 0.3 + 0.6 * k, [[-0.9, Z_GL - COVER - 0.3]])[0]
        m.add(cylinder(p0, p0 + [0, 0, COVER + 0.3 + 0.2], 0.05, 8))
    parts.append(Part("地上機器 立上り管 φ100 ×2", "管路 (条別)", m, C["power"], 400, "地上機器への立上り配管"))
    m = Mesh()
    for k in range(6):
        m.add(box_local(A, CROSS_AT - 0.9, CROSS_AT + 0.9, -1.3 + 0.13 * k, -1.25 + 0.13 * k, Z_GL + 0.25, Z_GL + 1.45))
    parts.append(Part("地上機器 詳細 (放熱フィン・扉)", "地上機器", m, (0.4, 0.45, 0.4), 400, "地上機器の細部"))

    # ---------- LOD500: 完成形状 (ケーブル入線・実測位置) ----------
    m = Mesh()
    for (y, z, r, nm) in [POWER[3], POWER[4], COMM[0]]:
        jitter = rng.normal(0, 0.02, size=(len(sts), 2))
        path = np.array([A.to_world(s, [[y + j[0], z + j[1]]])[0] for s, j in zip(sts, jitter)])
        m.add(tube_along(path, r * 0.55, 6))
    parts.append(Part("ケーブル (電力2条・通信1条 入線後)", "完成設備", m, C["cable"], 500, "完成時に入線されたケーブル"))
    m = Mesh()
    for s in HH_P + HH_C:
        m.add(box_local(A, s - 0.4, s + 0.4, -0.4, 0.4, Z_GL + 0.0, Z_GL + 0.008))
    parts.append(Part("鉄蓋 出来形位置 (実測, 記号)", "出来形", m, (0.55, 0.5, 0.4, 0.6), 500, "出来形計測結果の反映 (サンプルでは記号)"))
    return parts

def meta():
    return dict(
        id="conduit", name="電線共同溝（管路部・特殊部）", category="電線共同溝", thumb_hide_ref=True,
        description="歩道下の管路部 240m。電力 単管路方式 6条 (φ100/φ125)、通信 共用FA方式 (ボディ管φ200・FA管φ150・副管φ75×3)、電力/通信ハンドホール各3基、引込管6箇所、横断管、地上機器を含む。詳細度300で管条ごとの管路と躯体、400で継手・スペーサ・配筋・金物。",
        ref="管路配列参考図・土工断面図・ハンドホール構造図の一般的な寸法を参考にした架空配置。実案件の平面・特殊部位置は使用していない。",
        alignment=A, center=[115.0, 8.0, -0.5], ground={"cx": 120, "cy": 20, "z": -2.5, "size": 600},
        views=[{"name": "全景", "pos": [8, -22, 12], "target": [50, 2, -1]}, {"name": "特殊部", "pos": [30, -6, 2.5], "target": [40, 0, -0.8]},
               {"name": "管路断面", "pos": None, "target": None, "clip": 90}, {"name": "地上機器", "pos": [110, -10, 4], "target": [120, -1, 0]}],
        lod_def={100: ["管路ルートを線で、管路部・特殊部の位置を単純な形状で示す。"],
                 200: ["管路部の標準断面 (掘削断面) をルートに沿ってスイープし、特殊部を概形の直方体で表す。"],
                 300: ["主構造の外形が正確。管条ごとの管路 (管径・配列)、横断管、引込管、特殊部の躯体 (底版・側壁・開口付き頂版) と基礎、地上機器の外形をモデル化。鉄蓋や引込管端末などの接続部・附帯物は位置を記号で示す。舗装復旧・埋戻し・砂基礎の範囲を表す。"],
                 400: ["詳細度300に加えて管継手・ダクトスペーサ、鉄蓋・受枠、特殊部の配筋、立金物・ケーブル受金物、引込管端末 (立上り管・防護管)、地上機器への立上り管、埋設シート、地上機器の細部をモデル化。"],
                 500: ["完成形状 (入線後のケーブル、鉄蓋の出来形位置)。"]},
        notes=["道路 (歩道・車道) は参考表示。", "管路配列は参考図の電力 単管路方式・通信 共用FA方式に準じた一般的な配置。"],
    )

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "site")
    export_model(build_parts(), os.path.abspath(out), meta())
