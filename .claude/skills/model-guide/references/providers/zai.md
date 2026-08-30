# 智谱 Z.ai 官方数据源抓取方法（提供商专用）

> 本文件是 **智谱 Z.ai 模型**（`zai-model-userguide.html` / `data/zai.json`）的数据源方法。
> 通用流水线（模板/渲染/提取/校验）见 SKILL.md；其他提供商见 `references/providers/<厂商>.md`。

核心结论：**docs.bigmodel.cn 可直连静态抓取，open.bigmodel.cn/pricing 是 Vue SPA 需要 Playwright 渲染**；模型概览页决定"有哪些模型"，价格页决定"每个模型多少钱"。

## 目录

- 抓取脚本
- 来源优先级
- 页面机制
- 各页面内容与用途
- 价格口径（CNY，与档位映射）
- 数据注意点
- 已核对修正记录

## 抓取脚本

`scripts/zai/fetch_docs.py` 已沉淀，支持：

```bash
# 抓取模型概览（静态，直接成功）
python scripts/zai/fetch_docs.py overview -o _g_zai/

# 抓取产品价格（Vue SPA，自动使用 Playwright 渲染）
python scripts/zai/fetch_docs.py pricing -o _g_zai/

# 一次抓两个
python scripts/zai/fetch_docs.py overview pricing -o _g_zai/

# 若 Playwright 不可用，可手动在浏览器中保存 pricing.html 后解析
python scripts/zai/fetch_docs.py --local-pricing pricing.html pricing -o _g_zai/
```

输出为 `_g_zai/overview.txt` 与 `_g_zai/pricing.txt`，采用 `ROW:` / `CARD:` 结构化文本，便于后续人工核对或进一步解析。

## 来源优先级

1. `docs.bigmodel.cn/cn/guide/start/model-overview` — 模型总览：当前主推模型清单（最新模型、推荐模型、文本/视觉/图像/视频/音视频/向量等分类），发现新一代模型的入口
2. `open.bigmodel.cn/pricing` — 模型价格：全部模型的 CNY 价格（输入/输出单价、缓存、按次/按分钟等特殊计费），**价格档位的权威来源**
3. 分类文档（能力特性的权威来源）：模型概览页中各模型链接到 `docs.bigmodel.cn/cn/guide/models/...` 下的详情页，可进一步确认上下文、最大输出、模态与特性

## 页面机制

- **模型概览页**：静态 HTML，可直接解析表格与列表
- **价格页**：Vue SPA，初始 HTML 仅加载器，正文由 JS 异步渲染。抓取脚本会先尝试静态请求，失败后自动切换 Playwright 渲染，等待 `table` 选择器出现后提取页面完整 DOM

## 各页面内容与用途

| 页面 | 提供的关键字段 |
|---|---|
| model-overview（总览） | 模型 ID、分类归属、特点、上下文、最大输出、多模态支持 |
| pricing（价格） | 输入/输出单价（¥/1M tokens）、缓存存储/命中、按次/按分钟等特殊计费、免费模型标注、历史模型 |

## 价格口径（CNY，与档位映射）

Z.ai 价格为 **元 CNY / 1M tokens**（华北区原价），映射到页面 6 档阶梯条：

| 档位 | 格数 | 输入价区间（¥） | 示例 |
|---|---|---|---|
| 天价 | 6 | 20+ | Emohaa ¥15（接近） |
| 昂贵 | 5 | 8-20 | GLM-5.3 ¥8，GLM-5.2 ¥8，GLM-5.1(32K+) ¥8 |
| 较贵 | 4 | 2-8 | GLM-5(0-32K) ¥4，GLM-4.7 阶梯 2-4 |
| 适中 | 3 | 0.5-2 | GLM-4-Long ¥1，GLM-4.5-Air ¥0.8，GLM-4.6V(0-32K) ¥1 |
| 实惠 | 2 | 0.1-0.5 | GLM-4.7-FlashX ¥0.5，Embedding-3 ¥0.5，GLM-4.6V-FlashX(0-32K) ¥0.15 |
| 白菜价 | 1 | <0.1 | GLM-4-FlashX-250414 ¥0.1，CodeGeeX-4 ¥0.1，免费模型 |

- 定档按**输入原价**（不含限时折扣；折扣信息写入说明列，如"限时 5 折"）
- 有阶梯价格的模型，按常用或较高档位定档（如 GLM-5.1 按 32K+ 的 ¥8 归入"较贵"）
- 图像/视频生成按**请求次数**计费、语音识别按**tokens/秒**计费、语音合成按**字符**计费、实时音视频按**分钟**计费、实时语音按音频 token 计费——这些模型价格单元格用 `{"raw": 官方原文}` 而不用档位，避免单位不可比导致的误标

## 数据注意点

