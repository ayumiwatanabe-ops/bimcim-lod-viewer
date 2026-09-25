# -*- coding: utf-8 -*-
"""道路土工（切土・盛土） 詳細度別サンプル
   2車線道路 (車道3.5×2 + 路肩1.25×2 = 9.5m) を架空地形に通し、起点側が切土・終点側が盛土になる区間 240m。
   参考: 道路土工要綱の一般値 (切土 1:1.0 / 盛土 1:1.5, 小段 1.5m @5m), 道路標準横断図 (舗装構成)。実案件の寸法は不使用。
"""
import sys, os, math
import numpy as np
from lodkit import *

A = Alignment([("S", 80.0), ("C", 400.0, 100.0), ("S", 60.0)], grade=0.005)
L = A.length
W_HALF = 4.75           # 路肩端まで
CROSS = 0.02            # 横断勾配
PAV = [("表層", 0.05), ("基層", 0.10), ("上層路盤", 0.20), ("下層路盤", 0.30)]   # 計 0.65 m
T_PAV = sum(t for _, t in PAV)
CUT_SLOPE, FILL_SLOPE = 1.0, 1.5    # 1:n
BERM_H, BERM_W = 5.0, 1.5
DITCH_W, DITCH_D = 0.4, 0.4
rng = np.random.default_rng(3)

# ---------------- 架空地形 (起点側が高く切土、終点側が低く盛土) ----------------
def ground(x, y):
    return 6.5 - 0.05 * x + 0.02 * y + 1.2 * math.sin(x / 45.0) * math.cos(y / 38.0) + 0.5 * math.sin((x + 2 * y) / 22.0) + 0.25 * math.sin(x / 9.0 + y / 13.0)

def ground_at(s, yoff):
    P, T, R, U = A.frame(s); w = P + yoff * R
    return ground(w[0], w[1])

def fh(s): return A.frame(s)[0][2]

# ---------------- 各測点の設計横断 ----------------
def daylight(s, side):
    """路肩端から法面 (小段付き) を地山に到達するまで伸ばす。戻り: [(y,z,kind)], cut(bool)"""
    y = side * W_HALF; z = fh(s) - CROSS * W_HALF
    gz = ground_at(s, y); cut = gz > z
    n = CUT_SLOPE if cut else FILL_SLOPE; dz = 1.0 if cut else -1.0
    pts = [(y, z, "edge")]
    if cut:  # 法尻側溝
        y += side * DITCH_W; pts.append((y, z, "ditch"))
    h = 0.0; dstep = 0.1
    for _ in range(600):
        # 法面 0.1m ずつ
        y2 = y + side * n * dstep; z2 = z + dz * dstep
        if (ground_at(s, y2) - z2) * dz <= 0:   # 地山に到達
            pts.append((y2, z2, "top")); return pts, cut
        y, z = y2, z2; h += dstep
        if abs(h - BERM_H) < 1e-6:
            pts.append((y, z, "berm"))
            for k in range(1, 16):
                yb = y + side * BERM_W * k / 15
                if (ground_at(s, yb) - z) * dz <= 0: pts.append((yb, z, "top")); return pts, cut
            y = y + side * BERM_W; pts.append((y, z, "slope")); h = 0.0
    pts.append((y, z, "top")); return pts, cut

def resample(pts, n):
    P = np.asarray([[p[0], p[1]] for p in pts], float)
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1); cum = np.concatenate([[0], np.cumsum(seg)])
    t = np.linspace(0, cum[-1], n)
    return np.column_stack([np.interp(t, cum, P[:, 0]), np.interp(t, cum, P[:, 1])])

def section(s):
    """設計横断: 左右法面 (24点にリサンプル), 地山線 (16点), 路面"""
    Lp, Lcut = daylight(s, -1); Rp, Rcut = daylight(s, +1)
    return dict(L=resample(Lp, 24), R=resample(Rp, 24), Lcut=Lcut, Rcut=Rcut, Lraw=Lp, Rraw=Rp)

def road_top(s):
    return np.array([[-W_HALF, fh(s) - CROSS * W_HALF], [0.0, fh(s)], [W_HALF, fh(s) - CROSS * W_HALF]])

