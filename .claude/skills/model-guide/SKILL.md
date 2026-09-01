---
name: model-guide
description: 生成或更新大模型选择指南 HTML 页面（model userguide / 模型对比指南 / 模型选择速查页 / index 页面）。当用户要求"参考 index.html 风格"制作模型指南页、或要求"从官方文档更新模型信息/校准模型数据"时使用。覆盖两类任务：(1) 以统一设计体系新建模型指南页（如 openai/gemini/qwen/deepseek 等厂商）；(2) 从 OpenAI 官网 / Azure AI Foundry 等官方来源抓取最新模型数据（型号、推理、速度、价格、上下文/输入/输出）并更新到现有指南页。重要触发约定：只要用户输入"更新""重新生成""刷新""同步""重做"等词汇（如"更新模型指南""重新生成一下页面"），一律代表按模板完整重新生成一个新的 index 页面——执行完整流水线（官方抓取 → 数据回填 → 双语同步 → 渲染校验），除非抓取到的数据与上一次没有任何变化（此时仅报告"数据无变化"即可，无需重渲染）。即使用户只说"更新一下这个模型页面""做个 xx 模型的指南"也应触发。
---

# Model Guide 页面生成与更新技能

本技能沉淀了 cloud-model-use 项目中模型选择指南页的两类工作流。核心原则：**设计风格以 index.html 为唯一基准，模型数据以官方文档为唯一基准**，两者都不凭记忆生成。

## 提供商索引（生成方法按提供商分别沉淀）

技能的**通用资产**（模板、渲染器、提取器、校验器、设计规范、数据结构）对所有提供商通用；**提供商专用资产**（数据文件、官方数据源方法、厂商定制抓取/解析脚本）按提供商分别沉淀在 `data/<厂商>.json` 与 `references/providers/<厂商>.md`。

| 提供商 | 页面 | 数据文件 | 数据源方法 | 抓取/解析脚本 | 状态 |
|---|---|---|---|---|---|
| **OpenAI** | `openai-model-userguide.html` / `openai-model-userguide-en.html` | `data/openai.json` + `data/openai-en.json` | `references/providers/openai.md` | `openai/fetch_models.py` / `openai/parse_cards.py` / `openai/make_openai_en.py` | ✅ 已沉淀（全链路验证通过；**中英双语**） |
| **阿里 Qwen** | `qwen-model-userguide.html` / `qwen-model-userguide-en.html` | `data/qwen.json` + `data/qwen-en.json` | `references/providers/qwen.md` | `qwen/fetch_docs.py` / `qwen/make_qwen_en.py` | ✅ 已沉淀（全链路验证通过；**中英双语**） |
| **Google Gemini** | `gemini-model-userguide.html` / `gemini-model-userguide-en.html` | `data/gemini.json` + `data/gemini-en.json` | `references/providers/gemini.md` | `gemini/fetch_docs.py` / `gemini/make_gemini_en.py` | ✅ 已沉淀（全链路验证通过；**中英双语**） |
| **智谱 Z.ai** | `zai-model-userguide.html` / `zai-model-userguide-en.html` | `data/zai.json` + `data/zai-en.json` | `references/providers/zai.md` | `scripts/zai/fetch_docs.py` / `zai/make_zai_en.py` | ✅ 已沉淀（模板生成 + 页面生成全链路验证通过；**中英双语**） |
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

**触发语义约定（重要）**：当用户输入"更新""重新生成""刷新""同步""重做"等词汇（例如"更新模型指南""重新生成一下页面"），默认代表**按模板完整重新生成一个新的 index 页面**——执行完整流水线（官方抓取 → 数据回填/审补 → 双语同步 → 渲染 + 校验），而非局部修补。**唯一例外**：抓取到的数据与上一次相比没有任何变化（模型清单、字段、价格、日期均一致）时，只需报告"数据与上次一致，无需重新渲染"，不产出新页面。判断是否变化以本次抓取的官方数据与 `data/<厂商>.json` 的实际 diff 为准，而不是凭印象。

| 用户意图 | 工作流 |
|---|---|
| 新做一个模型指南页（"参考 index.html 风格做 xx 的指南"） | A. 生成页面 |
| 更新/重新生成现有页面（"更新""重新生成""刷新""同步""重做"等词汇，含"从官方文档获取最新信息更新"） | B. 更新数据（完整重新生成；数据无变化时仅报告） |
| 调整页面局部展示（改列、改图标、改档位划分） | C. 局部调整（改 data JSON + 渲染器，遵守设计体系） |

