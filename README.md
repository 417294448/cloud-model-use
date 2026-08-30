# cloud-model-use

[![Pages: 8](https://img.shields.io/badge/pages-8-0e7490)](#project-structure)
[![Models: 340+](https://img.shields.io/badge/models-340%2B-0d9463)](#project-structure)
[![Vendors: 4](https://img.shields.io/badge/vendors-4-2563eb)](#project-structure)
[![Languages: zh / en](https://img.shields.io/badge/languages-zh%20%2F%20en-f4f6f8)](#internationalization)

Data-driven, bilingual **model selection guides** for OpenAI, Alibaba Qwen, Google Gemini and Zhipu Z.ai — rendered from a single source of truth (`data/<vendor>.json`) into lightweight, dependency-free static HTML pages, aggregated by a language-switchable landing page (`index.html`).

> 简体中文简介：面向 OpenAI / 阿里 Qwen / Google Gemini / 智谱 Z.ai 的模型选型指南。每厂商一套「官方数据 → JSON 事实源 → 模板渲染」流水线，产出中英双语静态页面，由 index.html 统一聚合并支持全局中英切换。模型数据以官方文档为唯一基准，通过脚本自动同步并校验。

---

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Internationalization](#internationalization)
- [Updating Model Data](#updating-model-data)
- [Validation Pipeline](#validation-pipeline)
- [Adding a New Vendor](#adding-a-new-vendor)
- [Tech Notes](#tech-notes)
- [License](#license)

---

## Features

- **8 static pages** — 4 vendors × 2 languages (`<vendor>-model-userguide[|-en].html`), no build step, no runtime dependencies.
- **Single source of truth** — every page is rendered from `data/<vendor>.json` via a shared template; never hand-edit HTML.
- **Global language switching** — a `中 / EN` switcher in the top-right corner of `index.html` flips both the landing-page shell (title, description, stats, tabs) and all embedded vendor pages at once; preference is persisted in `localStorage`.
- **Official-data-driven updates** — per-vendor fetch/parse scripts pull from official sources (Azure AI Foundry, Aliyun Bailian, ai.google.dev, BigModel), with documented proxy fallbacks and retry strategies.
- **Mandatory bilingual sync** — any change to the Chinese data must be mirrored to the English data (via `make_<vendor>_en.py`, which warns on any untranslated string) before rendering.
- **Semantic parity check** — `check_bilingual.py` verifies that the Chinese and English data are structurally mirrored, share identical language-neutral values (model IDs, tiers, token counts), and contain no untranslated leftovers.
- **Change log** — every model-data change is recorded in `diff/YYYY-MM-DD.md`, one line per change, grouped by vendor section.

## Project Structure

```
.
├── index.html                          # Landing page: vendor tabs + global language switcher
├── <vendor>-model-userguide.html       # Rendered Chinese guide (openai / gemini / qwen / zai)
├── <vendor>-model-userguide-en.html    # Rendered English guide
├── diff/
│   └── YYYY-MM-DD.md                   # Model-data change log (one shared file per day)
└── .claude/skills/model-guide/         # The maintainable pipeline (Claude skill)
    ├── SKILL.md                        # Full workflow documentation
    ├── assets/guide.template.html      # Shared page template ({{PLACEHOLDER}} based)
    ├── data/                           # Source of truth (JSON, one per language per vendor)
    ├── references/
    │   ├── page-style.md               # Design system & tier mapping spec
    │   ├── data-schema.md              # data JSON structure spec
    │   └── providers/<vendor>.md       # Per-vendor official-source harvesting guide
    └── scripts/
        ├── render_guide.py             # JSON + template → HTML (auto-renders EN + semantic check)
        ├── check_html.py               # HTML structure check (tags, table columns)
        ├── check_data.py               # data JSON business-rule check
        ├── check_bilingual.py          # zh/en semantic parity check
        ├── extract_guide_data.py       # Reverse-extract: existing HTML → data JSON
        ├── fill_objective_fields.py    # Backfill objective fields from official data
        ├── sync_dates.py               # Unify "synced YYYY-MM-DD" markers / footer dates
        ├── verify_official.py          # Cross-check against official docs
        ├── compare_html.py             # Semantic HTML regression diff
        └── <vendor>/                   # Per-vendor fetch/parse/make_en scripts
```

## Quick Start

The site is fully static — open `index.html` directly in a browser, or serve it with any static file server:

```bash
python -m http.server 8000
# → http://localhost:8000/index.html
```

You can also open any vendor page standalone, e.g. `openai-model-userguide.html` (Chinese) or `openai-model-userguide-en.html` (English).

**Runtime requirements**

- Viewing: any modern browser.
- Updating / rendering: **Python 3.10+**. Rendering and validation scripts use only the standard library; per-vendor *fetching* scripts may additionally need `requests` / `playwright` (see `references/providers/<vendor>.md`).

## Internationalization

- **Two data files per vendor**: `data/<vendor>.json` (Chinese, the source of truth) and `data/<vendor>-en.json` (English copy, generated by `scripts/<vendor>/make_<vendor>_en.py`).
- **Language-neutral content** (model IDs, numbers, tier keys, modality keys, context values, URLs) is shared; only editorial text (meta copy, section titles/descriptions/headers, model notes, quick-pick labels, badges) differs per language.
- **Renderer labels** are switched by `--lang en` (reasoning/speed/price/tier/modality/lifecycle labels, legend titles, footer "Last updated").
- **Switching UX**:
  - Standalone pages: a static `中 / EN` switcher in the page header (`meta.lang_switch`), preserving the `?embed=1` query when embedded.
  - `index.html`: the top-right global switcher toggles the shell text (`data-i18n` + JS dictionary) and all four embedded iframes together, remembering the choice in `localStorage['model-guide-lang']`.

## Updating Model Data

The canonical workflow (documented in full in `SKILL.md`):

1. **Fetch official data** — run the vendor's fetch script (`scripts/<vendor>/fetch_*.py`) per `references/providers/<vendor>.md`. If a proxy channel is down, fall back to direct fetching (WebFetch) of the official pages.
2. **Update `data/<vendor>.json`** — add/remove models, fix fields, map tiers per `page-style.md`, update stats (count = rows in model tables, excluding `naming`/`matrix`/`deprecated`/`historical` auxiliary sections), then write the change log to `diff/YYYY-MM-DD.md`.
3. **Sync the English data** (mandatory):

   ```bash
   python .claude/skills/model-guide/scripts/<vendor>/make_<vendor>_en.py
   # must print 「全部中文已翻译」 — any untranslated string aborts (exit 1)
   ```

4. **Render & validate** — one command produces both pages and runs all checks:

   ```bash
   python .claude/skills/model-guide/scripts/render_guide.py \
     .claude/skills/model-guide/data/openai.json -o openai-model-userguide.html
   # auto-renders openai-model-userguide-en.html, then runs check_html + check_bilingual
   # use --zh-only to render only the Chinese page
   ```

5. **Clean up** — remove temporary fetch artifacts (`_g_*`, `_model_*` caches are gitignored).

> **Hard rule**: a Chinese data change without the matching English data + passing semantic parity check is considered incomplete.

## Validation Pipeline

All checks run automatically at render time; each can also be invoked directly:

| Script | Scope |
|---|---|
| `check_html.py` | Tag pairing & table column consistency of rendered HTML |
| `check_data.py` | data JSON business rules (deprecated-table inclusion, row length, enum values) |
| `check_bilingual.py` | zh/en structural mirror, identical language-neutral values, model-ID sets, no untranslated Chinese in EN data |
| `verify_official.py` | Cross-check model existence / price claims against official docs |
| `compare_html.py` | Semantic regression diff between two HTML versions |
| `sync_dates.py` | Unify "synced" date markers and footer dates across data files |

## Adding a New Vendor

1. Create `data/<vendor>.json` (copy `data/openai.json` and adapt, or reverse-extract an existing page with `extract_guide_data.py`).
2. Write `references/providers/<vendor>.md` documenting the official source & harvesting method.
3. (Optional) Add `scripts/<vendor>/fetch_*.py` / `parse_*.py` for structured official data.
4. Add `scripts/<vendor>/make_<vendor>_en.py` for bilingual support.
5. Render, validate, and register the vendor in `SKILL.md` and `index.html`.

## Tech Notes

- **Templates** — the shared template contains `{{PLACEHOLDER}}` tokens only; all branching lives in the renderer, keeping it dependency-free and auditable.
- **Tier mapping** — reasoning (5), speed (5), price (6), modality icons and badges follow `references/page-style.md`; OpenAI models labeled *Intelligence* are non-reasoning and map to the "Fast" tier.
- **gitignore** — temporary fetch artifacts (`_g_*`, `_model_pages/`, `_model_md/`) and automatic JSON backups (`*.json.bak.*`) are excluded; `diff/` is tracked.

## License

No license specified.
