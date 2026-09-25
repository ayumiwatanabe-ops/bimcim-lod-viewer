# -*- coding: utf-8 -*-
"""山岳トンネル (NATM 2車線) 詳細度別サンプル — lodkit 版"""
import sys, os, math
import numpy as np
from lodkit import *

P = dict(
    L=240.0,            # トンネル延長 [m]
    grade=0.01,         # 縦断勾配 (+1.0%)
    curve_R=500.0,      # 平面曲線半径 [m] (中間区間)
    straight1=60.0,     # 起点側直線長
    curve_len=120.0,    # 曲線長
    # 内空 (覆工内面) : 3心円 (上半 R1 / 側壁 R2) + インバート R3
    R1=5.15, zc=1.25,   # 上半半径, 中心高 (路面FH基準)
    R2=8.0,             # 側壁半径
    theta1=20.0,        # 上半/側壁の接点角度 [deg] (水平から)
    z_foot=-1.20,       # 側壁下端 (底盤) 高さ
    R3=11.0,            # インバート内面半径
    t_lining=0.30,      # 覆工厚
    t_invert=0.50,      # インバート厚
    # 内空設備
    walk_w=0.75, walk_h=0.50,      # 監視員通路 (左側)
    gutter_w=0.40, gutter_h=0.35,  # 側溝 (右側)
    pav=[("表層", 0.04), ("基層", 0.06), ("上層路盤", 0.15), ("下層路盤", 0.25)],
    drain_r=0.15,       # 中央排水管 φ300
    # 非常駐車帯 (拡幅部)
    widen_s0=100.0, widen_s1=140.0, widen_taper=10.0, widen_w=2.5,
    # 箱抜き
    recess_st=[45.0, 95.0, 145.0, 195.0], recess=(0.6, 0.6, 0.4),
    # 坑門工
    portal_len=1.0, portal_margin=2.5, portal_top=1.5, wing_len=4.0, wing_h=3.0,
)

# 線形: 直線60 + R=500 曲線120 + 直線60, 縦断 +1.0%
A = Alignment([("S", 60.0), ("C", 500.0, 120.0), ("S", 60.0)], grade=0.01)
frame = A.frame; to_world = A.to_world
def sweepA(section_fn, sts, close_ring=True, caps=True): return sweep(A, section_fn, sts, close_ring, caps)
def boxA(s0, s1, y0, y1, z0, z1, n_along=None): return box_local(A, s0, s1, y0, y1, z0, z1, n_along)
def extrudeA(poly2d, s, thickness, along=+1): return extrude(A, poly2d, s, thickness, along)

# 支保パターン区間 (起点側から)
PATTERNS = [
    # name,  s0,   s1,   吹付厚, 鋼支保工(サイズ,ピッチ) or None, ロックボルト(L, 縦ピッチ, 周ピッチ), インバート
    ("DⅢa", 0.0,   30.0,  0.20, ("H-150", 1.0), (4.0, 1.0, 1.2), True),
    ("DⅡ",  30.0,  90.0,  0.15, ("H-125", 1.2), (3.0, 1.2, 1.5), False),
    ("DⅠ",  90.0,  150.0, 0.10, None,           (3.0, 1.5, 1.5), False),
    ("DⅡ",  150.0, 210.0, 0.15, ("H-125", 1.2), (3.0, 1.2, 1.5), False),
    ("DⅢa", 210.0, 240.0, 0.20, ("H-150", 1.0), (4.0, 1.0, 1.2), True),
]
PATTERN_COLOR = {"DⅠ": (0.55, 0.80, 0.55), "DⅡ": (0.95, 0.85, 0.45), "DⅢa": (0.95, 0.55, 0.45)}
FOREPOLE_RANGES = [(0.0, 12.0), (228.0, 240.0)]   # 補助工法 (フォアポーリング) 範囲
REBAR_RANGES = [(0.0, 30.0), (210.0, 240.0)]      # 覆工鉄筋 (坑口部)

