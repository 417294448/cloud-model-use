---
name: model-guide
description: 生成或更新大模型选择指南 HTML 页面（model userguide / 模型对比指南 / 模型选择速查页）。当用户要求"参考 index.html 风格"制作模型指南页、或要求"从官方文档更新模型信息/校准模型数据"时使用。覆盖两类任务：(1) 以统一设计体系新建模型指南页（如 openai/gemini/qwen/deepseek 等厂商）；(2) 从 OpenAI 官网 / Azure AI Foundry 等官方来源抓取最新模型数据（型号、推理、速度、价格、上下文/输入/输出）并更新到现有指南页。即使用户只说"更新一下这个模型页面""做个 xx 模型的指南"也应触发。
---

# Model Guide 页面生成与更新技能

本技能沉淀了 cloud-model-use 项目中模型选择指南页的两类工作流。核心原则：**设计风格以 index.html 为唯一基准，模型数据以官方文档为唯一基准**，两者都不凭记忆生成。

## 提供商索引（生成方法按提供商分别沉淀）

技能的**通用资产**（模板、渲染器、提取器、校验器、设计规范、数据结构）对所有提供商通用；**提供商专用资产**（数据文件、官方数据源方法、厂商定制抓取/解析脚本）按提供商分别沉淀在 `data/<厂商>.json` 与 `references/providers/<厂商>.md`。

| 提供商 | 页面 | 数据文件 | 数据源方法 | 抓取/解析脚本 | 状态 |
|---|---|---|---|---|---|
| **OpenAI** | `openai-model-userguide.html` | `data/openai.json` | `references/providers/openai.md` | `openai/fetch_models.py` / `openai/parse_cards.py` | ✅ 已沉淀（模板生成 + 页面生成全链路验证通过） |
| **阿里 Qwen** | `qwen-model-userguide.html` | `data/qwen.json` | `references/providers/qwen.md` | `qwen/fetch_docs.py` | ✅ 已沉淀（全链路验证通过） |
| **Google Gemini** | `gemini-model-userguide.html` | `data/gemini.json` | `references/providers/gemini.md` | `gemini/fetch_docs.py` | ✅ 已沉淀（全链路验证通过） |
| **智谱 Z.ai** | `zai-model-userguide.html` | `data/zai.json` | `references/providers/zai.md` | `scripts/zai/fetch_docs.py` | ✅ 已沉淀（模板生成 + 页面生成全链路验证通过） |
| DeepSeek / 其他 | — | — | 待沉淀 | — | ⬜ 待做 |

**OpenAI、Qwen、Gemini、Z.ai 已完成模板化全链路（官方抓取 → 数据文件 → 渲染页面）。四个独立页面通过根目录 `index.html` 以 Tab 形式聚合（iframe 切换，各页独立维护）。用户提到 DeepSeek 等页面时，通用工作流（提取/渲染/校验/设计规范）直接适用，但官方数据源方法尚未沉淀——按「新增提供商指南」补做后再大规模更新。

## 新增提供商指南

1. **建数据文件**：若项目已有手写页面（如 gemini/qwen），先 `extract_guide_data.py 页面.html -o data/<厂商>.json` 反向提取并渲染回归验证；没有则复制 `data/openai.json` 改写 meta 与 sections。
2. **写数据源文档**：研究该厂商官方文档的可达性与结构（直连/代理、指标字段、模态与档位口径），沉淀为 `references/providers/<厂商>.md`，格式参照 `openai.md`。
3. **（可选）写厂商脚本**：官方有结构化指标数据时写 `fetch_<厂商>_*.py` / `parse_<厂商>_cards.py`；`fill_objective_fields.py` 的映射若需适配厂商语义（如 OpenAI 的 Reasoning vs Intelligence），在该脚本内加厂商分支或写 `fill_<厂商>.py`。
4. **登记**：更新上表状态。

## 模板化流水线（首选工作方式）

页面已模板化：`assets/guide.template.html`（骨架+样式）+ `data/<厂商>.json`（唯一事实源）→ `scripts/render_guide.py` 渲染出最终页面。**改内容永远改 data JSON 再渲染，不手改 HTML。**

```
官方文档 ──fetch/parse──► cards.json ──fill──► data/<厂商>.json ──render──► <厂商>-model-userguide.html
                              （客观字段自动填）      （编辑字段人工/Agent 补）
```

