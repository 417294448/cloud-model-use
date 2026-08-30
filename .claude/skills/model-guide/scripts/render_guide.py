"""渲染器：data JSON + guide.template.html → 模型指南 HTML。

用法:
    python render_guide.py <data.json> [-t 模板路径] [-o 输出.html]

数据文件结构见 references/data-schema.md（由 extract_guide_data.py 反向提取生成，
手写新厂商数据时照其结构即可）。渲染后自动跑 check_html.py 校验。

设计要点（为什么这样设计）:
    - 模板只有 {{TOKEN}} 占位符，无逻辑；全部分支/循环在渲染器里——零依赖，
      任何 Python 环境都能跑，占位符语义一眼可读。
    - 单元格按"类型注册表"渲染（CELL_RENDERERS），新增单元格类型只加一个函数，
      不动主流程。类型与 references/page-style.md 的映射表一一对应。
    - 客观字段（价格/推理/速度）只接受档位 key，渲染器负责翻译成标签 HTML，
      保证全站同一档位渲染结果逐字节一致。
"""
import json, os, re, sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_TEMPLATE = os.path.join(SKILL_DIR, 'assets', 'guide.template.html')

BRAIN = '<svg class="ic"><use href="#i-brain"/></svg>'
BOLT = '<svg class="ic"><use href="#i-bolt"/></svg>'


def ic(name):
    return f'<svg class="ic"><use href="#{name}"/></svg>'


# ===== 档位映射（与 references/page-style.md 一致，改档位只改这里）=====
#
# 双语支持：档位/推理/速度/模态/徽章标签按语言分表（LABELS[lang]），
# 由渲染时的全局 LANG 选取。CSS class 与档位排序（格数、点数）语言中立，
# 只放中文表一次即可，英文表复用同一 class/格数——见 _tiers()/_reasoning() 等取值函数。
# 默认 lang='zh'，其取值须与历史硬编码逐字节一致（回归验证依赖）。

LANG = 'zh'   # 渲染前由 render(..., lang=) 设置

# CSS class + 格数（语言中立，两种语言共用）
PRICE_CLASS = {
    'sky': ('t-red', 6), 'expensive': ('t-orange', 5), 'high': ('t-amber', 4),
    'mid': ('', 3), 'low': ('t-green', 2), 'cheap': ('t-teal', 1),
}
TIER_CLASS = {'flagship': 't-flag', 'balanced': 't-bal', 'budget': 't-bud'}
SPEED_CLASS = {5: 't-green', 4: 't-teal', 3: '', 2: 't-amber', 1: 't-red'}
MODALITY_ICON = {
    'text': 'i-text', 'image': 'i-image', 'audio': 'i-audio',
    'video': 'i-video', 'code': 'i-code', 'pdf': 'i-doc',
}
BADGE_CLS = {
    'NEW': 'b-new', '推荐': 'b-rec', 'PRO': 'b-pro',
    '预览': 'b-prev', '开源': 'b-oss', '弃用': 'b-dep', 'GA': 'b-rec', '正式版': 'b-rec',
    # 英文数据文件里徽章文案可能用英文写法，映射到同一色板
    'Rec': 'b-rec', 'Preview': 'b-prev', 'OSS': 'b-oss', 'Deprecated': 'b-dep',
}

# 逐语言标签文案
LABELS = {
    'zh': {
        'price': {'sky': '天价', 'expensive': '昂贵', 'high': '较贵',
                  'mid': '适中', 'low': '实惠', 'cheap': '白菜价'},
        'tier': {'flagship': '旗舰', 'balanced': '均衡', 'budget': '经济'},
        'reasoning': {5: '最强', 4: '深度', 3: '标准', 2: '基础', 1: '快速'},
        'speed': {5: '极速', 4: '快速', 3: '标准', 2: '较慢', 1: '很慢'},
        'modality': {'text': '文本', 'image': '图像', 'audio': '音频',
                     'video': '视频', 'code': '代码', 'pdf': 'PDF'},
        'lifecycle': {'deprecated': 'Deprecated', 'retired': 'Retired', 'legacy': 'Legacy'},
        # 图例标题与默认价格单位说明
        'legend_titles': {'tier': '定位', 'speed': '响应速度',
                          'modality': '模态能力', 'reasoning': '推理强度', 'price': '价格档位'},
        'price_note': '单位：USD / 1M tokens（输入 / 输出）',
        'updated_label': '最后更新',
    },
    'en': {
        'price': {'sky': 'Premium', 'expensive': 'Expensive', 'high': 'Costly',
                  'mid': 'Moderate', 'low': 'Affordable', 'cheap': 'Cheapest'},
        'tier': {'flagship': 'Flagship', 'balanced': 'Balanced', 'budget': 'Budget'},
        'reasoning': {5: 'Best', 4: 'Deep', 3: 'Standard', 2: 'Basic', 1: 'Fast'},
        'speed': {5: 'Fastest', 4: 'Fast', 3: 'Standard', 2: 'Slow', 1: 'Slowest'},
        'modality': {'text': 'Text', 'image': 'Image', 'audio': 'Audio',
                     'video': 'Video', 'code': 'Code', 'pdf': 'PDF'},
        'lifecycle': {'deprecated': 'Deprecated', 'retired': 'Retired', 'legacy': 'Legacy'},
        'legend_titles': {'tier': 'Tier', 'speed': 'Speed',
                          'modality': 'Modality', 'reasoning': 'Reasoning', 'price': 'Price'},
        'price_note': 'Unit: USD / 1M tokens (input / output)',
        'updated_label': 'Last updated',
    },
}


