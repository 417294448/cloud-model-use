# 页面设计体系规范（以 index.html 为基准）

本项目的模型指南页统一采用 index.html 的"精密实验室仪器"美学。生成/修改页面前，先读 index.html 的 `<style>` 区确认最新值，本文件是结构化速查。

## 目录

- 设计基调与 CSS 变量
  - 厂商主题色
- 字体与图标系统
- 页面骨架
- Hero 装饰元素
- 核心组件规范
- 数据档位映射表（推理 / 速度 / 价格 / 定位）
- 展示约定（模态图标、点阵、徽章）

## 设计基调与 CSS 变量

白底 + 浅冷灰面板，无渐变大字、无 emoji 徽章、无暗色块。`--accent` 默认使用深青蓝（index.html 基准），但各厂商子页采用独立主题色以增强区分度（见下节「厂商主题色」）。直接复制 index.html 的 `:root` 变量：

```css
--bg: #ffffff;  --bg-soft: #f4f6f8;  --bg-hover: #edf1f4;  --bg-tint: #eef4f6;
--border: #e6eaee;  --border-strong: #d3dae0;
--text: #10151a;  --text-dim: #4d5a64;  --text-faint: #8b98a1;
--accent: #0e7490;  --accent-bright: #0a5c73;  --accent-deep: #083d4d;
--accent-soft: rgba(14,116,144,.09);  --accent-border: rgba(14,116,144,.34);
--best: #0d9463;  --warn: #b4791f;  --orange: #c25e1c;  --danger: #c2493d;
--font-display: 'Sora', 'Noto Sans SC', sans-serif;
--font-mono: 'JetBrains Mono', Consolas, monospace;
--font-sans: 'Manrope', 'Noto Sans SC', 'PingFang SC', sans-serif;
```

### 厂商主题色

为增强厂商区分度，各厂商子页在统一白底基础上使用不同的 accent 色系。生成新厂商页面时，从对应厂商 palette 复制；默认/未知厂商仍使用原始深青蓝。

| 厂商 | 风格 | --accent | --accent-bright | --accent-deep | --bg-tint | --accent-soft / --accent-border / --accent-glow |
|---|---|---|---|---|---|---|
| OpenAI | 冷灰炭黑 | `#374151` | `#1f2937` | `#111827` | `#f3f4f6` | `rgba(31,41,55,0.09/0.34/0.14)` |
| 阿里 Qwen | 紫罗兰 | `#7c3aed` | `#6d28d9` | `#5b21b6` | `#f5f3ff` | `rgba(124,58,237,0.09/0.34/0.14)` |
| Google Gemini | 靛蓝 | `#4f46e5` | `#4338ca` | `#3730a3` | `#eef2ff` | `rgba(79,70,229,0.09/0.34/0.14)` |

同步替换 hero 区 SVG logo 渐变（`#logoGrad`）的深浅端点，使页头 logo 与主题色一致。

标志性细节：`body::before` 顶部 2px 渐变 accent 线；hero 区细网格纹理背景；hero 区右侧 vendor ornament SVG 装饰图（见「Hero 装饰元素」节）；表格行 hover 时首列 `inset 3px 0 0 var(--accent)` 竖条；`::selection` 与滚动条配色；表格行入场 `rowIn` 动画（仅定义 `from`，回到各行自然不透明度，弃用区 0.82 不受影响；`prefers-reduced-motion` 下关闭）。

## 字体与图标系统

- Google Fonts：Sora（标题）、JetBrains Mono（ID/数字）、Manrope（正文）、Noto Sans SC（中文）
- 图标：内联 SVG sprite（`<symbol id="i-*">` + `<use href="#i-*">`），与 index.html 同一套线性图标。常用：`i-text i-image i-audio i-video i-code i-brain i-bolt i-home i-doc i-mic i-speaker i-target i-search i-spark i-ruler i-grid i-share i-monitor i-circle-off i-arrow-right i-models i-modes i-coin i-eye i-brush i-chat`
- **不用 emoji 做信息载体**——所有模态/等级/类型一律 SVG 图标

## 页面骨架

```
<header class="hero">        eyebrow(等宽大写) + h1 + 描述 + 统计条(stat-num mono)
<nav class="nav">            吸顶锚点导航（复用 tabs 样式；JS scroll-spy 写 .active 滚动跟随高亮，
                           无 JS 时 :has(:target) 纯 CSS 规则兜底，由渲染器按导航项自动生成）
<div class="wrap">
  <section id="legend">      图例面板（全部符号的对照表，保留图标+文字）
  <section id="quick">       快速选型 quick-card 栅格
  <section id="naming">      命名规律表（首列 mono accent）
  <section id="...">         各分类表格（.table-panel 圆角面板包裹）
  <section id="deprecated">  弃用表（model-id 红色、行降不透明度）
  <section id="matrix">      能力矩阵（场景 → 推荐/备选/关键能力）
</div>
<footer class="footer">      更新日期 + 速记规则(mono) + 数据来源链接
<script>                   嵌入检测 + scroll-spy（模板内置，无需占位符）
```

