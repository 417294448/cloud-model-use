# -*- coding: utf-8 -*-
"""data/anthropic.json → data/anthropic-en.json（英文版）。

翻译策略：语言中立字段（模型 ID、数字、档位 key、模态 key、ctx 数值、URL）
原样保留；编辑字段按 TRANSLATE 精确匹配翻译；漏翻的中文会告警。
生成的是新文件 data/anthropic-en.json，不改动中文数据源。
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(os.path.dirname(HERE))  # .claude/skills/model-guide
SRC = os.path.join(SKILL_DIR, 'data', 'anthropic.json')
DST = os.path.join(SKILL_DIR, 'data', 'anthropic-en.json')

CJK = re.compile(r'[一-鿿]')

# ===== 翻译表（完整枚举 anthropic.json 中的可译编辑字段）=====
TRANSLATE = {
    # ---- meta ----
    'Anthropic Claude 模型选择指南 2026': 'Anthropic Claude Model Selection Guide 2026',
    'Anthropic Claude 模型选择指南': 'Anthropic Claude Model Selection Guide',
    'Claude Opus / Sonnet / Haiku 全系 · Fable 5.1 超旗舰 · Opus 5 新旗舰 · 1M 上下文 · 中英双语 — 数据来源：Anthropic Claude Platform 官方文档 <a href="https://platform.claude.com/docs/en/about-claude/pricing" target="_blank" rel="noopener noreferrer">价格</a> · <a href="https://platform.claude.com/docs/en/about-claude/model-deprecations" target="_blank" rel="noopener noreferrer">模型弃用</a> · <a href="https://platform.claude.com/docs/en/about-claude/models/overview" target="_blank" rel="noopener noreferrer">模型总览</a>（2026-09-08 同步）':
        'Claude Opus / Sonnet / Haiku family · Fable 5.1 super-flagship · Opus 5 new flagship · 1M context · bilingual — Sources: Anthropic Claude Platform official docs <a href="https://platform.claude.com/docs/en/about-claude/pricing" target="_blank" rel="noopener noreferrer">Pricing</a> · <a href="https://platform.claude.com/docs/en/about-claude/model-deprecations" target="_blank" rel="noopener noreferrer">Model deprecations</a> · <a href="https://platform.claude.com/docs/en/about-claude/models/overview" target="_blank" rel="noopener noreferrer">Models overview</a> (synced 2026-09-08)',
    '数据来源：Anthropic Claude Platform 官方文档 <a href="https://platform.claude.com/docs/en/about-claude/pricing" target="_blank" rel="noopener noreferrer">价格</a> · <a href="https://platform.claude.com/docs/en/about-claude/model-deprecations" target="_blank" rel="noopener noreferrer">模型弃用</a> · <a href="https://platform.claude.com/docs/en/about-claude/models/overview" target="_blank" rel="noopener noreferrer">模型总览</a>（2026-09-08 同步）':
        'Sources: Anthropic Claude Platform official docs <a href="https://platform.claude.com/docs/en/about-claude/pricing" target="_blank" rel="noopener noreferrer">Pricing</a> · <a href="https://platform.claude.com/docs/en/about-claude/model-deprecations" target="_blank" rel="noopener noreferrer">Model deprecations</a> · <a href="https://platform.claude.com/docs/en/about-claude/models/overview" target="_blank" rel="noopener noreferrer">Models overview</a> (synced 2026-09-08)',
    'opus = 旗舰最强 · sonnet = 均衡性价比 · haiku = 快速经济 · fable = 超旗舰 · 版本号越大越新 · Batch 半价 · 缓存输入约 1 折':
        'opus = flagship & strongest · sonnet = balanced value · haiku = fast & budget · fable = super-flagship · higher version = newer · Batch at half price · cached input ~1/10',
    '收录模型': 'Models',
    '模型系列': 'Series',
    '最大上下文': 'Max context',

    # ---- 通用 section 字段 ----
    '快速选型': 'Quick Picks',
    '按任务类型直达推荐模型（价格均为 USD / 1M tokens，输入/输出）':
        'Direct recommendation by task type (prices in USD / 1M tokens, input/output)',
    '命名规律速查': 'Naming Conventions',
    '命名规律': 'Naming',
    '掌握这些规律，看到任何 Claude 模型名都能秒懂其定位':
        'Understand these patterns and instantly grasp any Claude model name',
    'Claude 现役模型（Fable / Opus / Sonnet / Haiku）': 'Claude Current Models (Fable / Opus / Sonnet / Haiku)',
    '现役模型': 'Current models',
    '当前 API 在售模型全谱：Fable 5.1 为 2026 超旗舰（Opus 5 评测不足时的终局选择），Opus 5 为现役旗舰，Sonnet 为均衡性价比，Haiku 为快速经济。均支持文本/图像输入与 PDF/长文档；输出价约输入价 5 倍；Batch 半价，缓存输入约 1 折。价格为 USD / 1M tokens':
        'Full spectrum of models currently on the API: Fable 5.1 is the 2026 super-flagship (the endgame pick when Opus 5 evals fall short), Opus 5 the current flagship, Sonnet balanced value, Haiku fast & budget. All support text/image input plus PDF/long documents; output costs ~5x input; Batch at half price, cached input ~1/10. Prices in USD / 1M tokens',
    '已退役模型与迁移指引': 'Retired Models & Migration Guide',
    '已退役': 'Retired',
    '以下 Claude API 模型均已退役（退役后请求返回 404，无宽限期），请按官方推荐迁移。数据来源：Anthropic 官方模型弃用页（2026-09-08 同步）':
        'All of these Claude API models are retired (requests return 404, no grace period); migrate per official recommendation. Source: Anthropic official model deprecations page (synced 2026-09-08)',
    '能力矩阵速查': 'Capability Matrix',
    '能力矩阵': 'Capability Matrix',
    '根据需求快速匹配最佳模型': 'Match the best model to your needs quickly',

    # ---- 通用列头 ----
    '命名元素': 'Element', '含义': 'Meaning', '示例': 'Example',
    '模型 ID': 'Model ID', '定位': 'Tier', '价格': 'Price',
    '推理': 'Reasoning', '速度': 'Speed', '上下文': 'Context', '输入': 'Input',
    '输出': 'Output', '说明': 'Notes',
    '生命周期': 'Lifecycle', '退役日期': 'Retirement date', '替代方案': 'Replacement',
    '迁移建议': 'Migration advice',
    '需求场景': 'Scenario', '推荐模型': 'Recommended', '备选模型': 'Alternatives',
    '关键能力': 'Key capability',

    # ---- quick 卡片任务 ----
    '日常对话 / 写作': 'Chat / Writing',
    '最难推理 / 复杂数学': 'Hardest reasoning / Complex math',
    '极限长程自主任务': 'Extreme long-horizon autonomous tasks',
    '专业编程 / Agentic': 'Coding / Agentic',
    '复杂 Agent / 工具调用': 'Complex agents / Tool use',
    '超长文档理解': 'Long-document understanding',
    '图像 / PDF 理解': 'Image / PDF understanding',
    '高吞吐批量 / 省钱': 'High-throughput batch / cost saving',
    '分类 / 抽取 / 摘要': 'Classification / Extraction / Summarization',
    '低延迟实时助手': 'Low-latency realtime assistant',
    '长输出 / 内容生成': 'Long output / Content generation',
    '批量离线任务': 'Batch offline jobs',

    # ---- naming 命名规律 ----
    '三大系列名：旗舰最强 / 均衡性价比 / 快速经济':
        'Three series: flagship strongest / balanced value / fast & budget',
    'claude- 前缀': 'claude- prefix',
    'Claude API 模型统一前缀': 'Unified prefix for Claude API models',
    '2026 超旗舰代号，强于 Opus，定价更高':
        '2026 super-flagship codename, stronger than Opus, priced higher',
    '与 Fable 5 同能力同价，仅 Glasswing 邀请制组织可调用':
        'Same capability & price as Fable 5; accessible only to invite-only Project Glasswing organizations',
    '版本号演进': 'Version progression',
    '3 → 4 → 4.1 → 4.5 → 4.6 → 4.7 → 4.8 → 5，越大越新':
        '3 → 4 → 4.1 → 4.5 → 4.6 → 4.7 → 4.8 → 5; higher = newer',
    '-YYYYMMDD 快照': '-YYYYMMDD snapshot',
    '老式命名以发版日作版本（新代推荐用无日期 alias）':
        'Legacy naming uses release date as version (use the dateless alias for new models)',
    '无日期 alias': 'Dateless alias',
    '新一代推荐写法，自动指向最新快照':
        'Recommended for new models; auto-points to the latest snapshot',
    'claude-opus-4-8（勿手动追加日期后缀）': 'claude-opus-4-8 (do not append a date suffix manually)',
    '4.5+ 思考机制': '4.5+ thinking',
    '自适应思考 + effort；Fable 深度思考常开':
        'Adaptive thinking + effort; Fable deep thinking always on',
    '2026 超旗舰代号，强于 Opus，定价更高；5.1 为最新一代（2026-09-01）':
        '2026 super-flagship codename, stronger than Opus, priced higher; 5.1 is the newest generation (2026-09-01)',
    '与 Fable 同能力同价，仅 Project Glasswing 邀请制组织可调用（防御性安全用例）':
        'Same capability & price as Fable; accessible only to invite-only Project Glasswing organizations (defensive security use cases)',
    'Opus / Sonnet：4.5 → 4.6 → 4.7 → 4.8 → 5；Fable：5 → 5.1，越大越新':
        'Opus / Sonnet: 4.5 → 4.6 → 4.7 → 4.8 → 5; Fable: 5 → 5.1; higher = newer',

    # ---- current mdesc ----
    'Claude 超旗舰 Fable 5.1（2026-09-01 发布）：最难深度推理 / 长程自主 Agentic 的终局选择；深度思考常开 + effort（默认 high）；缓存读低至 $0.25/MTok；$10/$50':
        'Claude super-flagship Fable 5.1 (released 2026-09-01): the endgame pick for hardest deep reasoning / long-horizon autonomous Agentic; deep thinking always on + effort (default high); cache reads as low as $0.25/MTok; $10/$50',
    '上代超旗舰 Fable 5（2026-06-09 发布，Legacy）：仍可用；能力/价格被 5.1 平替，新项目迁移至 Fable 5.1；$10/$50':
        'Previous super-flagship Fable 5 (released 2026-06-09, Legacy): still available; superseded by 5.1 at the same price, migrate new projects to Fable 5.1; $10/$50',
    'Opus 5（2026-07-24 发布）：对 4.8 代差级升级——深度推理 / 长程 Agentic / 测试时扩展最强 Opus；自适应思考默认开（effort high 及以下可关）+ 可选 Fast 模式；$5/$25':
        'Opus 5 (released 2026-07-24): a generational leap over 4.8 — the strongest Opus for deep reasoning / long-horizon Agentic / test-time compute scaling; adaptive thinking on by default (can disable at effort high or below) + optional Fast mode; $5/$25',
    '上代 Opus 旗舰（2026-05-28 发布）：长程自主 Agentic / 知识工作 / 记忆最强 Opus，仍可生产并支持 Fast 模式；新项目建议升级 Opus 5；$5/$25':
        'Previous Opus flagship (released 2026-05-28): strongest Opus for long-horizon autonomous Agentic / knowledge work / memory; still production-ready and supports Fast mode; upgrade to Opus 5 for new projects; $5/$25',
    '上代 Opus，与 4.8 同请求面；仍可生产，新项目建议升级 Opus 5；$5/$25':
        'Previous-generation Opus, same request surface as 4.8; production-ready, upgrade to Opus 5 for new projects; $5/$25',
    '4.6 系 Opus，仍可用；自适应思考；$5/$25':
        'Opus of the 4.6 line, still available; adaptive thinking; $5/$25',
    '2025 末 Opus，仍可用；200K 上下文（1M 需 beta）；思考预算制过渡；$5/$25':
        'Late-2025 Opus, still available; 200K context (1M via beta); thinking-budget transitional; $5/$25',
    'Sonnet 新代：编码与 Agentic 逼近 Opus、价格更低；自适应思考默认开 + effort（默认 high）；$2/$10（intro 价转正——原定 2026-09-01 涨至 $3/$15 已取消）':
        'New Sonnet: coding & Agentic near Opus at a lower price; adaptive thinking on by default + effort (default high); $2/$10 (intro price made permanent — the scheduled 2026-09-01 increase to $3/$15 was cancelled)',
    '上代 Sonnet，仍可用；1M 上下文；$3/$15':
        'Previous Sonnet, still available; 1M context; $3/$15',
    '旧代均衡模型，仍可用（200K 上下文）；新项目选 Sonnet 5；$3/$15':
        'Older balanced model, still available (200K context); choose Sonnet 5 for new projects; $3/$15',
    '最快最省：高频分类/抽取/摘要/客服；输出上限 64K；$1/$5':
        'Fastest & cheapest: high-frequency classification/extraction/summarization/customer service; 64K output cap; $1/$5',

    # ---- deprecated 迁移建议 ----
    '已退役，直接迁移': 'Retired; migrate directly',

    # ---- matrix 场景 / raw ----
    '复杂推理 / 数学': 'Complex reasoning / Math',
    '高吞吐低成本': 'High-throughput, low cost',
    '~100万 token': '~1M tokens',
    '<span class="plain">$2/$10 · 均衡性价比</span>':
        '<span class="plain">$2/$10 · balanced value</span>',
    '<span class="tag t-teal"><svg class="ic"><use href="#i-brain"/></svg><span class="dots"><i class="on"></i><i class="on"></i><i class="on"></i><i class="on"></i><i class="on"></i></span>最强</span>':
        '<span class="tag t-teal"><svg class="ic"><use href="#i-brain"/></svg><span class="dots"><i class="on"></i><i class="on"></i><i class="on"></i><i class="on"></i><i class="on"></i></span>Top</span>',
    '<span class="mono-dim">Sonnet 逼近 Opus · 高性价比</span>':
        '<span class="mono-dim">Sonnet near Opus · great value</span>',
    '<span class="mono-dim">thinking 常开 · effort 默认 high</span>':
        '<span class="mono-dim">thinking always on · effort default high</span>',
    '<span class="ctx hi">1M 上下文</span>': '<span class="ctx hi">1M context</span>',
    '<div class="mods"><span class="tag mod-ico" title="图像"><svg class="ic"><use href="#i-image"/></svg></span><span class="tag mod-ico" title="PDF"><svg class="ic"><use href="#i-doc"/></svg></span></div> 全系支持':
        '<div class="mods"><span class="tag mod-ico" title="Image"><svg class="ic"><use href="#i-image"/></svg></span><span class="tag mod-ico" title="PDF"><svg class="ic"><use href="#i-doc"/></svg></span></div> all models',
    '<span class="plain">$1/$5 · 最快</span>': '<span class="plain">$1/$5 · fastest</span>',
    '<span class="mono-dim">Haiku 快速响应</span>': '<span class="mono-dim">Haiku fast response</span>',
    '<span class="mono-dim">Batch API 半价</span>': '<span class="mono-dim">Batch API at half price</span>',

    # ---- 徽章 ----
    '推荐': 'Rec',
}

MISSING = []


def tr(s):
    """递归翻译 str；dict/list 深入内部，避免漏翻嵌套结构。"""
    if isinstance(s, str):
        if s in TRANSLATE:
            return TRANSLATE[s]
        if CJK.search(s):
            MISSING.append(s)
        return s
    if isinstance(s, dict):
        return {k: tr(v) for k, v in s.items()}
    if isinstance(s, list):
        return [tr(x) for x in s]
    return s


def tr_cell(t, v):
    """按单元格类型翻译；dict 覆盖格取其 'v' 字段"""
    if isinstance(v, dict) and 't' in v:
        v = dict(v)
        v['v'] = tr(v['v'])
        return v
    if t == 'model_id':
        if isinstance(v, dict):
            v = dict(v)
            v['badges'] = [tr(b) for b in v.get('badges', [])]
        return v
    if t == 'scene':
        v = dict(v)
        v['text'] = tr(v['text'])
        if 'note' in v:
            v['note'] = tr(v['note'])
        return v
    return tr(v)


def main():
    data = json.load(open(SRC, encoding='utf-8'))
    meta = data['meta']
    meta['lang'] = 'en'
    meta['lang_switch'] = {
        'zh': {'href': 'anthropic-model-userguide.html', 'label': '中'},
        'en': {'href': 'anthropic-model-userguide-en.html', 'label': 'EN'},
    }
    for k in ('title', 'eyebrow', 'h1', 'hero_desc',
              'footer_title', 'footer_rules', 'footer_sources'):
        meta[k] = tr(meta[k])
    for s in meta['stats']:
        s['label'] = tr(s['label'])

    if isinstance(data.get('legend_overrides'), dict):
        ov = data['legend_overrides']
        if isinstance(ov.get('note'), str):
            ov['note'] = tr(ov['note'])

    for sec in data['sections']:
        for k in ('title', 'desc', 'nav'):
            if k in sec:
                sec[k] = tr(sec[k])
        if sec.get('kind') == 'quick':
            for c in sec['cards']:
                c['task'] = tr(c['task'])
        elif sec.get('kind') == 'table':
            sec['columns'] = [tr(c) for c in sec['columns']]
            rts = sec['row_types']
            for row in sec['rows']:
                for i, (t, v) in enumerate(zip(rts, row)):
                    row[i] = tr_cell(t, v)

    json.dump(data, open(DST, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)
    print(f'wrote {DST}')
    if MISSING:
        print(f'!! 以下 {len(MISSING)} 条中文未翻译（请补充 TRANSLATE）:')
        for m in sorted(set(MISSING)):
            print('  -', m)
        sys.exit(1)
    print('全部中文已翻译')


if __name__ == '__main__':
    main()
