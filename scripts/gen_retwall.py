# -*- coding: utf-8 -*-
"""擁壁（逆T式 RC擁壁 H=5.0m + 重力式擁壁 H=2.0m） 詳細度別サンプル
   延長 40m: 逆T式 30m (10mブロック×3) + 重力式 10m。背面盛土・前面地盤は参考。
   参考: 重力式擁壁一般図 (天端幅 0.4m、背面勾配 1:0.6、基礎材 t=200) と土木構造物標準設計の逆T式擁壁の一般的な寸法。実案件の展開図は使用していない。
"""
import sys, os, math
import numpy as np
from lodkit import *

A = Alignment([("S", 40.0)])          # 壁の軸 (x 方向)。前面 = -y 側, 背面 = +y 側
H = 5.0; T_STEM_TOP, T_STEM_BOT = 0.40, 0.50; T_BASE = 0.50; TOE, HEEL = 0.8, 2.6
Z_GL_FRONT = 0.0                        # 前面地盤高
Z_BASE = Z_GL_FRONT - 1.0               # 底版下面 (根入れ 1.0m ⇒ 底版上面 -0.5)
Z_TOP = Z_BASE + T_BASE + H             # 天端 = +4.5
X_G = 30.0                              # 重力式の起点
rng = np.random.default_rng(9)

def bw(x0, x1, y0, y1, z0, z1):
    """局所 y (前面0 / 背面+) で書いた直方体を世界座標 (局所 y+ = 世界 -y) に変換"""
    return box_world(x0, x1, -y1, -y0, z0, z1)

def stem_profile():
    """逆T式の断面 (y: 前面-/背面+, z)。底版 + たて壁"""
    return np.array([[-TOE, Z_BASE], [HEEL + T_STEM_BOT, Z_BASE], [HEEL + T_STEM_BOT, Z_BASE + T_BASE], [T_STEM_BOT, Z_BASE + T_BASE], [T_STEM_TOP, Z_TOP], [0.0, Z_TOP], [0.0, Z_BASE + T_BASE], [-TOE, Z_BASE + T_BASE]])
def stem_only(): return np.array([[0.0, Z_BASE + T_BASE], [T_STEM_BOT, Z_BASE + T_BASE], [T_STEM_TOP, Z_TOP], [0.0, Z_TOP]])
def base_only(): return np.array([[-TOE, Z_BASE], [HEEL + T_STEM_BOT, Z_BASE], [HEEL + T_STEM_BOT, Z_BASE + T_BASE], [-TOE, Z_BASE + T_BASE]])
def gravity_profile(h=2.0, top=0.4, n=0.6):
    zb = Z_GL_FRONT - 0.5
    return np.array([[0.0, zb], [top + n * h, zb], [top, zb + h], [0.0, zb + h]])

