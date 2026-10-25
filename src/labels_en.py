"""English display labels for the 2D/3D previews.

The domain data (furniture names, design narratives) is authored in Chinese;
these mappings only translate the fixed vocabulary — categories, room types and
styles — so the preview UI can be rendered in English.
"""

CATEGORY_EN = {
    "沙发": "Sofa", "床": "Bed", "餐桌": "Dining Table", "餐椅": "Dining Chair",
    "书桌": "Desk", "办公椅": "Office Chair", "衣柜": "Wardrobe", "书架": "Bookshelf",
    "茶几": "Coffee Table", "电视柜": "TV Stand", "单椅": "Armchair", "床头柜": "Nightstand",
    "挂饰": "Wall Art", "装饰品": "Decor",
}

_ROOM_EN = {"客厅": "Living Room", "卧室": "Bedroom", "餐厅": "Dining Room", "书房": "Study"}

# Ordered so longer tokens win (e.g. "工业风" before "现代").
_STYLE_EN = [
    ("工业风", "Industrial"), ("北欧", "Nordic"), ("现代", "Modern"),
    ("简约", "Minimalist"), ("中式", "Chinese"), ("日式", "Japanese"),
    ("极简", "Minimalist"), ("田园", "Country"), ("原木", "Wood"), ("复古", "Retro"),
]


def category_en(cat: str) -> str:
    return CATEGORY_EN.get(cat, cat)


def room_name_en(name: str) -> str:
    return _ROOM_EN.get(name, name)


def style_en(style: str) -> str:
    out = style
    for zh, en in _STYLE_EN:
        out = out.replace(zh, en)
    return out
