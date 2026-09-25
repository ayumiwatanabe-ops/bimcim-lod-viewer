# -*- coding: utf-8 -*-
"""BOXカルバート（1連 3.0×2.5m） 詳細度別サンプル
   道路盛土 (高さ 5m) を横断する水路用ボックス、延長 40m (10m ブロック×4)、両端ウイング、取付水路。
   参考: 道路土工カルバート工指針の標準的な部材厚 (頂版・底版 0.35m、側壁 0.30m)。実案件のボックスカルバート一般図 (DWG) は読取不可のため寸法は使用していない。
"""
import sys, os, math
import numpy as np
from lodkit import *

A = Alignment([("S", 60.0)], origin=(-10.0, 0.0))    # 水路軸: x=-10 (上流取付) 〜 0..40 (BOX) 〜 50 (下流取付)
X0, X1 = 0.0, 40.0
W_IN, H_IN = 3.0, 2.5
T_TOP, T_BOT, T_WALL = 0.35, 0.35, 0.30
HAUNCH = 0.3
Z_INV = 0.0                      # 内空底 (インバート) 高
Z_BOT = Z_INV - T_BOT            # 底版下面
Z_TOP = Z_INV + H_IN + T_TOP     # 頂版上面
X_ROAD = 20.0                    # 道路中心 (盛土) が横断する位置
rng = np.random.default_rng(5)

def ground(x, y):   # 原地盤: 水路軸に沿って緩い下り勾配、盛土は別部材
    return Z_INV - 0.3 - 0.004 * x + 0.15 * math.sin(x / 7.0) * math.cos(y / 9.0)

def embank(x, y):   # 道路盛土 (x=X_ROAD 中心, 天端幅 9.5, 高さ 5, 法 1:1.5)
    d = abs(x - X_ROAD); top = Z_TOP + 0.5 + 4.0
    z = top if d <= 4.75 else top - (d - 4.75) / 1.5
    return z if z > ground(x, y) + 0.05 else ground(x, y) - 1.0   # 地山より低い所は地中に隠す

def rect(y0, y1, z0, z1): return np.array([[y0, z0], [y1, z0], [y1, z1], [y0, z1]])

def outer(): return rect(-W_IN / 2 - T_WALL, W_IN / 2 + T_WALL, Z_BOT, Z_TOP)
def inner():
    w, h = W_IN / 2, HAUNCH
    return np.array([[-w, Z_INV], [w, Z_INV], [w, Z_INV + H_IN - h], [w - h, Z_INV + H_IN], [-w + h, Z_INV + H_IN], [-w, Z_INV + H_IN - h]])

