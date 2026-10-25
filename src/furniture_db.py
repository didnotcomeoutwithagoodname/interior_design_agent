"""阶段二：家具数据库 + RAG 检索。

- FurnitureStore 载入本地家具目录（JSON），并把每件家具的文本描述写入
  Chroma 向量库（持久化，避免重复建库）。
- retrieve() 以「品类 + 风格标签」为查询，用相似度检索 Top-K 候选，
  再用品类做硬约束过滤，返回风格相符的实物家具。
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import List, Optional

import config
from src.embeddings import get_embeddings
from src.schemas import FurnitureRequirement


class Furniture:
    """家具目录中的一件实体家具。"""

    def __init__(self, d: dict):
        self.id: str = d["id"]
        self.name: str = d["name"]
        self.category: str = d["category"]
        self.style: str = d["style"]
        self.style_tags: List[str] = d.get("style_tags", [])
        self.width: float = float(d.get("width_m", 1.0))
        self.depth: float = float(d.get("depth_m", 1.0))
        self.height: float = float(d.get("height_m", 1.0))
        self.material: str = d.get("material", "")
        self.price: str = d.get("price", "")
        self.description: str = d.get("description", "")

    def document_text(self) -> str:
        """构造用于 embedding 的文本。"""
        return " ".join([
            self.name,
            "品类:" + self.category,
            "风格:" + self.style,
            "标签:" + ",".join(self.style_tags),
            "材质:" + self.material,
            self.description,
        ])

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "category": self.category,
            "style": self.style, "style_tags": self.style_tags,
            "width": self.width, "depth": self.depth, "height": self.height,
            "material": self.material, "price": self.price, "description": self.description,
        }


# 品类别名：把 LLM 可能输出的各种写法归一为家具库中的规范品类
CATEGORY_ALIASES = {
    "沙发": "沙发", "三人沙发": "沙发", "双人沙发": "沙发", "贵妃椅": "沙发", "sofa": "沙发",
    "床": "床", "双人床": "床", "单人床": "床", "高低床": "床", "bed": "床",
    "餐桌": "餐桌", "圆桌": "餐桌", "长桌": "餐桌", "方桌": "餐桌", "饭桌": "餐桌",
    "餐椅": "餐椅", "椅子": "餐椅", "靠背椅": "餐椅",
    "书桌": "书桌", "写字台": "书桌", "办公桌": "书桌",
    "办公椅": "办公椅", "电脑椅": "办公椅",
    "衣柜": "衣柜", "衣橱": "衣柜",
    "书架": "书架", "书柜": "书架",
    "茶几": "茶几", "边几": "茶几",
    "电视柜": "电视柜", "电视墙柜": "电视柜",
    "单椅": "单椅", "休闲椅": "单椅", "躺椅": "单椅", "扶手椅": "单椅",
    "床头柜": "床头柜",
    "挂饰": "挂饰", "挂画": "挂饰", "装饰画": "挂饰", "壁画": "挂饰",
    "挂钟": "挂饰", "壁饰": "挂饰", "壁挂": "挂饰", "镜子": "挂饰",
    "装饰品": "装饰品", "绿植": "装饰品", "盆栽": "装饰品", "植物": "装饰品",
    "花瓶": "装饰品", "摆件": "装饰品", "雕塑": "装饰品",
}


def _canonical_category(cat: str) -> str:
    """去掉括号注释并归一为规范品类名。"""
    cat = re.sub(r"[（(].*?[)）]", "", cat).strip()
    return CATEGORY_ALIASES.get(cat, cat)


class FurnitureStore:
    def __init__(self):
        self.items: List[Furniture] = self._load_catalog()
        self._vectorstore = None

    # ---- 目录载入 ----
    def _load_catalog(self) -> List[Furniture]:
        with open(config.FURNITURE_CATALOG, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [Furniture(d) for d in data]

    def by_id(self, fid: str) -> Optional[Furniture]:
        return next((i for i in self.items if i.id == fid), None)

    def _catalog_signature(self) -> str:
        """目录内容的哈希签名，用于检测名称/描述等字段的改动。"""
        text = "\n".join(it.document_text() for it in self.items)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    # ---- 向量库 ----
    def _ensure_store(self):
        if self._vectorstore is not None:
            return
        from langchain_community.vectorstores import Chroma
        from langchain_core.documents import Document

        emb = get_embeddings()
        self._vectorstore = Chroma(
            collection_name="furniture",
            embedding_function=emb,
            persist_directory=str(config.VECTOR_DB_DIR),
        )
        # 目录规模或内容变化时重建向量库（例如新增品类、或翻译了家具名/描述）
        existing = self._vectorstore._collection.count()
        sig_path = Path(config.VECTOR_DB_DIR) / ".catalog_signature"
        stored_sig = sig_path.read_text(encoding="utf-8").strip() if sig_path.exists() else ""
        sig = self._catalog_signature()
        if existing != len(self.items) or stored_sig != sig:
            if existing:
                print(f"[rag] 目录已变化（{existing} → {len(self.items)} 件 / 内容更新），重建向量库。")
                old_ids = self._vectorstore._collection.get()["ids"]
                if old_ids:
                    self._vectorstore._collection.delete(ids=old_ids)
            docs = [
                Document(page_content=it.document_text(), metadata={"id": it.id})
                for it in self.items
            ]
            self._vectorstore.add_documents(docs)
            sig_path.write_text(sig, encoding="utf-8")
            print(f"[rag] 已写入 {len(docs)} 件家具到向量库 {config.VECTOR_DB_DIR}")

    # ---- RAG 检索 ----
    @staticmethod
    def _category_matches(a: str, b: str) -> bool:
        """按规范化品类精确匹配，避免「床」误匹配「床头柜」这类子串歧义。"""
        return _canonical_category(a) == _canonical_category(b)

    @staticmethod
    def _style_overlap(item: Furniture, tags: List[str]) -> int:
        """风格标签重叠数，用于与向量相似度做混合重排。"""
        item_tags = {t.lower() for t in item.style_tags}
        return sum(1 for t in tags if t.lower() in item_tags)

    def _build_query(self, req: FurnitureRequirement) -> str:
        return " ".join([req.category] + req.style_tags) + " 家具"

    def retrieve(self, req: FurnitureRequirement, top_k: Optional[int] = None) -> List[Furniture]:
        """检索风格相符的家具：先用品类硬约束过滤，再按相似度排序取 Top-K。"""
        top_k = top_k or config.TOP_K_FURNITURE
        self._ensure_store()

        # 目录规模小，检索全量候选再过滤，避免风格标签盖过品类信号
        hits = self._vectorstore.similarity_search_with_score(
            self._build_query(req), k=len(self.items))

        matched: List[tuple] = []  # (score, Furniture)，score 越小越相似
        for doc, score in hits:
            item = self.by_id(doc.metadata["id"])
            if item and self._category_matches(item.category, req.category):
                matched.append((score, item))

        if not matched:  # 品类无命中时放宽，仅按风格排序
            matched = [(score, self.by_id(doc.metadata["id"]))
                       for doc, score in hits
                       if self.by_id(doc.metadata["id"])]

        # 混合重排：优先风格标签重叠多者，其次向量相似度（score 越小越相似）
        matched.sort(key=lambda t: (-self._style_overlap(t[1], req.style_tags), t[0]))
        return [item for _, item in matched[:top_k]]
