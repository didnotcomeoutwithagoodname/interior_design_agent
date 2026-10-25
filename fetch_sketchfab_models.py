"""从 Sketchfab 下载高质量 CC0/CC-BY 家具模型（glb），替换低模模型。

Sketchfab 官方下载接口需要 API Token（免费账号即可）：
1. 注册/登录 https://sketchfab.com
2. 右上角头像 -> Settings -> Password & API -> "Add API token" 生成并复制
3. 通过环境变量 SKETCHFAB_TOKEN 传入，或命令行 --token

流程：
1. 用搜索 API 按品类找 downloadable + 免费许可（CC0 / CC BY）的模型；
2. 调 /v3/models/{uid}/download 拿到 glb 的签名下载地址并落盘；
3. 写出 data/sketchfab_models.json（品类 -> uid -> 本地路径/许可/来源）。

用法：
    $env:SKETCHFAB_TOKEN = "你的token"
    python fetch_sketchfab_models.py
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent
SEARCH_URL = "https://api.sketchfab.com/v3/search"
API_URL = "https://api.sketchfab.com/v3/models"
MODELS_DIR = BASE / "data" / "models" / "sketchfab"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# 品类 -> 搜索关键词（英文，Sketchfab 用英文标签）
CATEGORY_KEYWORDS = {
    "沙发":   "sofa couch",
    "床":     "bed bedroom",
    "床头柜": "nightstand bedside table",
    "单椅":   "armchair lounge chair",
    "办公椅": "office chair desk chair",
    "书桌":   "desk writing desk",
    "衣柜":   "wardrobe dresser closet",
    "书架":   "bookshelf bookcase shelf",
    "餐桌":   "dining table",
    "餐椅":   "dining chair",
    "茶几":   "coffee table",
    "电视柜": "tv stand media console",
}

# 允许的免费许可（label 判定）：CC0 与 CC BY；排除非商业/相同方式共享/禁止演绎
_BAD_LICENSE = ("noncommercial", "noderiv", "sharealike", "nc-", "nd-", "sa-")

# 命名里带这些词的模型多为低模/无贴图，质感差，排除
_LOWPOLY = ("lowpoly", "low poly", "low-poly", "psx", "ps1", "ps2", "blocky", "flat")


def _http_bytes(url: str, token: str | None = None, timeout: int = 120) -> bytes:
    headers = {"User-Agent": UA}
    if token:
        headers["Authorization"] = f"Token {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _http_json(url: str, token: str | None = None):
    return json.loads(_http_bytes(url, token).decode("utf-8"))


def _is_free_license(lic: dict) -> bool:
    label = (lic.get("label") or "").lower()
    if not label:
        return False
    if any(k in label for k in _BAD_LICENSE):
        return False
    return label.startswith("cc")


def search_candidates(keywords: str, token: str, count: int = 24) -> list:
    """返回该品类下 downloadable + 免费许可 + 有 glb 的候选模型（按大小升序）。"""
    import urllib.parse
    q = urllib.parse.quote(keywords)
    data = _http_json(f"{SEARCH_URL}?type=models&q={q}&downloadable=true&count={count}", token)
    out = []
    for m in data.get("results", []):
        if not m.get("isDownloadable"):
            continue
        if not _is_free_license(m.get("license", {})):
            continue
        glb = (m.get("archives") or {}).get("glb")
        if not glb:
            continue
        out.append({
            "uid": m["uid"],
            "name": m.get("name", ""),
            "size": glb.get("size", 0),
            "texture_max": glb.get("textureMaxResolution"),
            "license": m.get("license", {}).get("label", ""),
            "tags": [t.get("name", "") for t in m.get("tags", [])],
        })
    out.sort(key=lambda x: x["size"])
    return out


def pick_best(candidates: list, max_mb: int):
    """在候选里挑一个质感最好的：排除 lowpoly 命名、<0.3MB 的贴图缺失低模，
    再在体积上限内选细节最丰富（体积最大）的模型。"""
    min_bytes = 300_000  # 0.3MB 以下视为无贴图低模
    good = [c for c in candidates
            if c["size"] >= min_bytes
            and not any(k in c["name"].lower() for k in _LOWPOLY)]
    pool = good or candidates
    within = [c for c in pool if c["size"] <= max_mb * 1024 * 1024]
    if within:
        return max(within, key=lambda c: c["size"])   # 细节更丰富
    return min(pool, key=lambda c: c["size"])          # 都超限时取最小的


def download_glb(uid: str, token: str) -> bytes:
    """调用官方下载接口，取 glb 的签名 URL 并下载。"""
    info = _http_json(f"{API_URL}/{uid}/download", token)
    glb = info.get("glb") or info.get("gltf") or {}
    url = glb.get("url")
    if not url:  # 有些返回结构不同，兜底找第一个带 url 的项
        for v in info.values():
            if isinstance(v, dict) and v.get("url"):
                url = v["url"]
                break
    if not url:
        raise RuntimeError("下载接口未返回文件 URL：" + json.dumps(info)[:200])
    return _http_bytes(url)  # 签名 URL 不需要 token，但带 UA


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", default=os.environ.get("SKETCHFAB_TOKEN"))
    ap.add_argument("--max-mb", type=int, default=20, help="单个 glb 的体积上限（MB）")
    ap.add_argument("--limit", type=int, default=0, help="最多下载的品类数（0=全部）")
    args = ap.parse_args()

    if not args.token:
        raise SystemExit("缺少 Sketchfab API Token：请设置环境变量 SKETCHFAB_TOKEN 或传 --token")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    mapping = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        if args.limit and len(mapping) >= args.limit:
            break
        try:
            cands = search_candidates(keywords, args.token)
            best = pick_best(cands, args.max_mb)
            if not best:
                print(f"  [跳过] {category:<6} 无合适模型")
                continue
            raw = download_glb(best["uid"], args.token)
            dest = MODELS_DIR / f"{best['uid']}.glb"
            dest.write_bytes(raw)
            mapping.append({
                "category": category,
                "uid": best["uid"],
                "name": best["name"],
                "size_mb": round(best["size"] / 1024 / 1024, 1),
                "license": best["license"],
                "source_url": f"https://sketchfab.com/3d-models/{best['uid']}",
                "local_glb": str(dest.relative_to(BASE)).replace("\\", "/"),
            })
            print(f"  [OK] {category:<6} <- {best['name']} ({best['size'] / 1024 / 1024:.1f}MB, {best['license']})")
        except Exception as e:
            print(f"  [失败] {category} <- {e}")

    out = BASE / "data" / "sketchfab_models.json"
    out.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已下载 {len(mapping)} 个模型，映射写入 {out}")


if __name__ == "__main__":
    main()