- **更新现有页面（以 OpenAI 为例）**：`openai/fetch_models.py` 抓官方数据 → `openai/parse_cards.py` 解析 → `fill_objective_fields.py --write` 自动回填推理/速度/价格客观字段 → Agent 审补编辑字段（新模型行、说明、徽章、快速选型、统计数字）→ `sync_dates.py --write` 统一更新日期 → `render_guide.py` 渲染 → 完成。其他提供商套用同一流水线，替换厂商专用两步（fetch/parse）即可。
- **新建厂商页面**：复制 `data/openai.json` 为 `data/<厂商>.json`，改写 meta（标题/eyebrow/统计/来源）与各 section；或从官方文档重新填充。渲染即可。
- **为已有手写页面建模板**：`extract_guide_data.py 页面.html -o data/x.json`，渲染结果应与原页面语义一致（本技能已对 openai 页面验证逐字节等价，忽略注释与空白）。

## 先判断任务类型

| 用户意图 | 工作流 |
|---|---|
| 新做一个模型指南页（"参考 index.html 风格做 xx 的指南"） | A. 生成页面 |
| 更新现有页面的模型信息（"从官方文档获取最新信息更新"） | B. 更新数据 |
| 调整页面局部展示（改列、改图标、改档位划分） | C. 局部调整（改 data JSON + 渲染器，遵守设计体系） |

## 工作流 A：生成新页面

1. **读风格基准**：读取项目根目录 `index.html` 的 `<style>` 区（前 ~1300 行）和 `references/page-style.md`，提取设计体系。不要凭印象写样式——index.html 可能已迭代。
2. **收集内容**：确定厂商与模型清单。若用户给了来源（文档/URL），先抓取整理；没有则按工作流 B 的方法从官方文档获取。
3. **写文件**：单文件 HTML，内联 `<style>`，结构为：hero 页头（eyebrow + 标题 + 描述 + 统计条）→ 吸顶锚点导航 → 图例 → 快速选型卡片 → 各分类表格 → 弃用表 → 能力矩阵 → 页脚。组件规范见 `references/page-style.md`。
4. **校验**：运行 `python scripts/check_html.py <文件>`，必须标签配对正确、每张表表头列数 == 数据行单元格数。

## 工作流 B：更新数据

1. **抓官方数据**：按 `references/providers/<厂商>.md` 的方法抓取（OpenAI 见 `references/providers/openai.md`）。OpenAI 侧要点：
   - Azure 文档（模型清单、退役计划）用 `scripts/openai/fetch_azure_docs.py` 直连抓取，可 `--section "Azure OpenAI"` 只取所需章节；`developers.openai.com` / `platform.openai.com` 被 Cloudflare 拦截，须用 `scripts/openai/fetch_models.py`（走 `api.allorigins.win` 代理 + 重试，失败率约 70%，每页重试 6-8 次）。
   - 抓完 OpenAI 详情页后用 `scripts/openai/parse_cards.py` 解析为 JSON。
   - 模型详情页追加 `.md` 可拿到 Markdown 版本（含价格表、上下文/输入/输出 token 数），比解析 HTML 更可靠。
2. **映射为页面档位**：严格按 `references/page-style.md` 的映射表——推理 5 档（官方图标格数 1:1）、速度 5 档、价格 6 档、模态图标。**官方标 Intelligence 的模型是非推理模型，归入"快速"档，不要标推理点。**
3. **批量更新**：`fill_objective_fields.py --write` 自动回填客观字段；新增模型在 data JSON 对应 section 插行（objective 字段可先留空再自动填）；统计数字同步改；更新日期用 `sync_dates.py --write` 统一（只动「（YYYY-MM-DD 同步）」括注与 `footer_updated`，表格行内的官方退役日期不受影响；不带参数运行可只报告一致性）；最后 `render_guide.py` 渲染。
4. **校验**：渲染器自动调用 check_html.py。列结构变更（增删列/增删行类型）后重点检查结构不一致的表。
5. **清理临时文件**：任务结束后删除本次产生的临时抓取文件（`_gemini_*.html`、`_aliyun_*.html`、`_azure_tmp.html`、`_rt*.html/json` 等）。`_model_pages/`、`_model_md/` 是可复用缓存，可保留或按需清理；所有临时/缓存路径必须已在 `.gitignore` 中声明。

## 工作流 C：局部调整

改 data JSON 或渲染器，但遵守 `references/page-style.md` 的既有约定（如模态列用纯图标 + title、推理用点阵、价格用阶梯信号条、徽章实心白字、定位列在价格列前）。新增展示维度时先想"与官方哪个字段对应"，保持页面数据可溯源。新增单元格类型时在渲染器 CELL_RENDERERS 注册，并同步提取器 parse_cell。

