# AI Interior Design Agent

An end-to-end **Python + LangChain** agent that turns a natural-language design
brief into a professional **CAD floor plan (DXF)** and an **interactive 3D
visualization**, using **RAG** to source style-consistent furniture along the
way.

Given something like *"a 5 m × 6 m Nordic living room"*, it produces:

- a structured design plan (style, zones, furniture list, flooring),
- a furniture selection matched to the style via vector search,
- a non-overlapping furniture layout,
- an AutoCAD-compatible **DXF** blueprint,
- a **2D PNG** floor plan and a **navigable three.js 3D scene** with real
  furniture models and floor/wall textures.

## Workflow

The core pipeline (`main.py` → `src/pipeline.py`) runs in three stages:

```
User constraints
   │
   ▼
┌─────────────────────────────────┐
│ Stage 1 · Language design       │  LLM (or deterministic offline designer)
│  src/design_agent.py            │  → structured DesignPlan
└─────────────────────────────────┘
   │  FurnitureRequirement (category + style tags + count + zone)
   ▼
┌─────────────────────────────────┐
│ Stage 2 · RAG retrieval + place │  Chroma vector search + shelf-packing
│  src/furniture_db.py, placer.py │  + AABB collision check
└─────────────────────────────────┘
   │  Placement (furniture + coordinates)
   ▼
┌─────────────────────────────────┐
│ Stage 3 · CAD modeling          │  ezdxf → layered design.dxf
│  src/cad_builder.py             │
└─────────────────────────────────┘
   │
   ▼
 preview.py (2D PNG) · preview_3d.py (interactive 3D scene)
```

1. **Language design** — a DeepSeek-powered LLM (or a deterministic offline
   designer) interprets the constraints and returns a typed `DesignPlan`: room
   dimensions, functional zones, a furniture list across **14 categories**
   (sofa, bed, dining table, chairs, desk, wardrobe, bookshelf, coffee table,
   TV stand, armchair, nightstand, wall art, decor), and the flooring material.
   Ergonomic clearances, circulation rules, and style profiles from
   `src/design_knowledge.py` are injected as system knowledge.

2. **Furniture retrieval (RAG)** — a local catalog
   (`data/furniture_catalog.json`, 36 items) is embedded into a persistent
   **Chroma** vector store. Each requirement is matched by a **category hard
   constraint** plus **style-tag overlap reranking**, so the chosen piece is
   both functionally and stylistically correct.

3. **Placement** — furniture is laid out in each zone via **shelf-packing**
   (large items first) and verified with **AABB collision detection** so nothing
   overlaps.

4. **Visualization** — `preview.py` renders a 2D floor-plan PNG (matplotlib);
   `preview_3d.py` renders an interactive three.js scene.

## From floor plan to 3D render

`preview_3d.py` converts the professional floor plan into a visual, navigable
3D scene:

- real furniture **GLB models** (Sketchfab, CC-BY) auto-scaled to their catalog
  footprints and placed at the plan coordinates;
- **per-style floor textures** (light oak, dark wood, warm wood, grey tile,
  concrete, marble) and a plaster wall texture from **Poly Haven (CC0)**;
- wall art and plants rendered procedurally;
- orbit / zoom / pan controls and name labels.

## Technologies

- **Python 3.11** · **LangChain**
- **DeepSeek** `deepseek-chat` (OpenAI-compatible API, manual JSON mode)
- **Pydantic v2** typed schemas
- **Chroma** (langchain-community) + hash embeddings (offline-capable)
- **ezdxf** for DXF output
- **three.js** (GLTFLoader, OrbitControls, CSS2DRenderer, TextureLoader)
- **Sketchfab** models (CC-BY) · **Poly Haven** textures (CC0)

## Applications in interior design

- Rapid **design prototyping** from a plain-text brief
- **Style-consistent furniture sourcing** via RAG
- Shareable **DXF deliverables** (AutoCAD / LibreCAD)
- Interactive **client walkthroughs**
- A foundation for an automated **design → review → refine** loop

## Roadmap

- **Review agent (next):** capture a screenshot of the 3D view and feed it to a
  checker agent that critiques furniture selection, placement, and style
  consistency, then iterates on the design — closing the
  *design → visualize → review → refine* loop.
- Multi-room layouts, budget-aware optimization, and a larger catalog.

## Getting started

```bash
cd interior-design-agent
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Download 3D furniture models (NOT tracked in git, ~106MB):
python fetch_3d_models.py         # Poly Haven CC0 — no token needed
# Optional, higher detail (CC-BY, needs a free Sketchfab API token):
#   $env:SKETCHFAB_TOKEN = "your-token"
#   python fetch_sketchfab_models.py
python map_3d_models.py           # rebuild data/catalog_3d.json

# Offline (no API key needed)
python main.py --room 客厅 --width 5 --length 6 --style 北欧现代简约 --offline

# With a real LLM (configure .env first)
python main.py --room 卧室 --width 4 --length 5 --style 北欧

# Render previews
python preview.py               # 2D floor-plan PNG
python preview_3d.py --serve    # interactive 3D scene in the browser
```

> The domain vocabulary (room types, styles, furniture names) is authored in
> Chinese; the preview UI is rendered in English.

## Project structure

```
interior-design-agent/
├── main.py                    # CLI entry
├── config.py                  # .env configuration
├── preview.py                 # 2D floor-plan PNG (matplotlib)
├── preview_3d.py              # 3D interactive scene (three.js)
├── data/
│   ├── furniture_catalog.json # 36-item catalog, 14 categories
│   ├── catalog_3d.json        # furniture → 3D model mapping
│   ├── textures/              # floor & wall textures (CC0)
│   └── models/sketchfab/      # furniture GLB models (CC-BY)
├── src/
│   ├── schemas.py             # Pydantic domain models
│   ├── llm.py                 # LLM factory (OpenAI-compatible)
│   ├── embeddings.py          # pluggable embeddings (hash/openai/local)
│   ├── design_agent.py        # Stage 1 · language design
│   ├── design_knowledge.py    # ergonomics / styles / layouts / flooring
│   ├── furniture_db.py        # Stage 2 · catalog + Chroma + RAG
│   ├── placer.py              # Stage 2 · placement + collision check
│   ├── cad_builder.py         # Stage 3 · ezdxf DXF
│   ├── labels_en.py           # English labels for the previews
│   └── pipeline.py            # orchestrator
└── output/                    # design.dxf / design_plan.json / placements.json / previews
```
