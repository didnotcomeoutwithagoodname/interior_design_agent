"""阶段一：语言设计。

根据用户约束，先用自然语言给出设计构思，再输出结构化 DesignPlan。
- 有 LLM 时走「手动 JSON 模式」：把 src/design_knowledge.py 里的
  人体工学净空/动线/风格/标准尺寸知识注入系统提示，用 response_format=json_object
  + 精确 JSON 示例让模型直接输出结构化方案，再手动解析并做品类归一化、分区钳制；
- 否则用确定性离线设计器，按「房间类型 + 面积」自适应生成分区与家具需求，
  并做可行性校验（家具占地占比），保证无密钥也能产出合理方案。
"""
from __future__ import annotations

import json
import re
from typing import List

from src import design_knowledge as dk
from src.llm import get_llm
from src.schemas import DesignConstraint, DesignPlan, FurnitureRequirement, Room, Zone

# 合法家具品类，要求 LLM 严格使用这些词，便于后续与家具库精确匹配
CATEGORIES = ["沙发", "床", "餐桌", "餐椅", "书桌", "办公椅", "衣柜", "书架", "茶几", "电视柜", "单椅", "床头柜", "挂饰", "装饰品"]

_BASE_SYSTEM_PROMPT = """你是一名资深室内设计师。先根据约束构思设计，再输出结构化方案。

要求：
1. 坐标系：房间左下角为原点 (0,0)，x 向右、y 向上，单位米。每个 zone 的矩形必须完全落在房间内部：
   zone.x - width/2 ≥ 0 且 zone.x + width/2 ≤ 房间宽，zone.y - length/2 ≥ 0 且 zone.y + length/2 ≤ 房间进深。
2. 把房间划分为若干功能区（如 会客区、睡眠区、用餐区、工作区、收纳区、阅读角），zone.function 用英文：
   seating / sleeping / dining / working / storage / reading。
3. 关键：每个功能区的家具必须写进 room.furniture_requirements 列表，该列表不能为空。
   每件家具 category 必须是以下之一、一字不差，count 为整数，zone 填所属功能区名：
   沙发、床、餐桌、餐椅、书桌、办公椅、衣柜、书架、茶几、电视柜、单椅、床头柜、挂饰、装饰品
   示例（会客区要三件）：{"category":"沙发","count":1,"zone":"会客区","style_tags":["北欧","简约"]}、
   {"category":"茶几","count":1,"zone":"会客区","style_tags":["北欧","简约"]}、
   {"category":"电视柜","count":1,"zone":"会客区","style_tags":["北欧","简约"]}。
   用餐区必须配 餐椅（≥2），睡眠区必须配 床，工作区必须配 书桌 和 办公椅。
4. style_tags 用简短风格词（如 北欧、简约、中式、工业风、日式、田园、极简、现代），用于匹配家具库。
5. design_narrative 用自然语言写出整体构思，并结合下面的专业设计知识说明分区与动线安排。"""

# 系统提示 = 基础要求 + 专业背景知识 + 输出约束
SYSTEM_PROMPT = _BASE_SYSTEM_PROMPT + "\n\n" + dk.KNOWLEDGE_PROMPT + \
    "\n\n只输出符合给定 JSON 结构的对象，不要输出多余文字。"

# 手动 JSON 模式的输出格式：给出精确示例 + 硬性品类约束，再手动解析校验
_OUTPUT_FORMAT = """\
严格按下面的 JSON 结构输出（纯 JSON 对象，不要 Markdown 代码块、不要注释、不要多余文字），
字段名一字不差，坐标单位米且必须落在房间内：

{
  "style": "北欧现代简约",
  "design_narrative": "……",
  "rooms": [
    {
      "name": "卧室",
      "width": 4.0,
      "length": 5.0,
      "zones": [
        {"name": "睡眠区", "function": "sleeping", "x": 1.35, "y": 3.6, "width": 2.7, "length": 2.8}
      ],
      "furniture_requirements": [
        {"category": "床", "style_tags": ["北欧", "简约"], "count": 1, "zone": "睡眠区"},
        {"category": "床头柜", "style_tags": ["北欧", "简约"], "count": 2, "zone": "睡眠区"}
      ]
    }
  ]
}

【硬性约束】
- 每个 room 的 furniture_requirements 必须非空，列出该 room 各功能区需要的所有家具。
- category 只能从这 14 个词里选、一字不差：沙发、床、餐桌、餐椅、书桌、办公椅、衣柜、书架、茶几、电视柜、单椅、床头柜、挂饰、装饰品。
- 每个 room 增加 flooring 字段（地面材质，按风格：北欧=浅色橡木地板、日式=浅木色木地板、中式=深色实木地板、现代=浅灰瓷砖、工业风=水泥自流平、极简=哑光大理石地砖、田园=暖色木地板）。
- 每个房间建议配 1~2 件挂饰（挂画/挂钟/壁饰）和 1~2 件装饰品（绿植/花瓶/摆件）。
- 禁止使用其它词：双人床/单人床请写「床」；休闲椅/躺椅/扶手椅/床尾凳/沙发椅请写「单椅」；
  边几/角几/圆几请写「茶几」；梳妆台/写字台请写「书桌」；凳子/餐凳请写「餐椅」；
  电视/电视机请写「电视柜」；挂画/装饰画/壁画/挂钟/壁饰请写「挂饰」；绿植/盆栽/花瓶/摆件/雕塑请写「装饰品」。"""

