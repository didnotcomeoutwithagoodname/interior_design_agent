"""Render the design in output/ to a PNG floor-plan preview (same data as the DXF).

Usage:
    python preview.py                    # reads output/design_plan.json + placements.json
    python preview.py --out preview.png
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from src.labels_en import room_name_en, style_en  # noqa: E402

BASE = Path(__file__).resolve().parent


def _pick_cjk_font():
    for name in ("Microsoft YaHei", "SimHei", "SimSun", "Noto Sans CJK SC", "PingFang SC"):
        for f in font_manager.fontManager.ttflist:
            if f.name == name:
                return f.name
    return "DejaVu Sans"


def render(plan_path: Path, placements_path: Path, out_path: Path):
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    placements = json.loads(placements_path.read_text(encoding="utf-8"))

    font = _pick_cjk_font()
    plt.rcParams["font.sans-serif"] = [font, "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(10, 8))

    for room in plan["rooms"]:
        w, l = room["width"], room["length"]
        # 墙体（房间外框）
        ax.add_patch(Rectangle((0, 0), w, l, fill=False, edgecolor="#c0392b", linewidth=3))
        ax.text(w / 2, l + 0.25, f"{room_name_en(room['name'])}  {w}×{l} m",
                ha="center", va="bottom", fontsize=14, fontweight="bold", color="#2c3e50")

        # 功能分区（蓝色虚线）
        for z in room["zones"]:
            ax.add_patch(Rectangle((z["x"] - z["width"] / 2, z["y"] - z["length"] / 2),
                                   z["width"], z["length"], fill=False,
                                   edgecolor="#2980b9", linewidth=1.5, linestyle="--"))
            ax.text(z["x"], z["y"] + z["length"] / 2 + 0.15, z["name"],
                    ha="center", va="bottom", fontsize=9, color="#2980b9")

    # 家具（绿色块 + 名称）
    for p in placements:
        w, d = p["width"], p["depth"]
        x, y = p["x"], p["y"]
        ax.add_patch(Rectangle((x - w / 2, y - d / 2), w, d,
                               facecolor="#a9dfbf", edgecolor="#1e8449", linewidth=1.5))
        ax.text(x, y, p["name"], ha="center", va="center", fontsize=8, color="#145a32")

    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("x (m)", fontsize=10)
    ax.set_ylabel("y (m)", fontsize=10)
    ax.set_title(f"Interior Floor Plan · Style: {style_en(plan.get('style', ''))}", fontsize=15, pad=12)
    ax.grid(True, which="both", linestyle=":", linewidth=0.5, alpha=0.4)
    ax.margins(0.15)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Preview image generated: {out_path.resolve()}")


def main():
    ap = argparse.ArgumentParser(description="Render the interior floor-plan preview image")
    ap.add_argument("--out", default=str(BASE / "output" / "preview.png"))
    args = ap.parse_args()
    render(BASE / "output" / "design_plan.json",
           BASE / "output" / "placements.json",
           Path(args.out))


if __name__ == "__main__":
    main()
