# AI Interior Design Agent — Project Plan (项目计划书)

**Date:** 2026-10-25 · **Status:** In active development

---

## 1. Project Overview

An end-to-end agent that turns a natural-language interior-design brief into a
furnished floor plan and an interactive 3D visualization. The pipeline automates
the full chain — *brief → structured design → furniture retrieval & placement →
CAD drawing → 2D/3D preview* — using a Large Language Model (LLM) as the design
engine and Retrieval-Augmented Generation (RAG) for style-consistent furniture
selection.

> **Core value proposition:** convert a professional interior design plan into a
> visual 3D rendering in seconds, and keep furniture choices stylistically
> consistent through retrieval rather than manual curation.

---

## 2. Background & Problem

- **Manual effort.** Producing a furnished floor plan requires domain expertise
  (spatial layout, style language, furniture dimensions) and hours of work.
- **Style consistency is fragile.** Sourcing furniture piece-by-piece from a
  catalog often yields a room where pieces clash in style or scale.
- **No fast feedback loop.** Designers cannot quickly see a space in 3D and
  iterate on furniture selection before committing to a purchase or a plan.

This project addresses all three by coupling an LLM planner with a vector-search
furniture database and an automatic CAD/3D exporter.

---

## 3. Objectives & Success Criteria

1. **Natural-language input** → a valid, structured single-room design
   (room size, zones, style, budget, furniture requirements).
2. **Automatic furniture selection** that is *category-correct* and
   *style-consistent*, drawn from a real catalog with dimensions and prices.
3. **Non-overlapping placement** of furniture onto a floor plan with valid
   coordinates and rotation.
4. **Deliverables**: an AutoCAD-compatible DXF, a 2D PNG floor plan, and an
   interactive 3D page with real models and textures.

**Success criteria (measurable):**

| Criterion | Target |
|---|---|
| Schema validity (Pydantic) | 100% of runs |
| Overlapping placements | 0 |
| Category match rate | 100% (hard constraint) |
| Style-tag overlap | ≥ 1 shared tag on matched items |
| Outputs generated | DXF + PNG + HTML all present |

---

## 4. Scope

**In scope**

- Single-room design across common room types (living room, bedroom, dining
  room, study).
- 14 furniture categories (sofa, bed, dining table, desk, wardrobe, bookshelf,
  coffee table, TV stand, armchair, nightstand, dining chair, office chair,
  wall art, decor).
- Flooring, wall textures, wall art and decorative objects.
- Offline fallback (deterministic mock designer) plus a live LLM (DeepSeek).

**Out of scope (current)**

- Multi-room / multi-floor planning.
- Budget-aware optimization and shopping-cart integration.
- The **review/refinement loop** (see §8, Milestone M3 — the key next phase).
- Real-time multi-user collaboration.

---

## 5. System Architecture

```
                 ┌─────────────────────────────────────────────┐
  natural-lang   │  1. Design Agent (LLM)                      │
  brief ───────▶ │     prompt → Pydantic DesignPlan            │
                 └──────────────────┬──────────────────────────┘
                                    │ FurnitureRequirement[]
                                    ▼
                 ┌─────────────────────────────────────────────┐
                 │  2. RAG Furniture DB (Chroma)               │
                 │     category hard-constraint                │
                 │     + style-tag-overlap rerank              │
                 └──────────────────┬──────────────────────────┘
                                    │ selected Furniture[]
                                    ▼
                 ┌─────────────────────────────────────────────┐
                 │  3. Placement (shelf-packing + AABB)        │
                 │     → (x, y, rotation) per item             │
                 └──────────────────┬──────────────────────────┘
                                    │
                 ┌──────────────────┼──────────────────────────┐
                 ▼                  ▼                          ▼
          ezdxf → DXF       matplotlib → PNG          three.js → HTML
```

**Data flow:** `design_plan.json` → `placements.json` → `room.dxf` /
`preview.png` / `preview_3d.html`, all written under `output/`.

---

## 6. Technical Approach