# ---------------- 部材生成 ----------------
def build_parts():
    parts = []
    sts = stations(0, L, 2.0)
    C = dict(terrain=(0.62, 0.70, 0.50), cut=(0.72, 0.60, 0.44), fill=(0.60, 0.66, 0.42), berm=(0.80, 0.72, 0.55), road=(0.28, 0.28, 0.30),
             ditch=(0.62, 0.64, 0.66), body=(0.70, 0.62, 0.48), sym=(0.2, 0.6, 0.9, 0.35), guard=(0.85, 0.85, 0.88), veg=(0.35, 0.62, 0.30),
             frame=(0.78, 0.78, 0.76), pipe=(0.25, 0.45, 0.80), line=(0.95, 0.95, 0.9))
    secs = {float(s): section(s) for s in sts}

    # 現況地形 (詳細度の対象外: 参考表示)。土工範囲内は設計面へドレープ (3cm 下げ) して連続面にする
    xs = np.arange(-40, 300, 2.0); ys = np.arange(-80, 120, 2.0)
    samp = A.sample(2.0)["points"]
    pts = np.array([[p[0], p[1]] for p in samp]); tans = np.array([[p[3], p[4]] for p in samp])
    def draped(x, y):
        d = np.hypot(pts[:, 0] - x, pts[:, 1] - y); i = int(np.argmin(d)); s = min(L, i * 2.0)
        P = pts[i]; t = tans[i]; rel = np.array([x - P[0], y - P[1]])
        yoff = rel[0] * t[1] - rel[1] * t[0]   # 右+ (R = (ty, -tx))
        sec = secs[float(s)]
        side = sec["R"] if yoff >= 0 else sec["L"]
        ymax = abs(side[-1, 0])
        if abs(yoff) <= ymax:
            zz = np.interp(abs(yoff), np.abs(side[:, 0]), side[:, 1]) if abs(yoff) > W_HALF else fh(s) - CROSS * abs(yoff)
            return zz - 0.03
        return ground(x, y)
    parts.append(Part("現況地形 (参考・土工後の地表面)", "地形", surface_mesh(xs, ys, draped), C["terrain"], 100, "地形は詳細度の対象外。土工範囲は設計面に整形した状態で表示"))

    # ---------- LOD100: 位置 ----------
    cl = np.array([A.frame(s)[0] + np.array([0, 0, 0.3]) for s in sts])
    parts.append(Part("道路中心線形", "線形", tube_along(cl, 0.15, 6), (0.9, 0.1, 0.1), 100, "計画道路の中心線形"))
    parts.append(Part("土工範囲ボックス", "概略形状", box_local(A, 0, L, -18, 18, -6, 6), (0.3, 0.55, 0.95, 0.35), 100, "土工の範囲が分かる程度の直方体 (半透明)", lod_max=100))

    # ---------- LOD200: 標準横断スイープ (切土標準 H=5m / 盛土標準 H=5m を固定形状で) ----------
    def std_cut(s):
        z0 = fh(s); w = W_HALF
        return np.array([[-w, z0], [w, z0], [w + 5 * CUT_SLOPE, z0 + 5], [w + 5 * CUT_SLOPE + 4, z0 + 5], [w + 5 * CUT_SLOPE + 4, z0 - 1], [-w - 5 * CUT_SLOPE - 4, z0 - 1], [-w - 5 * CUT_SLOPE - 4, z0 + 5], [-w - 5 * CUT_SLOPE, z0 + 5]])[::-1]
    def std_fill(s):
        z0 = fh(s); w = W_HALF
        return np.array([[-w, z0], [w, z0], [w + 5 * FILL_SLOPE, z0 - 5], [-w - 5 * FILL_SLOPE, z0 - 5]])[::-1]
    s_split = next(s for s in sts if not secs[float(s)]["Rcut"])
    parts.append(Part("標準横断スイープ 切土部 (1:1.0, H=5m 固定)", "本体", sweep(A, std_cut, stations(0, s_split, 2.0)), C["cut"], 200, "標準横断面をスイープした概略形状 (地形との擦り付けなし)", lod_max=200))
    parts.append(Part("標準横断スイープ 盛土部 (1:1.5, H=5m 固定)", "本体", sweep(A, std_fill, stations(s_split, L, 2.0)), C["fill"], 200, "標準横断面をスイープした概略形状", lod_max=200))
    parts.append(Part("路面 (標準横断)", "本体", sweep(A, lambda s: np.array([[-W_HALF, fh(s)], [W_HALF, fh(s)], [W_HALF, fh(s) - 0.2], [-W_HALF, fh(s) - 0.2]]), sts), C["road"], 200, "", lod_max=200))

    # ---------- LOD300: 各測点横断による土工形状 ----------
    for side_key, side_name in (("L", "左"), ("R", "右")):
        grid = np.array([A.to_world(s, secs[float(s)][side_key]) for s in sts])
        # 切土/盛土で区間を分ける
        kinds = [secs[float(s)][side_key + "cut"] for s in sts]
        i = 0
        while i < len(sts):
            j = i
            while j + 1 < len(sts) and kinds[j + 1] == kinds[i]: j += 1
            if j > i:
                m = grid_mesh(grid[i:j + 1], False, False); m.F = np.vstack([m.F, m.F[:, ::-1]])
                nm = "切土法面 1:1.0 (小段 1.5m@5m)" if kinds[i] else "盛土法面 1:1.5 (小段 1.5m@5m)"
                parts.append(Part(f"{nm} [{side_name}側 No.{sts[i]:.0f}-{sts[j]:.0f}]", "法面", m, C["cut"] if kinds[i] else C["fill"], 300, "各測点の横断面から作成した法面 (地形との擦り付け位置が正確)"))
            i = j + 1
    # 路面 (詳細度300では舗装を一体) / 路床
    parts.append(Part("舗装 (一体) t=65cm", "舗装", sweep(A, lambda s: np.vstack([road_top(s), (road_top(s) - [0, T_PAV])[::-1]]), sts), C["road"], 300, "舗装構成は詳細度400で層別に分割", lod_max=300))
    # 盛土本体 / 切土部の路床: 路面下から地山線までの閉断面
    def body_sec(s):
        sec = secs[float(s)]; Lp, Rp = sec["L"], sec["R"]
        top = road_top(s) - [0, T_PAV]
        gl = np.column_stack([np.linspace(Rp[-1, 0], Lp[-1, 0], 16), [ground_at(s, y) for y in np.linspace(Rp[-1, 0], Lp[-1, 0], 16)]])
        # 盛土: 路面下 → 右法面(下り) → 地山 → 左法面(上り) → 戻る
        return np.vstack([top, Rp, gl, Lp[::-1]])   # 頂点数を測点間で一定にするため常に全点を使う
    fill_sts = stations(s_split, L, 2.0)
    parts.append(Part("盛土本体 (路体・路床)", "土工", sweep(A, body_sec, fill_sts), C["body"], 300, "盛土の土量形状"))
    # 側溝 (切土法尻)
    for side_key, side_name, sg in (("L", "左", -1), ("R", "右", 1)):
        ds = [s for s in sts if secs[float(s)][side_key + "cut"]]
        if len(ds) > 1:
            y0 = sg * W_HALF
            def dsec(s, y0=y0, sg=sg): z = fh(s) - CROSS * W_HALF; return np.array([[y0, z], [y0 + sg * DITCH_W, z], [y0 + sg * DITCH_W, z - DITCH_D], [y0, z - DITCH_D]])
            parts.append(Part(f"法尻側溝 U型300 ({side_name}側 切土区間)", "排水工", sweep(A, dsec, np.array(ds)), C["ditch"], 300, "切土区間の法尻に設置する側溝"))
    # 法面保護工 範囲記号 (LOD300)
    for side_key, side_name in (("L", "左"), ("R", "右")):
        gridc = []
        for s in sts:
            sec = secs[float(s)]; pl = sec[side_key]
            if sec[side_key + "cut"]: gridc.append(A.to_world(s, offset_polyline(pl, -0.5 * (1 if side_key == "R" else -1))))
        if len(gridc) > 1:
            m = grid_mesh(np.array(gridc), False, False); m.F = np.vstack([m.F, m.F[:, ::-1]])
            parts.append(Part(f"法面保護工 範囲記号 (吹付法枠工, {side_name}側 切土)", "記号", m, C["sym"], 300, "法面保護工の適用範囲を記号 (半透明面) で表示。詳細度400で実形状に置換", lod_max=300))

    # ---------- LOD400: 舗装層別・法面工・排水工・防護柵 ----------
    z = 0.0
    for nm, t in PAV:
        col = {"表層": (0.25, 0.25, 0.27), "基層": (0.36, 0.34, 0.34), "上層路盤": (0.48, 0.44, 0.38), "下層路盤": (0.62, 0.56, 0.45)}[nm]
        parts.append(Part(f"舗装 {nm} t={t*100:.0f}cm", "舗装", sweep(A, lambda s, z=z, t=t: np.vstack([road_top(s) - [0, z], (road_top(s) - [0, z + t])[::-1]]), sts), col, 400, "舗装構成を層別にモデル化"))
        z += t
    # 植生工 (盛土法面に 2cm の被覆面)
    for side_key, side_name, sg in (("L", "左", -1), ("R", "右", 1)):
        g = [A.to_world(s, offset_polyline(secs[float(s)][side_key], -0.02 * sg)) for s in sts if not secs[float(s)][side_key + "cut"]]
        if len(g) > 1:
            m = grid_mesh(np.array(g), False, False); m.F = np.vstack([m.F, m.F[:, ::-1]])
            parts.append(Part(f"植生工 (種子散布, {side_name}側 盛土法面)", "法面工", m, C["veg"], 400, "盛土法面の植生工"))
    # 吹付法枠工 (切土法面: 300×300 @2.0m 格子) — 小段間の法面ごとに格子
    for side_key, side_name, sg in (("L", "左", -1), ("R", "右", 1)):
        m = Mesh(); cnt = 0
        cut_sts = [s for s in sts if secs[float(s)][side_key + "cut"]]
        # 横枠: 各測点位置の法面に沿った梁は 2m 間隔の測点で
        for s in cut_sts[::1]:
            if int(round(s)) % 2: continue
            raw = secs[float(s)][side_key + "raw"]
            for a, b in zip(raw[:-1], raw[1:]):
                if a[2] in ("ditch", "slope") or (a[2] == "edge" and b[2] == "top"):
                    p0 = A.to_world(s, [[a[0], a[1]]])[0]; p1 = A.to_world(s, [[b[0], b[1]]])[0]
                    if np.linalg.norm(p1 - p0) < 0.5: continue
                    d = p1 - p0; n = np.array([0, 0, 1.0]); u = np.cross(d, n); u /= (np.linalg.norm(u) + 1e-9); w = np.cross(u, d / np.linalg.norm(d))
                    m.add(box_at((p0 + p1) / 2 + w * 0.15, (np.linalg.norm(d), 0.3, 0.3), d / np.linalg.norm(d), u, w)); cnt += 1
        # 縦枠: 法面に沿って線形方向に 2m ピッチの高さで
        for hk in np.arange(1.0, 15.0, 2.0):
            path = []
            for s in cut_sts:
                raw = secs[float(s)][side_key + "raw"]; zt = fh(s) + hk
                seg = [(a, b) for a, b in zip(raw[:-1], raw[1:]) if min(a[1], b[1]) <= zt <= max(a[1], b[1]) and a[2] != "berm"]
                if not seg: path.append(None); continue
                a, b = seg[0]; t = (zt - a[1]) / (b[1] - a[1] + 1e-9); yy = a[0] + t * (b[0] - a[0])
                path.append(A.to_world(s, [[yy + 0.2 * -sg, zt + 0.2]])[0])
            run = []
            for p in path + [None]:
                if p is None:
                    if len(run) > 1: m.add(tube_along(np.array(run), 0.15, 4)); cnt += 1
                    run = []
                else: run.append(p)
        if cnt: parts.append(Part(f"吹付法枠工 300×300 @2.0m ({side_name}側 切土法面)", "法面工", m, C["frame"], 400, "法面保護工の実形状 (格子枠)"))
    # 小段排水溝 + 縦排水管
    for side_key, side_name, sg in (("L", "左", -1), ("R", "右", 1)):
        m = Mesh(); mp = Mesh(); cnt = 0
        for s in sts:
            raw = secs[float(s)][side_key + "raw"]
            for a, b in zip(raw[:-1], raw[1:]):
                if a[2] == "berm":
                    c = A.to_world(s, [[(a[0] + b[0]) / 2, a[1] + 0.15]])[0]; T = A.frame(s)[1]
                    m.add(box_at(c, (2.05, 0.3, 0.3), T, np.cross(T, [0, 0, 1]), [0, 0, 1.0]))
        for s in np.arange(20, L, 40.0):
            sec = secs[float(min(sts, key=lambda v: abs(v - s)))]; raw = sec[side_key + "raw"]
            pth = [A.to_world(s, [[p[0] + 0.15 * -sg, p[1] + 0.15]])[0] for p in raw]
            mp.add(tube_along(np.array(pth), 0.15, 6)); cnt += 1
        if m.ntri: parts.append(Part(f"小段排水溝 ({side_name}側)", "排水工", m, C["ditch"], 400, "小段に沿う排水溝"))
        parts.append(Part(f"縦排水管 φ300 @40m ({side_name}側, {cnt}本)", "排水工", mp, C["pipe"], 400, "法面の縦排水"))
    # ガードレール (盛土区間 両側)
    for sg, side_name in ((-1, "左"), (1, "右")):
        m = Mesh(); cnt = 0
        for s in np.arange(s_split, L, 2.0):
            base = A.to_world(s, [[sg * (W_HALF - 0.4), fh(s) - CROSS * (W_HALF - 0.4)]])[0]
            m.add(cylinder(base, base + [0, 0, 0.8], 0.06, 6)); cnt += 1
        path = np.array([A.to_world(s, [[sg * (W_HALF - 0.4), fh(s) - CROSS * (W_HALF - 0.4) + 0.75]])[0] for s in np.arange(s_split, L, 2.0)])
        m.add(tube_along(path, 0.12, 6))
        parts.append(Part(f"ガードレール Gr-B ({side_name}側 盛土区間, 支柱{cnt}本)", "防護柵", m, C["guard"], 400, "盛土区間の防護柵"))

    # ---------- LOD500: 出来形 (法面凹凸) + 路面標示 ----------
    for side_key, side_name, sg in (("L", "左", -1), ("R", "右", 1)):
        g = []
        for s in sts:
            pl = secs[float(s)][side_key]; noise = rng.uniform(-0.08, 0.08, size=len(pl)); noise[0] = 0
            g.append(A.to_world(s, offset_polyline(pl, 0) + np.column_stack([noise * 0, noise])))
        m = grid_mesh(np.array(g), False, False); m.F = np.vstack([m.F, m.F[:, ::-1]])
        parts.append(Part(f"法面出来形 (実測凹凸を反映, {side_name}側)", "出来形", m, (0.55, 0.5, 0.4), 500, "施工後の実測面"))
    for yy, nm, w in ((0.0, "中央線", 0.15), (-W_HALF + 1.25, "外側線 (左)", 0.15), (W_HALF - 1.25, "外側線 (右)", 0.15)):
        parts.append(Part(f"路面標示 {nm}", "完成設備", sweep(A, lambda s, yy=yy, w=w: np.array([[yy - w / 2, fh(s) - CROSS * abs(yy) + 0.005], [yy + w / 2, fh(s) - CROSS * abs(yy) + 0.005], [yy + w / 2, fh(s) - CROSS * abs(yy) - 0.005], [yy - w / 2, fh(s) - CROSS * abs(yy) - 0.005]]), sts), C["line"], 500, "完成時の区画線"))
    return parts