# 色 (r,g,b[,a])
C = dict(
    lining=(0.82, 0.82, 0.80), shotcrete=(0.55, 0.55, 0.53), invert=(0.65, 0.65, 0.62),
    pave=(0.25, 0.25, 0.27), base=(0.45, 0.42, 0.38), subbase=(0.60, 0.55, 0.45),
    walk=(0.75, 0.75, 0.72), gutter=(0.60, 0.62, 0.65), drain=(0.20, 0.45, 0.80),
    portal=(0.78, 0.78, 0.74), steel=(0.20, 0.35, 0.75), bolt=(0.95, 0.55, 0.10),
    rebar=(0.70, 0.20, 0.15), sheet=(0.95, 0.90, 0.30), panel=(0.90, 0.92, 0.95),
    forepole=(0.60, 0.25, 0.75), light=(1.0, 0.95, 0.6), fan=(0.85, 0.85, 0.9),
    box100=(0.30, 0.55, 0.95, 0.35), marker=(0.95, 0.20, 0.20, 0.6), center=(0.9, 0.1, 0.1),
    sym=(0.2, 0.6, 0.9, 0.35), sym_fore=(0.6, 0.25, 0.75, 0.35), sym_recess=(0.95, 0.5, 0.1, 0.5),
)

# ------------------------------------------------------------------
# 線形 (平面: 直線-円曲線-直線, 縦断: 一定勾配)
# ------------------------------------------------------------------
def frame(s):
    """測点 s -> (P, T, R, U)  P:中心線位置 T:接線 R:右方向 U:上方向"""
    s1, lc, R = P["straight1"], P["curve_len"], P["curve_R"]
    if s <= s1:
        x, y, phi = s, 0.0, 0.0
    elif s <= s1 + lc:
        d = s - s1
        phi = d / R
        x = s1 + R * math.sin(phi)
        y = R * (1 - math.cos(phi))
    else:
        phi = lc / R
        d = s - s1 - lc
        x = s1 + R * math.sin(phi) + d * math.cos(phi)
        y = R * (1 - math.cos(phi)) + d * math.sin(phi)
    z = P["grade"] * s
    T = np.array([math.cos(phi), math.sin(phi), P["grade"]]); T /= np.linalg.norm(T)
    Rv = np.array([math.sin(phi), -math.cos(phi), 0.0])
    U = np.array([0.0, 0.0, 1.0])
    return np.array([x, y, z]), T, Rv, U

def to_world(s, pts2d):
    """局所断面座標 (y:右+, z:上+) -> ワールド"""
    Pc, T, Rv, U = frame(s)
    pts2d = np.asarray(pts2d, float)
    return Pc[None, :] + pts2d[:, 0:1] * Rv[None, :] + pts2d[:, 1:2] * U[None, :]

# ------------------------------------------------------------------
# 断面形状
# ------------------------------------------------------------------
def widen_at(s):
    s0, s1, tp, w = P["widen_s0"], P["widen_s1"], P["widen_taper"], P["widen_w"]
    if s <= s0 or s >= s1: return 0.0
    if s < s0 + tp: return w * (s - s0) / tp
    if s > s1 - tp: return w * (s1 - s) / tp
    return w

