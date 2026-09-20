# Anthropic 官方数据源抓取方法（提供商专用）

> 本文件是 **Anthropic Claude 模型**（`anthropic-model-userguide.html` / `data/anthropic.json`）的数据源方法。
> 通用流水线（模板/渲染/提取/校验）见 SKILL.md；其他提供商见 `references/providers/<厂商>.md`。

## 目录

- 来源优先级
- 可达性：文档站的地域限制与替代通道
- 各页面内容与用途
- 价格口径与档位映射
- 推理 / 速度档位映射（Claude 无官方格数）
- 数据注意点

## 来源优先级

1. `platform.claude.com/docs/en/about-claude/pricing` — **价格的唯一权威来源**：现役模型清单、每 1M token 输入/输出价、缓存价、Batch 半价
2. `platform.claude.com/docs/en/about-claude/model-deprecations` — **退役/弃用的唯一权威来源**：弃用公告日期、退役日期、推荐替代
3. `platform.claude.com/docs/en/about-claude/models/overview` — 模型总览：系列命名、alias、上下文/输出上限
4. Anthropic 官方 `claude-api` skill 内嵌缓存（`shared/models.md` 的模型目录、`shared/model-migration.md` 的退役表）——本身提炼自上述页面，**首次沉淀可用作基线**

## 可达性：文档站的地域限制与替代通道

实测（2026-09-08）：

| 通道 | 结果 |
|---|---|
| 直连 curl platform.claude.com/docs/... | ✅ **2026-09-20 实测已可用**：pricing 562KB / model-deprecations 421KB / models/overview 368KB，正文含完整价格表与退役表（此前 2026-09-08 为 302 重定向到 app-unavailable-in-region，已过时） |
| 追加 `.md` 后缀请求 | 未验证（当前直连 HTML 已足够，无需） |
| **WebFetch** | ⚠️ 可用但**返回快照不稳定**：同一 URL 时而返回最新版、时而返回较早缓存版（表现为 `Last updated` 日期偏旧、内容截断）——直连可用时优先用 curl，WebFetch 仅作回退 |
| **WebSearch** | ✅ 可用：检索到第三方对官方 pricing/deprecations 的转述与交叉比对（多源一致可采信） |
| **claude-api skill 官方缓存** | ✅ 可用：models.md / model-migration.md 内嵌从官方提炼的模型目录与退役表（缓存 2026-06-24） |

结论（2026-09-20 更新）：本项目网络下 **Anthropic 文档站现可直连抓取**（`curl -sL -A "<浏览器 UA>"`），数据核对以官方三页为准；WebFetch 因快照不稳定，仅作回退通道。历史结论（2026-09-08 "直连不可用，只能靠缓存 + WebSearch"）已过时，仅作背景。

## 各页面内容与用途

| 页面 | 提供的关键字段 |
|---|---|
| pricing | 现役模型清单与价位（Fable 5.1 / Fable 5 $10/$50、Mythos 5.1 / Mythos 5 $10/$50（limited availability）、Opus 5 / 4.8 / 4.7 / 4.6 / 4.5 $5/$25、Sonnet 5 $2/$10、Sonnet 4.6 / 4.5 $3/$15、Haiku 4.5 $1/$5）、缓存价（cache read 约输入价 0.1×，Fable 5.1 / Mythos 5.1 为 0.025×）、Batch 半价 |
| model-deprecations | 每个模型的弃用公告日期、退役日期（退役后 API 返回 404）、官方推荐替代模型 |
| models/overview | 系列命名（Opus/Sonnet/Haiku/Fable）、无日期 alias 用法、上下文窗口与 max output |

## 价格口径与档位映射

价格为 **USD / 1M tokens**（输入 / 输出），映射到页面 6 档阶梯条（以输入价定档，同 page-style 默认区间）：

| 档位 | 格数 | 输入价区间 | 示例 |
|---|---|---|---|
| 昂贵 | 5 | $10-100 | claude-fable-5 $10 |
| 较贵 | 4 | $2-10 | claude-opus-4-8 $5、claude-sonnet-5 $3 |
| 适中 | 3 | $0.5-2 | claude-haiku-4-5 $1 |

Claude 无「按张/按秒/按首」类非 token 计费模型，价格全部可用 token 档位表达。

## 推理 / 速度档位映射（Claude 无官方格数）

Anthropic 官方**不提供** OpenAI/Gemini 式的 Reasoning/Speed 图标格数。推理/速度两列为**编辑性估计**，依据官方定位描述（models/overview 各模型简介）映射，与 Gemini providers 文档的口径一致：

- **推理**：Fable 5 / Opus 4.6+ = 5（最强深度自适应思考，effort 高）；Opus 4.5 = 4（旧代次强）；Sonnet 5 / Sonnet 4.6 = 4（接近 Opus 的 Agentic 推理）；Sonnet 4.5 = 3；Haiku 4.5 = 2（轻量分类级）
- **速度**：Haiku = 5（官方定位 fast/cheap）；Sonnet = 4；Opus = 3；Fable 5 = 2（长程高难任务耗时较长）
- Claude 全系同模态（文本 + 图像输入、文本输出、PDF/长文档输入），**主表不设模态列**（无区分度）；图例模态组经 `legend_overrides.modalities = ["text","image","pdf"]` 收窄

## 数据注意点

- **无日期 alias**：现役新一代推荐用无日期 alias（`claude-opus-4-8`、`claude-sonnet-5`），自动指向最新快照；带日期快照（`claude-opus-4-5-20251101`）与 3.x 退役命名（`claude-3-opus-20240229`，日期=发版日）按官方原样
- **Fable 5 / Mythos 5**：同能力同价；Mythos 5 仅 Project Glasswing 专属，不入主表（naming 表说明）；Fable 5 需 30 天数据留存、深度思考常开不可关、价格高于 Opus
- **Sonnet 5 价格口径（2026-09-20 官方确认）**：官方 pricing 页明确 $2/$10 已是**常规价**，原定 2026-09-01 涨至 $3/$15 的计划**已取消**（"The previously scheduled increase to $3/$15 ... will not occur"）。页面按 $2/$10（high 档）记录，勿再按 $3/$15 定档
- **上下文口径**：Opus 4.6+/4.7/4.8、Sonnet 4.6/Sonnet 5、Fable 5 = 1M 标准；Opus 4.5 / Sonnet 4.5 = 200K（1M 需 beta/long-context）；Haiku 4.5 = 200K
- **输出上限**：Fable / Opus 4.6+ / Sonnet 4.6+ = 128K；Opus 4.5 / Sonnet 4.5 = 128K（长输出 beta 已 GA）；Haiku 4.5 = 64K
- **退役表收录规则**：只收 Claude API 主模型（全量退役 3.x / 2.x / 4.0 / 4.1 与 Haiku 3）；Bedrock/Vertex 平台各自的退役时点（如 Bedrock 的 3.7 延至 2026-05-11）不并表，页面以 Claude API 口径为准
- **退役日期语义**：退役后请求返回 404 not_found_error，无宽限期；弃用公告通常提前数月