def _L(group, key):
    """按当前 LANG 取标签文案，缺失时回退中文（新语言漏翻不至崩溃）"""
    table = LABELS.get(LANG, LABELS['zh'])[group]
    return table.get(key, LABELS['zh'][group].get(key, str(key)))


def tag(cls, inner):
    return f'<span class="tag{(" " + cls) if cls else ""}">{inner}</span>'


def dots(n_on, total=5):
    return '<span class="dots">' + ''.join(
        '<i class="on"></i>' if i < n_on else '<i></i>' for i in range(total)) + '</span>'


def bars(n_on, total=6):
    """价格档位阶梯条：一格一档，高度由 CSS nth-child 决定"""
    return '<span class="bars">' + ''.join(
        '<i class="on"></i>' if i < n_on else '<i></i>' for i in range(total)) + '</span>'


# ===== 单元格渲染器 =====

def cell_model_id(model):
    """{"id": ..., "badges": ["NEW", ...]} 或裸字符串 id"""
    if isinstance(model, str):
        model = {'id': model}
    html = f'<span class="model-id">{model["id"]}</span>'
    for b in model.get('badges', []):
        html += f'<span class="badge {BADGE_CLS.get(b, "b-prev")}">{b}</span>'
    return html


def cell_price(value):
    """档位 key → 纯阶梯条 + title 档名（颜色已独立编码档位，文字为冗余，移入悬停提示）；
    {"raw": html} 特例（如自托管），或 None（暂无定价，显示 —）"""
    if value is None:
        return '<span class="mono-dim">—</span>'
    if isinstance(value, dict):
        return value['raw']
    cls, level = PRICE_CLASS[value]
    name = _L('price', value)
    return (f'<span class="tag{(" " + cls) if cls else ""} price-ico" '
            f'title="{name}">{bars(level)}</span>')


def cell_tier(value):
    """定位列轻标记：圆点 + 着色文字（无底无框），与价格列底色药丸拉开视觉通道"""
    cls = TIER_CLASS[value]
    return f'<span class="tier-tag {cls}">{_L("tier", value)}</span>'


def cell_mods(mods):
    """["text","image"] 或 {"items": [...], "cls": "t-teal"}（输出模态高亮用）"""
    cls = ''
    if isinstance(mods, dict):
        cls, mods = mods.get('cls', ''), mods['items']
    parts = []
    for m in mods:
        icon, label = MODALITY_ICON[m], _L('modality', m)
        parts.append(f'<span class="tag{(" " + cls) if cls else ""} mod-ico" title="{label}">{ic(icon)}</span>')
    return '<div class="mods">' + ''.join(parts) + '</div>'


def cell_reasoning(level):
    name = _L('reasoning', level)
    cls = 't-teal' if level >= 2 else ''
    return tag(cls, BRAIN + dots(level) + name)


def cell_speed(level):
    cls = SPEED_CLASS[level]
    return tag(cls, BOLT + _L('speed', level))


def cell_ctx(value):
    """"400K" 或 {"v": "1.05M", "hi": true}"""
    if isinstance(value, dict):
        return f'<span class="ctx{ " hi" if value.get("hi") else ""}">{value["v"]}</span>'
    return f'<span class="ctx">{value}</span>'


