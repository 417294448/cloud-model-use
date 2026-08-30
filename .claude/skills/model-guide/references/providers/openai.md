# OpenAI 官方数据源抓取方法（提供商专用）

> 本文件是 **OpenAI 模型**（`openai-model-userguide.html` / `data/openai.json`）的数据源方法。
> 通用流水线（模板/渲染/提取/校验）见 SKILL.md；其他提供商的方法将分别沉淀为
> `references/providers/<厂商>.md`（Gemini、Qwen、DeepSeek 等待补充）。

更新 OpenAI 模型数据时，两个官方来源各有抓取门道。核心结论：**Azure 直连可用；OpenAI 官网被 Cloudflare 拦截，必须走公共代理 + 重试**。

## 目录

- 来源优先级
- 来源 1：Azure AI Foundry 文档（直连）
- 来源 2：developers.openai.com（代理 + 重试）
- 模型详情页的两种指标卡 DOM 结构
- .md Markdown 版本（最省事）
- 404 与回退策略
- 批量抓取脚本用法

## 来源优先级

1. `developers.openai.com/api/docs/models/*` — 模型详情页，含官方指标卡（Reasoning/Speed/Price/Input/Output），是**推理/速度档位的唯一权威来源**
2. `developers.openai.com/api/docs/models/compare` — 对比页，默认只展示最新系列（如 GPT-5.6 三兄弟）
3. `learn.microsoft.com/zh-cn/azure/ai-foundry/foundry-models/concepts/models-sold-directly-by-azure` — 模型全清单、上下文/输入/输出 token 数、发布日期、训练数据截止；覆盖 OpenAI 站 404 的模型（chat 变体等）
4. `learn.microsoft.com/en-us/azure/foundry/openai/concepts/model-retirement-schedule` — **模型退役计划**（可直连）：每个模型的版本、生命周期（Deprecated/Retired/Legacy/GA/Preview）、退役日期、官方推荐替代，是弃用表的唯一权威来源；页面"Azure OpenAI"模块即 OpenAI 模型部分

**弃用表收录规则**：只展示**本页主表已收录**的模型的弃用/退役信息。官方弃用清单中的历史模型（如 dall-e、babbage-002、text-moderation 等从未出现在本页主表的模型）不收录——弃用表的目的是告诉读者"你正在看的这些模型哪些不能用/何时退役"，无关的历史条目只会稀释信息。更新弃用表时以主表模型 ID 集合做过滤校验（参考实现：收集非弃用表全部 model_id，逐行匹配过滤）。

## 来源 1：Azure AI Foundry 文档（直连）

直接 curl 即可，无需代理：

```bash
curl -sL --max-time 60 -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36" \
  "https://learn.microsoft.com/zh-cn/azure/ai-foundry/foundry-models/concepts/models-sold-directly-by-azure" -o azure.html
```

页面是标准 Learn 文档 HTML，用 Python 提取 `<main>` 后转文本解析（`<tr>`→`ROW:`、`<td>`→`|`、`<h2/h3>`→`H2:/H3:`）。每个模型一节，含：模型 ID（含版本日期）、能力清单、上下文窗口（"1,050,000 输入：922,000输出：128,000"格式）、最大输出、训练数据截止。

注意：该页**不含已弃用模型**；价格不在此页（价格看 OpenAI 详情页指标卡或定价页）。

## 来源 2：developers.openai.com（代理 + 重试）

直连、WebFetch、llms.txt 均被 Cloudflare 403。**可行通道：`api.allorigins.win` 公共代理**：

```bash
curl -sL --max-time 40 --tlsv1.2 -A "Mozilla/5.0" \
  "https://api.allorigins.win/raw?url=developers.openai.com/api/docs/models/<slug>"
```

代理对源站约 70% 概率返回 52x 错误（响应体 16 字节 `error code: 52x`），**必须重试 6-8 次**，成功标志是响应 >100KB（正常页面约 300-420KB）。其他代理（codetabs 522、corsproxy 要 key、r.jina.ai 不通、wayback 超时）在本项目网络下均不可用，不必再试。