**嵌入模式**：URL 带 `?embed=1` 时（index.html 标签页内）隐藏 hero 与 `body::before` 顶线，避免与外层框架重复；单独打开不受影响。index.html 的 iframe src 已带该参数。**检测脚本必须内联在 `<head>` 同步执行**（`</style>` 之后），让 `.embedded` 在 body 解析前就位、hero 从首帧起不渲染——放 body 末尾会导致页头闪现一帧。index.html 自身无页脚，以各子页页脚为准（子页独立更新，信息可不一致）。

## Hero 装饰元素

各厂商子页在 `<header class="hero">` 内添加与主题色同色的 SVG 装饰图（`.hero-ornament`），置于 hero 区右侧，不引入外部图片，增强厂商视觉识别：

| 厂商 | 装饰图形 | 语义 |
|---|---|---|
| OpenAI | 神经网络节点连线 | 工程与推理 |
| 阿里 Qwen | 流动波纹 | 通义与中文韵律 |
| Google Gemini | 放射星形 + 同心圆 | 星辰与多模态辐射 |

CSS 规范：

```css
.hero-ornament {
  position: absolute;
  right: -20px;
  top: 50%;
  width: 340px;
  height: 340px;
  transform: translateY(-50%);
  color: var(--accent);
  opacity: 0.12;
  pointer-events: none;
  z-index: 0;
}
@media (max-width: 900px) {
  .hero-ornament { width: 220px; height: 220px; opacity: 0.08; right: -30px; }
}
```

装饰图透明度控制在 0.08–0.12，避免干扰文字；移动端缩小尺寸。默认/未知厂商可保留一处通用几何纹样，或省略。

## 核心组件规范

| 组件 | 类名 | 说明 |
|---|---|---|
| 药丸标签 | `.tag` + `.t-teal/.t-green/.t-amber/.t-orange/.t-red` | 等级/价格/速度通用载体，统一 22px 等高（表格行高节奏一致） |
| 定位轻标记 | `.tier-tag` + `.t-flag/.t-bal/.t-bud` | 圆点+着色文字，无底无框（见「定位」节） |
| 微型徽章 | `.badge` + `.b-new/.b-rec/.b-pro/.b-prev/.b-oss/.b-dep` | 模型名旁状态标记，统一实心白字（见「徽章」节） |
| 模型 ID | `.model-id` | JetBrains Mono 12.5px accent-bright 600 |
| 上下文数值 | `.ctx` / `.ctx.hi` | mono；超大上下文（≥1M）用 .hi 高亮 |
| 表格 | `.table-panel > table` | 灰底表头、细边框、行 hover accent 竖条 |
| 说明列 | `td.mdesc` | 可换行、12.5px dim，内嵌参数名用 `.mono-dim` |
| 等级点阵 | `.dots > i`（i.on 实心） | 推理等共用色相时的等级区分 |
| 语言切换器 | `.lang-switch` + `.lang-opt`（.on 高亮） | 页头右上角 中/EN 静态互链，胶囊边框；嵌入模式随页头隐藏 |

## 数据档位映射表

### 推理（5 档，与官方 Reasoning 图标格数 1:1）

| 档位 | 点阵 | 官方等级 | tag 类 |
|---|---|---|---|
| 最强 | ●●●●● | Highest（5格） | t-teal |
| 深度 | ●●●●○ | Higher（4格） | t-teal |
| 标准 | ●●●○○ | High（3格） | t-teal |
| 基础 | ●●○○○ | Average（2格） | t-teal |
| 快速 | ●○○○○ | Low（1格）/ 无推理 | 默认灰 |

**关键**：官方详情页标 **Intelligence**（而非 Reasoning）的模型是非推理模型（如 gpt-4.1、gpt-4o 系列），一律归"快速"档、不给推理点，无论其 Intelligence 是几格。

### 速度（5 档）

| 档位 | 官方 Speed | tag 类 |
|---|---|---|
| 极速 | Very fast（5格） | t-green |
| 快速 | Fast（4格） | t-teal |
| 标准 | Medium（3格） | 默认 |
| 较慢 | Slow（2格） | t-amber |
| 很慢 | Slowest（1格） | t-red |

### 价格（6 档，USD / 1M tokens，按输入价定档）