def cell_flow(flow):
    """{"from": "i-mic", "to": "i-text", "label": "语音转文字"} 或 {"icon": "i-audio", "label": "实时对话"}"""
    parts = [ic(flow.get('from') or flow['icon'])]
    if flow.get('to'):
        parts.append('<svg class="ic arr"><use href="#i-arrow-right"/></svg>')
        parts.append(ic(flow['to']))
    parts.append(f'<span class="fl">{flow["label"]}</span>')
    return '<span class="flow">' + ''.join(parts) + '</span>'


def cell_scene(scene):
    """{"icon": "i-doc", "text": "超长文档处理", "note": "~100万 token"(可选)}"""
    html = f'<span class="scene">{ic(scene["icon"])}{scene["text"]}'
    if scene.get('note'):
        html += f'<span class="scene-note">{scene["note"]}</span>'
    return html + '</span>'


CELL_RENDERERS = {
    'model_id': cell_model_id,
    'price': cell_price,
    'tier': cell_tier,
    'mods': cell_mods,
    'reasoning': cell_reasoning,
    'speed': cell_speed,
    'ctx': cell_ctx,
    'flow': cell_flow,
    'scene': cell_scene,
    'num': lambda v: f'<span class="num">{v}</span>',
    'mono': lambda v: f'<span class="mono-dim">{v}</span>',
    'mono_td': lambda v: v,        # 整格 mono-dim（td 带 class，见 TD_CLS）
    'plain': lambda v: v,
    'mdesc': lambda v: v,          # 内容即 HTML（可内嵌 mono-dim 等）
    'replacement': lambda v: f'<span class="arrow-sep">→</span><span class="mono-dim">{v}</span>',
    'lifecycle': lambda v: tag('t-amber' if v == 'legacy' else 't-red', _L('lifecycle', v)),
    'raw': lambda v: v,            # 原样输出（逃生口）
}

# 单元格 → <td> 的 class（默认无）
TD_CLS = {'mdesc': 'mdesc', 'plain': 'plain', 'mono_td': 'mono-dim'}


# ===== 区块渲染 =====

def render_table(sec):
    cols = sec['columns']
    table_cls = f' class="{sec["table_class"]}"' if sec.get('table_class') else ''
    out = ['<div class="table-panel">', f'<table{table_cls}>']
    out.append('<thead>\n<tr>' + ''.join(f'<th>{c}</th>' for c in cols) + '</tr>\n</thead>')
    out.append('<tbody>')
    for row in sec['rows']:
        types = sec['row_types']
        tds = []
        for t, v in zip(types, row):
            # 逐格类型覆盖：{"t": "ctx", "v": "32K/4K"}（用于同列混合类型的场景）
            if isinstance(v, dict) and 't' in v:
                t, v = v['t'], v['v']
            inner = CELL_RENDERERS[t](v)
            cls = TD_CLS.get(t)
            tds.append(f'<td class="{cls}">{inner}</td>' if cls else f'<td>{inner}</td>')
        out.append('<tr>\n' + '\n'.join(tds) + '\n</tr>')
    out.append('</tbody>\n</table>\n</div>')
    return '\n'.join(out)


def render_section(sec):
    kind = sec.get('kind', 'table')
    if kind == 'legend':
        return ('<!-- ===== 图例 ===== -->\n'
                f'<section class="sec" id="{sec["id"]}">\n'
                f'{render_legend(sec["groups"])}\n</section>')
    out = [f'<!-- ===== {sec["title"]} ===== -->',
           f'<section class="sec" id="{sec["id"]}">',
           f'<div class="sec-head">{ic(sec["icon"])}<h2 class="sec-title">{sec["title"]}</h2></div>']
    if sec.get('desc'):
        out.append(f'<p class="sec-desc">{sec["desc"]}</p>')
    if kind == 'table':
        out.append(render_table(sec))
    elif kind == 'quick':
        cards = []
        for c in sec['cards']:
            cards.append(f'<div class="quick-card"><span class="quick-task">{ic(c["icon"])}{c["task"]}</span>'
                         f'<span class="quick-model">{c["model"]}</span></div>')
        out.append('<div class="quick-grid">' + ''.join(cards) + '</div>')
    elif kind == 'raw':
        out.append(sec['html'])
    out.append('</section>')
    return '\n'.join(out)


def render_legend(groups):
    """图例：groups = [{"title": "定位", "wide": false, "items_html": "..."}]"""
    parts = []
    for g in groups:
        wide = ' wide' if g.get('wide') else ''
        parts.append(f'<div class="legend-group{wide}"><div class="legend-title">{g["title"]}</div>'
                     f'<div class="legend-items">{g["items_html"]}</div></div>')
    return '<div class="legend">' + ''.join(parts) + '</div>'