## 工作流 A：生成新页面

1. **读风格基准**：读取项目根目录 `index.html` 的 `<style>` 区（前 ~1300 行）和 `references/page-style.md`，提取设计体系。不要凭印象写样式——index.html 可能已迭代。
2. **收集内容**：确定厂商与模型清单。若用户给了来源（文档/URL），先抓取整理；没有则按工作流 B 的方法从官方文档获取。
3. **写文件**：单文件 HTML，内联 `<style>`，结构为：hero 页头（eyebrow + 标题 + 描述 + 统计条）→ 吸顶锚点导航 → 图例 → 快速选型卡片 → 各分类表格 → 弃用表 → 能力矩阵 → 页脚。组件规范见 `references/page-style.md`。
4. **校验**：运行 `python scripts/check_html.py <文件>`，必须标签配对正确、每张表表头列数 == 数据行单元格数。

## 工作流 B：更新数据

> **本工作流对应"更新/重新生成"触发语义**：按完整流水线重新生成新页面（抓官方数据 → 回填 → 双语同步 → 渲染 → 校验 → 写 diff）。执行第 1 步抓到官方数据后，先与 `data/<厂商>.json` 对比：若模型清单与全部字段（型号、推理/速度/价格档位、上下文/输入/输出、日期）均无变化，则**停止后续步骤**，向用户报告"数据与上次一致，无需重新渲染"，不重渲染、不写 diff 记录。有任何变化才继续完整流水线。

1. **抓官方数据**：按 `references/providers/<厂商>.md` 的方法抓取（OpenAI 见 `references/providers/openai.md`）。**各厂商脚本的代理通道可能整体失效**（实测 2026-08-30：OpenAI 的 `api.allorigins.win` 全部 52x、Gemini 的 `proxy.cors.sh`/`corsproxy.org` 全部失效）——此时用 IDE 的 **WebFetch 工具直连官方页面兜底**（实测 `developers.openai.com`、`ai.google.dev` 直连成功），再按 providers 文档的解析规则人工解析；数据以官方页面为准，代理与直连结果矛盾时以直连核对。**通道经验（2026-09-01 实测）**：OpenAI 的 `developers.openai.com` 已被 Cloudflare 全面拦截（allorigins 全 52x、curl_cffi 各浏览器指纹 403、Playwright 403），**首选 Azure Learn 三页直连**（模型清单/退役计划/定价，均稳定直连成功）作为 OpenAI 数据主力；Gemini 的 `api.allorigins.win` **间歇可用**（约 1/9 成功率），用间隔 8 秒 + 最多 20 次重试的脚本可拿到 models/pricing/deprecations 三页（判定成功 = HTTP 200 且 >100KB，防广告页误判）。OpenAI 侧要点：
   - Azure 文档（模型清单、退役计划）用 `scripts/openai/fetch_azure_docs.py` 直连抓取，可 `--section "Azure OpenAI"` 只取所需章节；`developers.openai.com` / `platform.openai.com` 被 Cloudflare 拦截，须用 `scripts/openai/fetch_models.py`（走 `api.allorigins.win` 代理 + 重试，失败率约 70%，每页重试 6-8 次）。
   - 抓完 OpenAI 详情页后用 `scripts/openai/parse_cards.py` 解析为 JSON。
   - 模型详情页追加 `.md` 可拿到 Markdown 版本（含价格表、上下文/输入/输出 token 数），比解析 HTML 更可靠。
