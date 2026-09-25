# -*- coding: utf-8 -*-
"""法面保護工（吹付法枠工・鉄筋挿入工）＋ かご工（ふとんかご護岸） 詳細度別サンプル
   延長 60m の切土法面 (1:1.0, H=12m, 小段 1.5m@6m) に吹付法枠 300×300 @2.0m、主アンカー・鉄筋挿入工、水平排水孔。
   法尻の渓流護岸にふとんかご 3段 (2.0×1.0×0.5m)。
   参考: 吹付法枠工・鉄筋挿入工詳細図 (b300×h300 @2.0m, D19 L=4.0m, 植生基材吹付 t=5cm) の一般的な寸法。実案件の法面展開・地形は使用していない。
"""
import sys, os, math
import numpy as np
from lodkit import *

A = Alignment([("S", 60.0)])      # 法尻に沿う軸 (x)。法面は +y 側に上がる
L = 60.0; SLOPE = 1.0; H1 = 6.0; BERM = 1.5; H2 = 6.0
Z_TOE = 0.0; Y_TOE = 3.0          # 法尻位置 (y=3), 渓流は y<3
FRAME = 0.3; PITCH = 2.0
rng = np.random.default_rng(13)

def slope_profile():
    """法面断面 (y, z): 法尻 → 法面1 → 小段 → 法面2 → 天端"""
    return np.array([[Y_TOE, Z_TOE], [Y_TOE + SLOPE * H1, Z_TOE + H1], [Y_TOE + SLOPE * H1 + BERM, Z_TOE + H1], [Y_TOE + SLOPE * H1 + BERM + SLOPE * H2, Z_TOE + H1 + H2], [Y_TOE + SLOPE * H1 + BERM + SLOPE * H2 + 6.0, Z_TOE + H1 + H2 + 1.0]])

def ground(x, y):   # 参考地形: 渓流 (y<3) と法面上の自然斜面
    p = slope_profile()
    if y >= Y_TOE: return float(np.interp(y, p[:, 0], p[:, 1])) + 0.1 * math.sin(x / 5.0)
    return Z_TOE - 1.5 * max(0.0, (Y_TOE - y)) / 3.0 * (1 if y > -2 else 0) - 2.5 * (1 if y <= -2 else 0) + 0.1 * math.sin(x / 4.0)

def face_frame(y0, z0, y1, z1):
    """法面 (2D 断面上の線分) の面内座標系: 法面に沿う上向き単位ベクトル d と外向き法線 n (y,z)"""
    d = np.array([y1 - y0, z1 - z0]); d /= np.linalg.norm(d); n = np.array([-d[1], d[0]])
    return d, n