def default_legend(ranges=None, note=None, modalities=None):
    """默认图例（与 page-style.md 的档位定义同步，覆盖大多数页面）。
    ranges/note/modalities 可按提供商覆盖（如 Qwen 用 CNY、Gemini 模态含 PDF）。
    档名/标题按当前 LANG 取；ranges/note 属数据层内容（含货币口径），不翻译，
    需英文口径时经 legend_overrides 覆盖。"""
    def r(n):
        return tag('t-teal' if n >= 2 else '', BRAIN + dots(n) + _L('reasoning', n))
    def s(n):
        return tag(SPEED_CLASS[n], BOLT + _L('speed', n))
    def t(k):
        return f'<span class="tier-tag {TIER_CLASS[k]}">{_L("tier", k)}</span>'
    def m(k):
        return tag('', f'{ic(MODALITY_ICON[k])}{_L("modality", k)}')
    titles = LABELS.get(LANG, LABELS['zh'])['legend_titles']
    if ranges is None:
        ranges = {'sky': '$100+ / $500+', 'expensive': '$10-100 / $50-500', 'high': '$2-10 / $8-50',
                  'mid': '$0.5-2 / $2-8', 'low': '$0.1-0.5 / $0.4-2', 'cheap': '&lt;$0.1 / &lt;$0.4'}
    if note is None:
        note = LABELS.get(LANG, LABELS['zh'])['price_note']
    if modalities is None:
        modalities = ['text', 'image', 'audio', 'video', 'code']
    price_items = []
    for k in ('sky', 'expensive', 'high', 'mid', 'low', 'cheap'):
        cls, lv = PRICE_CLASS[k]
        price_items.append(tag(cls, bars(lv) + _L('price', k) + f'<span class="legend-range">{ranges[k]}</span>'))
    return [
        {'title': titles['tier'], 'items_html': t('flagship') + t('balanced') + t('budget')},
        {'title': titles['speed'], 'items_html': ''.join(s(n) for n in (5, 4, 3, 2, 1))},
        {'title': titles['modality'], 'items_html': ''.join(m(k) for k in modalities)},
        {'title': titles['reasoning'], 'items_html': ''.join(r(n) for n in (5, 4, 3, 2, 1))},
        {'title': titles['price'], 'wide': True,
         'items_html': ''.join(price_items) + f'<span class="legend-note">{note}</span>'},
    ]


def build_lang_switch(meta, lang):
    """页头右上角语言切换器。数据未声明 meta.lang_switch 时返回空串，
    这样未双语化的页面渲染结果与历史逐字节一致（{{LANG_SWITCH}} → ''）。

    meta.lang_switch = {"zh": {"href": "x.html", "label": "中"},
                        "en": {"href": "x-en.html", "label": "EN"}}
    当前语言项高亮（.on），其余为跳转链接；链接末尾的 ?embed=1 由页内脚本补齐，
    保证在 index.html 的 iframe 里切换语言不丢嵌入态。"""
    ls = meta.get('lang_switch')
    if not ls:
        return ''
    order = [k for k in ('zh', 'en') if k in ls] + [k for k in ls if k not in ('zh', 'en')]
    parts = []
    for k in order:
        item = ls[k]
        if k == lang:
            parts.append(f'<span class="lang-opt on" aria-current="true">{item["label"]}</span>')
        else:
            parts.append(f'<a class="lang-opt" href="{item["href"]}" '
                         f'data-lang-href="{item["href"]}">{item["label"]}</a>')
    return '<div class="lang-switch" role="group" aria-label="language">' + ''.join(parts) + '</div>'