2. **映射为页面档位**：严格按 `references/page-style.md` 的映射表——推理 5 档（官方图标格数 1:1）、速度 5 档、价格 6 档、模态图标。**官方标 Intelligence 的模型是非推理模型，归入"快速"档，不要标推理点。**
3. **批量更新**：`fill_objective_fields.py --write` 自动回填客观字段；新增模型在 data JSON 对应 section 插行（objective 字段可先留空再自动填）；**统计数字同步改——`meta.stats` 首个数字「收录模型」= 各模型表行数之和（排除 `naming`/`matrix` 等辅助表与 `deprecated`/`historical` 区；Z.ai 的 `69+` 含 historical 为既有口径），更新后应核对与页面实际一致**；更新日期用 `sync_dates.py --write --date YYYY-MM-DD` 统一——**务必显式传 `--date` 指定本次实际更新日期**（本次踩坑：不带 `--date` 会取文件内旧日期，导致页面显示过期同步日期；且 zh/en 全部 8 份数据文件都要跑，保持两语言一致）——只动「（YYYY-MM-DD 同步）」括注与 `footer_updated`，表格行内的官方退役日期不受影响；不带参数运行可只报告一致性；**每次更新必须在 `diff/` 目录生成日期命名（如 `diff/2026-08-30.md`）的变更记录，同一天所有提供商的变更写入同一文件，按 `## 提供商` 分节**，且只记录模型数据变更（新增/删除/字段变更），每行一条。
4. **双语同步（必做）**：`<厂商>.json` 改完后必须同步英文数据与页面——先跑对应 `make_<厂商>_en.py`（新中文文案会漏翻告警，补翻译表后重跑，直至输出「全部中文已翻译」），再 `render_guide.py` 渲染。渲染器会自动检测同目录的 `<厂商>-en.json` 并**一并渲染英文页 + 自动跑 `check_bilingual.py` 中英文语义一致性校验**（结构镜像 / 语言中立档位值 / 模型 ID 集合 / en 无中文残留），任一项不一致即失败退出；只需中文页时加 `--zh-only`。**渲染输出路径是本次踩坑点（2026-09-01）：`render_guide.py` 的 `-o` 是相对当前工作目录的——必须在项目根目录 `d:/github-code/cloud-model-use` 执行命令（`python .claude/skills/model-guide/scripts/render_guide.py .claude/skills/model-guide/data/<厂商>.json -o <厂商>-model-userguide.html`），否则会把页面输出到技能目录内，而根目录的实际页面不会被更新（表现为"页面底部 Last updated 还是旧日期"）。渲染后务必核对根目录页面的同步日期与本次一致。**
5. **校验**：渲染器自动调用 check_html.py（zh/en 两页都会跑）。列结构变更（增删列/增删行类型）后重点检查结构不一致的表。
6. **清理临时文件**：任务结束后删除本次产生的临时抓取文件（`_gemini_*.html`、`_aliyun_*.html`、`_azure_tmp.html`、`_rt*.html/json` 等）。`_model_pages/`、`_model_md/` 是可复用缓存，可保留或按需清理；所有临时/缓存路径必须已在 `.gitignore` 中声明。

## 按提供商独立更新

四个已沉淀厂商在数据、脚本、页面上**完全独立**：
- 各厂商有独立的 `data/<厂商>.json` 事实源；
- 各厂商有独立的官方数据源方法、抓取/解析脚本；
- 渲染生成独立的 `<厂商>-model-userguide.html`；
- 根目录 `index.html` 只通过 iframe Tab 聚合四个页面，不依赖页面内容，仅在**总收录模型数**变化时才需要更新其统计数字。

因此可以**单独更新任一厂商**，也可以**批量更新全部厂商**，互不影响。

### 单独更新某一厂商
按「提供商索引」找到对应厂商脚本，执行该厂商工作流后**先同步英文数据、再渲染（渲染器自动渲染 zh+en 两页）**：

```bash
# 示例：仅更新 Z.ai（以下命令在项目根目录执行）
python scripts/zai/update_data.py --fetch --apply
python scripts/zai/make_zai_en.py                      # 同步英文数据（漏翻会告警）
python scripts/render_guide.py .claude/skills/model-guide/data/zai.json -o zai-model-userguide.html
```

**按量 API 下架模型的迁移（2026-09-01 实测）**：Z.ai 官方 pricing 页的**按量 API 区**是"哪些模型还在卖"的权威来源；某模型若只出现在「模型微调/私有实例」区（LoRA/全参微调、算力单元）而不再出现在按量价格表，说明其**按量 API 已下架**。此时应从主表（text/vision/image/video 等）移入 `historical` 区，说明列标注「按量 API 已下架，仅提供微调与私有化部署」；价格列置 `null` 或保留既有值并注明。本次据此将 `GLM-4-9B`、`ChatGLM3-6B` 移入 historical（update_data.py 会以「可能下架」报告此类模型，人工核对 pricing 页后确认迁移）。**迁移后主表行数减少但总数不变（historical 行数增加），`meta.stats` 收录数无需改动。**

```bash
# 示例：仅更新 OpenAI
python scripts/openai/fetch_models.py
python scripts/openai/parse_cards.py
python scripts/fill_objective_fields.py .claude/skills/model-guide/data/openai.json _openai_cards.json --write
python scripts/openai/make_openai_en.py                # 同步英文数据（漏翻会告警）
python scripts/sync_dates.py --write .claude/skills/model-guide/data/openai.json
python scripts/render_guide.py .claude/skills/model-guide/data/openai.json -o openai-model-userguide.html
```

