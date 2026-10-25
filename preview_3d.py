"""Render the design in output/ plus its 3D models into an interactive three.js page.

How it works:
- reads design_plan.json (room size / style), placements.json (furniture
  coordinates) and catalog_3d.json (furniture -> model path);
- generates an HTML page that uses three.js GLTFLoader to drop models into the
  room at their placed coordinates, auto-scaling each to its catalog footprint.

The models are large (high-quality Sketchfab GLBs, ~100MB total), so they are
not base64-embedded; they are loaded by path from a local static server
(browser file:// forbids cross-directory fetch).

Usage:
    python preview_3d.py --serve              # generate, start a server, open browser
    python preview_3d.py                      # only generate output/preview_3d.html
    # If a server is already running (e.g. python -m http.server 8123 at the
    # project root), open http://127.0.0.1:8123/output/preview_3d.html directly.
"""
from __future__ import annotations

import base64
import json
import math
from pathlib import Path

from src.labels_en import category_en, room_name_en, style_en

BASE = Path(__file__).resolve().parent

TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Interior Design 3D Preview</title>
<style>
  html, body { margin: 0; height: 100%; overflow: hidden;
    font-family: "Segoe UI", system-ui, "Microsoft YaHei", "PingFang SC", sans-serif; }
  #scene { position: absolute; inset: 0; }
  #hud { position: absolute; top: 16px; left: 16px; z-index: 10;
    background: rgba(255,255,255,.92); border-radius: 12px; padding: 14px 18px;
    box-shadow: 0 6px 24px rgba(0,0,0,.18); max-width: 320px; }
  #hud h1 { margin: 0 0 4px; font-size: 18px; color: #22303e; }
  #hud .sub { color: #6b7a8c; font-size: 13px; margin-bottom: 10px; }
  #hud ul { list-style: none; margin: 0; padding: 0; font-size: 12px; color: #3a4856; }
  #hud li { padding: 2px 0; }
  #hud li b { color: #1a76d2; }
  #hint { position: absolute; bottom: 14px; left: 50%; transform: translateX(-50%);
    z-index: 10; background: rgba(0,0,0,.55); color: #fff; font-size: 12px;
    padding: 6px 12px; border-radius: 20px; pointer-events: none; }
  .label { background: rgba(34,48,62,.82); color: #fff; font-size: 11px;
    padding: 2px 7px; border-radius: 10px; white-space: nowrap; }
</style>
<script type="importmap">
{ "imports": {
    "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
    "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"
} }
</script>
</head>
<body>
<div id="scene"></div>
<div id="hud">
  <h1>__ROOM_NAME__ · __STYLE__</h1>
  <div class="sub">__W__ m × __L__ m · __COUNT__ furniture pieces</div>
  <ul>__LEGEND__</ul>
</div>
<div id="hint">Left-drag: rotate · Scroll: zoom · Right-drag: pan</div>

<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';

const ROOM = __ROOM_JSON__;
const PLACEMENTS = __PLACEMENTS_JSON__;
const MODEL_DATA = __MODEL_DATA__;
const MODEL_ROT = __MODEL_ROT__;
const FLOOR_TEX = __FLOOR_TEX__;
const WALL_TEX = __WALL_TEX__;
const texLoader = new THREE.TextureLoader();

const W = ROOM.width, L = ROOM.length, CX = W / 2, CZ = L / 2;
const container = document.getElementById('scene');

// ---- 场景 / 相机 / 渲染器 ----
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xeef1f5);

const camera = new THREE.PerspectiveCamera(
  50, container.clientWidth / container.clientHeight, 0.1, 300);