def render(data, template_path=DEFAULT_TEMPLATE, lang='zh'):
    global LANG
    LANG = lang if lang in LABELS else 'zh'
    tpl = open(template_path, encoding='utf-8').read()
    meta = data['meta']

    # 数据文件可显式声明 lang；否则用参数。仅用于 <html lang> 与切换器高亮
    page_lang = meta.get('lang', LANG)

    stats = []
    for i, s in enumerate(meta['stats']):
        if i:
            stats.append('<div class="stat-divider"></div>')
        stats.append(f'<div class="stat"><span class="stat-num">{s["num"]}</span>'
                     f'<span class="stat-label">{ic(s["icon"])}<span>{s["label"]}</span></span></div>')

    nav = ''.join(f'<a href="#{s["id"]}">{s["nav"]}</a>' for s in data['sections'] if s.get('nav'))

    # 当前锚点高亮 CSS（:has(:target) 纯 CSS 方案，按数据中的导航项生成）
    nav_ids = [s['id'] for s in data['sections'] if s.get('nav')]
    if nav_ids:
        sels = ',\n  '.join(f'body:has(#{i}:target) .nav a[href="#{i}"]' for i in nav_ids)
        nav_spy_css = f'{sels} {{\n    color: var(--accent-bright);\n    border-bottom-color: var(--accent);\n  }}'
    else:
        nav_spy_css = ''

    sections = []
    if data.get('legend', 'default') == 'default':
        ov = data.get('legend_overrides', {})
        sections.append(render_section({'id': 'legend', 'title': '', 'icon': '',
                                        'kind': 'legend', 'groups': default_legend(**ov)}))
    for sec in data['sections']:
        sections.append(render_section(sec))

    repl = {
        'HTML_LANG': 'zh-CN' if page_lang == 'zh' else 'en',
        'TITLE': meta['title'],
        'EYEBROW': meta['eyebrow'],
        'H1': meta['h1'],
        'HERO_DESC': meta['hero_desc'],
        'HOME_HREF': meta.get('home_href', './index.html'),
        'HOME_TITLE': meta.get('home_title', '返回模型价格对比工具'),
        'HOME_LABEL': meta.get('home_label', '对比工具'),
        'LANG_SWITCH': build_lang_switch(meta, page_lang),
        'STATS': '\n      '.join(stats),
        'NAV': nav,
        'NAV_SPY_CSS': nav_spy_css,
        'SECTIONS': '\n\n'.join(sections),
        'FOOTER_TITLE': meta['footer_title'],
        'FOOTER_UPDATED': meta['footer_updated'],
        'FOOTER_UPDATE_LABEL': LABELS.get(LANG, LABELS['zh'])['updated_label'],
        'FOOTER_RULES': meta['footer_rules'],
        'FOOTER_SOURCES': meta['footer_sources'],
    }
    for k, v in repl.items():
        tpl = tpl.replace('{{' + k + '}}', v)
    leftover = re.findall(r'\{\{[A-Z_]+\}\}', tpl)
    if leftover:
        raise SystemExit(f'模板占位符未填充: {leftover}')
    return tpl


def _render_one(data_path, out_path, template_path, lang):
    """渲染单页并跑结构校验；校验失败退出"""
    data = json.load(open(data_path, encoding='utf-8'))
    html = render(data, template_path, lang=lang)
    open(out_path, 'w', encoding='utf-8').write(html)
    print(f'rendered: {out_path} ({len(html)} bytes, lang={lang})')
    checker = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'check_html.py')
    r = os.system(f'{sys.executable} "{checker}" "{out_path}"')
    if r != 0:
        sys.exit(1)


def main():
    data_path = sys.argv[1]
    out_path = None
    template_path = DEFAULT_TEMPLATE
    lang = 'zh'
    zh_only = '--zh-only' in sys.argv
    args = [a for a in sys.argv[2:] if a != '--zh-only']
    i = 0
    while i < len(args):
        if args[i] == '-o':
            out_path = args[i + 1]; i += 2
        elif args[i] == '-t':
            template_path = args[i + 1]; i += 2
        elif args[i] == '--lang':
            lang = args[i + 1]; i += 2
        else:
            i += 1
    if not out_path:
        out_path = os.path.splitext(os.path.basename(data_path))[0] + '.html'

    _render_one(data_path, out_path, template_path, lang)

    # 双语同步（默认开启）：渲染 zh 数据且同目录存在 <厂商>-en.json 时，自动一并渲染英文页，
    # 保证更新中文数据后英文版不遗漏；只需渲染英文页时用 --lang en 指定 en 数据即可。
    if lang == 'zh' and not zh_only:
        base = os.path.splitext(data_path)[0]
        en_data = base + '-en.json'
        if os.path.exists(en_data):
            en_out = out_path[:-5] + '-en.html' if out_path.endswith('.html') else out_path + '-en.html'
            _render_one(en_data, en_out, template_path, 'en')
            # 中英文语义一致性校验（结构镜像 / 语言中立值 / 模型 ID 集合 / en 无中文残留）
            bilingual = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'check_bilingual.py')
            r = os.system(f'{sys.executable} "{bilingual}" "{data_path}" "{en_data}"')
            if r != 0:
                sys.exit(1)


if __name__ == '__main__':
    main()