### 批量更新全部厂商
```bash
# 1. 并行抓取各厂商官方数据
python scripts/openai/fetch_models.py
python scripts/gemini/fetch_docs.py
python scripts/qwen/fetch_docs.py
python scripts/zai/fetch_docs.py overview pricing -o _g_zai/

# 2. 各厂商分别回填/审补并渲染（OpenAI 用 fill_objective_fields，其余按各自工作流）
#    render_guide.py 渲染 zh 时会自动一并渲染对应 en 页（发现 <厂商>-en.json 即同步）
python scripts/fill_objective_fields.py .claude/skills/model-guide/data/openai.json _openai_cards.json --write
python scripts/openai/make_openai_en.py                # 同步英文数据（漏翻会告警）
python scripts/render_guide.py .claude/skills/model-guide/data/openai.json -o openai-model-userguide.html

python scripts/gemini/make_gemini_en.py
python scripts/render_guide.py .claude/skills/model-guide/data/gemini.json -o gemini-model-userguide.html

python scripts/qwen/make_qwen_en.py
python scripts/render_guide.py .claude/skills/model-guide/data/qwen.json -o qwen-model-userguide.html

python scripts/zai/update_data.py --apply
python scripts/zai/make_zai_en.py
python scripts/render_guide.py .claude/skills/model-guide/data/zai.json -o zai-model-userguide.html

# 3. 统一同步日期（zh/en 两份数据文件都要跑，保持两语言日期一致；--date 显式指定本次实际更新日期）
python scripts/sync_dates.py --write --date 2026-09-01 \
  .claude/skills/model-guide/data/openai.json .claude/skills/model-guide/data/openai-en.json \
  .claude/skills/model-guide/data/gemini.json .claude/skills/model-guide/data/gemini-en.json \
  .claude/skills/model-guide/data/qwen.json .claude/skills/model-guide/data/qwen-en.json \
  .claude/skills/model-guide/data/zai.json .claude/skills/model-guide/data/zai-en.json

# 4. 如总收录模型数变化，更新 index.html 统计数字
# 5. 日期同步涉及翻译表日期时，同步更新 make_<厂商>_en.py 中的日期并重跑 en 数据
```

无论单独还是批量更新，模型数据变更都按日期写入同一个 `diff/YYYY-MM-DD.md` 文件，以 `## 提供商` 分节追加。

## 工作流 C：局部调整

改 data JSON 或渲染器，但遵守 `references/page-style.md` 的既有约定（如模态列用纯图标 + title、推理用点阵、价格用阶梯信号条、徽章实心白字、定位列在价格列前）。新增展示维度时先想"与官方哪个字段对应"，保持页面数据可溯源。新增单元格类型时在渲染器 CELL_RENDERERS 注册，并同步提取器 parse_cell。

## 四条硬性约定

- **样式不即兴**：所有颜色/字体/组件从 index.html 的 CSS 变量复制，不新造色值。
- **数据可溯源**：每个模型行的关键指标（推理、速度、价格、上下文）必须能对应到官方页面；官方查不到的（如 Azure-only 的 chat 变体）沿用现有值并在总结中注明"未能验证"。**核对结论要落文档**：更新时先用官方数据与 data JSON 做差异核对（模型清单 / 档位 / 价格 / 上下文 / 关停日期），无变化的厂商在 diff 记录里写明「数据核对一致，无变更」，只有真实变化才改数据。
- **改动后必校验**：`scripts/check_html.py` 全绿才算完成。**渲染后必核根目录页面**：确认根目录 `<厂商>-model-userguide.html`（及 -en）的同步日期与本次一致（`render_guide.py` 的 `-o` 相对当前工作目录，必须在项目根目录执行，否则页面输出到技能目录内、根目录页面不更新）。
- **更新必同步双语**：任何对 `<厂商>.json` 的模型/文案修改，都必须跑对应 `make_<厂商>_en.py`（漏翻会告警，补翻译表重跑至无告警）并渲染两页（渲染器自动同步 en 页并跑 `check_bilingual.py` 语义校验）；中英文两版缺一、或 `check_bilingual.py` 不一致即视为未完成。
- **任务结束清场**：skill 执行完毕后清理本次产生的临时抓取文件；缓存目录（如 `_model_pages/`、`_model_md/`）可保留但必须在 `.gitignore` 中声明，避免污染版本控制。

## 中英文切换（全部提供商已落地）

