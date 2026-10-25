"""把家具目录（catalog）关联到高质量 3D 模型，并生成完整模型库清单。

数据源（均为带贴图的高质量模型，已移除低模 Kenney）：
- Sketchfab（CC-BY，单文件 glb）—— 12 个品类各一个，细节最丰富，优先采用；
- Poly Haven（CC0，gltf + bin + 贴图）—— 10 个品类，作为备用。

产出：
1. data/model_library.json —— 全部可用 3D 模型的清单（「3D 模型数据库」）；
2. data/catalog_3d.json     —— 每件目录家具 -> 选定模型（model_3d），供 3D 预览使用。

用法：
    python map_3d_models.py
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent


def _rel(path: str) -> str:
    """统一为项目根相对、正斜杠路径，便于 web 加载。"""
    return path.replace("\\", "/")


def build_library(polyhaven: list, sketchfab: list) -> list:
    """生成全部可用模型清单（Poly Haven + Sketchfab）。"""
    lib = []
    for m in polyhaven:
        lib.append({
            "id": f"polyhaven_{m['asset_id']}",
            "category": m["category"],
            "style_tags": ["写实", "高模"],
            "path": _rel(m["local_gltf"]),
            "format": "gltf",
            "source": "Poly Haven",
            "license": m.get("license", "CC0"),
            "source_url": m.get("source_url", ""),
        })
    for m in sketchfab:
        lib.append({
            "id": f"sketchfab_{m['uid']}",
            "category": m["category"],
            "style_tags": ["写实", "高模"],
            "path": _rel(m["local_glb"]),
            "format": "glb",
            "source": "Sketchfab",
            "license": m.get("license", "CC-BY"),
            "source_url": m.get("source_url", ""),
        })
    return lib


def assign_models(catalog: list, sketchfab_by_cat: dict, polyhaven_by_cat: dict) -> list:
    """给每件目录家具选一个高质量模型：Sketchfab 优先，Poly Haven 兜底。"""
    out = []
    for item in catalog:
        category = item["category"]
        m = sketchfab_by_cat.get(category) or polyhaven_by_cat.get(category)
        if not m:
            print(f"  [跳过] {item['id']} 品类「{category}」无可用模型")
            continue
        out.append({
            "catalog_id": item["id"],
            "name": item["name"],
            "category": category,
            "style": item.get("style", ""),
            "model_3d": m["path"],
            "model_format": m["format"],
            "model_source": m["source"],
            "model_license": m["license"],
        })
    return out


def main():
    catalog = json.loads((BASE / "data" / "furniture_catalog.json").read_text(encoding="utf-8"))
    polyhaven = json.loads((BASE / "data" / "furniture_models.json").read_text(encoding="utf-8"))
    sketchfab = json.loads((BASE / "data" / "sketchfab_models.json").read_text(encoding="utf-8"))

    library = build_library(polyhaven, sketchfab)
    (BASE / "data" / "model_library.json").write_text(
        json.dumps(library, ensure_ascii=False, indent=2), encoding="utf-8")

    sketchfab_by_cat = {
        m["category"]: {
            "path": _rel(m["local_glb"]),
            "format": "glb",
            "source": "Sketchfab",
            "license": m.get("license", "CC-BY"),
        } for m in sketchfab
    }
    polyhaven_by_cat = {
        m["category"]: {
            "path": _rel(m["local_gltf"]),
            "format": "gltf",
            "source": "Poly Haven",
            "license": m.get("license", "CC0"),
        } for m in polyhaven
    }

    assigned = assign_models(catalog, sketchfab_by_cat, polyhaven_by_cat)
    (BASE / "data" / "catalog_3d.json").write_text(
        json.dumps(assigned, ensure_ascii=False, indent=2), encoding="utf-8")

    cnt = Counter(m["category"] for m in library)
    print(f"模型库共 {len(library)} 个模型（Sketchfab {len(sketchfab)} + Poly Haven {len(polyhaven)}）")
    print(f"品类分布：{dict(cnt)}")
    print(f"已关联 {len(assigned)} 件目录家具到 3D 模型")


if __name__ == "__main__":
    main()