def build_parts():
    parts = []
    C = dict(terrain=(0.62, 0.70, 0.50), slope=(0.72, 0.62, 0.46), berm=(0.80, 0.72, 0.55), frame=(0.80, 0.80, 0.78), anchor=(0.30, 0.30, 0.35),
             nail=(0.95, 0.55, 0.10), veg=(0.35, 0.62, 0.30), mesh=(0.55, 0.55, 0.58), drain=(0.25, 0.45, 0.80), sym=(0.2, 0.6, 0.9, 0.35),
             box100=(0.3, 0.55, 0.95, 0.35), gabion=(0.60, 0.58, 0.52), wire=(0.45, 0.45, 0.48), stone=(0.55, 0.52, 0.48), mat=(0.20, 0.20, 0.25),
             water=(0.35, 0.55, 0.80, 0.6), gravel=(0.66, 0.64, 0.58))
    sts = stations(0, L, 2.0)
    xs = np.arange(-15, 75, 2.0); ys = np.arange(-15, 35, 1.5)
    parts.append(Part("現況地形 (参考)", "地形", surface_mesh(xs, ys, ground), C["terrain"], 100, "地形は詳細度の対象外"))
    parts.append(Part("水面 (参考)", "地形", box_world(-15, 75, -12, 0.5, -2.0, -1.9), C["water"], 100, "渓流の水面 (参考)"))
    p = slope_profile()
    faces = [(p[0], p[1], "法面1 (H=6m)"), (p[2], p[3], "法面2 (H=6m)")]

    # ---------- LOD100 ----------
    parts.append(Part("法面保護工 範囲 (法肩線・法尻線)", "線形", Mesh().add(tube_along(np.array([[0, Y_TOE, Z_TOE + 0.2], [L, Y_TOE, Z_TOE + 0.2]]), 0.12, 6)).add(tube_along(np.array([[0, p[3][0], p[3][1] + 0.2], [L, p[3][0], p[3][1] + 0.2]]), 0.12, 6)), (0.9, 0.1, 0.1), 100, "対策範囲を線で示す"))
    parts.append(Part("法面保護工 範囲ボックス", "概略形状", box_world(-0.5, L + 0.5, Y_TOE - 0.5, p[3][0] + 0.5, Z_TOE - 0.5, p[3][1] + 0.5), C["box100"], 100, "対策範囲の直方体", lod_max=100))
    parts.append(Part("かご工 範囲ボックス", "概略形状", box_world(-0.5, L + 0.5, Y_TOE - 1.5, Y_TOE + 0.2, Z_TOE - 0.6, Z_TOE + 1.6), (0.95, 0.6, 0.2, 0.35), 100, "護岸の範囲", lod_max=100))

    # ---------- LOD200: 標準断面のスイープ ----------
    parts.append(Part("法面 (標準断面 1:1.0 スイープ)", "法面", sweep(A, lambda s: np.array([[Y_TOE, Z_TOE], [p[3][0], p[3][1]], [p[3][0], Z_TOE - 1.0], [Y_TOE, Z_TOE - 1.0]])[::-1], sts), C["slope"], 200, "小段なしの標準断面をスイープ", lod_max=200))
    parts.append(Part("かご工 (3段を一体化した台形ブロック)", "かご工", sweep(A, lambda s: np.array([[Y_TOE - 2.0, Z_TOE - 0.5], [Y_TOE, Z_TOE - 0.5], [Y_TOE, Z_TOE + 1.5], [Y_TOE - 1.0, Z_TOE + 1.5]])[::-1], sts), C["gabion"], 200, "ふとんかご護岸の概形", lod_max=200))

    # ---------- LOD300: 形状 (小段含む), 範囲記号 ----------
    for (a, b, nm) in faces:
        g = np.array([[[x, a[0], a[1]], [x, b[0], b[1]]] for x in (0.0, L)])
        m = grid_mesh(g, False, False); m.F = np.vstack([m.F, m.F[:, ::-1]])
        parts.append(Part(f"切土法面 {nm} 1:1.0", "法面", m, C["slope"], 300, "小段を含む法面形状"))
    parts.append(Part("小段 (幅1.5m)", "法面", box_world(0, L, p[1][0], p[2][0], p[1][1] - 0.05, p[1][1]), C["berm"], 300, "小段"))
    for (a, b, nm) in faces:
        d, n = face_frame(a[0], a[1], b[0], b[1])
        base = np.array([0, a[0] + 0.4 * n[0], a[1] + 0.4 * n[1]]); u = np.array([1.0, 0, 0]); v = np.array([0, d[0], d[1]])
        Lf = math.hypot(b[0] - a[0], b[1] - a[1])
        parts.append(Part(f"吹付法枠工 範囲記号 ({nm})", "記号", extrude_world(np.array([[0, 0], [L, 0], [L, Lf], [0, Lf]]), np.array([0, n[0], n[1]]), base, 0.05, u, v), C["sym"], 300, "法枠工の範囲をパターン (半透明面) で表示。詳細度400で実形状", lod_max=300))
    m = Mesh()
    for k, z in enumerate((2.0, 4.0, 8.0, 10.0)):
        y = float(np.interp(z, p[:, 1], p[:, 0]))
        for x in np.arange(1.5 if k % 2 else 3.0, L, 3.0): m.add(box_world(x - 0.15, x + 0.15, y - 0.5, y + 0.2, z - 0.15, z + 0.15))
    parts.append(Part("水平排水孔 位置記号 (φ50 @3m 千鳥)", "記号", m, C["sym"], 300, "排水孔の配置記号", lod_max=300))
    for k in range(3):
        parts.append(Part(f"ふとんかご {k+1}段目 (2.0×1.0×0.5m を一体化)", "かご工", box_world(0, L, Y_TOE - 2.0 + 0.5 * k, Y_TOE - 0.0 + 0.5 * k - 0.0, Z_TOE - 0.5 + 0.5 * k, Z_TOE + 0.5 * k), C["gabion"], 300, "各段のかごを一体化した外形 (段ごとに 0.5m セットバック)"))
    parts.append(Part("かご基礎 砕石 t=20cm", "かご工", box_world(-0.3, L + 0.3, Y_TOE - 2.3, Y_TOE + 0.3, Z_TOE - 0.7, Z_TOE - 0.5), C["gravel"], 300, "基礎"))

    # ---------- LOD400: 法枠実形状・アンカー・鉄筋挿入・排水孔・ラス網・植生基材・かご各個・金網・中詰石 ----------
    for (a, b, nm) in faces:
        d, n = face_frame(a[0], a[1], b[0], b[1]); Lf = math.hypot(b[0] - a[0], b[1] - a[1])
        u = np.array([1.0, 0, 0]); v = np.array([0, d[0], d[1]]); nw = np.array([0, n[0], n[1]])
        base = np.array([0, a[0], a[1]])
        m = Mesh(); cnt = 0
        for t in np.arange(0.0, Lf + 0.01, PITCH):   # 横枠 (法面に沿って水平)
            c = base + v * min(t, Lf - FRAME / 2) + nw * (FRAME / 2) + u * (L / 2)
            m.add(box_at(c, (L, FRAME, FRAME), u, v, nw)); cnt += 1
        for x in np.arange(0.0, L + 0.01, PITCH):    # 縦枠
            c = base + u * x + v * (Lf / 2) + nw * (FRAME / 2)
            m.add(box_at(c, (FRAME, Lf, FRAME), u, v, nw)); cnt += 1
        parts.append(Part(f"吹付法枠工 b300×h300 @2.0m ({nm}, 枠{cnt}本)", "法枠工", m, C["frame"], 400, "法枠の実形状 (格子)"))
        ma = Mesh(); mn = Mesh(); na = nn = 0
        for x in np.arange(0.0, L + 0.01, PITCH):
            for t in np.arange(0.0, Lf + 0.01, PITCH):
                c = base + u * x + v * min(t, Lf - 0.1) + nw * 0.15
                ma.add(cylinder(c - nw * 0.8, c + nw * 0.2, 0.012, 5)); na += 1
                if (int(x / PITCH) + int(t / PITCH)) % 2 == 0:
                    mn.add(cylinder(c - nw * 4.0, c + nw * 0.25, 0.02, 6)); mn.add(box_at(c + nw * 0.2, (0.15, 0.15, 0.016), u, v, nw)); nn += 1
        parts.append(Part(f"主アンカー D19 L=0.8m ({nm}, {na}本)", "法枠工", ma, C["anchor"], 400, "枠交点の主アンカー"))
        parts.append(Part(f"鉄筋挿入工 D19 L=4.0m ({nm}, {nn}本, 溝付角座金付き)", "鉄筋挿入工", mn, C["nail"], 400, "法面に直角に挿入する補強材"))
        parts.append(Part(f"ラス網 ({nm})", "法枠工", extrude_world(np.array([[0, 0], [L, 0], [L, Lf], [0, Lf]]), nw, base + nw * 0.03, 0.01, u, v), C["mesh"], 400, "吹付の下地金網"))
        mv = Mesh()
        for x in np.arange(0.0, L, PITCH):
            for t in np.arange(0.0, Lf, PITCH):
                w = min(PITCH, Lf - t) - FRAME
                if w <= 0.1: continue
                c = base + u * (x + PITCH / 2) + v * (t + FRAME / 2 + w / 2) + nw * 0.03
                mv.add(box_at(c, (PITCH - FRAME, w, 0.05), u, v, nw))
        parts.append(Part(f"植生基材吹付 t=5cm 枠内 ({nm})", "法面工", mv, C["veg"], 400, "枠内の植生基材吹付"))
    m = Mesh(); n = 0
    for k, z in enumerate((2.0, 4.0, 8.0, 10.0)):
        y = float(np.interp(z, p[:, 1], p[:, 0]))
        for x in np.arange(1.5 if k % 2 else 3.0, L, 3.0):
            m.add(cylinder([x, y + 0.2, z], [x, y + 0.2 + 5.0 * 0.996, z + 5.0 * 0.087], 0.025, 6)); n += 1
    parts.append(Part(f"水平排水孔 φ50 L=5m 上向き5° ({n}本)", "排水工", m, C["drain"], 400, "地山内の排水孔 (有孔管)"))
    # かご工 (各個: 2.0×1.0×0.5, 3段, 段ごとに 0.5m セットバック)
    mg = Mesh(); mw = Mesh(); ms = Mesh(); ng = 0
    for k in range(3):
        y0 = Y_TOE - 2.0 + 0.5 * k; z0 = Z_TOE - 0.5 + 0.5 * k
        for x in np.arange(0.0, L, 2.0):
            mg.add(box_world(x + 0.02, x + 1.98, y0 + 0.02, y0 + 0.98, z0 + 0.02, z0 + 0.48)); ng += 1
            for e in (x + 0.02, x + 1.98):   # かご枠 (稜線の針金を角材で表現)
                mw.add(box_world(e - 0.01, e + 0.01, y0, y0 + 1.0, z0 - 0.01, z0 + 0.01)); mw.add(box_world(e - 0.01, e + 0.01, y0, y0 + 1.0, z0 + 0.49, z0 + 0.51))
                mw.add(box_world(e - 0.01, e + 0.01, y0 - 0.01, y0 + 0.01, z0, z0 + 0.5)); mw.add(box_world(e - 0.01, e + 0.01, y0 + 0.99, y0 + 1.01, z0, z0 + 0.5))
            for yy in (y0, y0 + 1.0):
                mw.add(box_world(x, x + 2.0, yy - 0.01, yy + 0.01, z0 - 0.01, z0 + 0.01)); mw.add(box_world(x, x + 2.0, yy - 0.01, yy + 0.01, z0 + 0.49, z0 + 0.51))
            for yy in np.arange(y0 + 0.25, y0 + 1.0, 0.25):   # 金網 (前面・上面のメッシュ線を代表)
                mw.add(box_world(x, x + 2.0, yy - 0.005, yy + 0.005, z0 + 0.5, z0 + 0.51))
            for i in range(6):   # 中詰石 (代表)
                cx, cy, cz = x + rng.uniform(0.2, 1.8), y0 + rng.uniform(0.2, 0.8), z0 + rng.uniform(0.15, 0.4)
                ms.add(sphere([cx, cy, cz], rng.uniform(0.09, 0.14), 6))
    parts.append(Part(f"ふとんかご 各個 2.0×1.0×0.5m ({ng}個)", "かご工", mg, C["gabion"], 400, "かご単位の実形状"))
    parts.append(Part("かご枠・金網 (φ4mm 亜鉛めっき, 代表表現)", "かご工", mw, C["wire"], 400, "かご枠と金網"))
    parts.append(Part("中詰石 (代表)", "かご工", ms, C["stone"], 400, "中詰め玉石 (代表的に表示)"))
    parts.append(Part("吸出し防止材 (かご背面)", "かご工", box_world(0, L, Y_TOE - 0.02, Y_TOE + 0.01, Z_TOE - 0.5, Z_TOE + 1.5), C["mat"], 400, "背面の吸出し防止マット"))

    # ---------- LOD500 ----------
    for (a, b, nm) in faces:
        d, n = face_frame(a[0], a[1], b[0], b[1]); Lf = math.hypot(b[0] - a[0], b[1] - a[1])
        u = np.array([1.0, 0, 0]); v = np.array([0, d[0], d[1]]); nw = np.array([0, n[0], n[1]])
        base = np.array([0, a[0], a[1]])
        grid = []
        for x in np.arange(0.0, L + 0.01, 1.0):
            grid.append([base + u * x + v * t + nw * (0.1 + rng.uniform(-0.04, 0.04)) for t in np.arange(0.0, Lf + 0.01, 1.0)])
        m = grid_mesh(np.array(grid), False, False); m.F = np.vstack([m.F, m.F[:, ::-1]])
        parts.append(Part(f"吹付面 出来形 (実測凹凸, {nm})", "出来形", m, (0.55, 0.5, 0.4, 0.5), 500, "出来形計測の反映 (サンプルでは凹凸面)"))
    parts.append(Part("かご工 出来形 天端線 (実測, 記号)", "出来形", box_world(0, L, Y_TOE - 1.0, Y_TOE - 0.9, Z_TOE + 1.5, Z_TOE + 1.52), (0.55, 0.5, 0.4, 0.7), 500, "出来形計測の反映 (記号)"))
    return parts

