# -*- coding: utf-8 -*-
"""PC橋（ポストテンションT桁 2径間） 詳細度別サンプル
   橋長 61m (支間 30m×2)、幅員 10.0m、主桁 5本 @2.0m (桁高 1.9m)、逆T式橋台 2基、壁式橋脚 1基、場所打ち杭 φ1.0m。
   参考: 道路橋示方書・PC標準設計の一般的な寸法。実案件の橋梁一般図 (DWG) は読取不可のため寸法は使用していない。
"""
import sys, os, math
import numpy as np
from lodkit import *

A = Alignment([("S", 100.0)], origin=(-20.0, 0.0))     # 起点側取付部 -20m 〜 橋台A1 (x=0) 〜 A2 (x=61) 〜 終点側取付部 (x=80)
BL = 61.0; SPAN = 30.0; X_A1, X_P1, X_A2 = 0.0, 30.5, 61.0
W = 10.0; W_CURB = 0.75; N_G = 5; G_PITCH = 2.0; H_G = 1.9
Z_DECK = 0.0                     # 路面高 (地覆天端は +0.25)
T_PAV = 0.08; T_SLAB = 0.22      # 舗装 / 床版 (間詰め含む上フランジ厚相当)
Z_GTOP = Z_DECK - T_PAV          # 桁上面
Z_GBOT = Z_GTOP - H_G            # 桁下面
Z_BRG = Z_GBOT - 0.10            # 支承下面 = 沓座
rng = np.random.default_rng(7)

def ground(x, y):   # 河川を横断する架空地形: 中央 (x≈30.5) が河床、両岸が高い
    return -3.0 - 5.0 * math.exp(-((x - 30.5) / 13.0) ** 2) + 0.4 * math.sin(x / 9.0) * math.cos(y / 11.0) + 0.6 * max(0.0, abs(y) - 25) * 0.05

def t_girder(hg=H_G, bf=1.9, tf=0.22, bw=0.22, bb=0.65, hb=0.45):
    """T桁断面 (y:横, z:上が0)。上フランジ幅 bf, ウェブ厚 bw, 下フランジ bb×hb"""
    return np.array([[-bf / 2, 0], [bf / 2, 0], [bf / 2, -tf], [bw / 2, -tf - 0.15], [bw / 2, -hg + hb + 0.15], [bb / 2, -hg + hb], [bb / 2, -hg],
                     [-bb / 2, -hg], [-bb / 2, -hg + hb], [-bw / 2, -hg + hb + 0.15], [-bw / 2, -tf - 0.15], [-bf / 2, -tf]])

def rect(y0, y1, z0, z1): return np.array([[y0, z0], [y1, z0], [y1, z1], [y0, z1]])