def build_parts():
    parts = []
    C = dict(terrain=(0.62, 0.70, 0.50), fill=(0.66, 0.62, 0.46), conc=(0.80, 0.80, 0.77), base=(0.62, 0.60, 0.55), lean=(0.70, 0.70, 0.68),
             water=(0.35, 0.55, 0.80, 0.6), sym=(0.2, 0.6, 0.9, 0.4), box100=(0.3, 0.55, 0.95, 0.35), rebar=(0.70, 0.20, 0.15), ws=(0.15, 0.15, 0.2),
             joint=(0.3, 0.3, 0.3), wing=(0.78, 0.78, 0.75), channel=(0.66, 0.68, 0.70))
    sts = stations(X0 + 10, X1 + 10, 2.0)   # 線形上の測点 (origin -10 のため +10)
    # 地形・盛土 (参考)
    xs = np.arange(-30, 70, 2.0); ys = np.arange(-40, 40, 2.0)
    parts.append(Part("現況地形 (参考)", "地形", surface_mesh(xs, ys, ground), C["terrain"], 100, "地形は詳細度の対象外"))
    def embank_hole(x, y):   # BOX 位置 (|y|<2.2, 0<x<40) は盛土を BOX 天端で切る
        z = embank(x, y)
        if X0 - 1 < x < X1 + 1 and abs(y) < W_IN / 2 + T_WALL + 0.3 and z < Z_TOP: return Z_TOP
        return z
    parts.append(Part("道路盛土 (参考, 天端幅9.5m H=5m)", "土工", surface_mesh(np.arange(-8, 48, 1.0), np.arange(-40, 40, 2.0), embank_hole), C["fill"], 100, "ボックスが横断する道路盛土 (参考表示)"))
    parts.append(Part("道路舗装 (参考)", "道路", box_world(X0 - 0.5, X1 + 0.5, -4.75, 4.75, Z_TOP + 4.5, Z_TOP + 4.6) if False else box_world(-8, 48, X_ROAD - 4.75 - X_ROAD, 0, 0, 0.01), (0.3, 0.3, 0.32), 100, "", lod_max=0))
    parts.pop()  # (未使用)

    # ---------- LOD100 ----------
    parts.append(Part("水路中心線", "線形", tube_along(np.array([[X0 - 12, 0, Z_INV + 0.5], [X1 + 12, 0, Z_INV + 0.5]]), 0.12, 6), (0.9, 0.1, 0.1), 100, "カルバートの軸線"))
    parts.append(Part("カルバート範囲ボックス", "概略形状", box_world(X0 - 0.5, X1 + 0.5, -W_IN / 2 - T_WALL - 0.5, W_IN / 2 + T_WALL + 0.5, Z_BOT - 0.5, Z_TOP + 0.5), C["box100"], 100, "位置と延長が分かる直方体", lod_max=100))

    # ---------- LOD200: 標準断面のスイープ (外形一体) ----------
    parts.append(Part("ボックス本体 (外形一体, 内空なし)", "本体", box_world(X0, X1, -W_IN / 2 - T_WALL, W_IN / 2 + T_WALL, Z_BOT, Z_TOP), C["conc"], 200, "標準断面 (外形) をスイープした形状。内空・ウイングは表現しない", lod_max=200))

    # ---------- LOD300: 外形が正確 (頂版・側壁・底版・ハンチ, ウイング, 基礎, 目地記号, 取付水路) ----------
    for b in range(4):
        xa, xb = X0 + 10 * b, X0 + 10 * (b + 1) - 0.02
        parts.append(Part(f"頂版 t=35cm (ブロック{b+1})", "本体", box_world(xa, xb, -W_IN / 2 - T_WALL, W_IN / 2 + T_WALL, Z_INV + H_IN, Z_TOP), C["conc"], 300, "頂版"))
        parts.append(Part(f"底版 t=35cm (ブロック{b+1})", "本体", box_world(xa, xb, -W_IN / 2 - T_WALL, W_IN / 2 + T_WALL, Z_BOT, Z_INV), C["conc"], 300, "底版"))
        for sg, nm in ((-1, "左"), (1, "右")):
            y0, y1 = sorted((sg * W_IN / 2, sg * (W_IN / 2 + T_WALL)))
            parts.append(Part(f"側壁 t=30cm ({nm}, ブロック{b+1})", "本体", box_world(xa, xb, y0, y1, Z_INV, Z_INV + H_IN), C["conc"], 300, "側壁"))
            tri = np.array([[sg * W_IN / 2, Z_INV + H_IN], [sg * (W_IN / 2 - HAUNCH), Z_INV + H_IN], [sg * W_IN / 2, Z_INV + H_IN - HAUNCH]])
            if sg > 0: tri = tri[::-1]
            parts.append(Part(f"ハンチ ({nm}, ブロック{b+1})", "本体", extrude(A, tri, xa + 10, xb - xa), C["conc"], 300, "隅角部ハンチ"))
    parts.append(Part("均しコンクリート t=10cm", "基礎", box_world(X0 - 0.1, X1 + 0.1, -W_IN / 2 - T_WALL - 0.1, W_IN / 2 + T_WALL + 0.1, Z_BOT - 0.10, Z_BOT), C["lean"], 300, "均しコンクリート"))
    parts.append(Part("基礎砕石 t=20cm", "基礎", box_world(X0 - 0.3, X1 + 0.3, -W_IN / 2 - T_WALL - 0.3, W_IN / 2 + T_WALL + 0.3, Z_BOT - 0.30, Z_BOT - 0.10), C["base"], 300, "基礎砕石"))
    for b in range(1, 4):
        parts.append(Part(f"目地位置記号 (No.{10*b:.0f})", "記号", box_world(X0 + 10 * b - 0.05, X0 + 10 * b + 0.05, -W_IN / 2 - T_WALL - 0.2, W_IN / 2 + T_WALL + 0.2, Z_BOT - 0.2, Z_TOP + 0.2), C["sym"], 300, "ブロック間の目地位置 (記号)。詳細度400で止水板・目地材", lod_max=300))
    # ウイング (八の字: 水路軸に対して 30° 開き, 高さは天端から地盤へ)
    for xe, dir_ in ((X0, -1), (X1, +1)):
        for sg, nm in ((-1, "左"), (1, "右")):
            ang = math.radians(30); Lw = 5.0
            u = np.array([dir_ * math.cos(ang), sg * math.sin(ang), 0.0]); v = np.array([0, 0, 1.0])
            base = np.array([xe, sg * (W_IN / 2 + T_WALL), Z_BOT])
            poly = np.array([[0, 0], [Lw, 0], [Lw, 1.2], [0, Z_TOP - Z_BOT]])
            n = np.cross(u, v) * (sg)   # 外側へ厚み
            parts.append(Part(f"ウイング ({'上流' if dir_ < 0 else '下流'}{nm}, L=5m)", "ウイング", extrude_world(poly, n, base, 0.35, u, v), C["wing"], 300, "翼壁 (八の字)"))
            parts.append(Part(f"ウイング基礎 ({'上流' if dir_ < 0 else '下流'}{nm})", "ウイング", extrude_world(np.array([[0, -0.6], [Lw + 0.3, -0.6], [Lw + 0.3, 0], [0, 0]]), n, base, 1.2, u, v), C["wing"], 300, "翼壁フーチング"))
    # 取付水路 (上下流 各10m, U形 幅3.0 高1.0)
    for xa, xb, nm in ((X0 - 10, X0, "上流"), (X1, X1 + 10, "下流")):
        m = Mesh().add(box_world(xa, xb, -W_IN / 2 - 0.3, W_IN / 2 + 0.3, Z_INV - 0.3, Z_INV)).add(box_world(xa, xb, -W_IN / 2 - 0.3, -W_IN / 2, Z_INV, Z_INV + 1.0)).add(box_world(xa, xb, W_IN / 2, W_IN / 2 + 0.3, Z_INV, Z_INV + 1.0))
        parts.append(Part(f"取付水路 ({nm}, コンクリート三面張り L=10m)", "取付水路", m, C["channel"], 300, "取付水路"))
    parts.append(Part("水面 (参考)", "地形", box_world(X0 - 10, X1 + 10, -W_IN / 2 + 0.05, W_IN / 2 - 0.05, Z_INV + 0.3, Z_INV + 0.35), C["water"], 300, "参考"))

    # ---------- LOD400: 配筋・止水板・目地材 ----------
    m = Mesh(); n = 0
    for b in range(4):
        xa, xb = X0 + 10 * b + 0.05, X0 + 10 * (b + 1) - 0.07
        # 主筋 (断面方向の環状筋 D22@250, 内外2層) を 0.25m ピッチで
        for x in np.arange(xa + 0.1, xb, 0.25):
            for c in (0.07, T_WALL - 0.07):
                loop = np.array([[-W_IN / 2 - c, Z_BOT + c], [W_IN / 2 + c, Z_BOT + c], [W_IN / 2 + c, Z_TOP - c], [-W_IN / 2 - c, Z_TOP - c], [-W_IN / 2 - c, Z_BOT + c]]) if c > T_WALL / 2 else \
                       np.array([[-W_IN / 2 + c, Z_INV + c], [W_IN / 2 - c, Z_INV + c], [W_IN / 2 - c, Z_INV + H_IN - c], [-W_IN / 2 + c, Z_INV + H_IN - c], [-W_IN / 2 + c, Z_INV + c]])
                m.add(tube_along(np.column_stack([np.full(len(loop), x), loop[:, 0], loop[:, 1]]), 0.011, 4)); n += 1
        # 配力筋 (軸方向 D16@300) 各面 内外
        for c, yy_list, zz_list in ((0.09, [-W_IN / 2 - T_WALL + 0.09, W_IN / 2 + T_WALL - 0.09], [Z_BOT + 0.09, Z_TOP - 0.09]), (0.0, [], [])):
            for yy in yy_list:
                for zz in np.arange(Z_BOT + 0.2, Z_TOP, 0.3): m.add(tube_along(np.array([[xa, yy, zz], [xb, yy, zz]]), 0.008, 4)); n += 1
            for zz in zz_list:
                for yy in np.arange(-W_IN / 2 - T_WALL + 0.2, W_IN / 2 + T_WALL, 0.3): m.add(tube_along(np.array([[xa, yy, zz], [xb, yy, zz]]), 0.008, 4)); n += 1
    parts.append(Part(f"配筋 (主筋 D22@250 内外2層, 配力筋 D16@300, {n}本)", "配筋", m, C["rebar"], 400, "ボックス本体の配筋"))
    for b in range(1, 4):
        x = X0 + 10 * b
        loop = outer()
        parts.append(Part(f"止水板 (目地 No.{10*b:.0f})", "目地", extrude(A, np.array([[-W_IN / 2 - T_WALL / 2, Z_BOT + T_BOT / 2], [W_IN / 2 + T_WALL / 2, Z_BOT + T_BOT / 2], [W_IN / 2 + T_WALL / 2, Z_TOP - T_TOP / 2], [-W_IN / 2 - T_WALL / 2, Z_TOP - T_TOP / 2]])[::-1], x + 10 - 0.1, 0.2) if False else Mesh().add(box_world(x - 0.1, x + 0.1, -W_IN / 2 - T_WALL / 2 - 0.1, -W_IN / 2 - T_WALL / 2 + 0.1, Z_BOT + 0.1, Z_TOP - 0.1)).add(box_world(x - 0.1, x + 0.1, W_IN / 2 + T_WALL / 2 - 0.1, W_IN / 2 + T_WALL / 2 + 0.1, Z_BOT + 0.1, Z_TOP - 0.1)).add(box_world(x - 0.1, x + 0.1, -W_IN / 2 - T_WALL / 2, W_IN / 2 + T_WALL / 2, Z_TOP - T_TOP / 2 - 0.1, Z_TOP - T_TOP / 2 + 0.1)).add(box_world(x - 0.1, x + 0.1, -W_IN / 2 - T_WALL / 2, W_IN / 2 + T_WALL / 2, Z_BOT + T_BOT / 2 - 0.1, Z_BOT + T_BOT / 2 + 0.1)), C["ws"], 400, "目地部の止水板 (中埋め型)"))
        parts.append(Part(f"目地材 t=20mm (No.{10*b:.0f})", "目地", box_world(x - 0.01, x + 0.01, -W_IN / 2 - T_WALL, W_IN / 2 + T_WALL, Z_BOT, Z_TOP), C["joint"], 400, "伸縮目地材"))
    parts.append(Part("防水工 (頂版上面 塗膜, t表示)", "防水", box_world(X0, X1, -W_IN / 2 - T_WALL, W_IN / 2 + T_WALL, Z_TOP, Z_TOP + 0.01), (0.2, 0.2, 0.25), 400, "頂版の防水"))

    # ---------- LOD500 ----------
    m = Mesh()
    for x in np.arange(X0 + 1, X1, 2.0):
        m.add(box_world(x - 0.02, x + 0.02, -W_IN / 2, W_IN / 2, Z_INV + 0.02 + rng.uniform(-0.01, 0.01), Z_INV + 0.03 + rng.uniform(-0.01, 0.01)))
    parts.append(Part("内空 出来形計測線 (実測, 記号)", "出来形", m, (0.55, 0.5, 0.4, 0.7), 500, "出来形計測結果の反映 (サンプルでは記号)"))
    parts.append(Part("流入部 スクリーン (完成設備)", "完成設備", Mesh().add(*[box_world(X0 - 0.05, X0 + 0.05, y - 0.02, y + 0.02, Z_INV, Z_INV + H_IN) for y in np.arange(-W_IN / 2 + 0.3, W_IN / 2, 0.3)][:1]) if False else _screen(), (0.4, 0.42, 0.45), 500, "完成時の設備 (簡略)"))
    return parts