# 品类别名 -> 规范品类（LLM 偶发用词不规范的兜底归一化）
_CATEGORY_ALIASES = {
    "双人床": "床", "单人床": "床", "大床": "床", "床垫": "床",
    "休闲椅": "单椅", "躺椅": "单椅", "扶手椅": "单椅", "床尾凳": "单椅",
    "沙发椅": "单椅", "单人沙发": "单椅", "长凳": "单椅",
    "梳妆台": "书桌", "写字台": "书桌", "工作台": "书桌",
    "边几": "茶几", "角几": "茶几", "圆几": "茶几",
    "电视": "电视柜", "电视机": "电视柜",
    "梳妆凳": "餐椅", "餐凳": "餐椅", "凳子": "餐椅", "凳": "餐椅",
    "挂画": "挂饰", "装饰画": "挂饰", "壁画": "挂饰", "挂钟": "挂饰",
    "壁饰": "挂饰", "壁挂": "挂饰", "镜子": "挂饰",
    "绿植": "装饰品", "盆栽": "装饰品", "植物": "装饰品", "花瓶": "装饰品",
    "摆件": "装饰品", "雕塑": "装饰品",
}


def _normalize_categories(plan: DesignPlan) -> DesignPlan:
    """把 LLM 偶发输出的非规范品类归一化到 12 类，无法映射的丢弃。"""
    for room in plan.rooms:
        kept: List[FurnitureRequirement] = []
        for r in room.furniture_requirements:
            cat = (r.category or "").strip()
            if cat in CATEGORIES:
                r.category = cat
                kept.append(r)
            elif cat in _CATEGORY_ALIASES:
                r.category = _CATEGORY_ALIASES[cat]
                kept.append(r)
            else:
                print(f"[design] 忽略未识别的家具品类「{cat}」")
        room.furniture_requirements = kept
    return plan


def _clamp_zones(plan: DesignPlan) -> DesignPlan:
    """把每个 zone 的矩形钳制到房间内部，避免 LLM 把分区中心贴墙导致家具越出房间。"""
    for room in plan.rooms:
        W, L = room.width, room.length
        if W <= 0 or L <= 0:
            continue
        for z in room.zones:
            z.width = max(0.5, min(z.width, W))
            z.length = max(0.5, min(z.length, L))
            z.x = min(max(z.x, z.width / 2), W - z.width / 2)
            z.y = min(max(z.y, z.length / 2), L - z.length / 2)
    return plan


def _constraint_to_text(c: DesignConstraint) -> str:
    parts = [
        f"房间类型：{c.room_type}",
        f"房间尺寸：宽 {c.width} 米 × 进深 {c.length} 米",
        f"期望风格：{c.style}",
    ]
    if c.budget:
        parts.append(f"预算：{c.budget}")
    if c.occupants:
        parts.append(f"使用人群：{c.occupants}")
    if c.notes:
        parts.append(f"额外要求：{c.notes}")
    return "\n".join(parts)


def _feasibility_check(room_type: str, width: float, length: float,
                       reqs: List[FurnitureRequirement]) -> None:
    """可行性校验：家具占地占比一般 ≤50%，留出足够动线。"""
    area = width * length
    footprint = 0.0
    for r in reqs:
        dim = dk.FURNITURE_DIMENSIONS.get(r.category)
        if dim:
            footprint += dim[0] * dim[1] * r.count
    ratio = footprint / area if area else 0.0
    if ratio > 0.5:
        print(f"[design] 警告：{room_type} 家具占地 {footprint:.1f}㎡（{ratio:.0%}）超过 50%，"
              f"动线可能局促，建议减少大件家具或扩大房间。")
    else:
        print(f"[design] 可行性校验通过：家具占地 {footprint:.1f}㎡（{ratio:.0%}），留有充足动线。")


def _build_narrative(c: DesignConstraint, width: float, length: float,
                     zones: List[Zone], reqs: List[FurnitureRequirement],
                     tags: List[str]) -> str:
    """基于设计知识库生成更专业的设计说明。"""
    profile = dk.STYLE_PROFILES.get(tags[0]) if tags else None
    style_note = profile["note"] if profile else ""
    zone_desc = "、".join(f"{z.name}({z.function})" for z in zones)
    furniture_desc = "；".join(
        f"{r.zone}·{r.category}×{r.count}" for r in reqs)
    text = (
        f"采用「{c.style}」风格设计{c.room_type}（宽 {width}m × 进深 {length}m）。"
        f"整体以{'、'.join(tags)}为基调：{style_note}"
        f"按功能划分为 {len(zones)} 个区域——{zone_desc}；"
        f"家具配置为 {furniture_desc}。"
        f"动线遵循主通道 ≥0.9m、家具间 ≥0.6m 的净空原则，"
        f"大件贴墙、中间留出完整活动区。"
    )
    if c.budget:
        text += f" 预算控制在 {c.budget} 以内。"
    if c.occupants:
        text += f" 面向 {c.occupants} 使用。"
    return text