**备用通道（2026-08-30 实测）**：代理通道可能**整体失效**（`api.allorigins.win` 全部 52x 时 `fetch_models.py` 无法产出有效页），此时可用 IDE 的 **WebFetch 工具直连 `developers.openai.com` 详情页**（`/api/docs/models/<slug>`，实测直连成功），逐页核对指标卡与价格；配合 Azure 文档（直连）核对 token 数与退役计划。直连页面结构同「两种指标卡 DOM 结构」，`.md` Markdown 版本同样适用。

模型 slug 与 API 模型 ID 一致（`gpt-5.4`、`gpt-5.2-codex`、`o3-pro`、`gpt-realtime-2.1` 等）。索引页 `/api/docs/models` 可列出当前全部有效 slug——**发现新模型的途径**（本会话中发现了 gpt-5.6-cyber、daybreak-red/blue-latest）。

## 模型详情页的两种指标卡 DOM 结构

**结构 A（详情页主体）**：`lg:uppercase">标签</div>` 后跟指标值。标签为 Reasoning/Intelligence、Speed、Price、Input、Output：

- Reasoning/Intelligence：SVG 图标数 = 格数（5=Highest, 4=Higher, 3=High, 2=Average），后有文字等级
- Speed：同上（5=Very fast, 4=Fast, 3=Medium, 2=Slow, 1=Slowest）
- Price：`$2.5 • $15 Input • Output` 文本
- Input/Output：图标 + 文字（`Text, image`）；灰色 `text-gray-400` 包裹的图标 = 不支持该模态

**结构 B（compare 页/规格行）**：`flex flex-row justify-between ... <div>标签</div><div class="font-semibold">值`，含 Context Window、Max Output Tokens、Knowledge Cutoff、各端点支持情况。

**Reasoning vs Intelligence 是区分推理模型的关键**：标 Intelligence 的模型（gpt-4.1 系列、gpt-4o 系列）没有推理能力，页面落档为"快速"。

## .md Markdown 版本（最省事）

详情页 URL 追加 `.md` 返回 Markdown（页面自己也声明了这一点），同样经代理抓取：

```
https://api.allorigins.win/raw?url=developers.openai.com/api/docs/models/gpt-5.6-sol.md
```

含一句话定位、Model ID、模态、上下文/最大输入/最大输出 token、知识截止、**完整价格表**（Input/Cached input/Output 及促销说明）、端点支持矩阵。解析 Markdown 比解析 HTML 指标卡可靠得多，**优先用 .md 拿价格与 token 数，用 HTML 指标卡拿推理/速度格数**。

## 404 与回退策略

以下模型在 OpenAI 文档站 404（属于 ChatGPT 侧或 Azure-only），**回退用 Azure 文档数据**，并在总结中注明"未能以 OpenAI 官网验证"：

- 全部 `-chat` 变体（gpt-5-chat、gpt-5.1/5.2/5.3-chat）、gpt-chat-latest
- 部分老模型与工具模型（whisper、tts-1 系列、computer-use-preview、codex-mini 等，视官网当期收录而定）

**token 口径注意（2026-08-30 实测）**：`gpt-realtime` 系列官网上下文为 128K/32K，而 Azure 清单为 32K/4K，两者存在差异——页面既有口径沿用 Azure（32K/4K），官网与 Azure 冲突时先对齐 Azure 再人工确认，勿直接套官网值。

## 批量抓取脚本用法

```bash
# 抓取（slug 列表内置，可按需增删；已存在的文件自动跳过）
python scripts/openai/fetch_models.py gpt-5.4 o3-pro gpt-realtime-2.1
# 输出到 _model_pages/<slug>.html

# 解析为 JSON（推理/速度格数+文字、价格、模态）
python scripts/openai/parse_cards.py _model_pages
# stdout 输出 JSON，可重定向保存
```

代理不稳，批量抓 30+ 页面需 10-20 分钟，建议放后台运行。抓完先剔掉 <100KB 的失败页再解析。