const maxDim = Math.max(W, L);
camera.position.set(CX, maxDim * 1.15, CZ + maxDim * 1.2);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(container.clientWidth, container.clientHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
container.appendChild(renderer.domElement);

const labelRenderer = new CSS2DRenderer();
labelRenderer.setSize(container.clientWidth, container.clientHeight);
labelRenderer.domElement.style.position = 'absolute';
labelRenderer.domElement.style.top = '0';
labelRenderer.domElement.style.pointerEvents = 'none';
container.appendChild(labelRenderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(CX, 0.5, CZ);
controls.enableDamping = true;
controls.maxPolarAngle = Math.PI / 2 - 0.02;
controls.minDistance = 1.5;
controls.maxDistance = 40;

// ---- 灯光 ----
scene.add(new THREE.HemisphereLight(0xffffff, 0xc6ccd4, 1.0));
const sun = new THREE.DirectionalLight(0xfff4e0, 1.6);
sun.position.set(CX + 8, 12, CZ + 6);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.camera.left = -12; sun.shadow.camera.right = 12;
sun.shadow.camera.top = 12; sun.shadow.camera.bottom = -12;
sun.shadow.camera.far = 40;
scene.add(sun);

// ---- 地面 ----
const floorMat = new THREE.MeshStandardMaterial({ color: __FLOOR_COLOR__, roughness: 0.85 });
if (FLOOR_TEX) {
  texLoader.load(FLOOR_TEX, (tex) => {
    tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
    tex.repeat.set(W, L);
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.anisotropy = 8;
    floorMat.map = tex;
    floorMat.color.set(0xffffff);
    floorMat.needsUpdate = true;
  });
}
const floor = new THREE.Mesh(new THREE.PlaneGeometry(W, L), floorMat);
floor.rotation.x = -Math.PI / 2;
floor.position.set(CX, 0, CZ);
floor.receiveShadow = true;
scene.add(floor);

// ---- 墙体 ----
const WALL_H = 2.8, T = 0.12;
const wallMat = new THREE.MeshStandardMaterial({ color: 0xeae4d8, roughness: 0.9 });
if (WALL_TEX) {
  texLoader.load(WALL_TEX, (tex) => {
    tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
    tex.repeat.set(3, 3);
    tex.colorSpace = THREE.SRGBColorSpace;
    wallMat.map = tex;
    wallMat.color.set(0xffffff);
    wallMat.needsUpdate = true;
  });
}
function addWall(w, h, d, x, y, z) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), wallMat);
  m.position.set(x, y, z);
  m.castShadow = true; m.receiveShadow = true;
  scene.add(m);
}
addWall(W + 2 * T, WALL_H, T, CX, WALL_H / 2, -T / 2);          // 后墙 (z=0)
addWall(W + 2 * T, WALL_H, T, CX, WALL_H / 2, L + T / 2);        // 前墙 (z=L)
addWall(T, WALL_H, L, -T / 2, WALL_H / 2, CZ);                   // 左墙 (x=0)
addWall(T, WALL_H, L, W + T / 2, WALL_H / 2, CZ);                // 右墙 (x=W)

// ---- 网格 ----
const grid = new THREE.GridHelper(Math.ceil(maxDim) + 2, 20, 0x8a8f98, 0xc9cdd3);
grid.position.set(CX, 0.005, CZ);
scene.add(grid);

// ---- 标签 / 家具模型 ----
const loader = new GLTFLoader();
let pending = 0;

function addLabel(text, x, z) {
  const div = document.createElement('div');
  div.className = 'label';
  div.textContent = text;
  const obj = new CSS2DObject(div);
  obj.position.set(x, WALL_H - 0.4, z);
  scene.add(obj);
}

// ---- 挂饰：贴墙装饰画（程序化生成，挂在最近一侧墙）----
const artColors = [0x8a7f6a, 0x5b7a8a, 0x9a8b7a, 0x6a8a7a, 0x8a6a5a];
function addWallArt(x, z) {
  const w = 0.7, h = 0.9;
  const nearBack = z < L / 2;
  const wallZ = nearBack ? 0.05 : L - 0.05;
  const color = artColors[Math.floor(Math.random() * artColors.length)];

  const frame = new THREE.Mesh(
    new THREE.BoxGeometry(w, h, 0.05),
    new THREE.MeshStandardMaterial({ color: 0x3a3228, roughness: 0.7 }));
  frame.position.set(x, 1.5, wallZ);
  frame.castShadow = true;
  scene.add(frame);

  const art = new THREE.Mesh(
    new THREE.BoxGeometry(w - 0.08, h - 0.08, 0.03),
    new THREE.MeshStandardMaterial({ color: color, roughness: 0.9 }));
  art.position.set(x, 1.5, wallZ + (nearBack ? 0.045 : -0.045));
  scene.add(art);
}

// ---- 装饰品：绿植盆栽（程序化生成）----
function addDecor(x, z) {
  const pot = new THREE.Mesh(
    new THREE.CylinderGeometry(0.16, 0.12, 0.3, 16),
    new THREE.MeshStandardMaterial({ color: 0xb5733f, roughness: 0.8 }));
  pot.position.set(x, 0.15, z);
  pot.castShadow = true;
  scene.add(pot);

  const foliage = new THREE.Mesh(
    new THREE.SphereGeometry(0.22, 16, 12),
    new THREE.MeshStandardMaterial({ color: 0x4c8a4c, roughness: 0.9 }));
  foliage.position.set(x, 0.45, z);
  foliage.castShadow = true;
  scene.add(foliage);
}