def arch_curve(offset=0.0, n_top=40, n_side=12, widen=0.0):
    """覆工内面から offset だけ外側にオフセットしたアーチ曲線 (左脚 -> 天端 -> 右脚)。
    戻り値 (N,2) 配列 [y,z] と 各点の外向き法線 (N,2)"""
    R1, zc, R2, th1, zf = P["R1"] + offset, P["zc"], P["R2"] + offset, math.radians(P["theta1"]), P["z_foot"]
    c1 = np.array([0.0, zc])
    # 接点 (左: 180-th1, 右: th1)
    aL, aR = math.pi - th1, th1
    uL = np.array([math.cos(aL), math.sin(aL)]); uR = np.array([math.cos(aR), math.sin(aR)])
    c2L = c1 + (P["R1"] - P["R2"]) * uL
    c2R = c1 + (P["R1"] - P["R2"]) * uR
    # 左側壁: 角度 aL -> 下端
    aLend = math.pi + math.asin(min(1.0, max(-1.0, (c2L[1] - zf) / R2)))
    aRend = -math.asin(min(1.0, max(-1.0, (c2R[1] - zf) / R2)))
    pts, nrm = [], []
    for t in np.linspace(aLend, aL, n_side, endpoint=False):
        u = np.array([math.cos(t), math.sin(t)]); pts.append(c2L + R2 * u); nrm.append(u)
    for t in np.linspace(aL, aR, n_top, endpoint=False):
        u = np.array([math.cos(t), math.sin(t)]); pts.append(c1 + R1 * u); nrm.append(u)
    for t in np.linspace(aR, aRend, n_side + 1):
        u = np.array([math.cos(t), math.sin(t)]); pts.append(c2R + R2 * u); nrm.append(u)
    pts = np.array(pts); nrm = np.array(nrm)
    if widen > 0:  # 左側を拡幅 (y<0 側を水平方向にスケール)
        w0 = -pts[:, 0].min()
        k = (w0 + widen) / w0
        m = pts[:, 0] < 0
        pts[m, 0] *= k
    return pts, nrm

def invert_curve(offset=0.0, n=20):
    """インバート曲線 (右脚下端 -> 左脚下端, 下向きに膨らむ)。offset は外側(下)方向"""
    zf, R3 = P["z_foot"], P["R3"] + offset
    inner, _ = arch_curve(0.0)
    yL, yR = inner[0, 0], inner[-1, 0]
    half = (yR - yL) / 2.0
    zc = zf + math.sqrt(P["R3"] ** 2 - half ** 2)  # インバート円の中心 (内面半径基準)
    ys = np.linspace(yR, yL, n)                     # 右脚 -> 左脚
    zs = zc - np.sqrt(np.maximum(R3 ** 2 - ys ** 2, 0.0))
    return np.column_stack([ys, zs])

def foot_level_y():
    inner, _ = arch_curve(0.0)
    return inner[0, 0], inner[-1, 0]

# ------------------------------------------------------------------
# 部材生成
# ------------------------------------------------------------------
H_PROFILE = {"H-125": (0.125, 0.125, 0.012), "H-150": (0.150, 0.150, 0.014)}   # 簡略 H形鋼 (高さ, フランジ幅, 板厚)

def pattern_at(s):
    for pt in PATTERNS:
        if pt[1] <= s < pt[2] or (s == P["L"] and pt[2] == P["L"]): return pt
    return PATTERNS[-1]

def shot_thk(s): return pattern_at(s)[3]

