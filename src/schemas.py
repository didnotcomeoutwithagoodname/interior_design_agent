"""领域数据模型（Pydantic）。"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class Zone(BaseModel):
    """房间内的功能区。坐标：房间左下角为原点 (0,0)，单位米。"""
    name: str = Field(description="区域名称，如 会客区/睡眠区/用餐区/工作区/收纳区")
    function: str = Field(description="区域功能，如 seating/sleeping/dining/working/storage/reading")
    x: float = Field(description="区域中心 x 坐标（米）")
    y: float = Field(description="区域中心 y 坐标（米）")
    width: float = Field(description="区域宽度（米）")
    length: float = Field(description="区域进深（米）")


class FurnitureRequirement(BaseModel):
    """对家具的抽象需求，由设计阶段产生，RAG 阶段据此检索实物。"""
    category: str = Field(description="家具品类，如 沙发/床/餐桌/餐椅/书桌/办公椅/衣柜/书架/茶几/电视柜/单椅/床头柜")
    style_tags: List[str] = Field(description="风格标签，如 [北欧, 简约]")
    count: int = Field(default=1, description="需要的数量")
    zone: Optional[str] = Field(default=None, description="建议放置的区域名称")


class Room(BaseModel):
    name: str = Field(description="房间名称，如 客厅/卧室/餐厅/书房")
    width: float = Field(description="房间宽度（米）")
    length: float = Field(description="房间进深（米）")
    zones: List[Zone] = Field(default_factory=list)
    furniture_requirements: List[FurnitureRequirement] = Field(default_factory=list)
    flooring: str = Field(default="", description="地面材质/铺装，如 浅色橡木地板/浅灰瓷砖")


class DesignConstraint(BaseModel):
    """用户输入的设计约束。"""
    room_type: str = Field(default="客厅", description="主要房间类型")
    width: float = Field(default=5.0, description="房间宽度（米）")
    length: float = Field(default=6.0, description="房间进深（米）")
    style: str = Field(default="北欧现代简约", description="期望风格")
    budget: Optional[str] = Field(default=None, description="预算，如 3万元")
    occupants: Optional[str] = Field(default=None, description="使用人群 / 人数")
    notes: Optional[str] = Field(default=None, description="额外约束 / 需求")


class DesignPlan(BaseModel):
    """设计阶段的最终产物。"""
    style: str = Field(description="最终确定的设计风格")
    design_narrative: str = Field(description="设计说明（自然语言描述）")
    rooms: List[Room] = Field(description="房间与分区设计")