PLACEMENTS.forEach((p) => {
  if (p.category === '挂饰') {
    addWallArt(p.x, p.y);
    addLabel(p.name, p.x, p.y);
    return;
  }
  if (p.category === '装饰品') {
    addDecor(p.x, p.y);
    addLabel(p.name, p.x, p.y);
    return;
  }
  const url = MODEL_DATA[p.id];
  if (!url) { console.warn('无模型路径：', p.id); return; }
  pending += 1;

  loader.load(url, (gltf) => {
    const obj = gltf.scene;
    obj.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });

    // 缩放到与目录脚印（width × depth）一致
    const box = new THREE.Box3().setFromObject(obj);
    const size = box.getSize(new THREE.Vector3());
    const sx = (p.width && size.x) ? p.width / size.x : 1;
    const sz = (p.depth && size.z) ? p.depth / size.z : 1;
    const s = Math.min(sx, sz) || 1;
    obj.scale.setScalar(s);

    // 重新取包围盒，落座地面并居中
    const box2 = new THREE.Box3().setFromObject(obj);
    const center = box2.getCenter(new THREE.Vector3());
    obj.position.set(p.x - center.x, -box2.min.y, p.y - center.z);
    obj.rotation.y = (p.rotation || 0) + (MODEL_ROT[p.category] || 0);
    scene.add(obj);

    addLabel(p.name, p.x, p.y);
    pending -= 1;
  }, undefined, (err) => {
    console.warn('模型加载失败：', p.id, err);
    addLabel(p.name, p.x, p.y);
    pending -= 1;
  });
});

// ---- 渲染循环 ----
function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
  labelRenderer.render(scene, camera);
}
animate();