def build_parts():
    parts = []
    C = dict(terrain=(0.62, 0.70, 0.50), fill=(0.66, 0.62, 0.46), conc=(0.80, 0.80, 0.77), lean=(0.70, 0.70, 0.68), base=(0.62, 0.60, 0.55),
             gravel=(0.72, 0.70, 0.60), sym=(0.2, 0.6, 0.9, 0.4), box100=(0.3, 0.55, 0.95, 0.35), rebar=(0.70, 0.20, 0.15), pipe=(0.25, 0.45, 0.80),
             fence=(0.85, 0.85, 0.88), mat=(0.35, 0.60, 0.35), joint=(0.3, 0.3, 0.3))
    sts = stations(0, 30, 2.0)
    # 参考: 前面地盤・背面盛土
    parts.append(Part("前面地盤 (参考)", "地形", bw(-10, 50, -25, 0.0, Z_GL_FRONT - 3.0, Z_GL_FRONT), C["terrain"], 100, "参考表示"))
    def backfill(s):
        h = Z_TOP if s < 30 else Z_GL_FRONT - 0.5 + 2.0
        return np.array([[0.05, Z_GL_FRONT - 1.0], [14.0, Z_GL_FRONT - 1.0], [14.0, h + 1.5], [4.0, h], [0.05, h]])[::-1]
    parts.append(Part("背面盛土 (参考)", "土工", sweep(A, backfill, stations(0, 40, 2.0)), C["fill"], 100, "擁壁が支える背面の盛土 (参考表示)"))

    # ---------- LOD100 ----------
    parts.append(Part("擁壁法線 (前面線)", "線形", tube_along(np.array([[-1, 0, Z_TOP + 0.3], [41, 0, Z_TOP + 0.3]]), 0.12, 6), (0.9, 0.1, 0.1), 100, "擁壁の位置を示す線"))
    parts.append(Part("擁壁範囲ボックス", "概略形状", bw(-0.5, 40.5, -TOE - 0.3, HEEL + T_STEM_BOT + 0.3, Z_BASE - 0.3, Z_TOP + 0.3), C["box100"], 100, "位置・延長・高さが分かる直方体", lod_max=100))

    # ---------- LOD200: 断面スイープ (一体) ----------
    parts.append(Part("逆T式擁壁 (断面一体スイープ) L=30m", "本体", sweep(A, lambda s: stem_profile()[::-1], sts), C["conc"], 200, "一般図の標準断面をスイープした形状", lod_max=200))
    parts.append(Part("重力式擁壁 (断面一体スイープ) L=10m", "本体", sweep(A, lambda s: gravity_profile()[::-1], stations(30, 40, 2.0)), C["conc"], 200, "", lod_max=200))

    # ---------- LOD300: たて壁・底版を分離、基礎、目地・水抜き孔記号 ----------
    for b in range(3):
        xa, xb = 10 * b, 10 * (b + 1) - 0.02
        parts.append(Part(f"逆T式 たて壁 (H=5.0m, t=0.4〜0.5m, ブロック{b+1})", "本体", extrude(A, stem_only()[::-1], xa, xb - xa), C["conc"], 300, "たて壁 (前面鉛直・背面勾配)"))
        parts.append(Part(f"逆T式 底版 (B=3.9m, t=0.5m, ブロック{b+1})", "本体", extrude(A, base_only()[::-1], xa, xb - xa), C["conc"], 300, "底版 (つま先 0.8m / かかと 2.6m)"))
    parts.append(Part("重力式擁壁 (H=2.0m, 天端0.4m, 背面1:0.6) L=10m", "本体", extrude(A, gravity_profile()[::-1], X_G, 10.0), C["conc"], 300, "重力式擁壁の外形"))
    parts.append(Part("均しコンクリート t=10cm", "基礎", bw(-0.1, 30.1, -TOE - 0.1, HEEL + T_STEM_BOT + 0.1, Z_BASE - 0.1, Z_BASE), C["lean"], 300, "均しコンクリート"))
    parts.append(Part("基礎砕石 t=20cm", "基礎", bw(-0.3, 30.3, -TOE - 0.3, HEEL + T_STEM_BOT + 0.3, Z_BASE - 0.3, Z_BASE - 0.1), C["base"], 300, "基礎砕石"))
    parts.append(Part("重力式 基礎材 t=20cm", "基礎", bw(X_G - 0.1, 40.1, -0.1, 0.4 + 0.6 * 2.0 + 0.1, Z_GL_FRONT - 0.7, Z_GL_FRONT - 0.5), C["base"], 300, "基礎材 (RC-40)"))
    for b in (1, 2):
        parts.append(Part(f"目地位置記号 (No.{10*b})", "記号", bw(10 * b - 0.04, 10 * b + 0.04, -TOE - 0.2, HEEL + T_STEM_BOT + 0.2, Z_BASE - 0.2, Z_TOP + 0.2), C["sym"], 300, "目地の位置 (記号)。詳細度400で目地材・止水板", lod_max=300))
    parts.append(Part("目地位置記号 (No.30 逆T式/重力式 境界)", "記号", bw(30 - 0.04, 30 + 0.04, -TOE - 0.2, HEEL + T_STEM_BOT + 0.2, Z_BASE - 0.2, Z_TOP + 0.2), C["sym"], 300, "", lod_max=300))
    m = Mesh()
    for x in np.arange(1.0, 30.0, 2.0):
        for k, z in enumerate((Z_GL_FRONT + 0.5, Z_GL_FRONT + 2.5)):
            m.add(bw(x + (1.0 if k else 0.0) - 0.15, x + (1.0 if k else 0.0) + 0.15, -0.3, 0.05, z - 0.15, z + 0.15))
    parts.append(Part("水抜き孔 位置記号 (φ75 @2m 千鳥)", "記号", m, C["sym"], 300, "水抜き孔の配置をパターン化した記号", lod_max=300))
    parts.append(Part("裏込め材 範囲記号", "記号", sweep(A, lambda s: np.array([[T_STEM_BOT + 0.02, Z_BASE + T_BASE], [T_STEM_BOT + 0.6, Z_BASE + T_BASE], [T_STEM_TOP + 0.6, Z_TOP - 0.3], [T_STEM_TOP + 0.02, Z_TOP - 0.3]])[::-1], sts), (0.72, 0.70, 0.60, 0.4), 300, "裏込め砕石の範囲 (記号)。詳細度400で実体", lod_max=300))

    # ---------- LOD400: 配筋、水抜き孔、目地材・止水板、裏込め、透水マット、防護柵 ----------
    m = Mesh(); n = 0
    for b in range(3):
        xa, xb = 10 * b + 0.05, 10 * (b + 1) - 0.07
        for x in np.arange(xa + 0.1, xb, 0.25):   # たて壁 主筋 D19@250 (背面側=引張側) + 前面側 D13@250, 底版主筋
            m.add(tube_along(np.array([[x, -(T_STEM_BOT - 0.08), Z_BASE + 0.08], [x, -(T_STEM_TOP - 0.08), Z_TOP - 0.08]]), 0.0095, 4)); n += 1
            m.add(tube_along(np.array([[x, -0.08, Z_BASE + T_BASE + 0.05], [x, -0.08, Z_TOP - 0.08]]), 0.0065, 4)); n += 1
            for z in (Z_BASE + 0.08, Z_BASE + T_BASE - 0.08):
                m.add(tube_along(np.array([[x, TOE - 0.08, z], [x, -(HEEL + T_STEM_BOT - 0.08), z]]), 0.0095, 4)); n += 1
        for z in np.arange(Z_BASE + T_BASE + 0.2, Z_TOP, 0.3):   # 配力筋 D13@300
            for yy in (0.1, None):
                y_back = T_STEM_BOT - 0.1 + (T_STEM_TOP - T_STEM_BOT) * (z - Z_BASE - T_BASE) / H
                m.add(tube_along(np.array([[xa, -(yy if yy is not None else y_back), z], [xb, -(yy if yy is not None else y_back), z]]), 0.0065, 4)); n += 1
        for yy in np.arange(-TOE + 0.2, HEEL + T_STEM_BOT, 0.3):
            for z in (Z_BASE + 0.1, Z_BASE + T_BASE - 0.1):
                m.add(tube_along(np.array([[xa, -yy, z], [xb, -yy, z]]), 0.0065, 4)); n += 1
    parts.append(Part(f"配筋 (たて壁 D19@250 / 底版 D19@250 / 配力 D13@300, {n}本)", "配筋", m, C["rebar"], 400, "逆T式擁壁の配筋"))
    m = Mesh(); n = 0
    for x in np.arange(1.0, 30.0, 2.0):
        for k, z in enumerate((Z_GL_FRONT + 0.5, Z_GL_FRONT + 2.5)):
            xx = x + (1.0 if k else 0.0); yb = T_STEM_BOT + (T_STEM_TOP - T_STEM_BOT) * (z - Z_BASE - T_BASE) / H
            m.add(cylinder([xx, 0.05, z], [xx, -(yb + 0.1), z + 0.05], 0.0375, 8)); n += 1
    parts.append(Part(f"水抜き孔 φ75 ({n}箇所, 千鳥 @2m)", "排水工", m, C["pipe"], 400, "水抜き孔の実形状"))
    parts.append(Part("裏込め砕石 (幅0.6m)", "裏込め", sweep(A, lambda s: np.array([[T_STEM_BOT + 0.02, Z_BASE + T_BASE], [T_STEM_BOT + 0.6, Z_BASE + T_BASE], [T_STEM_TOP + 0.6, Z_TOP - 0.3], [T_STEM_TOP + 0.02, Z_TOP - 0.3]])[::-1], sts), C["gravel"], 400, "裏込め材の実体"))
    parts.append(Part("透水マット (背面)", "裏込め", sweep(A, lambda s: np.array([[T_STEM_BOT, Z_BASE + T_BASE], [T_STEM_BOT + 0.02, Z_BASE + T_BASE], [T_STEM_TOP + 0.02, Z_TOP - 0.3], [T_STEM_TOP, Z_TOP - 0.3]])[::-1], sts), C["mat"], 400, "壁背面の透水マット"))
    parts.append(Part("裏込め排水管 φ100 (底版上 背面)", "排水工", tube_along(np.array([[0, -(T_STEM_BOT + 0.15), Z_BASE + T_BASE + 0.08], [30, -(T_STEM_BOT + 0.15), Z_BASE + T_BASE + 0.08]]), 0.05, 8), C["pipe"], 400, "裏面排水管"))
    for x in (10, 20, 30):
        parts.append(Part(f"目地材 t=20mm・止水板 (No.{x})", "目地", Mesh().add(bw(x - 0.01, x + 0.01, -TOE, HEEL + T_STEM_BOT, Z_BASE, Z_TOP)).add(bw(x - 0.1, x + 0.1, T_STEM_BOT / 2 - 0.02, T_STEM_BOT / 2 + 0.02, Z_BASE + 0.1, Z_TOP - 0.1)), C["joint"], 400, "目地材と止水板"))
    m = Mesh(); n = 0
    for x in np.arange(0.5, 30.0, 2.0):
        m.add(cylinder([x, -0.2, Z_TOP], [x, -0.2, Z_TOP + 1.1], 0.05, 6)); n += 1
    for z in (Z_TOP + 0.6, Z_TOP + 1.05): m.add(tube_along(np.array([[0, -0.2, z], [30, -0.2, z]]), 0.03, 6))
    parts.append(Part(f"天端 防護柵 (支柱{n}本)", "附属物", m, C["fence"], 400, "天端の転落防止柵"))

    # ---------- LOD500 ----------
    parts.append(Part("壁面 出来形 (実測: 天端の通り・倒れ, 記号)", "出来形", sweep(A, lambda s: np.array([[-0.03 + 0.01 * math.sin(s), Z_BASE + T_BASE], [0.0, Z_BASE + T_BASE], [0.0, Z_TOP], [-0.03 + 0.01 * math.sin(s), Z_TOP]])[::-1], sts), (0.55, 0.5, 0.4, 0.6), 500, "出来形計測結果の反映 (サンプルでは記号)"))
    parts.append(Part("天端コンクリート仕上げ・境界標 (完成)", "完成設備", Mesh().add(*[bw(x - 0.05, x + 0.05, -0.05, 0.05, Z_TOP, Z_TOP + 0.15) for x in (0.3, 10, 20, 29.7)][:1]) if False else _bp(), (0.9, 0.9, 0.85), 500, "完成時の境界標"))
    return parts

