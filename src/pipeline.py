"""端到端编排：设计 → RAG 检索摆放 → CAD 建模。"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import config
from src.cad_builder import CADBuilder
from src.design_agent import DesignAgent
from src.furniture_db import FurnitureStore
from src.placer import Placement, Placer
from src.schemas import DesignConstraint, DesignPlan


@dataclass
class PipelineResult:
    plan: DesignPlan
    placements: List[Placement] = field(default_factory=list)
    dxf_path: Path | None = None
    plan_path: Path | None = None
    placements_path: Path | None = None


def run_pipeline(constraint: DesignConstraint) -> PipelineResult:
    # ---- 阶段一：语言设计 ----
    print("=" * 56)
    print("阶段 1/3 —— 语言设计")
    print("=" * 56)
    plan = DesignAgent().design(constraint)
    print(f"风格：{plan.style}")
    print(f"设计说明：{plan.design_narrative}")

    # ---- 阶段二：RAG 检索 + 摆放 ----
    print("\n" + "=" * 56)
    print("阶段 2/3 —— RAG 检索家具并摆放")
    print("=" * 56)
    store = FurnitureStore()
    placements = Placer(store).place(plan)
    for p in placements:
        print(f"  {p.furniture.name:<18} 品类[{p.furniture.category}] "
              f"风格[{p.furniture.style}] → ({p.x:.2f}, {p.y:.2f}) @ {p.zone.name}")

    # ---- 阶段三：CAD 建模 ----
    print("\n" + "=" * 56)
    print("阶段 3/3 —— CAD 建模（DXF）")
    print("=" * 56)
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    dxf_path = CADBuilder().build(plan, placements, config.OUTPUT_DIR / "design.dxf")

    plan_path = config.OUTPUT_DIR / "design_plan.json"
    plan_path.write_text(plan.model_dump_json(indent=2, ensure_ascii=False), encoding="utf-8")

    placements_path = config.OUTPUT_DIR / "placements.json"
    placements_data = [
        {**p.furniture.to_dict(), "x": p.x, "y": p.y, "rotation": p.rotation, "zone": p.zone.name}
        for p in placements
    ]
    placements_path.write_text(
        json.dumps(placements_data, ensure_ascii=False, indent=2), encoding="utf-8")

    return PipelineResult(
        plan=plan, placements=placements,
        dxf_path=dxf_path, plan_path=plan_path, placements_path=placements_path,
    )