- **模型 ID 大小写**：Z.ai 官方模型 ID 为大写 `GLM-...`、`CogView-...`、`Embedding-...`、`Vidu...` 等形式，应保持官方写法（品牌标识）；`check_data.py` 已兼容大写字母，不再报形式警告
- **历史模型区**：Z.ai 页面使用 `historical` 区存放已停止推荐但未在主表出现过的旧版模型（如 `GLM-4`、`GLM-4-0520`、`GLM-4V-Plus`），与 OpenAI 页面 `deprecated` 区（模型必须先存在于主表）语义不同
- **推理档位**：max/旗舰 = 5、plus/Turbo = 4、标准版 = 3、Flash/Air = 2、轻量免费 = 1（编辑性映射，官方无格数）
- **速度档位**：FlashX/Flash/AirX = 4-5 快速/极速、Turbo = 4、Air/标准 = 3、旗舰/max = 2-3（编辑性估计）
- **定位**：同代旗舰版（GLM-5.3/5.2/5.1/5）= 旗舰；Flash/Air/平衡版 = 均衡；免费/轻量 = 经济
- **模态**：Z.ai 文档中"文件"输入对应页面 `pdf` 模态（使用 `i-doc` 图标），与 text/image/audio/video 并列
- **免费模型**：价格列可用 `cheap` 档（1 格），说明列标注"免费"；部分免费模型在价格页明确标注"免费"
- **主题色**：Z.ai 使用科技蓝色系 `--accent: #2563eb`，渲染后需手动替换 `:root` 与 `logoGrad` 色值（当前渲染器未注入主题色）
- **按量未公开的模型**：`GLM-4.6` 在模型概览中列为文本模型，但价格页仅出现在私有实例/微调区，无公开按量单价；`data/zai.json` 中价格置 `null` 并在说明中标注
- ** pricing 中比模型概览更细的型号**：`GLM-4.6V-FlashX`、`GLM-4V-Plus-0111`、`ViduQ1-Text/Image/Start-End`、`Vidu2-Image/Start-End/Reference`、`CogVideoX-2`、`GLM-Realtime-Flash/Air` 等仅出现在价格页，已根据价格页补入数据

## 已核对修正记录

| 时间 | 修正内容 | 依据 |
|---|---|---|
| 2026-08-29 | `GLM-4.6` 价格由 mid 改为 `null`，标注按量价格未公开 | pricing 页面无按量计费，仅私有实例 |
| 2026-08-29 | `Embedding-3/2` 价格档由 cheap 改为 low（¥0.5/1M） | pricing 页面单价 0.5 元/百万Tokens |
| 2026-08-29 | `GLM-4.6V` 价格档由 low 改为 mid（最低 ¥1/1M） | pricing 页面 [0,32) 档 1 元/百万Tokens |
| 2026-08-29 | 新增 `GLM-4.6V-FlashX` | pricing 页面有按量价格 |
| 2026-08-29 | `GLM-Image` 价格改为 ¥0.1/次 | pricing 页面 |
| 2026-08-29 | `Vidu Q1` / `Vidu 2` 拆分为具体型号与价格 | pricing 页面 |
| 2026-08-29 | 新增 `CogVideoX-2`（¥0.5/次） | pricing 页面 |
| 2026-08-29 | `GLM-Realtime` 拆分为 `GLM-Realtime-Flash` / `GLM-Realtime-Air` 并补充按分钟价格 | pricing 页面 |
| 2026-08-29 | `GLM-TTS` 价格改为 ¥2/万字符 | pricing 页面 |
| 2026-08-29 | `GLM-ASR-2512` 价格改为输入 ¥16/1M tokens（约 ¥0.0002/秒），输出免费 | pricing 页面 |
| 2026-08-29 | `GLM-OCR` 上下文改为 32K，价格改为 ¥0.2/1M tokens | pricing 页面 |
| 2026-08-29 | 新增 `GLM-4V-Plus-0111` | pricing 页面 |
| 2026-08-30 | 自动同步上下文/最大输出/价格字段 | update_data.py |
| 2026-08-30 | 补录 pricing 页面缺失的 18 个模型；新增 `historical` 区存放 `GLM-4-0520` / `GLM-4V-Plus` / `GLM-4` | pricing 页面旗舰模型/模型推理区 |
| 2026-08-30 | 按定价修正档位：`GLM-5.3-Flash`→mid（原价 ¥0.8）、`GLM-4V-Plus-0111`→high、`GLM-4-Air-250414`/`GLM-Z1-Air`→low、`GLM-Z1-FlashX`→cheap、`Rerank`→mid | pricing 页面单价（输入原价定档） |
| 2026-08-30 | `GLM-4V` / `GLM-4-Air` / `GLM-4-Flash` 移入 `historical`（官方定价页历史模型区）；`GLM-4.5` / `CogView-3` 按量 API 已下架（仅微调/私有化）移入 `historical` | pricing 页面历史模型区/模型推理区 |
| 2026-08-30 | 历史区价格按官方更新：`GLM-4-0520`/`GLM-4`→sky(¥100)、`GLM-4V`→sky(¥50)、`GLM-4V-Plus`→high(¥4)、`GLM-4-Air`→low(¥0.5) | pricing 页面历史模型区单价 |
