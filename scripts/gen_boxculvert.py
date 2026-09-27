# -*- coding: utf-8 -*-
"""BOXカルバート（1連 3.0×2.5m） 詳細度別サンプル
   道路盛土 (天端幅 9.5m, 高さ 5m, 法 1:1.5) を横断する水路用ボックス。延長は盛土の法尻間に合わせた 36m (9m ブロック×4)。
   両端に胸壁 (パラペット) と斜め翼壁 (八の字, 上端は盛土法面に沿って下がる)、取付水路、基礎、目地・止水板、配筋。
   参考: 道路土工カルバート工指針の標準的な部材厚 (頂版・底版 0.35m、側壁 0.30m、ハンチ 0.3m)。実案件の一般図は参照できていないため寸法は一般値。
"""
import sys, os, math
import numpy as np
from lodkit import *

A = Alignment([("S", 60.0)], origin=(-10.0, 0.0))    # 水路軸 (x)。origin -10 → 測点 s = x + 10
X_ROAD = 20.0                                         # 道路中心 (盛土) が横断する位置
W_TOP, H_EMB, N_EMB = 9.5, 5.0, 1.5                   # 盛土 天端幅 / 高さ / 法勾配 1:n
W_IN, H_IN = 3.0, 2.5
T_TOP, T_BOT, T_WALL, HAUNCH = 0.35, 0.35, 0.30, 0.3
Z_INV = 0.0; Z_BOT = Z_INV - T_BOT; Z_TOP = Z_INV + H_IN + T_TOP
Z_ROAD = Z_TOP + 0.6 + H_EMB                          # 盛土天端 (路面) 高。BOX 頂版上の土被り 0.6m + 盛土 5m
X0, X1 = X_ROAD - 18.0, X_ROAD + 18.0                 # BOX 延長 36m (盛土法尻 = 地盤高での法尻位置に合わせる)
BLOCK = 9.0
W_OUT = W_IN / 2 + T_WALL                             # 外壁面の y
rng = np.random.default_rng(5)

def ground(x, y):   # 原地盤: 水路軸に沿って緩い下り勾配
    return Z_INV - 0.3 - 0.004 * x + 0.12 * math.sin(x / 7.0) * math.cos(y / 9.0)

def embank(x, y):   # 道路盛土 (x=X_ROAD 中心, 天端幅 W_TOP, 法 1:1.5)。盛土が地山より低い所は地中に隠す
    d = abs(x - X_ROAD)
    z = Z_ROAD if d <= W_TOP / 2 else Z_ROAD - (d - W_TOP / 2) / N_EMB
    if abs(y) > 30: return ground(x, y) - 1.0
    return z if z > ground(x, y) + 0.05 else ground(x, y) - 1.0

def rect(y0, y1, z0, z1): return np.array([[y0, z0], [y1, z0], [y1, z1], [y0, z1]])

def wing(x_end, direction, side, thk=0.35, ang_deg=30.0, length=6.0):
    """斜め翼壁: BOX 端部 (x_end) から水路の外側へ ang 度開きながら length 伸びる。上端は盛土法面に沿って下がる"""
    ang = math.radians(ang_deg)
    u = np.array([direction * math.cos(ang), side * math.sin(ang), 0.0])          # 壁の延びる方向 (水平)
    v = np.array([0.0, 0.0, 1.0])
    n = np.array([-u[1], u[0], 0.0])
    if np.dot(n, np.array([0.0, side, 0.0])) < 0: n = -n                            # 壁厚は水路の外側へ
    base = np.array([x_end, side * W_OUT, Z_BOT])
    z_start = Z_TOP + 0.6                                                           # BOX 端部の胸壁天端
    z_end = max(Z_INV + 0.8, min(z_start - 1.0, embank(x_end + direction * length, side * (W_OUT + length * math.sin(ang)))))
    poly = np.array([[0, 0], [length, 0], [length, z_end - Z_BOT], [0, z_start - Z_BOT]])
    wall = extrude_world(poly, n, base, thk, u, v)
    foot = extrude_world(np.array([[-0.2, -0.5], [length + 0.3, -0.5], [length + 0.3, 0.0], [-0.2, 0.0]]), n, base - n * 0.4, thk + 0.8, u, v)
    return wall, foot

