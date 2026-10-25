"""室内设计 Agent 入口。

示例：
    python main.py                                    # 默认：客厅 5x6 北欧现代简约
    python main.py --room 卧室 --width 4 --length 5 --style 日式原木
    python main.py --room 客厅 --style 中式 --budget 8万 --notes 要一个阅读角
    python main.py --offline                          # 强制离线设计器（无需任何 API 密钥）
"""
from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

import argparse  # noqa: E402

import config  # noqa: E402
from src.pipeline import run_pipeline  # noqa: E402
from src.schemas import DesignConstraint  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="室内设计 Agent：语言设计 → RAG 选家具 → CAD 建模")
    ap.add_argument("--room", default="客厅", help="房间类型（客厅/卧室/餐厅/书房）")
    ap.add_argument("--width", type=float, default=5.0, help="房间宽度（米）")
    ap.add_argument("--length", type=float, default=6.0, help="房间进深（米）")
    ap.add_argument("--style", default="北欧现代简约", help="期望风格")
    ap.add_argument("--budget", default=None, help="预算")
    ap.add_argument("--occupants", default=None, help="使用人群/人数")
    ap.add_argument("--notes", default=None, help="额外约束")
    ap.add_argument("--offline", action="store_true", help="强制离线设计器")
    args = ap.parse_args()

    if args.offline:
        config.LLM_PROVIDER = "offline"

    constraint = DesignConstraint(
        room_type=args.room, width=args.width, length=args.length, style=args.style,
        budget=args.budget, occupants=args.occupants, notes=args.notes,
    )

    result = run_pipeline(constraint)

    print("\n" + "=" * 56)
    print("完成")
    print("=" * 56)
    print(f"  设计方案 JSON : {result.plan_path}")
    print(f"  家具摆放 JSON : {result.placements_path}")
    print(f"  CAD 图纸 DXF  : {result.dxf_path}")
    print("  提示：用 AutoCAD / LibreCAD / 在线查看器打开 .dxf 即可查看平面图。")


if __name__ == "__main__":
    main()
