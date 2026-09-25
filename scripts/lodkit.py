# -*- coding: utf-8 -*-
"""
詳細度(LOD)別サンプルモデル 共通ライブラリ
  - 線形 (Alignment) / メッシュ生成ユーティリティ / 部材 (Part)
  - GLB / OBJ / DXF / IFC 書き出し、ビューア用 model.json・summary.json 出力
"""
import os, json, math
import numpy as np

# ------------------------------------------------------------------ 線形
class Alignment:
    """平面: 直線(S,長さ)・円曲線(C,半径,長さ; 半径>0 で左回り) の連続。縦断: 一定勾配。"""
    def __init__(self, segments=(("S", 100.0),), grade=0.0, z0=0.0, origin=(0.0, 0.0), heading=0.0):
        self.segments = list(segments); self.grade = grade; self.z0 = z0; self.origin = origin; self.heading = heading
        self.length = sum(sg[-1] for sg in self.segments)

    def frame(self, s):
        x, y, phi = self.origin[0], self.origin[1], self.heading
        rem = s
        for sg in self.segments:
            if sg[0] == "S":
                L = sg[1]; d = min(rem, L)
                x += d * math.cos(phi); y += d * math.sin(phi)
            else:
                R, L = sg[1], sg[2]; d = min(rem, L); dphi = d / R
                x += R * (math.sin(phi + dphi) - math.sin(phi)); y += -R * (math.cos(phi + dphi) - math.cos(phi)); phi += dphi
            rem -= d
            if rem <= 1e-9: break
        if rem > 1e-9:  # 延長を超えた分は最後の接線方向に直線延長
            x += rem * math.cos(phi); y += rem * math.sin(phi)
        z = self.z0 + self.grade * s
        T = np.array([math.cos(phi), math.sin(phi), self.grade]); T /= np.linalg.norm(T)
        Rv = np.array([math.sin(phi), -math.cos(phi), 0.0])
        U = np.array([0.0, 0.0, 1.0])
        return np.array([x, y, z]), T, Rv, U

    def to_world(self, s, pts2d):
        Pc, T, Rv, U = self.frame(s)
        pts2d = np.asarray(pts2d, float)
        return Pc[None, :] + pts2d[:, 0:1] * Rv[None, :] + pts2d[:, 1:2] * U[None, :]

    def sample(self, step=2.0):
        n = int(round(self.length / step)) + 1
        out = []
        for i in range(n):
            s = min(self.length, i * step); P, T, R, U = self.frame(s)
            out.append([round(float(v), 4) for v in P] + [round(float(v), 5) for v in T])
        return {"length": self.length, "step": step, "points": out}

def stations(s0, s1, ds=2.0):
    n = max(2, int(round((s1 - s0) / ds)) + 1)
    return np.linspace(s0, s1, n)

# ------------------------------------------------------------------ メッシュ
class Mesh:
    def __init__(self, V=None, F=None):
        self.V = np.zeros((0, 3)) if V is None else np.asarray(V, float)
        self.F = np.zeros((0, 3), int) if F is None else np.asarray(F, int)
    def add(self, other):
        n = len(self.V); self.V = np.vstack([self.V, other.V]); self.F = np.vstack([self.F, other.F + n]); return self
    def translate(self, d):
        self.V = self.V + np.asarray(d, float)[None, :]; return self
    @property
    def ntri(self): return len(self.F)

def earclip(poly):
    poly = [tuple(p) for p in poly]; n = len(poly); idx = list(range(n))
    def area(pl): return 0.5 * sum(pl[i][0] * pl[(i + 1) % len(pl)][1] - pl[(i + 1) % len(pl)][0] * pl[i][1] for i in range(len(pl)))
    if area(poly) < 0: idx = idx[::-1]
    def cross(o, a, b): return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    def inside(p, a, b, c): return cross(a, b, p) >= -1e-12 and cross(b, c, p) >= -1e-12 and cross(c, a, p) >= -1e-12
    tris = []; guard = 0
    while len(idx) > 3 and guard < 20000:
        guard += 1; found = False
        for i in range(len(idx)):
            a, b, c = idx[i - 1], idx[i], idx[(i + 1) % len(idx)]
            if cross(poly[a], poly[b], poly[c]) <= 1e-12: continue
            if any(inside(poly[j], poly[a], poly[b], poly[c]) for j in idx if j not in (a, b, c)): continue
            tris.append([a, b, c]); idx.pop(i); found = True; break
        if not found: tris.append([idx[0], idx[1], idx[2]]); idx.pop(1)
    if len(idx) == 3: tris.append(idx[:])
    return tris