def build_parts():
    parts = []
    C = dict(terrain=(0.62, 0.70, 0.50), fill=(0.66, 0.62, 0.46), road=(0.30, 0.30, 0.32), conc=(0.80, 0.80, 0.77), base=(0.62, 0.60, 0.55), lean=(0.70, 0.70, 0.68),
             water=(0.35, 0.55, 0.80, 0.6), sym=(0.2, 0.6, 0.9, 0.4), box100=(0.3, 0.55, 0.95, 0.35), rebar=(0.70, 0.20, 0.15), ws=(0.15, 0.15, 0.2),
             joint=(0.3, 0.3, 0.3), wing=(0.78, 0.78, 0.75), channel=(0.66, 0.68, 0.70), guard=(0.85, 0.85, 0.88))
    st = lambda x: x + 10.0   # world x → 測点
    # ---------- 参考: 地形・盛土・路面 ----------
    parts.append(Part("現況地形 (参考)", "地形", surface_mesh(np.arange(-25, 65, 2.0), np.arange(-35, 35, 2.0), ground), C["terrain"], 100, "地形は詳細度の対象外"))
    def embank_hole(x, y):
        z = embank(x, y)
        if X0 - 0.5 < x < X1 + 0.5 and abs(y) < W_OUT + 0.4 and z < Z_TOP + 0.02: return Z_TOP + 0.02
        return z
    parts.append(Part(f"道路盛土 (参考, 天端幅{W_TOP}m H={H_EMB}m 法1:{N_EMB})", "土工", surface_mesh(np.arange(X_ROAD - 16, X_ROAD + 16.01, 0.5), np.arange(-30, 30.01, 1.0), embank_hole), C["fill"], 100, "ボックスが横断する道路盛土 (参考表示)"))
    parts.append(Part("道路舗装 (参考)", "道路", box_world(X_ROAD - W_TOP / 2 + 0.75, X_ROAD + W_TOP / 2 - 0.75, -30, 30, Z_ROAD, Z_ROAD + 0.05), C["road"], 100, "盛土上の道路 (参考表示)"))
    parts.append(Part("水面 (参考)", "地形", box_world(X0 - 10, X1 + 10, -W_IN / 2 + 0.05, W_IN / 2 - 0.05, Z_INV + 0.3, Z_INV + 0.35), C["water"], 100, "参考"))

    # ---------- LOD100 ----------
    parts.append(Part("水路中心線", "線形", tube_along(np.array([[X0 - 12, 0, Z_INV + 0.5], [X1 + 12, 0, Z_INV + 0.5]]), 0.12, 6), (0.9, 0.1, 0.1), 100, "カルバートの軸線"))
    parts.append(Part("カルバート範囲ボックス", "概略形状", box_world(X0 - 0.5, X1 + 0.5, -W_OUT - 0.5, W_OUT + 0.5, Z_BOT - 0.5, Z_TOP + 0.5), C["box100"], 100, "位置と延長が分かる直方体", lod_max=100))

    # ---------- LOD200: 標準断面のスイープ (外形一体) ----------
    parts.append(Part("ボックス本体 (外形一体, 内空なし)", "本体", box_world(X0, X1, -W_OUT, W_OUT, Z_BOT, Z_TOP), C["conc"], 200, "標準断面 (外形) をスイープした形状。内空・翼壁は表現しない", lod_max=200))
    for xe, d in ((X0, -1), (X1, +1)):
        parts.append(Part(f"翼壁 概形 ({'上流' if d < 0 else '下流'})", "翼壁", box_world(min(xe, xe + d * 5), max(xe, xe + d * 5), -W_OUT - 3.0, W_OUT + 3.0, Z_BOT, Z_TOP + 0.6), (0.78, 0.78, 0.75, 0.6), 200, "翼壁の範囲を示す概形 (半透明)", lod_max=200))

    # ---------- LOD300: 外形が正確 ----------
    nblk = int(round((X1 - X0) / BLOCK))
    for b in range(nblk):
        xa, xb = X0 + BLOCK * b, X0 + BLOCK * (b + 1) - 0.02
        parts.append(Part(f"頂版 t={T_TOP*100:.0f}cm (ブロック{b+1})", "本体", box_world(xa, xb, -W_OUT, W_OUT, Z_INV + H_IN, Z_TOP), C["conc"], 300, "頂版"))
        parts.append(Part(f"底版 t={T_BOT*100:.0f}cm (ブロック{b+1})", "本体", box_world(xa, xb, -W_OUT, W_OUT, Z_BOT, Z_INV), C["conc"], 300, "底版"))
        for sg, nm in ((-1, "左"), (1, "右")):
            y0, y1 = sorted((sg * W_IN / 2, sg * W_OUT))
            parts.append(Part(f"側壁 t={T_WALL*100:.0f}cm ({nm}, ブロック{b+1})", "本体", box_world(xa, xb, y0, y1, Z_INV, Z_INV + H_IN), C["conc"], 300, "側壁"))
            tri = np.array([[sg * W_IN / 2, Z_INV + H_IN], [sg * (W_IN / 2 - HAUNCH), Z_INV + H_IN], [sg * W_IN / 2, Z_INV + H_IN - HAUNCH]])
            if sg > 0: tri = tri[::-1]
            parts.append(Part(f"ハンチ ({nm}, ブロック{b+1})", "本体", extrude(A, tri, st(xa), xb - xa), C["conc"], 300, "隅角部ハンチ"))
    for xe, d in ((X0, -1), (X1, +1)):
        nm = "上流" if d < 0 else "下流"
        xa, xb = (xe - 0.3, xe) if d < 0 else (xe, xe + 0.3)
        parts.append(Part(f"胸壁 (パラペット) t=30cm H=60cm ({nm})", "本体", box_world(xa, xb, -W_OUT, W_OUT, Z_TOP, Z_TOP + 0.6), C["conc"], 300, "端部の土留め胸壁"))
        for sg, side_nm in ((-1, "左"), (1, "右")):
            wall, foot = wing(xe, d, sg)
            parts.append(Part(f"翼壁 ({nm}{side_nm}, 斜め30° L=6m)", "翼壁", wall, C["wing"], 300, "八の字の斜め翼壁 (上端は盛土法面に沿って下がる)"))
            parts.append(Part(f"翼壁 基礎 ({nm}{side_nm})", "翼壁", foot, C["wing"], 300, "翼壁フーチング"))
    parts.append(Part("均しコンクリート t=10cm", "基礎", box_world(X0 - 0.1, X1 + 0.1, -W_OUT - 0.1, W_OUT + 0.1, Z_BOT - 0.10, Z_BOT), C["lean"], 300, "均しコンクリート"))
    parts.append(Part("基礎砕石 t=20cm", "基礎", box_world(X0 - 0.3, X1 + 0.3, -W_OUT - 0.3, W_OUT + 0.3, Z_BOT - 0.30, Z_BOT - 0.10), C["base"], 300, "基礎砕石"))
    for b in range(1, nblk):
        x = X0 + BLOCK * b
        parts.append(Part(f"目地位置記号 (ブロック{b}/{b+1} 間)", "記号", box_world(x - 0.05, x + 0.05, -W_OUT - 0.2, W_OUT + 0.2, Z_BOT - 0.2, Z_TOP + 0.2), C["sym"], 300, "ブロック間の目地位置 (記号)。詳細度400で止水板・目地材", lod_max=300))
    for xa, xb, nm in ((X0 - 10, X0, "上流"), (X1, X1 + 10, "下流")):
        m = Mesh().add(box_world(xa, xb, -W_IN / 2 - 0.3, W_IN / 2 + 0.3, Z_INV - 0.3, Z_INV)).add(box_world(xa, xb, -W_IN / 2 - 0.3, -W_IN / 2, Z_INV, Z_INV + 1.0)).add(box_world(xa, xb, W_IN / 2, W_IN / 2 + 0.3, Z_INV, Z_INV + 1.0))
        parts.append(Part(f"取付水路 ({nm}, コンクリート三面張り L=10m)", "取付水路", m, C["channel"], 300, "取付水路"))
    parts.append(Part("埋戻し範囲記号 (BOX 周辺)", "記号", box_world(X0, X1, -W_OUT - 1.0, W_OUT + 1.0, Z_BOT - 0.3, Z_TOP + 0.6), (0.66, 0.60, 0.48, 0.3), 300, "良質土での埋戻し範囲 (半透明)", lod_max=300))

    # ---------- LOD400: 配筋・止水板・目地材・防水・裏込め・防護柵 ----------
    m = Mesh(); n = 0
    for b in range(nblk):
        xa, xb = X0 + BLOCK * b + 0.05, X0 + BLOCK * (b + 1) - 0.07
        for x in np.arange(xa + 0.1, xb, 0.25):   # 主筋 (環状) D22@250 外側・内側
            c = 0.07
            for loop in (np.array([[-W_OUT + c, Z_BOT + c], [W_OUT - c, Z_BOT + c], [W_OUT - c, Z_TOP - c], [-W_OUT + c, Z_TOP - c], [-W_OUT + c, Z_BOT + c]]),
                         np.array([[-W_IN / 2 - c, Z_INV - c], [W_IN / 2 + c, Z_INV - c], [W_IN / 2 + c, Z_INV + H_IN + c], [-W_IN / 2 - c, Z_INV + H_IN + c], [-W_IN / 2 - c, Z_INV - c]])):
                m.add(tube_along(np.column_stack([np.full(len(loop), x), loop[:, 0], loop[:, 1]]), 0.011, 4)); n += 1
        for yy in (-W_OUT + 0.09, W_OUT - 0.09, -W_IN / 2 - 0.09, W_IN / 2 + 0.09):   # 配力筋 D16@300 (側壁)
            for zz in np.arange(Z_BOT + 0.2, Z_TOP, 0.3): m.add(tube_along(np.array([[xa, yy, zz], [xb, yy, zz]]), 0.008, 4)); n += 1
        for zz in (Z_BOT + 0.09, Z_TOP - 0.09, Z_INV - 0.09, Z_INV + H_IN + 0.09):   # 配力筋 (頂版・底版)
            for yy in np.arange(-W_OUT + 0.2, W_OUT, 0.3): m.add(tube_along(np.array([[xa, yy, zz], [xb, yy, zz]]), 0.008, 4)); n += 1
    parts.append(Part(f"配筋 (主筋 D22@250 内外2層, 配力筋 D16@300, {n}本)", "配筋", m, C["rebar"], 400, "ボックス本体の配筋"))
    for b in range(1, nblk):
        x = X0 + BLOCK * b
        ws = Mesh()
        ws.add(box_world(x - 0.1, x + 0.1, -W_OUT + T_WALL / 2 - 0.1, -W_OUT + T_WALL / 2 + 0.1, Z_BOT + 0.1, Z_TOP - 0.1)).add(box_world(x - 0.1, x + 0.1, W_OUT - T_WALL / 2 - 0.1, W_OUT - T_WALL / 2 + 0.1, Z_BOT + 0.1, Z_TOP - 0.1))
        ws.add(box_world(x - 0.1, x + 0.1, -W_OUT + T_WALL / 2, W_OUT - T_WALL / 2, Z_TOP - T_TOP / 2 - 0.1, Z_TOP - T_TOP / 2 + 0.1)).add(box_world(x - 0.1, x + 0.1, -W_OUT + T_WALL / 2, W_OUT - T_WALL / 2, Z_BOT + T_BOT / 2 - 0.1, Z_BOT + T_BOT / 2 + 0.1))
        parts.append(Part(f"止水板 (中埋め型, 目地 {b}/{b+1})", "目地", ws, C["ws"], 400, "目地部の止水板"))
        parts.append(Part(f"目地材 t=20mm (目地 {b}/{b+1})", "目地", box_world(x - 0.01, x + 0.01, -W_OUT, W_OUT, Z_BOT, Z_TOP), C["joint"], 400, "伸縮目地材"))
    parts.append(Part("防水工 (頂版上面 塗膜)", "防水", box_world(X0, X1, -W_OUT, W_OUT, Z_TOP, Z_TOP + 0.01), (0.2, 0.2, 0.25), 400, "頂版の防水"))
    parts.append(Part("裏込め砕石 (BOX 側面, 幅0.5m)", "裏込め", Mesh().add(box_world(X0, X1, -W_OUT - 0.5, -W_OUT, Z_BOT, Z_TOP)).add(box_world(X0, X1, W_OUT, W_OUT + 0.5, Z_BOT, Z_TOP)), (0.72, 0.70, 0.60), 400, "側壁背面の裏込め材"))
    m = Mesh(); n = 0
    for xe, d in ((X0, -1), (X1, +1)):
        xg = xe + d * 0.15
        for y in np.arange(-W_OUT - 2.0, W_OUT + 2.01, 2.0):
            m.add(cylinder([xg, y, Z_TOP + 0.6], [xg, y, Z_TOP + 1.7], 0.05, 6)); n += 1
        m.add(tube_along(np.array([[xg, -W_OUT - 2.0, Z_TOP + 1.65], [xg, W_OUT + 2.0, Z_TOP + 1.65]]), 0.03, 6))
    parts.append(Part(f"転落防止柵 (胸壁上, 支柱{n}本)", "附属物", m, C["guard"], 400, "胸壁天端の防護柵"))

    # ---------- LOD500 ----------
    m = Mesh()
    for x in np.arange(X0 + 1, X1, 2.0):
        m.add(box_world(x - 0.02, x + 0.02, -W_IN / 2, W_IN / 2, Z_INV + 0.02 + rng.uniform(-0.01, 0.01), Z_INV + 0.03 + rng.uniform(-0.01, 0.01)))
    parts.append(Part("内空 出来形計測線 (実測, 記号)", "出来形", m, (0.55, 0.5, 0.4, 0.7), 500, "出来形計測結果の反映 (サンプルでは記号)"))
    m = Mesh()
    for y in np.arange(-W_IN / 2 + 0.3, W_IN / 2, 0.3): m.add(box_world(X0 - 0.06, X0 - 0.02, y - 0.02, y + 0.02, Z_INV, Z_INV + H_IN))
    parts.append(Part("流入部 スクリーン (完成設備)", "完成設備", m, (0.4, 0.42, 0.45), 500, "完成時の設備 (簡略)"))
    return parts