def mock_design(c: DesignConstraint) -> DesignPlan:
    """确定性离线设计器：按房间类型 + 面积生成合理分区与家具需求。"""
    room_type = c.room_type
    layouts = dk.ROOM_LAYOUTS.get(room_type) or dk.ROOM_LAYOUTS["客厅"]
    width, length = c.width, c.length
    area = width * length
    margin = dk.CLEARANCES["wall_margin"]  # 贴墙/贴边
    n = len(layouts)

    # ---- 分区：横向通宽分区，沿进深方向堆叠，按功能需要分配深度 ----
    gap = dk.CLEARANCES["secondary"]  # 0.6m 分区间次要通道
    ratios = dk.ZONE_LENGTH_RATIO.get(room_type)
    if not ratios or len(ratios) != n:
        ratios = [1.0] * n  # 未配置的房间类型则均分
    avail = length - 2 * margin - (n - 1) * gap
    zone_ls = [avail * r / sum(ratios) for r in ratios]
    if min(zone_ls) < 1.2:  # 房间过浅时压缩到最小通道，保证分区可用
        gap = 0.15
        avail = length - 2 * margin - (n - 1) * gap
        zone_ls = [avail * r / sum(ratios) for r in ratios]

    zones: List[Zone] = []
    y_cursor = margin
    for i, (zname, zfunc, _items) in enumerate(layouts):
        zl = zone_ls[i]
        zy = y_cursor + zl / 2
        zones.append(Zone(name=zname, function=zfunc,
                          x=round(width / 2, 2), y=round(zy, 2),
                          width=round(width - 2 * margin, 2),
                          length=round(zl, 2)))
        y_cursor += zl + gap

    # ---- 家具需求：基础布局 ----
    tags = dk.match_style_tags(c.style)
    reqs: List[FurnitureRequirement] = []
    for zname, _zfunc, items in layouts:
        for cat, count in items:
            reqs.append(FurnitureRequirement(category=cat, style_tags=list(tags),
                                             count=count, zone=zname))

    # ---- 面积自适应：大房间补充餐椅/单椅等 ----
    for zname, cat, extra, min_area in dk.ROOM_EXTRAS.get(room_type, []):
        if area >= min_area:
            existing = next((r for r in reqs if r.category == cat and r.zone == zname), None)
            if existing:
                existing.count += extra
            else:
                reqs.append(FurnitureRequirement(category=cat, style_tags=list(tags),
                                                 count=extra, zone=zname))

    # ---- 可行性校验 + 设计说明 ----
    _feasibility_check(room_type, width, length, reqs)
    narrative = _build_narrative(c, width, length, zones, reqs, tags)

    return DesignPlan(
        style=c.style,
        design_narrative=narrative,
        rooms=[Room(name=room_type, width=width, length=length,
                    zones=zones, furniture_requirements=reqs,
                    flooring=dk.match_style_flooring(c.style))],
    )


class DesignAgent:
    def __init__(self, llm=None):
        self.llm = llm if llm is not None else get_llm()

    def design(self, c: DesignConstraint) -> DesignPlan:
        if self.llm is None:
            print("[design] 未检测到 LLM，使用确定性离线设计器（内置设计知识库）。")
            return mock_design(c)

        try:
            # DeepSeek 只支持 response_format=json_object（不支持 OpenAI 的 json_schema），
            # 且 function_calling 偶发返回空 tool_call，故用「手动 JSON 模式」：
            # 绑定 json_object + 提示里给精确示例，拿到结果后手动解析并校验。
            llm_json = self.llm.bind(response_format={"type": "json_object"})
            resp = llm_json.invoke([
                ("system", SYSTEM_PROMPT + "\n\n" + _OUTPUT_FORMAT),
                ("human", _constraint_to_text(c)),
            ])
            text = resp.content if isinstance(getattr(resp, "content", None), str) else str(resp)
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
            data = json.loads(text)
            plan = _clamp_zones(_normalize_categories(DesignPlan.model_validate(data)))
            for room in plan.rooms:
                if not getattr(room, "flooring", ""):
                    room.flooring = dk.match_style_flooring(plan.style or c.style)

            total_furniture = sum(len(r.furniture_requirements) for r in plan.rooms)
            if total_furniture == 0:
                print("[design] LLM 未产出有效家具需求，回退到离线设计器。")
                return mock_design(c)
            return plan
        except Exception as e:  # 解析/校验失败时回退，保证可用
            print(f"[design] LLM 结构化输出失败（{e}），回退到离线设计器。")
            return mock_design(c)