window.addEventListener('resize', () => {
  camera.aspect = container.clientWidth / container.clientHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(container.clientWidth, container.clientHeight);
  labelRenderer.setSize(container.clientWidth, container.clientHeight);
});
</script>
</body>
</html>
"""


def _model_url(model_path: str) -> str:
    """把 catalog_3d 里的项目根相对路径转成服务器根相对 URL（/data/models/...）。"""
    return "/" + model_path.replace("\\", "/").lstrip("/")


def _data_uri(path: Path, mime: str) -> str:
    """把文件内容编码为 data URI，用于打包成无需服务器的独立 HTML。"""
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


_FLOOR_COLORS = [
    ("浅色", "0xd9c8ab"),
    ("深色实木", "0x8a5a3b"),
    ("木地板", "0xc0a37a"),
    ("浅灰", "0xc9ccd0"),
    ("瓷砖", "0xd6d2ca"),
    ("大理石", "0xdedad2"),
    ("水泥", "0x9a9a9a"),
    ("暖色", "0xd0b28a"),
]


def _floor_color(flooring: str) -> str:
    """把地面材质描述映射为 three.js 颜色字面量（作为 JS 代码注入）。"""
    for kw, color in _FLOOR_COLORS:
        if kw in flooring:
            return color
    return "0xd9c9ad"


# 地面材质 -> 纹理文件（Poly Haven CC0，位于 data/textures/floor/）
_FLOOR_TEXTURES = [
    ("浅木色", "hinoki_wood.jpg"),
    ("深色实木", "dark_wood.jpg"),
    ("浅色", "oak_wood.jpg"),
    ("暖色", "warm_wood.jpg"),
    ("浅灰", "grey_tiles.jpg"),
    ("瓷砖", "grey_tiles.jpg"),
    ("大理石", "marble.jpg"),
    ("水泥", "concrete.jpg"),
    ("木地板", "oak_wood.jpg"),
]

_WALL_TEXTURE = "/data/textures/wall/plaster.jpg"
_WALL_TEXTURE_FILE = BASE / _WALL_TEXTURE.lstrip("/")

# 模型默认朝向修正（度）：部分 GLB 模型的正面朝向与布局约定相反，需绕 Y 轴旋转 180°。
_MODEL_ROTATION_DEG = {"床": 180.0, "衣柜": 180.0}


def _floor_texture(flooring: str) -> str:
    """把地面材质描述映射为服务器根相对纹理 URL。"""
    for kw, tex in _FLOOR_TEXTURES:
        if kw in flooring:
            return f"/data/textures/floor/{tex}"
    return "/data/textures/floor/oak_wood.jpg"


def _floor_texture_file(flooring: str) -> Path:
    """地面纹理的本地文件路径（用于打包进独立 HTML）。"""
    return BASE / _floor_texture(flooring).lstrip("/")


def render(out_path: Path, standalone: bool = False):
    plan = json.loads((BASE / "output" / "design_plan.json").read_text(encoding="utf-8"))
    placements = json.loads((BASE / "output" / "placements.json").read_text(encoding="utf-8"))
    catalog_3d = json.loads((BASE / "data" / "catalog_3d.json").read_text(encoding="utf-8"))

    room = plan["rooms"][0]
    style = plan.get("style", "")
    model_rot = {cat: math.radians(deg) for cat, deg in _MODEL_ROTATION_DEG.items()}

    # 全部摆放项都渲染：挂饰/装饰品无 glb 模型，由页面程序化生成
    used = list(placements)
    legend = "".join(f"<li><b>{category_en(p['category'])}</b> · {p['name']}</li>" for p in used)
    floor_color = _floor_color(room.get("flooring", ""))

    if standalone:
        # 单文件版：只把本次设计实际用到的模型 + 贴图内嵌为 data URI，无需本地服务器
        model_data = {}
        for fid in {p["id"] for p in used if p["category"] not in ("挂饰", "装饰品")}:
            entry = next((m for m in catalog_3d if m["catalog_id"] == fid), None)
            if entry:
                model_data[fid] = _data_uri(BASE / entry["model_3d"], "model/gltf-binary")
        floor_tex = _data_uri(_floor_texture_file(room.get("flooring", "")), "image/jpeg")
        wall_tex = _data_uri(_WALL_TEXTURE_FILE, "image/jpeg")
    else:
        model_data = {m["catalog_id"]: _model_url(m["model_3d"]) for m in catalog_3d}
        floor_tex = _floor_texture(room.get("flooring", ""))
        wall_tex = _WALL_TEXTURE

    html = (TEMPLATE
            .replace("__ROOM_NAME__", room_name_en(room["name"]))
            .replace("__STYLE__", style_en(style))
            .replace("__W__", str(room["width"]))
            .replace("__L__", str(room["length"]))
            .replace("__COUNT__", str(len(used)))
            .replace("__LEGEND__", legend)
            .replace("__ROOM_JSON__", json.dumps(room, ensure_ascii=False))
            .replace("__PLACEMENTS_JSON__", json.dumps(used, ensure_ascii=False))
            .replace("__MODEL_DATA__", json.dumps(model_data, ensure_ascii=False))
            .replace("__MODEL_ROT__", json.dumps(model_rot, ensure_ascii=False))
            .replace("__FLOOR_COLOR__", floor_color)
            .replace("__FLOOR_TEX__", json.dumps(floor_tex, ensure_ascii=False))
            .replace("__WALL_TEX__", json.dumps(wall_tex, ensure_ascii=False)))

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"3D preview generated: {out_path.resolve()}")


def _serve_and_open(out: Path, port: int):
    """Start a local static server at the project root and open the browser (Ctrl+C to stop)."""
    import functools
    import http.server
    import threading
    import webbrowser

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(BASE))
    try:
        httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    except OSError as e:
        print(f"Port {port} is in use ({e}). Try another port: python preview_3d.py --serve --port 8611")
        return

    url = f"http://127.0.0.1:{port}/output/preview_3d.html"
    print(f"Local server started: {url} (press Ctrl+C to stop)")
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--serve", action="store_true", help="start a local server and open the browser after generating")
    ap.add_argument("--port", type=int, default=8610, help="port used with --serve")
    ap.add_argument("--standalone", action="store_true",
                    help="bundle the used models/textures into one self-contained HTML file (no server needed)")
    args = ap.parse_args()

    if args.standalone:
        out = BASE / "output" / "preview_3d_standalone.html"
        render(out, standalone=True)
        print("Single-file preview ready — send this one .html file to anyone; "
              "they only need an internet connection (for the three.js CDN).")
    else:
        out = BASE / "output" / "preview_3d.html"
        render(out)
        if args.serve:
            _serve_and_open(out, args.port)
        else:
            print("Tip: run python preview_3d.py --serve to auto-start a server; "
                  "or open http://127.0.0.1:<port>/output/preview_3d.html if a server is already running.")


if __name__ == "__main__":
    main()