def meta():
    return dict(
        id="boxculvert", name="BOXカルバート（1連 3.0×2.5m）", category="カルバート", wip=True,
        description="道路盛土 (天端幅9.5m, H=5m) を横断する水路用ボックスカルバート、延長36m (9mブロック×4)。頂版・底版0.35m、側壁0.30m、ハンチ、胸壁、斜め翼壁 (八の字)、取付水路、基礎、目地・止水板、配筋を含む。",
        ref="道路土工カルバート工指針の標準的な部材厚を参考にした架空断面。実案件の一般図 (DWG/DocuWorks) は読取環境がなく未参照。",
        alignment=A, center=[20.0, 0.0, 1.5], ground={"cx": 20, "cy": 0, "z": -1.0, "size": 300},
        views=[{"name": "全景", "pos": [-28, -42, 24], "target": [20, 0, 1]}, {"name": "上流坑口", "pos": [-10, -10, 4], "target": [2, 0, 1.5]},
               {"name": "内空", "pos": [-4, 0, 1.4], "target": [10, 0, 1.3]}, {"name": "断面", "pos": None, "target": None, "clip": 30}],
        lod_def={100: ["カルバートの位置と延長を軸線と直方体で示す。"],
                 200: ["標準断面の外形を延長方向にスイープした一体形状。翼壁は範囲を示す概形のみ。"],
                 300: ["頂版・側壁・底版・ハンチ・胸壁、翼壁 (斜め翼壁と基礎)、基礎 (均しコン・砕石)、取付水路の外形が正確。目地・埋戻しは位置・範囲を記号で示す。"],
                 400: ["詳細度300に加えて配筋 (主筋・配力筋)、止水板・目地材、防水工、裏込め砕石、転落防止柵などの細部をモデル化。"],
                 500: ["完成形状 (出来形計測の反映、流入部スクリーンなどの完成設備)。"]},
        notes=["【試作中】一般値による暫定形状です。実案件の一般図 (PDF) をいただければ寸法を合わせて更新します。", "道路盛土・路面・地形は参考表示。", "配筋は代表的な主筋・配力筋のみ (組立筋・ハンチ筋は省略)。"],
    )

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "site")
    export_model(build_parts(), os.path.abspath(out), meta())