def loop_to_2d(loop):
    c = loop.mean(0); X = loop - c
    u, s, vt = np.linalg.svd(X, full_matrices=False)
    return X @ vt[:2].T

def grid_mesh(grid, close_ring=False, caps=False):
    ns, k, _ = grid.shape
    V = grid.reshape(-1, 3); F = []
    kk = k if close_ring else k - 1
    for i in range(ns - 1):
        for j in range(kk):
            a = i * k + j; b = i * k + (j + 1) % k; c = (i + 1) * k + j; d = (i + 1) * k + (j + 1) % k
            F.append([a, c, b]); F.append([b, c, d])
    if caps and close_ring:
        for i, flip in ((0, False), (ns - 1, True)):
            base = i * k
            for t in earclip(loop_to_2d(grid[i])):
                t = [base + x for x in t]; F.append(t[::-1] if flip else t)
    return Mesh(V, np.array(F, int))

def sweep(al, section_fn, sts, close_ring=True, caps=True):
    grid = np.array([al.to_world(s, section_fn(s)) for s in sts])
    return grid_mesh(grid, close_ring, caps)

def ring_section(inner_fn, outer_fn):
    def f(s):
        a = inner_fn(s); b = outer_fn(s); return np.vstack([a, b[::-1]])
    return f

def prism(A, B, poly2d):
    n = len(A); V = np.vstack([A, B]); F = []
    for t in earclip(poly2d):
        F.append([t[0], t[2], t[1]]); F.append([n + t[0], n + t[1], n + t[2]])
    for i in range(n):
        j = (i + 1) % n; F.append([i, j, n + j]); F.append([i, n + j, n + i])
    return Mesh(V, np.array(F, int))

def extrude(al, poly2d, s, thickness, along=+1):
    """線形の測点 s の断面上の多角形を線形方向へ押し出す"""
    Pc, T, Rv, U = al.frame(s)
    poly2d = np.asarray(poly2d, float)
    A = al.to_world(s, poly2d); B = A + along * thickness * T[None, :]
    if along < 0: A, B = B, A
    return prism(A, B, poly2d)

def extrude_world(poly2d, axis, base, thickness, u_dir, v_dir):
    """任意平面: base + u*u_dir + v*v_dir 上の多角形を axis 方向に押し出す"""
    poly2d = np.asarray(poly2d, float); u_dir = np.asarray(u_dir, float); v_dir = np.asarray(v_dir, float)
    A = np.asarray(base, float)[None, :] + poly2d[:, 0:1] * u_dir[None, :] + poly2d[:, 1:2] * v_dir[None, :]
    B = A + np.asarray(axis, float)[None, :] * thickness
    return prism(A, B, poly2d)

def box_local(al, s0, s1, y0, y1, z0, z1, n_along=None):
    if n_along is None: n_along = max(2, int((s1 - s0) / 4) + 1)
    rect = np.array([[y0, z0], [y1, z0], [y1, z1], [y0, z1]])
    return sweep(al, lambda s: rect, np.linspace(s0, s1, n_along), True, True)

def box_world(x0, x1, y0, y1, z0, z1):
    V = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0], [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], float)
    F = np.array([[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5], [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]], int)
    return Mesh(V, F)

def box_at(center, size, u=(1, 0, 0), v=(0, 1, 0), w=(0, 0, 1)):
    """中心・寸法・軸ベクトルで直方体"""
    c = np.asarray(center, float); sx, sy, sz = size
    u, v, w = (np.asarray(a, float) for a in (u, v, w))
    m = box_world(-sx / 2, sx / 2, -sy / 2, sy / 2, -sz / 2, sz / 2)
    m.V = c[None, :] + m.V[:, 0:1] * u[None, :] + m.V[:, 1:2] * v[None, :] + m.V[:, 2:3] * w[None, :]
    return m

