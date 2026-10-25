# 室内设计背景知识库

> 本文档是设计 Agent 的领域背景知识，整理自公开的设计规范、人体工学与无障碍标准。
> 代码内可直接调用同源知识：`src/design_knowledge.py`（含 `KNOWLEDGE_PROMPT` 注入 LLM）。

## 1. 人体工学净空与动线（单位：米）

| 项目 | 数值 | 说明 |
|---|---|---|
| 主通道净宽 | ≥ 0.9 | 最关键的动线数字，常用路线务必保证 |
| 两人并排通过 | ≥ 1.2 | |
| 家具间次要通道 | ≥ 0.6 | 侧身通行最小约 0.3 |
| 沙发 → 茶几 | 0.35–0.45 | 伸手取物最舒适 |
| 座位 → 电视 | ≥ 1.5（舒适 2.5） | 视距约 1.5–2.5 倍屏幕对角线 |
| 床两侧净空 | ≥ 0.6 | 单/双人床靠墙则仅需一侧 |
| 床尾净空 | ≥ 0.9 | 床尾到对面家具/柜 |
| 衣柜前开柜 | ≥ 0.9 | 平开门需完整开柜空间 |
| 餐桌每人占边 | ≥ 0.6 | 每人用餐位 |
| 餐椅拉出 + 走道 | ≥ 0.9 | 餐桌边缘到墙/家具 |
| 书桌/办公椅后方 | ≥ 0.9 | 起身与转身空间 |
| 轮椅回转空间 | 1.5 × 1.5 | 无障碍基准 |

**动线原则**：连续、不穿行会客区；大件家具贴墙；中间留完整活动区；避免家具挡门、挡柜门。

## 2. 各房间布局原则

- **客厅**：沙发背靠墙、面向电视柜；茶几在沙发前 0.4m；电视视距 1.5–2.5m；留 0.9m 主通道。
- **卧室**：床靠墙、两侧留 0.6m；床头柜在两侧；衣柜靠收纳区、前留 0.9m。
- **餐厅**：餐桌居中，四周 0.9m 供餐椅拉出；大空间 6 椅、小空间 4 椅。
- **书房**：书桌靠墙、办公椅背对墙；书架近工作区。

## 3. 标准家具尺寸（宽 × 深 × 高，米）

| 品类 | 尺寸 | 品类 | 尺寸 |
|---|---|---|---|
| 沙发 | 2.2 × 0.9 × 0.8 | 书桌 | 1.2 × 0.6 × 0.75 |
| 床 | 1.8 × 2.0 × 1.0 | 办公椅 | 0.6 × 0.6 × 1.1 |
| 床头柜 | 0.45 × 0.4 × 0.5 | 衣柜 | 1.8 × 0.6 × 2.2 |
| 单椅 | 0.7 × 0.7 × 0.8 | 书架 | 0.8 × 0.3 × 1.8 |
| 餐桌 | 1.6 × 0.8 × 0.75 | 茶几 | 1.1 × 0.6 × 0.45 |
| 餐椅 | 0.45 × 0.5 × 0.8 | 电视柜 | 1.8 × 0.4 × 0.45 |

## 4. 风格特征

| 风格 | 配色 | 材质 | 特征 |
|---|---|---|---|
| 北欧 | 白 / 浅灰 / 奶油 / 原木色 | 原木、布艺、羊毛、亚麻 | 浅色、采光、留白、温暖（hygge） |
| 现代 | 白 / 灰 / 黑 + 金属 | 玻璃、金属、皮革、烤漆 | 利落线条、几何、功能 |
| 中式 | 深木 / 红 / 赭石 / 米白 | 实木、棉麻、瓷器、竹 | 对称、榫卯、沉稳 |
| 日式 | 米白 / 浅木 / 砂 / 绿 | 原木、竹、藤、棉麻 | 低矮、留白、侘寂 |
| 工业风 | 黑 / 深灰 / 砖红 / 棕 | 金属、皮革、混凝土、做旧木 | 裸露、硬朗、粗犷 |
| 极简 | 白 / 灰 / 米 | 石材、玻璃、哑光板材 | 少即是多、强收纳 |
| 田园 | 米白 / 浅绿 / 碎花 / 原木 | 实木、布艺、藤编 | 自然、温馨 |

## 5. 数据来源

- [Time-Saver Standards for Interior Design（室内设计时间节省标准，archive.org）](https://archive.org/download/time-saver-standards-for-interior-design/Time_Saver_Standards_for_Interior_Design_text.pdf)
- [How to Plan a Room Layout Before You Buy Furniture（Coohom 布局指南）](https://www.coohom.com/blog/how-to-plan-a-room-layout-before-you-buy-furniture)
- [Measurements to Know: A Guide for Furniture Layout and Ergonomics（Houzz）](https://www.houzz.co.uk/magazine/measurements-to-know-a-guide-for-furniture-layout-and-ergonomics-stsetivw-vs~109239110)
- [Standard Room Size in Feet（Coohom）](https://www.coohom.com/article/standard-room-size-in-feet-the-essential-guide-for-home-planning)
- [Space Standards for Household Activities（University of Illinois）](https://libsysdigi.library.illinois.edu/oca/Books2009-05/spacestandardsfo00mccu/spacestandardsfo00mccu.pdf)
- [室内设计空间尺度图解（新筑课堂）](https://app.justeasy.cn/news/5524?type=1&from=android&referer=android&version=1.3.7&img=https)
- [如何做空间动线：让布局更流畅贯通（新筑课堂）](https://app.justeasy.cn/news/7459?type=1&from=android&referer=android&version=1.3.7&img=https)
- [更符合人体工程学的16个装饰尺寸（新筑课堂）](https://app.justeasy.cn/news/33316?type=1&from=ios&referer=0&version=0&img=https)
- [无障碍住宅设计基准（台湾内政部建筑研究所）](https://ws.moi.gov.tw/Download.ashx?u=LzAwMS9VcGxvYWQvT2xkRmlsZV9BYnJpX0dvdi9yZXNlYXJjaC8xNTAwLzE0NDc5Mjk5ODgxLnBkZg%3d%3d&n=Y29tcGxldGUucGRm)
- [Design guideline: qualitative & parametric rules（Nature Scientific Reports）](https://www.nature.com/articles/s41598-025-32433-9/tables/3)
- [Interior styles: what types are there（Furn.biz）](https://furn.biz/blog/interior-styles-what-types-are-there-and-which-one-suits-you)