## 三条硬性约定

- **样式不即兴**：所有颜色/字体/组件从 index.html 的 CSS 变量复制，不新造色值。
- **数据可溯源**：每个模型行的关键指标（推理、速度、价格、上下文）必须能对应到官方页面；官方查不到的（如 Azure-only 的 chat 变体）沿用现有值并在总结中注明"未能验证"。
- **改动后必校验**：`scripts/check_html.py` 全绿才算完成。
- **任务结束清场**：skill 执行完毕后清理本次产生的临时抓取文件；缓存目录（如 `_model_pages/`、`_model_md/`）可保留但必须在 `.gitignore` 中声明，避免污染版本控制。

## 已评估暂缓事项

- **中英文切换**（2026-08 评估，决定暂缓）：页面图标化改造后核心信息（型号/规格/档位）已语言中立；双语编辑内容同步成本高；index.html 主站已有英文出口。**触发再做的条件**：页面公开分享且确认有非中文读者。届时走方案 A：复制 data JSON 翻译为 `<厂商>-en.json`，render_guide.py 渲染独立英文页，两页右上角互加静态 中/EN 链接（复用 index.html lang-switch 样式，零 JS），渲染器无需改动。

## 资源索引

**通用资产（所有提供商共用）**
- `references/page-style.md` — 设计体系完整规范（CSS 变量、厂商主题色、Hero 装饰元素、组件、档位映射表）
- `references/data-schema.md` — data JSON 结构说明（手写/手改数据文件时查阅）
- `assets/guide.template.html` — 页面模板（CSS + 骨架 + {{占位符}}）
- `scripts/render_guide.py` — 渲染器（data JSON + template → HTML，自动校验）
- `scripts/extract_guide_data.py` — 反向提取（已有 HTML → data JSON）
- `scripts/fill_objective_fields.py` — 官方数据自动回填客观字段
- `scripts/check_html.py` — HTML 结构校验（标签配对 + 表格列数）
- `scripts/check_data.py` — data JSON 业务规则校验（弃用表收录规则、行长度、枚举值合法）
- `scripts/verify_official.py` — 官方交叉校验（模型存在性、价格声称、遗漏差集归因）
- `scripts/compare_html.py` — HTML 语义对比（回归验证：忽略注释/空白找差异）

**OpenAI 专用**
- `data/openai.json` — OpenAI 页面数据（唯一事实源，也是新厂商的参照样例）
- `references/providers/openai.md` — OpenAI 官方数据源抓取方法（代理、重试、解析结构、404 回退）
- `scripts/openai/fetch_models.py` — 批量抓取 OpenAI 模型详情页（代理 + 重试）
- `scripts/openai/parse_cards.py` — 解析 OpenAI 详情页指标卡为 JSON
- `scripts/openai/fetch_azure_docs.py` — 抓取 Azure Learn 文档页转结构化文本（可 --section 截取章节；退役计划/模型清单均用此脚本）

**阿里 Qwen 专用**
- `data/qwen.json` — Qwen 页面数据（唯一事实源；CNY 计价，图例经 legend_overrides 覆盖）
- `references/providers/qwen.md` — 阿里云百炼数据源方法（直连、ICE_PAGE_PROPS 正文提取、价格口径、思考/速度档位映射约定）
- `scripts/qwen/fetch_docs.py` — 抓取 help.aliyun.com 文档页转结构化文本（提取 __ICE_PAGE_PROPS__ 内嵌正文）

**Google Gemini 专用**
- `data/gemini.json` — Gemini 页面数据（唯一事实源；USD 计价；PDF 已作为独立输入模态与 text/image/audio/video 并列）
- `references/providers/gemini.md` — Google 数据源方法（proxy.cors.sh 通道、三页分工、关停日期语义、PDF 模态标注规则）
- `scripts/gemini/fetch_docs.py` — 抓取 ai.google.dev 文档页转结构化文本（经 proxy.cors.sh 代理）

**智谱 Z.ai 专用**
- `data/zai.json` — Z.ai 页面数据（唯一事实源；CNY 计价；官方模型 ID 为大写 GLM/CogView/Embedding 形式）
- `references/providers/zai.md` — BigModel 数据源方法（docs.bigmodel.cn / open.bigmodel.cn 直连、价格口径、特殊计费单元处理、主题色说明）
- `scripts/zai/fetch_docs.py` — 抓取 BigModel 模型概览（静态）与产品价格（Vue SPA，需 Playwright 渲染）转结构化文本

**其他提供商**：待按「新增提供商指南」沉淀（DeepSeek…）