def meta():
    return dict(
        id="slope", name="法枠工・鉄筋挿入工・かご工", category="法面工・護岸",
        description="延長60mの切土法面 (1:1.0, H=12m, 小段1.5m) に吹付法枠 300×300 @2.0m、主アンカー D19、鉄筋挿入工 D19 L=4m、ラス網、植生基材吹付、水平排水孔。法尻の渓流護岸にふとんかご 3段 (2.0×1.0×0.5m)、基礎砕石、吸出し防止材。",
        ref="吹付法枠工・鉄筋挿入工詳細図の一般的な寸法 (b300×h300 @2.0m, D19 L=4.0m, 植生基材 t=5cm) を参考にした架空法面。実案件の法面展開・地形は使用していない。",
        alignment=A, center=[30.0, 8.0, 5.0], ground={"cx": 30, "cy": 8, "z": -3.0, "size": 300},
        views=[{"name": "全景", "pos": [-25, -40, 25], "target": [30, 8, 5]}, {"name": "法枠", "pos": [20, -12, 8], "target": [30, 8, 6]},
               {"name": "かご工", "pos": [10, -8, 2], "target": [20, 2, 0.5]}, {"name": "断面", "pos": None, "target": None, "clip": 30}],
        lod_def={100: ["対策範囲を線と直方体で示す。"],
                 200: ["法面 (小段なしの標準断面) とかご工 (3段一体の台形) をスイープした概形。"],
                 300: ["小段を含む法面形状、かご工の各段の外形、基礎が正確。法枠工・排水孔は範囲・配置を記号 (パターン) で示す。"],
                 400: ["詳細度300に加えて法枠の格子、主アンカー、鉄筋挿入工、ラス網、植生基材吹付、水平排水孔、かご各個・金網・中詰石・吸出し防止材を実形状でモデル化。"],
                 500: ["完成形状 (吹付面の出来形凹凸、かご天端の実測線)。"]},
        notes=["中詰石・金網は代表的な表現 (全数ではない)。", "地形・水面は参考表示。"],
    )

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "site")
    export_model(build_parts(), os.path.abspath(out), meta())
