# Google Gemini 官方数据源抓取方法（提供商专用）

> 本文件是 **Google Gemini 模型**（`gemini-model-userguide.html` / `data/gemini.json`）的数据源方法。
> 通用流水线（模板/渲染/提取/校验）见 SKILL.md；其他提供商见 `references/providers/<厂商>.md`。

核心结论：**ai.google.dev / cloud.google.com 在本项目网络下直连超时，allorigins 等常用代理对 Google 源站返回 520/522；`proxy.cors.sh` 通道可用**，已由 `scripts/gemini/fetch_docs.py` 固化。

## 目录

- 来源优先级
- 可达性：Google 文档的代理通道
- 各页面内容与用途
- 价格口径与档位映射
- 数据注意点

## 来源优先级

1. `ai.google.dev/gemini-api/docs/models` — **模型清单的唯一权威来源**：全部端点、Stable/Preview 状态、Shut down 标记（页面底部标注 Last updated 日期）
2. `ai.google.dev/gemini-api/docs/pricing` — **价格的唯一权威来源**：Free/Paid Tier、Standard/Batch/Flex/Priority 四档计费、促销价与生效日期、Grounding 费率
3. `ai.google.dev/gemini-api/docs/deprecations` — **关停计划的唯一权威来源**：每个模型的弃用公告日期、关停日期（最早可能日期）、官方推荐替代；已关停模型灰底标注

## 可达性：Google 文档的代理通道

实测结果（2026-08-29）：

| 通道 | 结果 |
|---|---|
| 直连 curl | 超时（网络阻断） |
| api.allorigins.win | 520/522（Google 源站对该代理不可达，重试 15 次均失败） |
| api.codetabs.com | 522 |
| web.archive.org（直连/经代理） | 超时 / 522 |
| r.jina.ai | 500 |
| api.cors.lol | 429 限流 |
| **proxy.cors.sh** | ✅ **200 可用**（models 147KB / pricing 240KB / deprecations 115KB） |
| corsproxy.org | ✅ 200 可用（备用通道） |

公共代理均有**速率限制**（连续调用几次后会限流），`scripts/gemini/fetch_docs.py` 已固化**多代理轮询重试**机制（cors.sh → corsproxy.org → allorigins 循环，最多 6 次）。备用方案：若全部失效，`GET https://generativelanguage.googleapis.com/v1beta/models`（需 API key）可列模型清单。

## 各页面内容与用途

| 页面 | 提供的关键字段 |
|---|---|
| models | 端点 ID、Stable/Preview 标记、Shut down 模型清单、命名规则（stable/preview/latest/experimental） |
| pricing | 输入/输出价（$ / 1M tokens）、促销价截止日期（如 2026 促销价至 2026-12-31）、缓存价、Batch/Flex/Priority 倍率、Grounding 免费额度与费率 |
| deprecations | 弃用公告日、关停日、替代模型、灰色已关停标注 |

## 价格口径与档位映射

价格为 **USD / 1M tokens**（Paid Tier，Standard 档，促销价），映射到页面 6 档阶梯条：

| 档位 | 格数 | 输入价区间 | 示例 |
|---|---|---|---|
| 天价 | 6 | $100+ | （无） |
| 昂贵 | 5 | $10-100 | （无） |
| 较贵 | 4 | $2-10 | gemini-3.1-pro-preview $2、gemini-3.5-transcribe $2、robotics-er-2 $2 |
| 适中 | 3 | $0.5-2 | gemini-3.7/3.6-flash $0.75、gemini-2.5-pro $1.25、tts $0.5-1、omni $1.5 |
| 实惠 | 2 | $0.1-0.5 | gemini-2.5-flash $0.3、3.1-flash-lite $0.25、embedding-2 $0.2 |
| 白菜价 | 1 | <$0.1 | （2.5-flash-lite $0.1 边界） |

- 定档按 Paid Tier Standard 输入促销价；促销截止日期写入章节 desc
- 视频（Veo）按秒、音乐（Lyria）按首、图像按张计费——用"计费"列写原文，不套档位
- Live/Translate/TTS 音频类按 token 计费且音频价高于文本，直接以输入价定档即可（不像 Qwen 音频按市场失真）

## 数据注意点

- **推理档位**：Gemini 3.x/2.5 全系输出价含思考 token（均可思考）——pro=5 最强、flash=4 深度（3.7）/3 标准（3.5）、lite=2 基础、非思考（TTS/Transcribe 等）=1 快速（编辑性映射，官方无格数）
- **速度档位**：lite=5、flash/live=4-5、pro=3、视频生成=1（编辑性估计）
- **弃用表收录规则**：只收录主表已存在模型（同 OpenAI/Qwen）；已关停的 gemini-2.0-flash、imagen-4.0-generate-001、veo-3.0-generate-001 以「弃用」徽章保留在主表中并同步进弃用表
- **关停日期语义**：官方注明"关停日期为最早可能日期"，以提前通知为准——deprecated 表的日期列照录原文
- **命名特例**：`gemini-embedding-2-preview` 端点仍在用，但 deprecations 中"embedding-2-preview → gemini-embedding-2"指预览期结束转正式，不要误列为关停
- **Gemma**：开源免费，不在 Gemini API 价格体系内（pricing 页 Gemma 章节全部 Not available），价格单元格用 `{"raw": 开源免费}` 而非档位
- **快照/日期后缀**：`-MM-YYYY` 预览快照（如 native-audio-preview-12-2025）保留原样列示；`-latest` 别名不单列
- **PDF 模态**：Google 官方将 PDF 列为独立输入模态（text、image、video、audio、pdf）。Gemini 3 全系、Gemini 2.5 主力模型、Gemini 2.0 及 `gemini-embedding-2-preview` 均支持 PDF 输入；图像生成、`computer-use`、音频专用、机器人、Gemma 等模型不单独标注 PDF