**机制**：语言中立内容（模型 ID、数字、档位 key、模态 key、ctx 数值、URL）两种语言共用；需翻译的编辑字段（meta 文案、section 标题/描述/表头、mdesc、quick 卡片、flow/scene 标签、徽章）按语言分数据文件。渲染时 `--lang en` 只切换渲染器内的标签表（推理/速度/价格/模态/定位/生命周期/图例标题、页脚「最后更新/Last updated」），数据内容本身不变。

```
data/<厂商>.json（zh，事实源）───────render_guide.py───────► <厂商>-model-userguide.html
data/<厂商>-en.json（en 副本）────────render_guide.py --lang en──► <厂商>-model-userguide-en.html
```

- **英文数据生成**：改完 `data/<厂商>.json` 后运行对应脚本（路径已在脚本内自动推导）：
  - OpenAI → `python scripts/openai/make_openai_en.py`
  - Qwen → `python scripts/qwen/make_qwen_en.py`；Gemini → `scripts/gemini/make_gemini_en.py`；Z.ai → `scripts/zai/make_zai_en.py`
  
  脚本按翻译表精确替换编辑字段，语言中立字段原样保留；**漏翻的中文会告警列出**（exit 1），需补进翻译表后重跑。翻译是递归的，`{"raw": html}`、ctx 高亮 `{"v": …, "hi": true}` 等嵌套结构也会翻译。
- **渲染两页**（以 Qwen 为例，其余同）：渲染 zh 数据时渲染器会自动检测同目录的 `<厂商>-en.json` 并**一并渲染英文页 + 自动跑 `check_bilingual.py` 中英文语义一致性校验**，一条命令即可完成两页与校验：
  ```bash
  python scripts/render_guide.py .claude/skills/model-guide/data/qwen.json -o qwen-model-userguide.html
  # 上述命令自动输出 qwen-model-userguide-en.html（lang=en）并校验两文件语义一致
  # 只需中文页时加 --zh-only；单独重渲英文页：render_guide.py data/qwen-en.json -o qwen-model-userguide-en.html --lang en
  ```
- **中英文语义 check（`scripts/check_bilingual.py`，渲染时自动执行）**：① sections 结构镜像（id/kind/columns 长度/row_types/行数）；② 语言中立单元格值一致（model_id、tier、price 档位 key、reasoning、speed、mods、ctx、num、lifecycle——仅当 zh 侧不含中文时强制逐字一致，中文编辑值由 make 脚本漏翻告警兜底）；③ 模型 ID 集合（含弃用表）完全一致；④ en 数据无中文残留。任一项失败渲染即退出。
- **语言切换器**：`meta.lang_switch`（`{"zh": {"href": "…", "label": "中"}, "en": {"href": "…-en.html", "label": "EN"}}`）声明后，渲染器在页头右上角生成 中/EN 静态互链（当前语言高亮）。链接带 `data-lang-href`，页内脚本自动附加 `?embed=1` 保持嵌入态。**嵌入模式（?embed=1）隐藏页头，切换器随页头不显示**——index.html 的页面右上角（hero 顶部）提供全局语言切换：点击「EN」同时切换**外壳文案**（H1/描述/统计标签/Tab 名/`<title>`，经 `data-i18n` + JS `I18N` 字典）与**全部 iframe**（到 `<厂商>-en.html`，保留 `?embed=1`），并用 `localStorage['model-guide-lang']` 记忆偏好、刷新保持。
- **维护约定**：每次更新 zh 数据后同步跑对应 `make_<厂商>_en.py` 并渲染两页；新增模型/字段的中文文案需补翻译表，否则脚本告警。两份 JSON 存在漂移风险，告警机制用于兜底。

## 已评估暂缓事项

- ~~**中英文切换**~~ → 已落地，见上文「中英文切换（全部提供商已落地）」。四厂商双语页均通过 `check_html` 全绿；新厂商按同一模式复制数据文件 + 翻译编辑字段即可。

## 资源索引