**符号：阶梯信号条**（`.bars`，一格一档、高度递增、实心=档位色、空槽=灰）——与推理点阵区分开，每个维度一种视觉语言。

| 档位 | 阶梯条 | 输入价区间 | tag 类 |
|---|---|---|---|
| 天价 | ▁▂▃▄▅▆（6 格） | $100+ | t-red |
| 昂贵 | ▁▂▃▄▅（5 格） | $10-100 | t-orange |
| 较贵 | ▁▂▃▄（4 格） | $2-10 | t-amber |
| 适中 | ▁▂▃（3 格） | $0.5-2 | 默认 |
| 实惠 | ▁▂（2 格） | $0.1-0.5 | t-green |
| 白菜价 | ▁（1 格） | <$0.1 | t-teal |

输出价通常 4-5 倍于输入价，定档以输入价为准；图例中标注输入/输出双区间。渲染 HTML：`<span class="bars"><i class="on"></i>…</span>`，格数由 `render_guide.py` 的 `PRICE_TIERS` 决定。

（历史版本曾用 `$$$$$`→`¢` 的 $ 数量符号，因"3/4/5 个 $ 需逐个数、¢ 风格突变、与仪表美学不统一"已弃用；提取器仍兼容解析旧符号。）

### 定位（3 档）

旗舰（`t-flag`，warn 琥珀）/ 均衡（`t-bal`，accent-bright 青）/ 经济（`t-bud`，best 绿）。判断依据：同代旗舰版/pro 版 = 旗舰；mini/标准版 = 均衡；nano/轻量版 = 经济。

**展示形式：轻标记**——`<span class="tier-tag t-flag">旗舰</span>`，6px 着色圆点 + 着色文字，**无底无框**。这是刻意的视觉通道分离：定位列若也用底色药丸，会与相邻价格列（底色药丸+阶梯条）同色相撞（如旗舰 t-amber 与较贵 t-amber 相邻无法区分）。改后：价格=面、定位=点、模态=图标、推理=点阵、速度=闪电，五个维度各占一种视觉通道。

**列顺序约定：定位列在价格列前面**（`模型 ID | 定位 | 价格 | …`）——先看模型是什么档次，再看多少钱，符合选型阅读动线。仅对同时含这两列的表（frontier/codex/reasoning/media/legacy）；无定位列的表（audio/oss/embed 等）价格列保持原位。

### 徽章（6 种，统一实心填充白字）

| 徽章 | 类名 | 底色 | 语义 |
|---|---|---|---|
| NEW | `.b-new` | 青蓝 `--accent` | 新发布 |
| 推荐 / GA / 正式版 | `.b-rec` | 绿 `--best` | 官方推荐/已转正 |
| PRO | `.b-pro` | 琥珀 `--warn` | 增强版 |
| 预览 | `.b-prev` | 深灰 `--text-dim` | 预览/试用中 |
| 开源 | `.b-oss` | 深青 `--accent-deep` | 开源模型（与 NEW 青蓝拉开层次） |
| 弃用 | `.b-dep` | 红 `--danger` | 已弃用 |

徽章构成"状态色板"：绿=推荐、青=新、深青=开源、琥珀=PRO、灰=预览、红=弃用，扫一眼即可读出模型状态。

（历史版本为浅色线框 soft 风格，因白底页面存在感弱已改为实心；色值均取自 `:root` 变量，不新造颜色。）

## 展示约定

- **模态列用纯图标**：`<span class="tag mod-ico" title="文本"><svg class="ic"><use href="#i-text"/></svg></span>`——图标 + title 悬停提示，`cursor: help`；图例区保留"图标+文字"对照（它是符号说明书）
- **推理列** = 脑图标 + 5 点点阵 + 档位文字（见上映射）
- **速度列** = 闪电图标 + 档位文字（颜色即档位，无点阵）
- **token 三段式**：上下文 | 输入 | 输出 三列（如 `1.05M | 922K | 128K`），与官方 Context Window / Max Input / Max Output 口径对齐
- **价格列** = 纯阶梯信号条 + title 档名（颜色已独立编码档位——红=天价、橙=昂贵、琥珀=较贵、灰=适中、绿=实惠、青=白菜价，文字为冗余故移入悬停提示；图例区保留"条+名+区间"对照）
- **推理列** = 脑图标 + 5 点点阵 + 档位文字（前四档同为青色，档位只能靠点数区分，文字是唯一免"数点"通道，**不可移除**——与价格列的判定规则一致：颜色能独立编码档位的列，文字才可移除）
- **类型流向**（音频表）= 输入图标 → 输出图标 + 文字（如 mic → text "语音转文字"）