def cylinder(p0, p1, r, nseg=8):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0; L = np.linalg.norm(d); d /= L
    a = np.array([0, 0, 1.0]) if abs(d[2]) < 0.9 else np.array([1.0, 0, 0])
    u = np.cross(d, a); u /= np.linalg.norm(u); v = np.cross(d, u)
    ring = [r * (math.cos(t) * u + math.sin(t) * v) for t in np.linspace(0, 2 * math.pi, nseg, endpoint=False)]
    V = [p0 + q for q in ring] + [p1 + q for q in ring] + [p0, p1]
    F = []
    for i in range(nseg):
        j = (i + 1) % nseg
        F.append([i, j, nseg + j]); F.append([i, nseg + j, nseg + i]); F.append([2 * nseg, j, i]); F.append([2 * nseg + 1, nseg + i, nseg + j])
    return Mesh(np.array(V), np.array(F, int))

def tube_along(path, r, nseg=6):
    path = np.asarray(path, float); n = len(path); rings = []
    for i in range(n):
        d = (path[min(i + 1, n - 1)] - path[max(i - 1, 0)]); d /= (np.linalg.norm(d) + 1e-12)
        a = np.array([0, 0, 1.0]) if abs(d[2]) < 0.9 else np.array([1.0, 0, 0])
        u = np.cross(d, a); u /= np.linalg.norm(u); v = np.cross(d, u)
        rings.append([path[i] + r * (math.cos(t) * u + math.sin(t) * v) for t in np.linspace(0, 2 * math.pi, nseg, endpoint=False)])
    return grid_mesh(np.array(rings), True, True)

def sphere(c, r, n=8):
    c = np.asarray(c, float); rings = []
    for i in range(n + 1):
        ph = math.pi * i / n
        rings.append([c + r * np.array([math.sin(ph) * math.cos(t), math.sin(ph) * math.sin(t), math.cos(ph)]) for t in np.linspace(0, 2 * math.pi, n, endpoint=False)])
    return grid_mesh(np.array(rings), True, False)

def surface_mesh(xs, ys, zfn, double=False):
    """格子サーフェス z = zfn(x, y) (xs, ys: 1D 配列)"""
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    Z = np.vectorize(zfn)(X, Y)
    grid = np.stack([X, Y, Z], axis=-1)
    m = grid_mesh(grid, False, False)
    if double: m.F = np.vstack([m.F, m.F[:, ::-1]])
    return m

def profile_sweep(al, s, pts2d, nrm2d, prof):
    """断面内の曲線 (pts2d, 外向き法線 nrm2d) に沿って、(法線方向 a, 線形方向 b) の 2D 断面 prof をスイープ"""
    Pc, T, Rv, U = al.frame(s); rings = []
    for p, nv in zip(pts2d, nrm2d):
        base = Pc + p[0] * Rv + p[1] * U; nw = nv[0] * Rv + nv[1] * U
        rings.append([base + a * nw + b * T for a, b in prof])
    return grid_mesh(np.array(rings), True, True)

def h_shape(h, w, t):
    hw, hh = w / 2, h / 2
    return [(-hh, -hw), (-hh, hw), (-hh + t, hw), (-hh + t, t / 2), (hh - t, t / 2), (hh - t, hw), (hh, hw), (hh, -hw), (hh - t, -hw), (hh - t, -t / 2), (-hh + t, -t / 2), (-hh + t, -hw)]

def offset_polyline(pts, d):
    """開いた 2D 折れ線を法線方向に d オフセット (簡易: 頂点法線の平均)"""
    pts = np.asarray(pts, float); n = len(pts); out = np.zeros_like(pts)
    for i in range(n):
        a = pts[max(i - 1, 0)]; b = pts[min(i + 1, n - 1)]; t = b - a; t /= (np.linalg.norm(t) + 1e-12)
        nrm = np.array([t[1], -t[0]]); out[i] = pts[i] + d * nrm
    return out

def fix_normals(parts):
    import trimesh
    for p in parts:
        try:
            tm = trimesh.Trimesh(p.mesh.V, p.mesh.F, process=False); tm.fix_normals(multibody=True); p.mesh.F = np.asarray(tm.faces, int)
        except Exception as e:
            print("fix_normals skipped:", p.name, e)

# ------------------------------------------------------------------ 部材・詳細度
class Part:
    def __init__(self, name, category, mesh, color, lod, note="", lod_max=999):
        self.name, self.category, self.mesh, self.color, self.lod, self.note, self.lod_max = name, category, mesh, color, lod, note, lod_max

