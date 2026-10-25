"""阶段三：CAD 建模。用 ezdxf 把设计图渲染成标准 DXF 文件（AutoCAD 可直接打开）。

图层约定：
- WALLS     墙体（红色）
- ZONES     功能分区（蓝色虚线）
- FURNITURE 家具（绿色块）
- LABELS    文字标注
- ANNOT     图框与标题
单位：1 DXF 单位 = 1 米。
"""
from __future__ import annotations

from pathlib import Path
from typing import List

import ezdxf
from ezdxf.enums import TextEntityAlignment

from src.placer import Placement
from src.schemas import DesignPlan

_LAYERS = {"WALLS": 1, "ZONES": 5, "FURNITURE": 3, "LABELS": 7, "ANNOT": 7}


class CADBuilder:
    def __init__(self):
        self.doc = ezdxf.new("R2010", setup=True)
        for name, color in _LAYERS.items():
            if name not in self.doc.layers:
                self.doc.layers.add(name, color=color)
        self.msp = self.doc.modelspace()

    # ---- 基础图元 ----
    def _rect(self, cx, cy, w, l, layer, linetype=None):
        pts = [
            (cx - w / 2, cy - l / 2),
            (cx + w / 2, cy - l / 2),
            (cx + w / 2, cy + l / 2),
            (cx - w / 2, cy + l / 2),
        ]
        attrs = {"layer": layer}
        if linetype:
            attrs["linetype"] = linetype
        self.msp.add_lwpolyline(pts, close=True, dxfattribs=attrs)

    def _text(self, x, y, text, height=0.22, layer="LABELS",
              align=TextEntityAlignment.MIDDLE_CENTER):
        t = self.msp.add_text(text, dxfattribs={"height": height, "layer": layer})
        t.set_placement((x, y), align=align)
        return t

    # ---- 房间与分区 ----
    def _draw_room(self, room):
        # 墙体：房间左下角在 (0,0)
        self._rect(room.width / 2, room.length / 2, room.width, room.length, "WALLS")
        self._text(room.width / 2, room.length + 0.4, room.name, height=0.32, layer="LABELS")
        flooring = getattr(room, "flooring", "") or "未指定"
        self._text(room.width / 2, room.length + 0.15, f"地面：{flooring}",
                   height=0.16, layer="LABELS")

        for z in room.zones:
            self._rect(z.x, z.y, z.width, z.length, "ZONES", linetype="DASHED")
            self._text(z.x, z.y + z.length / 2 + 0.15, z.name, height=0.16, layer="LABELS")

    # ---- 家具 ----
    def _furniture_block(self, furniture) -> str:
        name = "FURN_" + furniture.id
        if name in self.doc.blocks:
            return name
        blk = self.doc.blocks.new(name=name)
        w, d = furniture.width, furniture.depth
        blk.add_lwpolyline(
            [(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)],
            close=True,
        )
        return name

    def _draw_furniture(self, placements: List[Placement]):
        for p in placements:
            f = p.furniture
            block = self._furniture_block(f)
            self.msp.add_blockref(block, insert=(p.x, p.y),
                                  dxfattribs={"layer": "FURNITURE", "rotation": p.rotation})
            self._text(p.x, p.y - f.depth / 2 - 0.12, f.name, height=0.14, layer="LABELS")

    # ---- 图框 ----
    def _draw_frame(self, plan: DesignPlan):
        max_x = max((r.width for r in plan.rooms), default=5.0) + 1.5
        max_y = max((r.length for r in plan.rooms), default=6.0) + 2.0
        self.msp.add_lwpolyline(
            [(-0.5, -0.5), (max_x, -0.5), (max_x, max_y), (-0.5, max_y)],
            close=True, dxfattribs={"layer": "ANNOT"},
        )
        self._text(max_x / 2, max_y - 0.35,
                   f"室内设计平面图  风格：{plan.style}  单位：米",
                   height=0.3, layer="ANNOT")

    def build(self, plan: DesignPlan, placements: List[Placement], out_path: Path) -> Path:
        for room in plan.rooms:
            self._draw_room(room)
        self._draw_furniture(placements)
        self._draw_frame(plan)
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        self.doc.saveas(str(out_path))
        return out_path
