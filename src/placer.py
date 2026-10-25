"""阶段二末：把检索到的家具摆进分区（互不重叠 + 按功能合理摆放 + 靠墙）。

摆放策略：按分区功能分派，而不是无差别地「货架式装箱」——
- 睡眠区（卧室）：床靠墙居中、床头柜分列两侧、挂饰在床头正上方贴墙、
  单椅放在床尾角落；
- 会客区（客厅）：沙发背靠后墙、电视柜正对沙发贴对侧、茶几居中在沙发前，
  挂饰在沙发上方，装饰品/单椅在两侧角落；
- 用餐区（餐厅）：餐桌居中，餐椅沿长边两侧环绕；
- 工作区（书房）：书桌靠墙，办公椅在书桌前，挂饰/装饰品/单椅点缀；
- 收纳区：衣柜/书架贴墙并排；
- 阅读角：书架贴墙，单椅在其旁侧。

「靠墙」是关键：房间被横向划分为上下堆叠的分区，只有最上面的分区贴后墙、
最下面的分区贴前墙。靠墙家具（床、衣柜、书架、沙发、书桌）要贴到该分区真正
接触的那面墙（而不是盲目贴分区上边——那可能只是分区之间的通道）。
无法识别功能的分区回退到货架式装箱。所有结果最后做两两重叠校验。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from src.furniture_db import Furniture, FurnitureStore
from src.schemas import DesignPlan, FurnitureRequirement, Room, Zone

# 品类 -> 适宜分区功能
_CATEGORY_FUNCTION = {
    "沙发": "seating", "茶几": "seating", "电视柜": "seating", "单椅": "seating",
    "床": "sleeping", "床头柜": "sleeping", "衣柜": "storage",
    "餐桌": "dining", "餐椅": "dining",
    "书桌": "working", "办公椅": "working", "书架": "working",
}


@dataclass
class Placement:
    furniture: Furniture
    x: float
    y: float
    zone: Zone
    rotation: float = 0.0


class Placer:
    GAP = 0.2        # 家具之间的最小间距（米）
    MARGIN = 0.15    # 分区内边距（米）
    WALL_GAP = 0.05  # 靠墙家具与墙边的额外间距（米）

    def __init__(self, store: FurnitureStore):
        self.store = store

    # ---- 分区定位 ----
    def _find_zone(self, room: Room, req: FurnitureRequirement) -> Zone:
        if req.zone:
            for z in room.zones:
                if z.name == req.zone:
                    return z
        target = _CATEGORY_FUNCTION.get(req.category)
        for z in room.zones:
            if z.function == target:
                return z
        if req.category in ("书架", "单椅"):
            for z in room.zones:
                if z.function == "reading":
                    return z
        if room.zones:
            return room.zones[0]
        return Zone(name="全屋", function="any", x=room.width / 2, y=room.length / 2,
                    width=room.width, length=room.length)

    # ---- 主流程 ----
    def place(self, plan: DesignPlan) -> List[Placement]:
        placements: List[Placement] = []
        for room in plan.rooms:
            placements.extend(self._place_room(room))
        self._verify(placements)
        return placements

    def _place_room(self, room: Room) -> List[Placement]:
        # 把每项需求检索到实体家具，并按目标分区汇总（同一分区的家具一起摆放）
        by_zone: Dict[str, List[Furniture]] = {}
        zone_of: Dict[str, Zone] = {}
        for req in room.furniture_requirements:
            candidates = self.store.retrieve(req)
            if not candidates:
                print(f"[place] 警告：未找到「{req.category}」的匹配家具，跳过。")
                continue
            best = candidates[0]
            zone = self._find_zone(room, req)
            by_zone.setdefault(zone.name, []).extend([best] * req.count)
            zone_of[zone.name] = zone

        out: List[Placement] = []
        for zname, items in by_zone.items():
            out.extend(self._place_zone(room, zone_of[zname], items))
        return out

    # ---- 判断分区贴靠哪面墙 ----
    @staticmethod
    def _wall_flags(room: Room, zone: Zone):
        """分区是否贴后墙(y=0) / 前墙(y=length)。"""
        back = (zone.y - zone.length / 2) <= 0.35
        front = (zone.y + zone.length / 2) >= room.length - 0.35
        return back, front

    @staticmethod
    def _wall_edge(zone: Zone, back: bool, front: bool):
        """返回该分区家具应贴靠的墙边 y 坐标与延伸方向符号。

        sign=+1 表示家具从上边向室内（向下）延伸，-1 反之。
        """
        if back:
            return zone.y - zone.length / 2, +1
        if front:
            return zone.y + zone.length / 2, -1
        return zone.y - zone.length / 2, +1  # 中间分区默认靠上边

    # ---- 按分区功能分派 ----
    def _place_zone(self, room: Room, zone: Zone, items: List[Furniture]) -> List[Placement]:
        fn = {
            "sleeping": self._place_sleeping,
            "seating": self._place_seating,
            "dining": self._place_dining,
            "working": self._place_working,
            "storage": self._place_storage,
            "reading": self._place_reading,
        }.get(zone.function)
        if fn is None:
            return self._pack(zone, items)
        back, front = self._wall_flags(room, zone)
        return fn(zone, items, back, front)

    # ---- 工具 ----
    def _put(self, f: Furniture, x: float, y: float, zone: Zone) -> Placement:
        return Placement(f, round(x, 3), round(y, 3), zone)

    @staticmethod
    def _group(items: List[Furniture]) -> Dict[str, List[Furniture]]:
        g: Dict[str, List[Furniture]] = {}
        for f in items:
            g.setdefault(f.category, []).append(f)
        return g

    # ---- 睡眠区：床 + 床头柜 + 挂饰 + 单椅 ----
    def _place_sleeping(self, zone: Zone, items: List[Furniture],
                        back: bool, front: bool) -> List[Placement]:
        by = self._group(items)
        top = zone.y - zone.length / 2
        bottom = zone.y + zone.length / 2
        edge, sign = self._wall_edge(zone, back, front)
        out: List[Placement] = []

        bed = by.get("床", [None])[0]
        if bed:
            bx = zone.x
            by_ = edge + sign * (self.WALL_GAP + bed.depth / 2)
            out.append(self._put(bed, bx, by_, zone))
            # 床头柜分列两侧、与床头对齐
            for i, ns in enumerate(by.get("床头柜", [])[:2]):
                side = -1 if i == 0 else 1
                nx = bx + side * (bed.width / 2 + ns.width / 2 + 0.05)
                ny = edge + sign * (self.WALL_GAP + ns.depth / 2)
                out.append(self._put(ns, nx, ny, zone))

        # 挂饰：床头正上方贴墙
        for a in by.get("挂饰", []):
            out.append(self._put(a, zone.x, edge - sign * 0.05, zone))

        # 单椅：床尾角落（与床头相对的一侧）
        for c in by.get("单椅", []):
            cx = zone.x + zone.width / 2 - self.MARGIN - c.width / 2
            cy = (bottom - self.MARGIN - c.depth / 2) if sign == +1 \
                else (top + self.MARGIN + c.depth / 2)
            out.append(self._put(c, cx, cy, zone))

        rest = [f for f in items if f.category not in ("床", "床头柜", "挂饰", "单椅")]
        out.extend(self._pack(zone, rest))
        return out

    # ---- 会客区：沙发 / 电视柜 / 茶几 / 挂饰 / 装饰品 / 单椅 ----
    def _place_seating(self, zone: Zone, items: List[Furniture],
                       back: bool, front: bool) -> List[Placement]:
        by = self._group(items)
        left = zone.x - zone.width / 2
        right = zone.x + zone.width / 2
        top = zone.y - zone.length / 2
        bottom = zone.y + zone.length / 2
        edge, sign = self._wall_edge(zone, back, front)
        out: List[Placement] = []

        sofa = by.get("沙发", [None])[0]
        sofa_front = None
        if sofa:
            sy = edge + sign * (self.WALL_GAP + sofa.depth / 2)
            out.append(self._put(sofa, zone.x, sy, zone))
            sofa_front = sy + sign * sofa.depth / 2

        # 电视柜正对沙发，贴在沙发对侧
        tv = by.get("电视柜", [None])[0]
        tv_front = None
        if tv:
            opp_edge = bottom if sign == +1 else top
            ty = opp_edge - sign * (self.MARGIN + tv.depth / 2)
            out.append(self._put(tv, zone.x, ty, zone))
            tv_front = ty - sign * tv.depth / 2  # 朝向沙发的一侧

        # 茶几在沙发正前方约 0.4m；放不下时作为边几放到左下角落
        for cf in by.get("茶几", []):
            if sofa_front is not None:
                limit = tv_front if tv_front is not None else (bottom if sign == +1 else top)
                if abs(limit - sofa_front) >= cf.depth + 2 * self.GAP:
                    cy = sofa_front + sign * (self.GAP + cf.depth / 2)
                else:
                    out.append(self._put(cf, left + self.MARGIN + cf.width / 2,
                                         bottom - self.MARGIN - cf.depth / 2, zone))
                    continue
            else:
                cy = zone.y
            out.append(self._put(cf, zone.x, cy, zone))

        # 挂饰：沙发上方贴墙
        for a in by.get("挂饰", []):
            out.append(self._put(a, zone.x, edge - sign * 0.05, zone))

        # 装饰品 / 单椅：两侧角落
        for d in by.get("装饰品", []):
            out.append(self._put(d, left + self.MARGIN + d.width / 2,
                                 top + self.MARGIN + d.depth / 2, zone))
        for c in by.get("单椅", []):
            out.append(self._put(c, right - self.MARGIN - c.width / 2,
                                 top + self.MARGIN + c.depth / 2, zone))

        rest = [f for f in items if f.category not in
                ("沙发", "电视柜", "茶几", "挂饰", "装饰品", "单椅")]
        out.extend(self._pack(zone, rest))
        return out

    # ---- 用餐区：餐桌 + 餐椅环绕 ----
    def _place_dining(self, zone: Zone, items: List[Furniture],
                      back: bool, front: bool) -> List[Placement]:
        by = self._group(items)
        right = zone.x + zone.width / 2
        top = zone.y - zone.length / 2
        edge, sign = self._wall_edge(zone, back, front)
        out: List[Placement] = []

        table = by.get("餐桌", [None])[0]
        chairs = by.get("餐椅", [])
        if table:
            out.append(self._put(table, zone.x, zone.y, zone))
            # 餐椅沿两条长边（上/下）环绕，各占一半
            top_chairs = chairs[0::2]
            bot_chairs = chairs[1::2]

            def place_side(chair_list: List[Furniture], s: int):
                m = len(chair_list)
                span = max(table.width - 0.2, 0.0)
                for j, ch in enumerate(chair_list):
                    cx = zone.x if m == 1 else zone.x - span / 2 + span * j / (m - 1)
                    cy = zone.y + s * (table.depth / 2 + ch.depth / 2 + 0.1)
                    out.append(self._put(ch, cx, cy, zone))

            place_side(top_chairs, -1)
            place_side(bot_chairs, +1)

        for a in by.get("挂饰", []):
            out.append(self._put(a, zone.x, edge - sign * 0.05, zone))
        for d in by.get("装饰品", []):
            out.append(self._put(d, right - self.MARGIN - d.width / 2,
                                 top + self.MARGIN + d.depth / 2, zone))

        rest = [f for f in items if f.category not in ("餐桌", "餐椅", "挂饰", "装饰品")]
        out.extend(self._pack(zone, rest))
        return out

    # ---- 工作区：书桌 + 办公椅 + 挂饰 + 装饰品 + 单椅 ----
    def _place_working(self, zone: Zone, items: List[Furniture],
                       back: bool, front: bool) -> List[Placement]:
        by = self._group(items)
        left = zone.x - zone.width / 2
        right = zone.x + zone.width / 2
        top = zone.y - zone.length / 2
        bottom = zone.y + zone.length / 2
        edge, sign = self._wall_edge(zone, back, front)
        out: List[Placement] = []

        desk = by.get("书桌", [None])[0]
        if desk:
            dx = zone.x
            dy = edge + sign * (self.WALL_GAP + desk.depth / 2)
            out.append(self._put(desk, dx, dy, zone))
            for c in by.get("办公椅", []):
                out.append(self._put(c, dx, dy + sign * (desk.depth / 2 + 0.1 + c.depth / 2), zone))

        for a in by.get("挂饰", []):
            out.append(self._put(a, zone.x, edge - sign * 0.05, zone))
        for d in by.get("装饰品", []):
            out.append(self._put(d, left + self.MARGIN + d.width / 2,
                                 top + self.MARGIN + d.depth / 2, zone))
        for c in by.get("单椅", []):
            out.append(self._put(c, right - self.MARGIN - c.width / 2,
                                 bottom - self.MARGIN - c.depth / 2, zone))

        rest = [f for f in items if f.category not in
                ("书桌", "办公椅", "挂饰", "装饰品", "单椅")]
        out.extend(self._pack(zone, rest))
        return out

    # ---- 收纳区：衣柜 / 书架贴墙并排 ----
    def _place_storage(self, zone: Zone, items: List[Furniture],
                       back: bool, front: bool) -> List[Placement]:
        left = zone.x - zone.width / 2
        edge, sign = self._wall_edge(zone, back, front)
        out: List[Placement] = []
        cur_x = left + self.MARGIN
        for f in sorted(items, key=lambda f: -f.width):
            cy = edge + sign * (self.WALL_GAP + f.depth / 2)
            out.append(self._put(f, cur_x + f.width / 2, cy, zone))
            cur_x += f.width + self.GAP
        return out

    # ---- 阅读角：书架贴墙 + 单椅旁侧 ----
    def _place_reading(self, zone: Zone, items: List[Furniture],
                       back: bool, front: bool) -> List[Placement]:
        by = self._group(items)
        left = zone.x - zone.width / 2
        edge, sign = self._wall_edge(zone, back, front)
        out: List[Placement] = []

        shelf = by.get("书架", [None])[0]
        if shelf:
            out.append(self._put(shelf, left + self.MARGIN + shelf.width / 2,
                                 edge + sign * (self.WALL_GAP + shelf.depth / 2), zone))
        for c in by.get("单椅", []):
            sx = left + self.MARGIN + (shelf.width if shelf else 0) + self.GAP + c.width / 2
            out.append(self._put(c, sx, edge + sign * (self.WALL_GAP + c.depth / 2), zone))

        rest = [f for f in items if f.category not in ("书架", "单椅")]
        out.extend(self._pack(zone, rest))
        return out

    # ---- 无重叠装箱（兜底） ----
    def _pack(self, zone: Zone, items: List[Furniture]) -> List[Placement]:
        # 大件优先（先按进深再按宽度降序），让床/沙发等大件先落地
        items = sorted(items, key=lambda f: (-f.depth, -f.width))

        x0 = zone.x - zone.width / 2 + self.MARGIN
        y0 = zone.y - zone.length / 2 + self.MARGIN
        max_x = zone.x + zone.width / 2 - self.MARGIN
        max_y = zone.y + zone.length / 2 - self.MARGIN

        cur_x, cur_y, row_h = x0, y0, 0.0
        out: List[Placement] = []
        for f in items:
            if cur_x > x0 and cur_x + f.width > max_x:
                cur_x = x0
                cur_y += row_h + self.GAP
                row_h = 0.0
            if cur_y + f.depth > max_y:
                print(f"[place] 警告：分区「{zone.name}」空间不足，「{f.name}」超出分区范围"
                      f"（但不会与其他家具重叠）。")
            out.append(Placement(f, round(cur_x + f.width / 2, 3),
                                 round(cur_y + f.depth / 2, 3), zone))
            cur_x += f.width + self.GAP
            row_h = max(row_h, f.depth)
        return out

    # ---- 重叠校验 ----
    @staticmethod
    def _bbox(p: Placement):
        w, d = p.furniture.width, p.furniture.depth
        return p.x - w / 2, p.y - d / 2, p.x + w / 2, p.y + d / 2

    def _verify(self, placements: List[Placement]) -> bool:
        bad = []
        for i in range(len(placements)):
            for j in range(i + 1, len(placements)):
                ax0, ay0, ax1, ay1 = self._bbox(placements[i])
                bx0, by0, bx1, by1 = self._bbox(placements[j])
                if ax0 < bx1 and ax1 > bx0 and ay0 < by1 and ay1 > by0:
                    bad.append((placements[i].furniture.name, placements[j].furniture.name))
        if bad:
            print(f"[place] 警告：检测到 {len(bad)} 组重叠：{bad}")
        else:
            print(f"[place] 校验通过：{len(placements)} 件家具互不重叠。")
        return not bad
