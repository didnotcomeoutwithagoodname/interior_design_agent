"""从 Poly Haven 下载免费 CC0 家具 3D 模型，充实家具数据库。

原理：
1. 调 Poly Haven 资产 API，筛出 furniture 类模型；
2. 按关键词把每个资产映射到我们的家具品类；
3. 下载 gltf（1k 贴图版）+ .bin + 贴图到 data/models/<asset_id>/；
4. 写出 data/furniture_models.json（品类 -> 模型本地路径/来源/许可）。

用法：
    python fetch_3d_models.py            # 为每个能匹配的品类下载一个模型
    python fetch_3d_models.py --limit 4  # 只下载前 4 个
"""
from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent
ASSETS_URL = "https://api.polyhaven.com/assets?type=models"
DL_BASE = "https://dl.polyhaven.org/file/ph-assets/Models"
MODELS_DIR = BASE / "data" / "models"

# 品类 -> 关键词（匹配 Poly Haven 资产的 name/category，注意：具体品类排在通用品类前面）
CATEGORY_KEYWORDS = {
    "沙发": ["sofa", "couch"],
    "床": [" bed", "bed "],  # 避免误匹配 bedside/headboard
    "床头柜": ["nightstand", "night stand", "bedside"],
    "单椅": ["armchair", "arm chair", "lounge chair"],
    "办公椅": ["office chair", "desk chair"],
    "书桌": ["desk"],
    "衣柜": ["wardrobe", "dresser", "cupboard", "cabinet"],
    "书架": ["shelf", "bookcase", "bookshelf"],
    "餐桌": ["dining table", "table"],
    "茶几": ["coffee table", "side table", "end table"],
    "电视柜": ["tv", "television", "media console", "entertainment"],
}


def _http_bytes(url: str) -> bytes:
    # dl.polyhaven.org 会拒绝非浏览器 UA（返回 404），必须伪装浏览器
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def _http_json(url: str):
    return json.loads(_http_bytes(url).decode("utf-8"))


def _download(url: str, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(_http_bytes(url))


def download_asset(asset_id: str) -> Path:
    """下载 gltf + bin + 贴图，返回本地 gltf 路径（用 files 接口的权威 URL）。"""
    asset_dir = MODELS_DIR / asset_id
    gltf_local = asset_dir / f"{asset_id}.gltf"
    if gltf_local.exists():
        return gltf_local

    files = _http_json(f"https://api.polyhaven.com/files/{asset_id}")
    gltf_variant = files.get("gltf", {}).get("1k", {}).get("gltf") \
        or files.get("gltf", {}).get("2k", {}).get("gltf")
    if not gltf_variant:
        raise RuntimeError("该资产无 gltf 变体")

    _download(gltf_variant["url"], gltf_local)
    for rel, info in gltf_variant.get("include", {}).items():
        _download(info["url"], asset_dir / rel)
    return gltf_local


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="最多下载的品类数（0=全部）")
    args = ap.parse_args()

    print(f"拉取 Poly Haven 家具资产列表…")
    assets = _http_json(ASSETS_URL)

    used: set = set()
    mapping: list = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        if args.limit and len(mapping) >= args.limit:
            break
        picked = None
        for aid, meta in assets.items():
            if aid in used:
                continue
            text = (meta.get("name", "") + " " + meta.get("category", "")).lower()
            if any(k in text for k in keywords):
                picked = (aid, meta)
                break
        if not picked:
            print(f"  [跳过] 品类「{category}」无匹配模型")
            continue
        aid, meta = picked
        used.add(aid)
        try:
            gltf = download_asset(aid)
            mapping.append({
                "category": category,
                "asset_id": aid,
                "asset_name": meta.get("name"),
                "license": "CC0",
                "source_url": f"https://polyhaven.com/a/{aid}",
                "local_gltf": str(gltf.relative_to(BASE)),
            })
            print(f"  [OK] {category:<6} <- {meta.get('name')} ({aid})")
        except Exception as e:
            print(f"  [失败] {category} <- {aid}: {e}")

    out = BASE / "data" / "furniture_models.json"
    out.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已写入 {len(mapping)} 条映射到 {out}")


if __name__ == "__main__":
    main()