def _screen():
    m = Mesh()
    for y in np.arange(-W_IN / 2 + 0.3, W_IN / 2, 0.3): m.add(box_world(X0 - 0.06, X0 - 0.02, y - 0.02, y + 0.02, Z_INV, Z_INV + H_IN))
    return m

def meta():
    return dict(
        id="boxculvert", name="BOXカルバート（1連 3.0×2.5m）", category="カルバート", wip=True,
        description="道路盛土を横断する水路用ボックスカルバート、延長40m (10mブロック×4)。頂版・底版0.35m、側壁0.30m、ハンチ、両端ウイング (八の字)、取付水路、基礎、目地・止水板、配筋を含む。",
        ref="道路土工カルバート工指針の標準的な部材厚を参考にした架空断面。実案件のボックスカルバート一般図は使用していない。",
        alignment=A, center=[20.0, 0.0, 1.5], ground={"cx": 20, "cy": 0, "z": -1.0, "size": 300},
        views=[{"name": "全景", "pos": [-30, -45, 25], "target": [20, 0, 1]}, {"name": "上流坑口", "pos": [-14, -8, 3], "target": [0, 0, 1.5]},
               {"name": "内空", "pos": [-6, 0, 1.4], "target": [10, 0, 1.3]}, {"name": "断面", "pos": None, "target": None, "clip": 25}],
        lod_def={100: ["カルバートの位置と延長を軸線と直方体で示す。"],
                 200: ["標準断面の外形を延長方向にスイープした一体形状。内空・ウイングは表現しない。"],
                 300: ["頂版・側壁・底版・ハンチ、ウイング、基礎 (均しコン・砕石)、取付水路の外形が正確。目地は位置を記号で示す。"],
                 400: ["詳細度300に加えて配筋 (主筋・配力筋)、止水板・目地材、防水工などの細部をモデル化。"],
                 500: ["完成形状 (出来形計測の反映、流入部スクリーンなどの完成設備)。"]},
        notes=["【試作中】形状は暫定で、実際のボックスカルバートとは細部が異なります。詳細度の説明用として参考程度にご覧ください。", "道路盛土・地形は参考表示。", "配筋は代表的な主筋・配力筋のみ (組立筋・ハンチ筋は省略)。"],
    )

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "site")
    export_model(build_parts(), os.path.abspath(out), meta())
