# 阿里云百炼（通义千问 Qwen）官方数据源抓取方法（提供商专用）

> 本文件是 **通义千问模型**（`qwen-model-userguide.html` / `data/qwen.json`）的数据源方法。
> 通用流水线（模板/渲染/提取/校验）见 SKILL.md；其他提供商见 `references/providers/<厂商>.md`。

核心结论：**help.aliyun.com 可直连，无需代理**；页面是 ICE 框架 SPA，正文内嵌在 `window.__ICE_PAGE_PROPS__` 中，用 `scripts/qwen/fetch_docs.py` 一键抓取并转结构化文本。

## 目录

- 来源优先级
- 页面机制：ICE_PAGE_PROPS 内嵌正文
- 各页面内容与用途
- 价格口径（CNY，与档位映射）
- 数据注意点

## 来源优先级

1. `help.aliyun.com/zh/model-studio/models` — 模型总览：当前主推模型清单（按 文本生成/图像与视频/音频/全模态/向量 分类），发现新一代模型的入口
2. `help.aliyun.com/zh/model-studio/billing` — 模型价格：全部模型的 CNY 价格（输入/输出单价、阶梯计费、Batch 半价、免费额度），**价格档位的权威来源**
3. 分类文档（选型指南+规格表，**能力特性的权威来源**）：
   - `vision-model` — 视觉理解：上下文、视频时长、Function Calling、内置工具、结构化输出
   - `image-model` — 图像生成：文生图/编辑支持、最大输出数、分辨率
   - `omni` — 全模态：输入输出模态、FC/联网/思考模式、各语言支持
   - `s2s-model` — 语音转语音：S2S vs Pipeline 选型、实时对话能力
   - `tts-model` — 语音合成：系列/API/声音复刻/声音设计/指令控制
   - `speech-recognition` — 语音识别：实时/非实时、热词、说话人分离、情感识别、**即将下线模型清单**
   - `embedding-rerank-model` — 向量与重排序：向量维度、最大 Token、适用场景
   - `qwq` — 深度思考：混合思考 vs 仅思考模式说明

## 页面机制：ICE_PAGE_PROPS 内嵌正文

help.aliyun.com 的文档页 HTML 是 JS 壳，正文不在 DOM 里，而是内嵌在：

```
window.__ICE_PAGE_PROPS__={"docDetailData":{"storeData":{"data":{"content":"<div ...>正文HTML</div>"}}}}
```

提取方法（已由 `scripts/qwen/fetch_docs.py` 固化）：定位 `window.__ICE_PAGE_PROPS__=` 到 `</script>` 的文本，整体作为 JSON 解析，取 `docDetailData.storeData.data.content`，再按 `<tr>→ROW:` 规则转文本。直接 grep DOM 会误判"页面无数据"。

## 各页面内容与用途

| 页面 | 提供的关键字段 |
|---|---|
| models（总览） | 最新一代模型 ID（如 qwen3.8-max、qwen3.5-omni-plus）、分类归属 |
| billing（价格） | 输入/输出单价（¥/1M tokens）、阶梯区间、Batch 半价、限时折扣、免费额度 |
| vision-model | 上下文（1M/256K/64k）、最大输出、视频时长（2 小时/1 小时）、FC/内置工具/结构化输出 |
| omni / s2s-model | 输入输出模态、API（HTTP/WebSocket）、FC/联网/思考支持、语言数 |
| tts-model | 系列归属、API、声音复刻/设计/指令控制支持矩阵 |
| speech-recognition | 实时/非实时、精度增强（热词/Prompt）、说话人分离、时长限制、即将下线列表 |

## 价格口径（CNY，与档位映射）

百炼价格为 **元 CNY / 1M tokens**（华北2·北京原价），映射到页面 6 档阶梯条：

| 档位 | 格数 | 输入价区间（¥） | 示例 |
|---|---|---|---|
| 天价 | 6 | 20+ | qwen3.8-max-prime ¥24 |
| 昂贵 | 5 | 8-20 | qwen3.8-max ¥12、qwen3.6-max-preview ¥9 |
| 较贵 | 4 | 2-8 | qwen3.7-plus ¥2、qwen3-coder-plus ¥4、qwen3.5-omni-plus ¥7 |
| 适中 | 3 | 0.5-2 | qwen3.8-flash ¥0.8、qwen3.6-flash ¥1.2、qwq-plus ¥1.6 |
| 实惠 | 2 | 0.1-0.5 | qwen3.7-flash ¥0.2、qwen-long ¥0.5 |
| 白菜价 | 1 | <0.1 | text-embedding-v4 等 |

- 定档按**输入原价**（不含限时折扣；折扣信息写入说明列，如"限时 5 折"）
- 图例区间通过 data JSON 的 `legend_overrides` 覆盖（渲染器 default_legend 支持 ranges/note 参数）
- 视频生成按**输出秒数**计费（输入不计费）、图像生成按张计费——这些表不放价格档位，用"计费"列写原文
- **音频/实时/翻译类模型按音频 token 计费，单价与文本 token 不可比**（如 livetranslate 音频输入 ¥40-64/1M tokens、omni-realtime 音频输入 ¥27-80/1M tokens）：直接套档位会把它们误标成"天价"，此类模型价格单元格用 `{"raw": 官方原文}` 而不用档位（2026-08-29 数据校验时修正过 livetranslate 四行）
- **已验证的档位对照样例**（2026-08-29 与 billing 页逐行核对）：omni-plus-realtime ¥10→昂贵、omni-flash-realtime ¥2.2→较贵、audio-realtime-flash ¥3→较贵、qwen-omni-turbo ¥0.4→实惠

## 数据注意点

- **思考档位**：max=5 最强、plus=4 深度、flash=3 标准、旧版/非思考=1 快速（编辑性映射，官方无格数；QwQ 仅思考=5）
- **速度档位**：flash=4、plus=3、max/prime=2、realtime=4-5（编辑性估计，官方无速度分级）
- **旧版收录**：「旧版与即将下线」表只收录主表已存在的模型（弃用表收录规则，同 OpenAI）；即将下线清单来自 speech-recognition 页"其他（即将下线）"小节
- **第三方模型**：MiniMax/speech、happyhorse、z-image、kimi、GLM、DeepSeek 等百炼托管三方模型可收录，模型 ID 含 `/` 属正常（check_data 会有形式警告，可忽略）
- **日期快照**：`-latest` 与 `-YYYYMMDD` 快照一般不单列（主版本行已注明"当前能力等同于某快照"），保持表格简洁；开源模型的 `-2507` 快照例外——它就是当前代本体（如 qwen3-235b-a22b-instruct-2507）
- **交叉校验流程**：更新数据后跑 `scripts/verify_official.py data/qwen.json --docs <model-pricing.txt> <speech-recognition.txt>`——校验存在性、价格声称、遗漏差集（归因：候选补充/旧代/第三方/工具API/快照别名）。注意 sensevoice/gummy 等下线模型只在 speech-recognition 页出现、不在价格页，校验时两份文档都要给，否则会误报"不存在"