def build_parts():
    parts = []
    C = dict(terrain=(0.62, 0.70, 0.50), water=(0.35, 0.55, 0.80, 0.6), girder=(0.85, 0.85, 0.82), slab=(0.80, 0.80, 0.78), pav=(0.28, 0.28, 0.30),
             curb=(0.75, 0.75, 0.72), rail=(0.55, 0.60, 0.66), sub=(0.78, 0.78, 0.74), pile=(0.68, 0.66, 0.60), brg=(0.25, 0.25, 0.28),
             pc=(0.95, 0.55, 0.10), rebar=(0.70, 0.20, 0.15), exp=(0.40, 0.42, 0.45), drain=(0.20, 0.45, 0.80), fill=(0.66, 0.62, 0.46),
             sym=(0.2, 0.6, 0.9, 0.35), box100=(0.3, 0.55, 0.95, 0.35), marker=(0.95, 0.2, 0.2, 0.7), light=(0.85, 0.85, 0.9))
    # 地形 (参考) + 水面
    xs = np.arange(-40, 120, 2.0); ys = np.arange(-60, 60, 2.0)
    parts.append(Part("現況地形 (参考)", "地形", surface_mesh(xs, ys, ground), C["terrain"], 100, "地形は詳細度の対象外"))
    parts.append(Part("水面 (参考)", "地形", box_world(17, 44, -60, 60, -7.6, -7.4), C["water"], 100, "河川の水面 (参考)"))
    # 取付部盛土 (参考: 土工モデル側で扱う想定)
    for x0, x1, nm in ((-20.0, -0.5, "起点側"), (61.5, 80.0, "終点側")):
        def fsec(s, x0=x0):
            return np.array([[-W / 2, Z_DECK - 0.1], [W / 2, Z_DECK - 0.1], [W / 2 + 12, Z_DECK - 8.1], [-W / 2 - 12, Z_DECK - 8.1]])[::-1]
        parts.append(Part(f"取付部盛土 ({nm}, 参考)", "土工", sweep(A, fsec, stations(x0 + 20, x1 + 20, 2.0)), C["fill"], 200, "橋梁前後の取付道路 (参考)"))

    # ---------- LOD100 ----------
    parts.append(Part("橋梁位置 (中心線)", "線形", tube_along(np.array([[X_A1 - 5, 0, Z_DECK + 0.3], [X_A2 + 5, 0, Z_DECK + 0.3]]), 0.15, 6), (0.9, 0.1, 0.1), 100, "橋梁の位置を示す線"))
    parts.append(Part("橋梁範囲ボックス", "概略形状", box_world(X_A1 - 1, X_A2 + 1, -W / 2 - 0.5, W / 2 + 0.5, Z_BRG - 1, Z_DECK + 1.2), C["box100"], 100, "橋梁の範囲が分かる程度の直方体", lod_max=100))
    for x, nm in ((X_A1, "A1"), (X_P1, "P1"), (X_A2, "A2")):
        parts.append(Part(f"下部工位置マーカー {nm}", "概略形状", cylinder([x, 0, ground(x, 0) - 2], [x, 0, Z_BRG], 0.4, 10), C["marker"], 100, "下部工の位置", lod_max=100))

    # ---------- LOD200: 構造形式が分かる程度 (桁橋であること・橋台/橋脚の位置と概形・高欄の有無) ----------
    ys_g200 = [(i - (N_G - 1) / 2) * G_PITCH for i in range(N_G)]
    parts.append(Part("床版・舗装 (概形, 一体)", "上部工", box_world(X_A1 - 0.4, X_A2 + 0.4, -W / 2, W / 2, Z_GTOP - 0.22, Z_DECK), C["slab"], 200, "床版と舗装を一体化した板", lod_max=200))
    m = Mesh()
    for yg in ys_g200: m.add(box_world(X_A1 + 0.3, X_A2 - 0.3, yg - 0.35, yg + 0.35, Z_GBOT, Z_GTOP - 0.22))
    parts.append(Part("主桁 (概形, 矩形断面 ×5)", "上部工", m, C["girder"], 200, "T桁を矩形の梁として表現 (本数・桁高が分かる程度)", lod_max=200))
    m = Mesh()
    for xc in (X_A1 + 0.5, X_P1 - 0.5, X_P1 + 0.5, X_A2 - 0.5): m.add(box_world(xc - 0.15, xc + 0.15, ys_g200[0], ys_g200[-1], Z_GBOT + 0.3, Z_GTOP - 0.22))
    parts.append(Part("横桁 (概形, 端横桁のみ)", "上部工", m, C["slab"], 200, "", lod_max=200))
    for sg, nm in ((-1, "左"), (1, "右")):
        y0, y1 = sorted((sg * (W / 2), sg * (W / 2 - W_CURB)))
        parts.append(Part(f"地覆 (概形, {nm})", "上部工", box_world(X_A1 - 0.4, X_A2 + 0.4, y0, y1, Z_DECK, Z_DECK + 0.25), C["curb"], 200, "", lod_max=200))
        m = Mesh()
        for x in np.arange(X_A1, X_A2 + 0.1, 4.0): m.add(box_world(x - 0.05, x + 0.05, sg * (W / 2 - 0.35) - 0.05, sg * (W / 2 - 0.35) + 0.05, Z_DECK + 0.25, Z_DECK + 1.3))
        m.add(box_world(X_A1 - 0.4, X_A2 + 0.4, sg * (W / 2 - 0.35) - 0.04, sg * (W / 2 - 0.35) + 0.04, Z_DECK + 1.2, Z_DECK + 1.3))
        parts.append(Part(f"高欄 (概形, {nm})", "附属物", m, C["rail"], 200, "高欄の有無と高さが分かる程度 (支柱@4m + 上段ビーム)", lod_max=200))
    for x, nm, back in ((X_A1, "A1", -1), (X_A2, "A2", +1)):
        zf = ground(x, 0) - 1.5
        parts.append(Part(f"橋台 {nm} (概形: たて壁+胸壁)", "下部工", box_world(x - 1.0, x + 1.0, -W / 2 - 0.3, W / 2 + 0.3, zf + 1.5, Z_DECK), C["sub"], 200, "橋台の概形", lod_max=200))
        parts.append(Part(f"橋台 {nm} フーチング (概形)", "下部工", box_world(x - 3.0, x + 3.0, -W / 2 - 0.5, W / 2 + 0.5, zf, zf + 1.5), C["sub"], 200, "", lod_max=200))
    zf = ground(X_P1, 0) - 1.5
    parts.append(Part("橋脚 P1 (概形: 柱+梁)", "下部工", Mesh().add(box_world(X_P1 - 1.0, X_P1 + 1.0, -4.0, 4.0, zf + 2.0, Z_BRG - 1.2)).add(box_world(X_P1 - 1.2, X_P1 + 1.2, -W / 2 - 0.2, W / 2 + 0.2, Z_BRG - 1.2, Z_GBOT)), C["sub"], 200, "壁式橋脚の概形", lod_max=200))
    parts.append(Part("橋脚 P1 フーチング (概形)", "下部工", box_world(X_P1 - 3.5, X_P1 + 3.5, -5.5, 5.5, zf, zf + 2.0), C["sub"], 200, "", lod_max=200))
    parts.append(Part("基礎 (概形: 杭範囲の直方体)", "基礎", Mesh().add(box_world(X_A1 - 2.3, X_A1 + 2.3, -4.1, 4.1, ground(X_A1, 0) - 16.5, ground(X_A1, 0) - 1.5)).add(box_world(X_A2 - 2.3, X_A2 + 2.3, -4.1, 4.1, ground(X_A2, 0) - 16.5, ground(X_A2, 0) - 1.5)).add(box_world(X_P1 - 2.5, X_P1 + 2.5, -4.5, 4.5, zf - 15.0, zf)), (0.68, 0.66, 0.60, 0.4), 200, "杭基礎の範囲を半透明の直方体で表示", lod_max=200))

    # ---------- LOD300: 外形が正確 ----------
    ys_g = [(i - (N_G - 1) / 2) * G_PITCH for i in range(N_G)]
    for span, (xa, xb) in enumerate(((X_A1 + 0.45, X_P1 - 0.45), (X_P1 + 0.45, X_A2 - 0.45)), 1):
        for gi, yg in enumerate(ys_g, 1):
            prof = t_girder(); prof[:, 0] += yg; prof[:, 1] += Z_GTOP
            parts.append(Part(f"主桁 G{gi} (PC T桁 H=1.9m, 第{span}径間)", "上部工", extrude(A, prof[::-1], xa + 20, xb - xa), C["girder"], 300, "主桁の外形 (ポステンT桁)"))
        # 横桁 (端部2 + 中間3)
        for k, xc in enumerate(np.linspace(xa + 0.5, xb - 0.5, 5)):
            parts.append(Part(f"横桁 {'端' if k in (0, 4) else '中間'} (第{span}径間 No.{k+1})", "上部工", box_world(xc - 0.15, xc + 0.15, ys_g[0] + 0.1, ys_g[-1] - 0.1, Z_GBOT + 0.3, Z_GTOP - 0.22), C["slab"], 300, "横桁"))
        # 間詰め (主桁上フランジ間) と 床版一体
        parts.append(Part(f"間詰めコンクリート・床版 (第{span}径間)", "上部工", box_world(xa, xb, -W / 2 + W_CURB, W / 2 - W_CURB, Z_GTOP - 0.22, Z_GTOP), C["slab"], 300, "上フランジ間の間詰めと床版"))
    parts.append(Part("舗装 (アスファルト t=8cm)", "上部工", box_world(X_A1 - 0.4, X_A2 + 0.4, -W / 2 + W_CURB, W / 2 - W_CURB, Z_GTOP, Z_DECK), C["pav"], 300, "橋面舗装"))
    for sg, nm in ((-1, "左"), (1, "右")):
        y0, y1 = sorted((sg * (W / 2), sg * (W / 2 - W_CURB)))
        parts.append(Part(f"地覆 ({nm})", "上部工", box_world(X_A1 - 0.4, X_A2 + 0.4, y0, y1, Z_GTOP - 0.22, Z_DECK + 0.25), C["curb"], 300, "地覆"))
        # 高欄 (支柱 + ビーム 2段)
        m = Mesh(); cnt = 0
        for x in np.arange(X_A1, X_A2 + 0.1, 2.0):
            m.add(box_world(x - 0.06, x + 0.06, sg * (W / 2 - 0.35) - 0.06, sg * (W / 2 - 0.35) + 0.06, Z_DECK + 0.25, Z_DECK + 1.35)); cnt += 1
        for zr in (Z_DECK + 0.75, Z_DECK + 1.3):
            m.add(box_world(X_A1 - 0.4, X_A2 + 0.4, sg * (W / 2 - 0.35) - 0.05, sg * (W / 2 - 0.35) + 0.05, zr - 0.06, zr + 0.06))
        parts.append(Part(f"高欄 ({nm}, 支柱{cnt}本)", "附属物", m, C["rail"], 300, "高欄 (車両用防護柵)"))
    # 下部工: 逆T式橋台 (たて壁 + 胸壁 + フーチング + ウイング) / 壁式橋脚 (柱 + 梁 + フーチング) / 杭
    for x, nm, back in ((X_A1, "A1", -1), (X_A2, "A2", +1)):
        zf = ground(x, 0) - 1.5   # フーチング下面
        parts.append(Part(f"橋台 {nm} フーチング", "下部工", box_world(x - 3.0, x + 3.0, -W / 2 - 0.5, W / 2 + 0.5, zf, zf + 1.5), C["sub"], 300, "逆T式橋台のフーチング"))
        parts.append(Part(f"橋台 {nm} たて壁", "下部工", box_world(x - 0.9 if back < 0 else x - 0.9, x + 0.9, -W / 2 - 0.3, W / 2 + 0.3, zf + 1.5, Z_BRG), C["sub"], 300, "たて壁 (沓座まで)"))
        xb0, xb1 = (x - 0.9, x - 0.4) if back < 0 else (x + 0.4, x + 0.9)
        parts.append(Part(f"橋台 {nm} 胸壁 (パラペット)", "下部工", box_world(xb0, xb1, -W / 2 - 0.3, W / 2 + 0.3, Z_BRG, Z_DECK), C["sub"], 300, "胸壁"))
        for sg in (-1, 1):
            xw0, xw1 = (x - 5.0, x - 0.9) if back < 0 else (x + 0.9, x + 5.0)
            parts.append(Part(f"橋台 {nm} ウイング ({'左' if sg < 0 else '右'})", "下部工", box_world(xw0, xw1, sg * (W / 2 + 0.3) - 0.25, sg * (W / 2 + 0.3) + 0.25, zf + 1.5, Z_DECK - 0.3), C["sub"], 300, "ウイング (簡略)"))
        m = Mesh(); n = 0
        for xp in (x - 1.8, x + 1.8):
            for yp in np.linspace(-3.6, 3.6, 4):
                m.add(cylinder([xp, yp, zf - 15.0], [xp, yp, zf + 0.1], 0.5, 10)); n += 1
        parts.append(Part(f"橋台 {nm} 場所打ち杭 φ1.0m L=15m ({n}本)", "基礎", m, C["pile"], 300, "杭基礎"))
    zf = ground(X_P1, 0) - 1.5
    parts.append(Part("橋脚 P1 フーチング", "下部工", box_world(X_P1 - 3.5, X_P1 + 3.5, -5.5, 5.5, zf, zf + 2.0), C["sub"], 300, "橋脚フーチング"))
    parts.append(Part("橋脚 P1 躯体 (壁式)", "下部工", box_world(X_P1 - 1.0, X_P1 + 1.0, -4.0, 4.0, zf + 2.0, Z_BRG - 1.2), C["sub"], 300, "壁式橋脚"))
    parts.append(Part("橋脚 P1 梁 (張出し)", "下部工", box_world(X_P1 - 1.2, X_P1 + 1.2, -W / 2 - 0.2, W / 2 + 0.2, Z_BRG - 1.2, Z_BRG), C["sub"], 300, "橋座部"))
    m = Mesh(); n = 0
    for xp in (X_P1 - 2.0, X_P1 + 2.0):
        for yp in np.linspace(-4.0, 4.0, 5):
            m.add(cylinder([xp, yp, zf - 15.0], [xp, yp, zf + 0.1], 0.5, 10)); n += 1
    parts.append(Part(f"橋脚 P1 場所打ち杭 φ1.0m L=15m ({n}本)", "基礎", m, C["pile"], 300, "杭基礎"))
    # 支承位置 (LOD300 は記号: 半透明ブロック) / 伸縮装置位置記号
    m = Mesh()
    for x in (X_A1 + 0.45, X_P1 - 0.45, X_P1 + 0.45, X_A2 - 0.45):
        for yg in ys_g: m.add(box_world(x - 0.35, x + 0.35, yg - 0.35, yg + 0.35, Z_BRG - 0.05, Z_GBOT + 0.05))
    parts.append(Part("支承位置記号 (ゴム支承 ×20)", "記号", m, C["sym"], 300, "支承の位置を記号で表示。詳細度400で実形状", lod_max=300))
    for x in (X_A1, X_A2):
        parts.append(Part(f"伸縮装置位置記号 ({'A1' if x == X_A1 else 'A2'})", "記号", box_world(x - 0.3, x + 0.3, -W / 2 + W_CURB, W / 2 - W_CURB, Z_DECK - 0.02, Z_DECK + 0.2), C["sym"], 300, "伸縮装置の位置を記号で表示", lod_max=300))
    # 排水
    m = Mesh()
    for x in np.arange(X_A1 + 5, X_A2, 10.0):
        for sg in (-1, 1):
            m.add(cylinder([x, sg * (W / 2 - W_CURB - 0.2), Z_GTOP], [x, sg * (W / 2 - W_CURB - 0.2), Z_GBOT - 0.5], 0.08, 8))
    parts.append(Part("排水管 φ150 (橋面排水)", "排水工", m, C["drain"], 300, "橋面排水管"))

    # ---------- LOD400: 細部・配筋・PC鋼材 ----------
    # PC鋼材: 各主桁 3ケーブル、放物線 (支点で上、支間中央で下)
    m = Mesh(); n = 0
    for xa, xb in ((X_A1 + 0.45, X_P1 - 0.45), (X_P1 + 0.45, X_A2 - 0.45)):
        for yg in ys_g:
            for k, (za, zm) in enumerate(((Z_GTOP - 0.45, Z_GBOT + 0.2), (Z_GTOP - 0.7, Z_GBOT + 0.3), (Z_GTOP - 0.95, Z_GBOT + 0.4))):
                xs_ = np.linspace(xa, xb, 25); t = (xs_ - xa) / (xb - xa)
                zs_ = za + (zm - za) * (1 - (2 * t - 1) ** 2)
                m.add(tube_along(np.column_stack([xs_, np.full_like(xs_, yg + (k - 1) * 0.05), zs_]), 0.035, 5)); n += 1
    parts.append(Part(f"PC鋼材 (12S12.7 ×{n}本, 放物線配置)", "PC鋼材", m, C["pc"], 400, "内ケーブルの配置"))
    # 床版鉄筋 (上下2段: 横方向 D16@200, 橋軸方向 D13@250)
    m = Mesh(); n = 0
    for xa, xb in ((X_A1 + 0.45, X_P1 - 0.45), (X_P1 + 0.45, X_A2 - 0.45)):
        for zr in (Z_GTOP - 0.05, Z_GTOP - 0.17):
            for x in np.arange(xa + 0.1, xb, 0.2):
                m.add(tube_along(np.array([[x, -W / 2 + W_CURB + 0.05, zr], [x, W / 2 - W_CURB - 0.05, zr]]), 0.008, 4)); n += 1
            for y in np.arange(-W / 2 + W_CURB + 0.1, W / 2 - W_CURB, 0.25):
                m.add(tube_along(np.array([[xa + 0.05, y, zr - 0.012], [xb - 0.05, y, zr - 0.012]]), 0.0065, 4)); n += 1
    parts.append(Part(f"床版鉄筋 (D16@200 / D13@250, 上下2段, {n}本)", "配筋", m, C["rebar"], 400, "床版・間詰め部の配筋"))
    # 橋台配筋 (A1 のみ代表: たて壁 主筋 D22@250 前後面 + 配力 D16@300)
    m = Mesh(); n = 0
    x = X_A1; zf = ground(x, 0) - 1.5
    for xr in (x - 0.8, x + 0.8):
        for y in np.arange(-W / 2 - 0.2, W / 2 + 0.2, 0.25):
            m.add(tube_along(np.array([[xr, y, zf + 0.1], [xr, y, Z_DECK - 0.1]]), 0.011, 4)); n += 1
        for z in np.arange(zf + 1.6, Z_DECK, 0.3):
            m.add(tube_along(np.array([[xr, -W / 2 - 0.25, z], [xr, W / 2 + 0.25, z]]), 0.008, 4)); n += 1
    for zr in (zf + 0.1, zf + 1.4):
        for y in np.arange(-W / 2 - 0.4, W / 2 + 0.4, 0.25):
            m.add(tube_along(np.array([[x - 2.9, y, zr], [x + 2.9, y, zr]]), 0.011, 4)); n += 1
    parts.append(Part(f"橋台 A1 配筋 (たて壁 D22@250, フーチング D22@250, {n}本)", "配筋", m, C["rebar"], 400, "下部工の配筋 (A1 を代表)"))
    # 支承 (ゴム支承: 沓座モルタル + ゴム + ソールプレート)
    m = Mesh()
    for x in (X_A1 + 0.45, X_P1 - 0.45, X_P1 + 0.45, X_A2 - 0.45):
        for yg in ys_g:
            m.add(box_world(x - 0.3, x + 0.3, yg - 0.3, yg + 0.3, Z_BRG, Z_BRG + 0.03)); m.add(box_world(x - 0.22, x + 0.22, yg - 0.22, yg + 0.22, Z_BRG + 0.03, Z_GBOT - 0.02)); m.add(box_world(x - 0.3, x + 0.3, yg - 0.3, yg + 0.3, Z_GBOT - 0.02, Z_GBOT))
    parts.append(Part("ゴム支承 (×20)", "支承", m, C["brg"], 400, "支承の実形状"))
    # 伸縮装置 (鋼製フィンガー簡略)
    for x in (X_A1, X_A2):
        parts.append(Part(f"伸縮装置 ({'A1' if x == X_A1 else 'A2'})", "附属物", box_world(x - 0.25, x + 0.25, -W / 2 + W_CURB, W / 2 - W_CURB, Z_DECK - 0.12, Z_DECK), C["exp"], 400, "伸縮装置"))
    # 落橋防止 (アンカーバー) / 排水桝
    m = Mesh()
    for x in (X_A1 + 0.9, X_A2 - 0.9):
        for yg in ys_g: m.add(cylinder([x, yg, Z_BRG - 0.6], [x, yg, Z_GBOT + 0.5], 0.05, 6))
    parts.append(Part("落橋防止構造 (アンカーバー ×10)", "附属物", m, (0.4, 0.4, 0.45), 400, "落橋防止装置"))
    m = Mesh()
    for x in np.arange(X_A1 + 5, X_A2, 10.0):
        for sg in (-1, 1): m.add(box_world(x - 0.2, x + 0.2, sg * (W / 2 - W_CURB - 0.2) - 0.2, sg * (W / 2 - W_CURB - 0.2) + 0.2, Z_GTOP - 0.05, Z_DECK + 0.01))
    parts.append(Part("排水桝", "排水工", m, C["exp"], 400, "排水桝"))

    # ---------- LOD500: 完成形状 ----------
    parts.append(Part("路面標示 (中央線・外側線)", "完成設備", Mesh().add(box_world(X_A1 - 0.4, X_A2 + 0.4, -0.075, 0.075, Z_DECK, Z_DECK + 0.006)).add(box_world(X_A1 - 0.4, X_A2 + 0.4, -W / 2 + W_CURB + 0.6, -W / 2 + W_CURB + 0.75, Z_DECK, Z_DECK + 0.006)).add(box_world(X_A1 - 0.4, X_A2 + 0.4, W / 2 - W_CURB - 0.75, W / 2 - W_CURB - 0.6, Z_DECK, Z_DECK + 0.006)), (0.95, 0.95, 0.9), 500, "完成時の区画線"))
    m = Mesh()
    for x in (X_A1 + 15, X_A2 - 15):
        m.add(cylinder([x, W / 2 - 0.35, Z_DECK + 0.25], [x, W / 2 - 0.35, Z_DECK + 8.0], 0.1, 8)); m.add(box_world(x - 0.3, x + 1.5, W / 2 - 0.55, W / 2 - 0.15, Z_DECK + 7.8, Z_DECK + 8.0))
    parts.append(Part("照明柱 (2基)", "完成設備", m, C["light"], 500, "完成時の附属設備"))
    parts.append(Part("桁のキャンバー出来形 (主桁上面の実測値, 記号)", "出来形", box_world(X_A1, X_A2, -W / 2 + W_CURB, W / 2 - W_CURB, Z_GTOP + 0.0, Z_GTOP + 0.01), (0.55, 0.5, 0.4, 0.5), 500, "出来形計測結果を反映する面 (サンプルでは記号)"))
    return parts