| Layer | Technology | Notes |
|---|---|---|
| LLM | DeepSeek `deepseek-chat` (OpenAI-compatible) | Manual JSON mode for robust structured output |
| Schemas | Pydantic v2 | Validation + clamping of coordinates/sizes |
| RAG | Chroma (persistent) + hash embeddings | Offline, deterministic embeddings |
| Retrieval | Category hard-constraint + style-tag rerank | Prevents `床`↔`床头柜` substring confusion |
| Placement | Shelf-packing heuristic + AABB collision | Guarantees non-overlap within zones |
| CAD | ezdxf | Rectangles per furniture footprint |
| 2D preview | matplotlib | Same data as DXF |
| 3D preview | three.js (GLTFLoader, OrbitControls, CSS2DRenderer, TextureLoader) | Sketchfab GLB models + Poly Haven CC0 textures |
| Runtime | Python 3.11 venv, Windows 11 | `.env` holds API keys (never committed) |

---

## 7. Current Status (Completed)

- **M0 — Core pipeline**: LLM design → RAG → placement → DXF → 2D preview,
  with a deterministic offline fallback.
- **M1 — Live model**: DeepSeek integration + real Sketchfab GLB models in the
  3D view.
- **M2 — Rich scene**: flooring + wall textures (Poly Haven CC0), wall art and
  decorative objects (procedurally rendered when no model exists).
- **M2.5 — English UI**: both preview scripts and the furniture catalog
  (`name` / `material` / `description`) now render in English, while the
  internal retrieval vocabulary (`category`, `style`, `style_tags`) stays
  Chinese for stable matching.
- **Hardening**: RAG rebuilds on catalog *content* change via a SHA-256
  signature (not just count), so renamed items re-embed correctly.

---

## 8. Development Plan & Milestones

### M3 — Review / Checker Agent (next phase, highest priority)
**Gap:** today the pipeline stops at visualization. There is no loop that looks
back at the rendered room and improves it.

**Plan:**
1. **Capture** a screenshot of the 3D scene (headless render or canvas export).
2. **Feed** the image — together with `design_plan.json` and `placements.json` —
   to a *checker agent* (vision-capable LLM).
3. **Critique** along two axes: (a) *furniture selection* — category, scale,
   budget fit; (b) *style consistency* — does each piece match the declared
   style and the others.
4. **Iterate** — the checker emits structured revision requests
   (swap item X for a more consistent candidate, move Y off the wall, adjust
   spacing) that re-enter the retrieval/placement stage until a
   score threshold is met.

**Deliverable:** a closed *design → visualize → review → refine* loop.

### M4 — Multi-room & budget optimization
- Support multiple rooms/zones and their relationships.
- Optimize selection against a budget and a preference weight vector.

### M5 — Packaging & polish
- CLI and/or web front-end, test suite, documentation, CI.

---

## 9. Timeline (estimated)

| Milestone | Estimate |
|---|---|
| M3 Review agent | ~2 weeks |
| M4 Multi-room + budget | ~2 weeks |
| M5 Packaging | ~2 weeks |

Estimates are for a single developer; each milestone is independently testable.

---

## 10. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| LLM structured-output drift / invalid JSON | Manual JSON mode, Pydantic validation, coordinate clamping, offline fallback |
| RAG vector-store staleness | Content-hash signature rebuild (implemented) |
| Style vocabulary mismatch (English vs. Chinese keys) | Keep matching keys stable; translate only for display |
| Large 3D assets load slowly | Load by path from a local server; procedural fallback for decor/wall art |
| Category substring ambiguity (`床` vs `床头柜`) | Canonical-category hard constraint + alias normalization |

---

## 11. Applications & Prospects

- **Rapid prototyping** — iterate on a room concept before any physical work.
- **Interior-design workflow** — convert a professional floor plan into a
  client-facing 3D walkthrough in one step.
- **Furniture e-commerce** — embed the retrieval engine as a "complete the
  room" recommender over a live product catalog.
- **Self-improving design agent** — the M3 checker turns the tool into a system
  that learns to refine its own choices, a foundation for autonomous design QA.