LOD_COMMON = {
    100: "対象を記号や線、単純な形状でその位置を示したモデル。",
    200: "対象の構造形式が分かる程度のモデル。標準横断で切土・盛土を表現、又は各構造物一般図に示される標準横断面を対象範囲でスイープさせて作成する程度の表現。",
    300: "附帯工等の細部構造、接続部構造を除き、対象の外形形状を正確に表現したモデル。",
    400: "詳細度300に加えて、附帯工、接続構造などの細部構造及び配筋も含めて、正確にモデル化する。",
    500: "対象の現実の形状を表現したモデル。",
}
LOD_SHORT = {100: "位置", 200: "構造形式", 300: "外形形状", 400: "細部・配筋", 500: "完成形状"}

def parts_for_lod(parts, lod): return [p for p in parts if p.lod <= lod <= p.lod_max]

# ------------------------------------------------------------------ 書き出し
def to_yup(V):
    V = np.asarray(V, float); return np.column_stack([V[:, 0], V[:, 2], -V[:, 1]])

def write_obj(path, plist):
    with open(path, "w", encoding="utf-8") as f, open(path[:-4] + ".mtl", "w", encoding="utf-8") as fm:
        f.write(f"# Y-up (glTF convention). DXF/IFC are Z-up.\nmtllib {os.path.basename(path)[:-4]}.mtl\n"); off = 1
        for i, p in enumerate(plist):
            mat = f"m{i}"; c = p.color
            fm.write(f"newmtl {mat}\nKd {c[0]:.3f} {c[1]:.3f} {c[2]:.3f}\nd {c[3] if len(c) > 3 else 1.0:.2f}\n\n")
            f.write(f"o {p.name}\nusemtl {mat}\n")
            for v in to_yup(p.mesh.V): f.write(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}\n")
            for t in p.mesh.F: f.write(f"f {t[0]+off} {t[1]+off} {t[2]+off}\n")
            off += len(p.mesh.V)

def write_glb(path, plist):
    import trimesh
    sc = trimesh.Scene()
    for i, p in enumerate(plist):
        m = trimesh.Trimesh(to_yup(p.mesh.V), p.mesh.F, process=False)
        c = list(p.color) + ([1.0] if len(p.color) == 3 else [])
        mat = trimesh.visual.material.PBRMaterial(name=f"m{i}", baseColorFactor=[float(x) for x in c], metallicFactor=0.0, roughnessFactor=0.8,
                                                  alphaMode="BLEND" if c[3] < 1 else "OPAQUE", doubleSided=True)
        m.visual = trimesh.visual.TextureVisuals(material=mat)
        sc.add_geometry(m, node_name=f"{p.category}|{p.name}", geom_name=f"g{i}")
    sc.export(path)

def write_dxf(path, plist, lod):
    import ezdxf
    doc = ezdxf.new("R2018"); doc.header["$INSUNITS"] = 6
    msp = doc.modelspace()
    for i, p in enumerate(plist):
        layer = f"LOD{lod}_{p.category}"
        if layer not in doc.layers: doc.layers.add(layer)
        c = p.color
        ent = msp.add_mesh(dxfattribs={"layer": layer, "true_color": ezdxf.rgb2int((int(c[0]*255), int(c[1]*255), int(c[2]*255)))})
        if len(c) > 3: ent.transparency = 1.0 - c[3]
        with ent.edit_data() as md:
            md.vertices = [tuple(v) for v in p.mesh.V]; md.faces = [tuple(int(x) for x in t) for t in p.mesh.F]
    doc.saveas(path)