def meta():
    return dict(
        id="pcbridge", name="PC橋（ポステンT桁 2径間）", category="橋梁",
        description="橋長61m (支間30m×2)、幅員10.0m。PC T桁5本、逆T式橋台2基、壁式橋脚1基、場所打ち杭。支承・伸縮装置・高欄・排水、PC鋼材・配筋を含む。",
        ref="道路橋示方書・PC標準設計の一般的な寸法による架空橋。実案件の橋梁一般図は使用していない。",
        alignment=A, center=[30.5, 0.0, -2.0], ground={"cx": 30, "cy": 0, "z": -8.5, "size": 400},
        views=[{"name": "全景", "pos": [-40, -70, 35], "target": [30, 0, -3]}, {"name": "橋台", "pos": [-14, -18, 4], "target": [2, 0, -3]},
               {"name": "桁下", "pos": [20, -12, -6], "target": [32, 0, -3]}, {"name": "断面", "pos": None, "target": None, "clip": 35}],
        lod_def={100: ["橋梁の位置を線・直方体と下部工位置のマーカーで示す。"],
                 200: ["構造形式が分かる程度。桁 (本数・桁高) と床版を矩形で、地覆・高欄、橋台・橋脚・フーチングを概形で表す。支承・伸縮装置・杭は表現しない (杭は範囲のみ)。"],
                 300: ["主構造の外形が正確なモデル。主桁・横桁・床版・地覆・高欄、橋台 (たて壁・胸壁・ウイング・フーチング)・橋脚・杭の形状。支承・伸縮装置は位置を記号で示す。"],
                 400: ["詳細度300に加えて PC鋼材、床版・橋台の配筋、支承・伸縮装置・落橋防止構造・排水桝などの細部を実形状でモデル化。"],
                 500: ["完成形状 (出来形計測の反映、路面標示、照明柱などの完成設備)。"]},
        notes=["配筋は床版と橋台A1を代表として作成 (全部材の配筋は省略)。", "取付部盛土と地形は参考表示。"],
    )

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "site")
    export_model(build_parts(), os.path.abspath(out), meta())