def meta():
    return dict(
        id="earthwork", name="道路土工（切土・盛土）", category="土工",
        description="2車線道路 (幅員9.5m) を架空地形に通した区間 240m。起点側が切土 (1:1.0, 小段1.5m@5m)、終点側が盛土 (1:1.5)。舗装4層、法尻側溝、法面保護工 (吹付法枠・植生)、小段排水、縦排水、ガードレールを含む。",
        ref="道路土工要綱の一般値と道路標準横断図 (舗装構成) を参考にした架空断面。実案件の線形・地形は使用していない。",
        alignment=A, center=[115.0, 12.0, 0.0], ground={"cx": 120, "cy": 20, "z": -8.0, "size": 800},
        views=[{"name": "全景", "pos": [-80, -130, 90], "target": [115, 12, 0]}, {"name": "切土部", "pos": [-20, -45, 22], "target": [40, 0, 2]},
               {"name": "盛土部", "pos": [150, -60, 20], "target": [200, 22, -2]}, {"name": "断面", "pos": None, "target": None, "clip": 60}],
        lod_def={100: ["土工の位置と概略範囲を線形と単純な直方体で示す。"],
                 200: ["標準横断面 (切土 1:1.0 / 盛土 1:1.5, 高さ固定) を線形に沿ってスイープした概略形状。地形との擦り付けは行わない。"],
                 300: ["各測点の横断面から作成した土工形状。法面・小段・法尻側溝の外形が正確で、地形との擦り付け位置が分かる。法面保護工の範囲は記号 (半透明面) で示す。"],
                 400: ["詳細度300に加えて舗装構成 (層別)、法面保護工 (吹付法枠・植生工)、小段排水溝、縦排水管、防護柵などの附帯工を実形状でモデル化。"],
                 500: ["出来形 (実測した法面の凹凸) と完成時の路面標示を反映。"]},
        notes=["切土・盛土の判定は各測点で地形と路肩端の高さを比較して自動判定。", "地形は詳細度の対象外 (参考表示)。"],
    )

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "site")
    export_model(build_parts(), os.path.abspath(out), meta())