def write_ifc(path, plist, lod, model_name):
    import ifcopenshell, ifcopenshell.api
    f = ifcopenshell.api.run("project.create_file", version="IFC4")
    proj = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcProject", name=f"{model_name} 詳細度{lod} サンプル")
    ifcopenshell.api.run("unit.assign_unit", f)
    ctx = ifcopenshell.api.run("context.add_context", f, context_type="Model")
    body = ifcopenshell.api.run("context.add_context", f, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=ctx)
    site = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcSite", name="サンプル敷地")
    bld = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcBuilding", name=f"{model_name} (汎用サンプル)")
    ifcopenshell.api.run("aggregate.assign_object", f, products=[site], relating_object=proj)
    ifcopenshell.api.run("aggregate.assign_object", f, products=[bld], relating_object=site)
    for i, p in enumerate(plist):
        el = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcBuildingElementProxy", name=p.name); el.ObjectType = p.category
        rep = ifcopenshell.api.run("geometry.add_mesh_representation", f, context=body,
                                   vertices=[[tuple(float(x) for x in v) for v in p.mesh.V]], faces=[[tuple(int(x) for x in t) for t in p.mesh.F]])
        ifcopenshell.api.run("geometry.assign_representation", f, product=el, representation=rep)
        ifcopenshell.api.run("spatial.assign_container", f, products=[el], relating_structure=bld)
        c = p.color
        style = ifcopenshell.api.run("style.add_style", f, name=f"style_{i}")
        ifcopenshell.api.run("style.add_surface_style", f, style=style, ifc_class="IfcSurfaceStyleShading",
                             attributes={"SurfaceColour": {"Name": None, "Red": float(c[0]), "Green": float(c[1]), "Blue": float(c[2])}, "Transparency": float(1.0 - c[3]) if len(c) > 3 else 0.0})
        ifcopenshell.api.run("style.assign_representation_styles", f, shape_representation=rep, styles=[style])
        pset = ifcopenshell.api.run("pset.add_pset", f, product=el, name="Pset_BIMCIM_Sample")
        ifcopenshell.api.run("pset.edit_pset", f, pset=pset, properties={"詳細度": str(lod), "部材分類": p.category, "初出詳細度": str(p.lod), "備考": p.note})
    f.write(path)

def export_model(parts, out_root, meta, formats=("glb", "obj", "dxf", "ifc")):
    """meta: id, name, category, description, alignment(Alignment), lod_def{lod:[specific, short]}, views, notes, ground, center, ref"""
    mid = meta["id"]; d = os.path.join(out_root, "models", mid); os.makedirs(d, exist_ok=True)
    fix_normals(parts)
    print(f"[{mid}] parts: {len(parts)}, tris: {sum(p.mesh.ntri for p in parts)}")
    summary = {"lods": {}}
    for lod in (100, 200, 300, 400, 500):
        pl = parts_for_lod(parts, lod); base = os.path.join(d, f"LOD{lod}")
        if "glb" in formats: write_glb(base + ".glb", pl)
        if "obj" in formats: write_obj(base + ".obj", pl)
        if "dxf" in formats: write_dxf(base + ".dxf", pl, lod)
        if "ifc" in formats: write_ifc(base + ".ifc", pl, lod, meta["name"])
        summary["lods"][str(lod)] = [dict(name=p.name, category=p.category, first_lod=p.lod, note=p.note, tris=int(p.mesh.ntri)) for p in pl]
        print(f"  LOD{lod}: {len(pl)} parts, {sum(p.mesh.ntri for p in pl)} tris, glb {os.path.getsize(base + '.glb')/1048576:.1f} MB")
    with open(os.path.join(d, "summary.json"), "w", encoding="utf-8") as fh: json.dump(summary, fh, ensure_ascii=False, indent=1)
    al = meta["alignment"]
    mj = {
        "id": mid, "name": meta["name"], "category": meta.get("category", ""), "description": meta.get("description", ""),
        "ref": meta.get("ref", ""), "alignment": al.sample(2.0), "center": [float(v) for v in meta["center"]],
        "ground": meta.get("ground", {"cx": float(meta["center"][0]), "cy": float(meta["center"][1]), "z": 0.0, "size": 600}),
        "views": meta["views"], "notes": meta.get("notes", []), "station_label": meta.get("station_label", "No."),
        "lod_def": {str(k): [LOD_COMMON[k], v[0], v[1] if len(v) > 1 else LOD_SHORT[k]] for k, v in meta["lod_def"].items()},
        "lod_files": {str(l): f"LOD{l}.glb" for l in (100, 200, 300, 400, 500)}, "thumb_hide_ref": bool(meta.get("thumb_hide_ref", False)), "wip": bool(meta.get("wip", False)),
    }
    with open(os.path.join(d, "model.json"), "w", encoding="utf-8") as fh: json.dump(mj, fh, ensure_ascii=False, indent=1)
    return d