def build_parts(seed=1):
    rng = np.random.default_rng(seed)
    parts = []
    L = P["L"]
    tl = P["t_lining"]

    # ---------- 中心線形 (全LOD) ----------
    st = stations(0, L, 2.0)
    cl = np.array([frame(s)[0] for s in st])
    parts.append(Part("道路中心線形", "線形", tube_along(cl, 0.08, 6), C["center"], 100, "計画道路の中心線形 (細いチューブで表現)"))

    # ---------- LOD100: 位置を示す矩形ボックス ----------
    inner, _ = arch_curve(0.0)
    W = inner[:, 0].max() - inner[:, 0].min() + 2 * (tl + 0.2)
    parts.append(Part("トンネル位置ボックス", "概略形状", boxA(0, L, -W / 2 - 0.5, W / 2 + 0.5, P["z_foot"] - 1.0, inner[:, 1].max() + tl + 0.6),
                      C["box100"], 100, "トンネル配置が分かる程度の矩形形状 (半透明)", lod_max=100))
    for s, nm in ((0.0, "起点側坑口位置"), (L, "終点側坑口位置")):
        Pc, T, Rv, U = frame(s)
        parts.append(Part(nm, "坑口位置", cylinder(Pc + U * -2, Pc + U * 9, 0.35, 12), C["marker"], 100, "坑口の位置のみを示すマーカー (形状はモデル化しない)", lod_max=200))

    # ---------- LOD200: 標準横断面スイープ (単純断面, 拡幅・インバートなし) ----------
    t200 = tl + 0.15
    f200 = ring_section(lambda s: arch_curve(0.0)[0], lambda s: arch_curve(t200)[0])
    parts.append(Part("トンネル本体 (標準横断面スイープ)", "本体", sweepA(f200, stations(0, L, 2.0)), C["lining"], 200,
                      "標準横断面 (覆工+吹付を一体の単純断面) を中心線形に沿ってスイープ", lod_max=200))
    # LOD200 の路面 (参考: 標準横断に含まれる舗装面)
    yL, yR = foot_level_y()
    parts.append(Part("路面 (標準横断)", "本体", boxA(0, L, yL, yR, -0.5, 0.0), C["pave"], 200, "標準横断面に含まれる路面", lod_max=200))

    # ---------- LOD300+: 覆工 / 吹付け / インバート (支保パターン区間ごと) ----------
    for name, s0, s1, tsh, steel, bolt, inv in PATTERNS:
        st = stations(s0, s1, 1.0)
        fl = ring_section(lambda s: arch_curve(0.0, widen=widen_at(s))[0], lambda s: arch_curve(tl, widen=widen_at(s))[0])
        parts.append(Part(f"覆工コンクリート t={tl*100:.0f}cm [{name}区間 No.{s0:.0f}-{s1:.0f}]", "覆工", sweepA(fl, st), PATTERN_COLOR[name], 300,
                          f"支保パターン {name} 区間の覆工 (区間ごとに色分け=記号表示)"))
        fs = ring_section(lambda s: arch_curve(tl, widen=widen_at(s))[0], lambda s: arch_curve(tl + tsh, widen=widen_at(s))[0])
        parts.append(Part(f"吹付けコンクリート t={tsh*100:.0f}cm [{name}区間]", "吹付け", sweepA(fs, st), C["shotcrete"], 300,
                          "掘削外形 = 吹付け外面 (詳細度500では余掘りを反映)"))
        if inv:
            fi = ring_section(lambda s: invert_curve(0.0), lambda s: invert_curve(P["t_invert"]))
            parts.append(Part(f"インバート t={P['t_invert']*100:.0f}cm [{name}区間]", "インバート", sweepA(fi, st), C["invert"], 300, "DⅢ区間のインバートコンクリート"))
    # 支保パターン範囲記号 (LOD300のみ: 掘削外側 0.6m に半透明の帯)
    for name, s0, s1, tsh, steel, bolt, inv in PATTERNS:
        fsym = ring_section(lambda s: arch_curve(tl + tsh + 0.6)[0], lambda s: arch_curve(tl + tsh + 0.75)[0])
        col = PATTERN_COLOR[name] + (0.35,)
        parts.append(Part(f"支保パターン範囲記号 {name} (No.{s0:.0f}-{s1:.0f})", "記号", sweepA(fsym, stations(s0 + 0.5, s1 - 0.5, 2.0)), col, 300,
                          "適用支保パターンの範囲を記号(半透明帯)で表示。詳細度400では実形状の支保工に置き換わる", lod_max=300))
    # 補助工法範囲記号 (LOD300のみ)
    for s0, s1 in FOREPOLE_RANGES:
        def fsym2(s):
            a, _ = arch_curve(tl + shot_thk(s) + 1.0, n_top=30, n_side=2); b, _ = arch_curve(tl + shot_thk(s) + 1.2, n_top=30, n_side=2)
            a, b = a[2:-3], b[2:-3]
            return np.vstack([a, b[::-1]])
        parts.append(Part(f"補助工法範囲記号 フォアポーリング (No.{s0:.0f}-{s1:.0f})", "記号", sweepA(fsym2, stations(s0, s1, 2.0)), C["sym_fore"], 300,
                          "補助工法の適用範囲を記号(半透明)で表示", lod_max=300))
    # 箱抜き位置記号 (LOD300) / 箱抜き形状 (LOD400+)
    rw, rh, rd = P["recess"]
    for sr in P["recess_st"]:
        arch, nrm = arch_curve(0.0)
        # 右側壁 z=1.5 付近の点
        k = np.argmin(np.abs(arch[:, 1] - 1.5) + (arch[:, 0] < 0) * 100)
        y0, z0 = arch[k]
        parts.append(Part(f"箱抜き位置記号 (No.{sr:.0f})", "記号", boxA(sr - rw, sr + rw, y0 - 0.9, y0 + 0.3, z0 - rh, z0 + rh), C["sym_recess"], 300,
                          "箱抜き位置をパターン化した記号(半透明ボックス)で表示", lod_max=300))
        parts.append(Part(f"箱抜き {rw*100:.0f}x{rh*100:.0f}x{rd*100:.0f} (No.{sr:.0f})", "箱抜き", boxA(sr - rw / 2, sr + rw / 2, y0 - 0.02, y0 + rd, z0 - rh / 2, z0 + rh / 2),
                          (0.35, 0.35, 0.38), 400, "箱抜き形状 (覆工内の凹み) を正確にモデル化"))

    # ---------- LOD300+: 坑門工 (面壁 + ウイング) ----------
    for s_end, along in ((0.0, -1), (L, +1)):
        outer, _ = arch_curve(0.05)
        yl, yr = outer[0, 0] - P["portal_margin"], outer[-1, 0] + P["portal_margin"]
        top = outer[:, 1].max() + P["portal_top"]
        zb = P["z_foot"] - 0.5
        poly = np.vstack([[[outer[0, 0], zb]], [[yl, zb]], [[yl, top]], [[yr, top]], [[yr, zb]], [[outer[-1, 0], zb]], outer[::-1]])
        m = extrudeA(poly, s_end, P["portal_len"], along)
        nm = "起点側" if s_end == 0 else "終点側"
        parts.append(Part(f"坑門工 面壁 ({nm})", "坑門工", m, C["portal"], 300, "坑口部の外形寸法を正確にモデル化 (面壁式坑門)"))
        for side, y in (("左", yl), ("右", yr)):
            wing = np.array([[y - 0.6 if side == "左" else y, zb], [y if side == "左" else y + 0.6, zb], [y if side == "左" else y + 0.6, zb + P["wing_h"] + 3.0], [y - 0.6 if side == "左" else y, zb + P["wing_h"]]])
            parts.append(Part(f"坑門工 ウイング ({nm}{side})", "坑門工", extrudeA(wing, s_end + (P["wing_len"] if along < 0 else 0) * 0 + (0 if along < 0 else 0), P["wing_len"], along), C["portal"], 300, "ウイング (簡略)"))

    # ---------- LOD300+: 内空設備 (舗装, 監視員通路, 側溝, 排水) ----------
    z = 0.0
    y_pl, y_pr = yL + P["walk_w"], yR - P["gutter_w"]
    for nm, t in P["pav"]:
        col = {"表層": C["pave"], "基層": (0.35, 0.33, 0.33), "上層路盤": C["base"], "下層路盤": C["subbase"]}[nm]
        parts.append(Part(f"舗装 {nm} t={t*100:.0f}cm", "舗装", boxA(0, L, y_pl, y_pr, z - t, z), col, 300, "舗装構成をモデル化"))
        z -= t
    parts.append(Part("監視員通路 (左)", "内空設備", boxA(0, L, yL, y_pl, -0.5, P["walk_h"]), C["walk"], 300, ""))
    parts.append(Part("側溝 (右)", "内空設備", boxA(0, L, y_pr, yR, -0.5, 0.0), C["gutter"], 300, "側溝 (簡略ボックス)"))
    parts.append(Part("中央排水管 φ300", "排水工", tube_along(np.array([to_world(s, [[0.0, -0.85]])[0] for s in stations(0, L, 2.0)]), P["drain_r"], 10), C["drain"], 300, "中央排水工"))
    parts.append(Part("埋戻し (底盤)", "内空設備", boxA(0, L, yL, yR, P["z_foot"], -0.5), (0.7, 0.62, 0.5), 300, "底盤〜路盤下の埋戻し"))

    # ---------- LOD400+: 鋼製支保工 / ロックボルト / 防水シート / 内装板 / 覆工鉄筋 / フォアポーリング ----------
    for name, s0, s1, tsh, steel, bolt, inv in PATTERNS:
        if steel:
            h, w, t = H_PROFILE[steel[0]]
            prof = h_shape(h, w, t)
            m = Mesh(); s = s0 + steel[1] / 2
            cnt = 0
            while s < s1:
                pts, nrm = arch_curve(tl + tsh - h / 2 - 0.01, n_top=30, n_side=8, widen=widen_at(s))
                m.add(profile_sweep(A, s, pts, nrm, prof)); cnt += 1; s += steel[1]
            parts.append(Part(f"鋼製支保工 {steel[0]} @{steel[1]:.1f}m [{name}区間] ({cnt}基)", "鋼製支保工", m, C["steel"], 400, "鋼アーチ支保工を1基ずつモデル化"))
        Lb, ds, dc = bolt
        m = Mesh(); s = s0 + ds / 2; cnt = 0
        while s < s1:
            pts, nrm = arch_curve(tl + tsh, n_top=60, n_side=20, widen=widen_at(s))
            # 弧長で等間隔に配置 (脚部 +1.0m 以上)
            seg = np.linalg.norm(np.diff(pts, axis=0), axis=1); cum = np.concatenate([[0], np.cumsum(seg)])
            valid = pts[:, 1] > P["z_foot"] + 1.0
            arc = cum[valid][-1] - cum[valid][0]; nb = int(arc / dc) + 1
            targets = np.linspace(cum[valid][0] + 0.3, cum[valid][-1] - 0.3, nb)
            for tgt in targets:
                k = np.argmin(np.abs(cum - tgt)); p0 = to_world(s, [pts[k]])[0]; p1 = to_world(s, [pts[k] + nrm[k] * Lb])[0]
                m.add(cylinder(p0, p1, 0.04, 6)); cnt += 1
            s += ds
        parts.append(Part(f"ロックボルト L={Lb:.1f}m @{ds:.1f}x{dc:.1f} [{name}区間] ({cnt}本)", "ロックボルト", m, C["bolt"], 400, "ロックボルト全数をモデル化"))
    # 防水シート (覆工と吹付の間, 厚さ 2cm で表現)
    fsheet = ring_section(lambda s: arch_curve(tl - 0.01, widen=widen_at(s))[0], lambda s: arch_curve(tl + 0.01, widen=widen_at(s))[0])
    parts.append(Part("防水シート", "防水工", sweepA(fsheet, stations(0, L, 2.0)), C["sheet"], 400, "覆工背面の防水シート (厚さは誇張表示)"))
    # 内装板 (側壁 高さ 3.5m まで, 厚さ 3cm)
    def fpanel(s):
        a, _ = arch_curve(-0.03, widen=widen_at(s)); b, _ = arch_curve(0.0, widen=widen_at(s))
        return a, b
    for side in ("左", "右"):
        def fp(s, side=side):
            a, b = fpanel(s)
            m = (a[:, 1] < 3.5) & ((a[:, 0] < 0) if side == "左" else (a[:, 0] > 0))
            return np.vstack([a[m], b[m][::-1]])
        parts.append(Part(f"内装板 ({side}側壁 H=3.5m)", "内装工", sweepA(fp, stations(P["portal_len"], L - P["portal_len"], 2.0)), C["panel"], 400, "内装板 (側壁部)"))
    # 覆工鉄筋 (坑口部): 主筋 D19@250 (アーチ方向) 2段 + 配力筋 D13@300 (線形方向)
    for s0, s1 in REBAR_RANGES:
        m = Mesh(); s = s0 + 0.125; nh = 0
        while s < s1:
            for off in (0.08, tl - 0.08):
                pts, nrm = arch_curve(off, n_top=24, n_side=6)
                m.add(tube_along(to_world(s, pts), 0.0095, 5)); nh += 1
            s += 0.25
        ml = Mesh(); nl = 0
        for off in (0.065, tl - 0.065):
            pts, nrm = arch_curve(off, n_top=60, n_side=16)
            seg = np.linalg.norm(np.diff(pts, axis=0), axis=1); cum = np.concatenate([[0], np.cumsum(seg)])
            for tgt in np.arange(0.15, cum[-1], 0.30):
                k = np.argmin(np.abs(cum - tgt))
                path = np.array([to_world(ss, [pts[k]])[0] for ss in stations(s0, s1, 3.0)])
                ml.add(tube_along(path, 0.0065, 4)); nl += 1
        parts.append(Part(f"覆工鉄筋 主筋 D19@250 (No.{s0:.0f}-{s1:.0f}, {nh}本)", "配筋", m, C["rebar"], 400, "坑口部覆工の配筋 (主筋)"))
        parts.append(Part(f"覆工鉄筋 配力筋 D13@300 (No.{s0:.0f}-{s1:.0f}, {nl}本)", "配筋", ml, (0.85, 0.35, 0.25), 400, "坑口部覆工の配筋 (配力筋)"))
    # フォアポーリング (φ50 L=3.0m @450mm, 打設角 10°, 1シフト 3m)
    for s0, s1 in FOREPOLE_RANGES:
        m = Mesh(); s = s0; cnt = 0
        while s < s1:
            pts, nrm = arch_curve(tl + shot_thk(s), n_top=60, n_side=4)
            top = pts[:, 1] > P["zc"] + 0.3 * P["R1"]
            seg = np.linalg.norm(np.diff(pts, axis=0), axis=1); cum = np.concatenate([[0], np.cumsum(seg)])
            c0, c1 = cum[top][0], cum[top][-1]
            for tgt in np.arange(c0, c1, 0.45):
                k = np.argmin(np.abs(cum - tgt))
                Pc, T, Rv, U = frame(s)
                p0 = to_world(s, [pts[k]])[0]
                nw = nrm[k][0] * Rv + nrm[k][1] * U
                d = math.cos(math.radians(10)) * T + math.sin(math.radians(10)) * nw
                m.add(cylinder(p0, p0 + 3.0 * d, 0.03, 5)); cnt += 1
            s += 3.0
        parts.append(Part(f"フォアポーリング φ50 L=3.0m @450 (No.{s0:.0f}-{s1:.0f}, {cnt}本)", "補助工法", m, C["forepole"], 400, "補助工法の形状を正確にモデル化"))

    # ---------- LOD500: 完成形状 (出来形反映 + 完成設備) ----------
    # 余掘りを反映した掘削出来形 (吹付け外面に凹凸)
    def fas(s):
        a, _ = arch_curve(tl + shot_thk(s), widen=widen_at(s)); b, n = arch_curve(tl + shot_thk(s) + 0.02, widen=widen_at(s))
        noise = rng.uniform(0.0, 0.25, size=len(b)) * (b[:, 1] > P["z_foot"] + 0.5)
        b = b + n * noise[:, None]
        return np.vstack([a, b[::-1]])
    parts.append(Part("掘削出来形 (余掘り反映)", "出来形", sweepA(fas, stations(0, L, 1.0)), (0.45, 0.40, 0.35), 500, "施工時の余掘り(実測)を反映した掘削面 = 完成形状"))
    # 照明 (両側 SL付近, 10m ピッチ)
    m = Mesh(); cnt = 0
    for s in np.arange(5.0, L, 10.0):
        for y in (-4.6, 4.6):
            Pc, T, Rv, U = frame(s)
            c = to_world(s, [[y, 4.6]])[0]
            m.add(cylinder(c - 0.6 * T, c + 0.6 * T, 0.12, 8)); cnt += 1
    parts.append(Part(f"照明器具 ({cnt}台)", "完成設備", m, C["light"], 500, "完成時の設備 (照明)"))
    m = Mesh()
    for s in (60.0, 180.0):
        Pc, T, Rv, U = frame(s)
        c = to_world(s, [[0.0, 5.2]])[0]
        m.add(cylinder(c - 1.6 * T, c + 1.6 * T, 0.55, 14))
    parts.append(Part("ジェットファン (2台)", "完成設備", m, C["fan"], 500, "完成時の設備 (換気)"))
    m = Mesh()
    for sr in P["recess_st"]:
        arch, nrm = arch_curve(0.0)
        k = np.argmin(np.abs(arch[:, 1] - 1.5) + (arch[:, 0] < 0) * 100); y0, z0 = arch[k]
        m.add(boxA(sr - 0.2, sr + 0.2, y0 - 0.05, y0 + 0.25, z0 - 0.2, z0 + 0.2))
    parts.append(Part("非常用設備 (箱抜き内 機器)", "完成設備", m, (0.85, 0.15, 0.15), 500, "完成時の設備 (非常電話等)"))
    return parts