def _bp():
    m = Mesh()
    for x in (0.3, 10, 20, 29.7, 39.7): m.add(bw(x - 0.05, x + 0.05, -0.05, 0.05, Z_TOP if x < 30 else Z_GL_FRONT + 1.5, (Z_TOP if x < 30 else Z_GL_FRONT + 1.5) + 0.15))
    return m

def meta():
    return dict(
        id="retwall", name="擁壁（逆T式 H=5m + 重力式 H=2m）", category="擁壁",
        description="逆T式RC擁壁 (H=5.0m, 底版幅3.9m) 30m (10mブロック×3) と重力式擁壁 (H=2.0m, 天端0.4m, 背面1:0.6) 10m。基礎、目地・止水板、水抜き孔、裏込め・透水マット、配筋、天端防護柵を含む。",
        ref="重力式擁壁一般図の一般的な寸法 (天端幅・背面勾配・基礎材) と土木構造物標準設計の逆T式擁壁を参考にした架空断面。実案件の展開図は使用していない。",
        alignment=A, center=[20.0, -1.0, 2.0], ground={"cx": 20, "cy": -2, "z": -3.0, "size": 250},
        views=[{"name": "全景", "pos": [-22, 32, 16], "target": [20, -1, 1.5]}, {"name": "前面", "pos": [15, 14, 3], "target": [15, 0, 2]},
               {"name": "背面", "pos": [15, -14, 9], "target": [15, -2, 2]}, {"name": "断面", "pos": None, "target": None, "clip": 15}],
        lod_def={100: ["擁壁の位置・延長を法線と直方体で示す。"],
                 200: ["一般図の標準断面を延長方向にスイープした一体形状。"],
                 300: ["たて壁・底版 (逆T式)、重力式の外形、基礎 (均しコン・砕石) が正確。目地・水抜き孔・裏込め材は位置・範囲を記号で示す。"],
                 400: ["詳細度300に加えて配筋、水抜き孔、目地材・止水板、裏込め砕石・透水マット・裏面排水管、天端防護柵などの細部をモデル化。"],
                 500: ["完成形状 (出来形計測の反映、境界標などの完成設備)。"]},
        notes=["背面盛土・前面地盤は参考表示。", "重力式擁壁は目地なしの 1 ブロックとして作成。"],
    )

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "site")
    export_model(build_parts(), os.path.abspath(out), meta())