**通用资产（所有提供商共用）**
- `references/page-style.md` — 设计体系完整规范（CSS 变量、厂商主题色、Hero 装饰元素、组件、档位映射表）
- `references/data-schema.md` — data JSON 结构说明（手写/手改数据文件时查阅）
- `assets/guide.template.html` — 页面模板（CSS + 骨架 + {{占位符}}）
- `scripts/render_guide.py` — 渲染器（data JSON + template → HTML，自动校验；渲染 zh 数据时若存在对应 `<厂商>-en.json` 自动一并渲染 en 页，`--zh-only` 关闭；`--lang en` 渲染英文标签）
- `scripts/extract_guide_data.py` — 反向提取（已有 HTML → data JSON）
- `scripts/fill_objective_fields.py` — 官方数据自动回填客观字段
- `scripts/check_html.py` — HTML 结构校验（标签配对 + 表格列数）
- `scripts/check_data.py` — data JSON 业务规则校验（弃用表收录规则、行长度、枚举值合法）
- `scripts/check_bilingual.py` — 中英文语义一致性校验（结构镜像 / 语言中立值 / 模型 ID 集合 / en 无中文残留；渲染 zh 时自动执行）
- `scripts/verify_official.py` — 官方交叉校验（模型存在性、价格声称、遗漏差集归因）
- `scripts/compare_html.py` — HTML 语义对比（回归验证：忽略注释/空白找差异）

**OpenAI 专用**
- `data/openai.json` — OpenAI 页面数据（唯一事实源，也是新厂商的参照样例）
- `data/openai-en.json` — 英文版页面数据（`make_openai_en.py` 生成，双语试点）
- `references/providers/openai.md` — OpenAI 官方数据源抓取方法（代理、重试、解析结构、404 回退）
- `scripts/openai/fetch_models.py` — 批量抓取 OpenAI 模型详情页（代理 + 重试）
- `scripts/openai/parse_cards.py` — 解析 OpenAI 详情页指标卡为 JSON
- `scripts/openai/make_openai_en.py` — 由 openai.json 生成 openai-en.json（翻译表精确替换 + 漏翻告警）
- `scripts/openai/fetch_azure_docs.py` — 抓取 Azure Learn 文档页转结构化文本（可 --section 截取章节；退役计划/模型清单均用此脚本）

**阿里 Qwen 专用**
- `data/qwen.json` — Qwen 页面数据（唯一事实源；CNY 计价，图例经 legend_overrides 覆盖）
- `references/providers/qwen.md` — 阿里云百炼数据源方法（直连、ICE_PAGE_PROPS 正文提取、价格口径、思考/速度档位映射约定）
- `scripts/qwen/fetch_docs.py` — 抓取 help.aliyun.com 文档页转结构化文本（提取 __ICE_PAGE_PROPS__ 内嵌正文）
- `data/qwen-en.json` — 英文版页面数据（`make_qwen_en.py` 生成）
- `scripts/qwen/make_qwen_en.py` — 由 qwen.json 生成 qwen-en.json（翻译表 + 漏翻告警）

**Google Gemini 专用**
- `data/gemini.json` — Gemini 页面数据（唯一事实源；USD 计价；PDF 已作为独立输入模态与 text/image/audio/video 并列）
- `references/providers/gemini.md` — Google 数据源方法（proxy.cors.sh 通道、三页分工、关停日期语义、PDF 模态标注规则）
- `scripts/gemini/fetch_docs.py` — 抓取 ai.google.dev 文档页转结构化文本（经 proxy.cors.sh 代理）
- `data/gemini-en.json` — 英文版页面数据（`make_gemini_en.py` 生成）
- `scripts/gemini/make_gemini_en.py` — 由 gemini.json 生成 gemini-en.json（翻译表 + 漏翻告警）

**智谱 Z.ai 专用**
- `data/zai.json` — Z.ai 页面数据（唯一事实源；CNY 计价；官方模型 ID 为大写 GLM/CogView/Embedding 形式）
- `references/providers/zai.md` — BigModel 数据源方法（docs.bigmodel.cn / open.bigmodel.cn 直连、价格口径、特殊计费单元处理、主题色说明）
- `scripts/zai/fetch_docs.py` — 抓取 BigModel 模型概览（静态）与产品价格（Vue SPA，需 Playwright 渲染）转结构化文本
- `scripts/zai/update_data.py` — 自动对比 overview/pricing 与 `data/zai.json`，生成差异报告并自动应用上下文/输出/价格字段变更
- `scripts/zai/patch_zai_data.py` — 根据 pricing 缺失模型清单批量补充新模型，并自动插入 `historical` 历史模型区；变更记录默认追加到 `diff/YYYY-MM-DD.md` 的 `## Z.ai（补丁）` 分节
- `data/zai-en.json` — 英文版页面数据（`make_zai_en.py` 生成）
- `scripts/zai/make_zai_en.py` — 由 zai.json 生成 zai-en.json（翻译表 + 漏翻告警）

**其他提供商**：待按「新增提供商指南」沉淀（DeepSeek…）