def meta():
    return dict(
        id="tunnel", name="山岳トンネル（NATM 2車線）", category="トンネル",
        description="延長240m・2車線の汎用断面（3心円 R1=5.15m/R2=8.0m, 覆工30cm）。支保パターン DⅢa/DⅡ/DⅠ の配置例、非常駐車帯、坑門工、補助工法を含む。",
        ref="国交省 BIM/CIM活用ガイドライン(案) 共通編 表1-2 (山岳トンネルの例) の定義に対応。実案件の寸法・線形は使用していない。",
        alignment=A, center=[110.0, 15.0, 0.0], ground={"cx": 120, "cy": 30, "z": -2.3, "size": 700},
        views=[{"name": "全景", "pos": [-70, -120, 80], "target": [110, 15, 0]}, {"name": "坑口", "pos": [-30, -16, 10], "target": [10, 1, 3]},
               {"name": "内部", "pos": [62, 0.5, 2], "target": [67, 0.8, 2.2]}, {"name": "断面", "pos": None, "target": None, "clip": 120}],
        lod_def={100: ["対象構造物の位置を示すモデル。トンネルの配置が分かる程度の矩形形状若しくは線状のモデル。"],
                 200: ["構造形式が確認できる程度の形状。計画道路の中心線形とトンネル標準横断面でモデル化。坑口部はモデル化せず位置を示す。"],
                 300: ["主構造の形状が正確なモデル。避難通路などの拡幅部の形状をモデル化。適用支保パターンの範囲を記号等で、補助工法は対象工法をパターン化し記号等で必要範囲をモデル化。坑口部は外形寸法を正確にモデル化。舗装構成や排水工等の内空設備をモデル化。箱抜き位置は形状をパターン化し、記号等で設置範囲を示す。"],
                 400: ["詳細度300に加えてロックボルトや配筋を含む全てをモデル化。トンネル本体や坑口部、箱抜き部の配筋、内装板、支保パターン、補助工法の形状の正確なモデル。"],
                 500: ["設計・施工段階で活用したモデルに完成形状を反映したモデル。"]},
        notes=["工種別の定義文は国交省ガイドライン共通編 表1-2「山岳トンネルの例」の記載そのまま。",
               "支保パターン: DⅢa(坑口部30m)・DⅡ・DⅠ。ロックボルト L=3〜4m、鋼製支保工 H-125/H-150、覆工鉄筋は坑口部30m。"],
    )

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "site")
    export_model(build_parts(), os.path.abspath(out), meta())
