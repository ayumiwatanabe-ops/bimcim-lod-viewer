# -*- coding: utf-8 -*-
"""
Blender (headless) で各詳細度の GLB を読み込み、説明用の静止画を出力する。
    blender -b --python render_blender.py -- <モデルルートフォルダ> <出力フォルダ>
出力: LODxxx_01_全景.png / _02_坑口.png / _03_内部.png / _04_断面.png
"""
import bpy, sys, os, math
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
ROOT, OUT = argv[0], argv[1]
os.makedirs(OUT, exist_ok=True)

def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def setup_scene():
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = 1600, 1000
    sc.render.film_transparent = False
    world = bpy.data.worlds.new("W"); sc.world = world; world.use_nodes = True
    bg = world.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.75, 0.80, 0.86, 1); bg.inputs[1].default_value = 0.6
    sc.view_settings.view_transform = "Standard"
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN")); sun.data.energy = 2.0
    sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(-40)); sc.collection.objects.link(sun)
    sun2 = bpy.data.objects.new("Sun2", bpy.data.lights.new("Sun2", "SUN")); sun2.data.energy = 1.2
    sun2.rotation_euler = (math.radians(-60), math.radians(30), math.radians(140)); sc.collection.objects.link(sun2)
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.lens = 28; cam.data.clip_end = 5000
    return cam

def look_at(cam, pos, target):
    cam.location = Vector(pos)
    d = Vector(target) - Vector(pos)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

def render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

def ground():
    bpy.ops.mesh.primitive_plane_add(size=800, location=(120, 30, -2.2))
    g = bpy.context.active_object
    m = bpy.data.materials.new("ground"); m.diffuse_color = (0.55, 0.62, 0.45, 1); g.data.materials.append(m)
    return g

def bisect_all(point, normal):
    """point/normal の平面で全メッシュを切断し、normal 側を削除 (断面表示用)"""
    import bmesh
    for ob in [o for o in bpy.context.scene.objects if o.type == "MESH"]:
        bm = bmesh.new(); bm.from_mesh(ob.data)
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        mw = ob.matrix_world; inv = mw.inverted()
        p_local = inv @ Vector(point); n_local = (inv.to_3x3() @ Vector(normal)).normalized()
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=p_local, plane_no=n_local, clear_outer=True, clear_inner=False)
        bm.to_mesh(ob.data); bm.free()

for lod in (100, 200, 300, 400, 500):
    glb = os.path.join(ROOT, f"LOD{lod}", f"tunnel_LOD{lod}.glb")
    if not os.path.exists(glb):
        continue
    clear(); cam = setup_scene()
    bpy.ops.import_scene.gltf(filepath=glb)
    ground()
    # 全景 (起点側斜め上空)
    look_at(cam, (-70, -110, 70), (110, 15, 0)); render(os.path.join(OUT, f"LOD{lod}_01_全景.png"))
    # 坑口 (起点側正面やや上)
    look_at(cam, (-28, -14, 9), (12, 1, 3)); render(os.path.join(OUT, f"LOD{lod}_02_坑口.png"))
    # 内部 (No.60 から終点方向)
    cam.data.lens = 22
    look_at(cam, (62, 0.5, 2.0), (120, 5, 2.5)); render(os.path.join(OUT, f"LOD{lod}_03_内部.png"))
    # 断面 (No.120 で切断し, 終点側を削除して斜めから)
    cam.data.lens = 35
    import numpy as np
    s = 120.0; R = 500.0; s1 = 60.0
    phi = (s - s1) / R
    px, py = s1 + R * math.sin(phi), R * (1 - math.cos(phi))
    nrm = (math.cos(phi), math.sin(phi), 0.0)
    bisect_all((px, py, 0), nrm)
    look_at(cam, (px + 22 * nrm[0] + 8, py + 22 * nrm[1] - 14, 10), (px, py, 2.5)); render(os.path.join(OUT, f"LOD{lod}_04_断面.png"))
print("done")
