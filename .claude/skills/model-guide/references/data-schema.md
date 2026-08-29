# data JSON 结构说明

data/<厂商>.json 是页面的唯一事实源：`render_guide.py` 把它和 `assets/guide.template.html` 合成最终 HTML。手写或手改数据文件前先读本文件。`data/openai.json` 是完整样例。

## 目录

- 顶层结构
- meta（页头/页脚）
- sections（通用字段）
- table 型 section（columns / row_types / rows）
- quick 型 section（快速选型卡片）
- 单元格类型速查（row_types 可用值）
- 特殊机制（逐格类型覆盖、table_class、raw 逃生口、legend）

## 顶层结构

```json
{
  "meta": { ... },
  "legend": "default",
  "sections": [ ... ]
}
```

`legend: "default"` 时渲染器自动生成图例（档位说明与渲染器映射表同步，推荐）；也可省略——渲染器默认就是 default。

## meta（页头/页脚）

```json
"meta": {
  "title": "OpenAI 模型选择指南 2026",          // <title>
  "eyebrow": "OPENAI MODEL SELECTION GUIDE · 2026",
  "h1": "OpenAI 模型选择指南",
  "hero_desc": "70+ 模型全解析 · ...（可含 <a> 链接 HTML）",
  "home_href": "./index.html",                   // 可省，默认 ./index.html
  "home_title": "返回模型价格对比工具",
  "home_label": "对比工具",
  "stats": [
    {"num": "75", "icon": "i-models", "label": "收录模型"},
    {"num": "9", "icon": "i-modes", "label": "模型分类"}
  ],
  "footer_title": "OpenAI 模型选择指南",
  "footer_updated": "2026-08-27",
  "footer_rules": "版本号越大越新 · mini = 省钱 · ...",
  "footer_sources": "数据来源：<a ...>OpenAI 官方文档</a> · ..."
}
```

## sections（通用字段）

每个 section：

```json
{
  "id": "frontier",                    // 锚点 id（导航 #frontier 跳转）
  "title": "Frontier 前沿模型",
  "icon": "i-spark",                   // sec-head 图标
  "nav": "Frontier",                   // 吸顶导航短名（可省，省则不进导航）
  "desc": "OpenAI 最先进的模型…（可含 <span class=\"mono\"> HTML）",
  "kind": "table"                      // table | quick | raw
}
```

`kind: "raw"` 时只需 `"html": "..."`，原样插入（逃生口）。

## table 型 section

```json
{
  "kind": "table",
  "table_class": "rules",              // 可省；rules=命名规律表（首列 accent mono），deprecated=弃用表
  "columns": ["模型 ID", "价格", "定位", "模态", "推理", "速度", "上下文", "输入", "输出", "说明"],
  "row_types": ["model_id", "price", "tier", "mods", "reasoning", "speed", "ctx", "ctx", "ctx", "mdesc"],
  "rows": [
    [
      {"id": "gpt-5.6-sol", "badges": ["NEW"]},
      "high",
      "flagship",
      ["text", "image"],
      5,
      4,
      {"v": "1.05M", "hi": true},
      "922K",
      "128K",
      "GPT-5.6 系列（代号 Sol）…"
    ]
  ]
}
```

`columns` 与 `row_types` 等长；`rows` 每行是与 row_types 对齐的值数组。

## quick 型 section（快速选型）

```json
{
  "id": "quick", "kind": "quick", "title": "快速选型", "icon": "i-bolt",
  "desc": "按任务类型直达推荐模型",
  "cards": [
    {"icon": "i-chat", "task": "日常对话 / 写作", "model": "gpt-chat-latest"}
  ]
}
```

## 单元格类型速查（row_types 可用值）

| 类型 | 值格式 | 渲染结果 |
|---|---|---|
| `model_id` | `"id"` 或 `{"id": "...", "badges": ["NEW","推荐","PRO","预览","开源","弃用","GA"]}` | mono ID + 实心徽章（色板见 page-style.md「徽章」节） |
| `price` | `"sky"/"expensive"/"high"/"mid"/"low"/"cheap"`；特例 `{"raw": "<span class=\"tag t-green\">…自托管</span>"}`；`null` 显示 — | 纯阶梯条 + title 档名（6/5/4/3/2/1 格） |
| `tier` | `"flagship"/"balanced"/"budget"` | 旗舰/均衡/经济 |
| `mods` | `["text","image","audio","video","code","pdf"]` 子集；高亮 `{"items": [...], "cls": "t-teal"}`（输出模态列用） | 纯图标 + title |
| `reasoning` | `5/4/3/2/1` | 脑图标 + 5 点阵 + 最强/深度/标准/基础/快速 |
| `speed` | `5/4/3/2/1` | 闪电 + 极速/快速/标准/较慢/很慢 |
| `ctx` | `"400K"` 或 `{"v": "1.05M", "hi": true}`（hi=高亮） | mono 数值 |
| `num` | `"1200 亿"` | mono 加粗 |
| `mono` | `"gpt-5.2-codex"` | mono-dim 文本 |
| `mono_td` | 文本 | 整格 mono-dim（命名规律示例列） |
| `plain` | 文本/HTML | 普通说明文字（td.plain） |
| `mdesc` | HTML（可内嵌 `<span class="mono-dim">`） | 说明列（td.mdesc，可换行） |
| `flow` | `{"from": "i-mic", "to": "i-text", "label": "语音转文字"}` 或 `{"icon": "i-audio", "label": "实时对话"}` | 图标→图标 流向 |
| `scene` | `{"icon": "i-doc", "text": "超长文档处理", "note": "~100万 token"}`（note 可省） | 能力矩阵场景列 |
| `replacement` | `"o3-mini 或 o4-mini"` | 弃用表 → 替代方案 |
| `lifecycle` | `"deprecated"/"retired"/"legacy"` | 生命周期 tag（红=弃用/退役，琥珀=旧版） |
| `raw` | 任意 HTML | 原样输出（逃生口） |

## 特殊机制

**逐格类型覆盖**：同一列混有两种类型时（如音频表"特性"列，多数行是 plain、realtime 行是 ctx），把该格写成 `{"t": "ctx", "v": "32K/4K"}` 即可逐格指定类型，无需拆表。

**table_class**：`"rules"`（命名规律表，首列 accent mono 样式）与 `"deprecated"`（弃用表，ID 红色、行降不透明度）是当前仅有的两个修饰类，需要新修饰时在模板 CSS 里加并在渲染器/提取器同步。

**raw 逃生口**：任何渲染器不认识的结构（如能力矩阵的"关键能力"列混搭 tag+文本）直接用 `raw` 原样写 HTML。raw 用得越多，模板化收益越少——同一结构出现 3 次以上时，应该给它注册正式的单元格类型。

**legend**：默认由渲染器生成，与 PRICE_TIERS / SPEED_LEVELS / REASONING_NAMES / MODALITIES 映射表自动同步——改档位定义只改渲染器顶部的映射表，图例与全站标签会一起更新。
