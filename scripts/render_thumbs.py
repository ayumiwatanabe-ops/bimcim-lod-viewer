# -*- coding: utf-8 -*-
"""Blender (headless): site/models/<id>/LOD300.glb をサムネイル (thumb.jpg) と説明用画像にレンダリング
    blender -b --python render_thumbs.py -- <siteフォルダ> [model_id ...]
"""
import bpy, sys, os, math, json
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
SITE = argv[0]; only = argv[1:]
MODELS = os.path.join(SITE, "models")

def clear(): bpy.ops.wm.read_factory_settings(use_empty=True)
def setup_scene():
    sc = bpy.context.scene; sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = 1280, 800
    world = bpy.data.worlds.new("W"); sc.world = world; world.use_nodes = True
    bg = world.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.75, 0.80, 0.86, 1); bg.inputs[1].default_value = 0.6
    sc.view_settings.view_transform = "Standard"
    for nm, e, rot in (("Sun", 2.0, (50, 10, -40)), ("Sun2", 1.2, (-60, 30, 140))):
        o = bpy.data.objects.new(nm, bpy.data.lights.new(nm, "SUN")); o.data.energy = e; o.rotation_euler = [math.radians(a) for a in rot]; sc.collection.objects.link(o)
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.lens = 30; cam.data.clip_end = 5000
    return cam
def look_at(cam, pos, target):
    cam.location = Vector(pos); d = Vector(target) - Vector(pos); cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
def render(path):
    bpy.context.scene.render.filepath = path; bpy.ops.render.render(write_still=True)

for mid in sorted(os.listdir(MODELS)):
    if only and mid not in only: continue
    mdir = os.path.join(MODELS, mid); mj = os.path.join(mdir, "model.json")
    if not os.path.exists(mj): continue
    meta = json.load(open(mj, encoding="utf-8"))
    for lod in (300, 400):
        glb = os.path.join(mdir, f"LOD{lod}.glb")
        if not os.path.exists(glb): continue
        clear(); cam = setup_scene()
        bpy.ops.import_scene.gltf(filepath=glb)
        if meta.get("thumb_hide_ref"):
            for ob in bpy.context.scene.objects:
                if "参考" in ob.name: ob.hide_render = True
        g = meta["ground"]
        bpy.ops.mesh.primitive_plane_add(size=g["size"], location=(g["cx"], g["cy"], g["z"] - 0.05))
        m = bpy.data.materials.new("ground"); m.diffuse_color = (0.55, 0.62, 0.45, 1); bpy.context.active_object.data.materials.append(m)
        v = meta["views"][0]
        look_at(cam, v["pos"], v["target"])
        render(os.path.join(mdir, f"view_LOD{lod}.png"))
        if lod == 300:
            bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 640, 400
            bpy.context.scene.render.image_settings.file_format = "JPEG"; bpy.context.scene.render.image_settings.quality = 82
            render(os.path.join(mdir, "thumb.jpg"))
print("done")
