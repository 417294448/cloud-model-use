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

PRICE_TIERS = {
    'sky':       ('t-red', 6, '天价'),
    'expensive': ('t-orange', 5, '昂贵'),
    'high':      ('t-amber', 4, '较贵'),
    'mid':       ('', 3, '适中'),
    'low':       ('t-green', 2, '实惠'),
    'cheap':     ('t-teal', 1, '白菜价'),
}

TIER_LEVELS = {
    'flagship': ('t-flag', '旗舰'),
    'balanced': ('t-bal', '均衡'),
    'budget':   ('t-bud', '经济'),
}

REASONING_NAMES = {5: '最强', 4: '深度', 3: '标准', 2: '基础', 1: '快速'}
SPEED_LEVELS = {
    5: ('t-green', '极速'),
    4: ('t-teal', '快速'),
    3: ('', '标准'),
    2: ('t-amber', '较慢'),
    1: ('t-red', '很慢'),
}

MODALITIES = {
    'text': ('i-text', '文本'),
    'image': ('i-image', '图像'),
    'audio': ('i-audio', '音频'),
    'video': ('i-video', '视频'),
    'code': ('i-code', '代码'),
    'pdf': ('i-doc', 'PDF'),
}

BADGE_CLS = {
    'NEW': 'b-new', '推荐': 'b-rec', 'PRO': 'b-pro',
    '预览': 'b-prev', '开源': 'b-oss', '弃用': 'b-dep', 'GA': 'b-rec', '正式版': 'b-rec',
}

# 生命周期（退役计划表）：deprecated=已宣布弃用、retired=已退役、legacy=旧版计划退役
LIFECYCLE = {
    'deprecated': ('t-red', 'Deprecated'),
    'retired': ('t-red', 'Retired'),
    'legacy': ('t-amber', 'Legacy'),
}


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
    cls, level, name = PRICE_TIERS[value]
    return (f'<span class="tag{(" " + cls) if cls else ""} price-ico" '
            f'title="{name}">{bars(level)}</span>')


def cell_tier(value):
    """定位列轻标记：圆点 + 着色文字（无底无框），与价格列底色药丸拉开视觉通道"""
    cls, name = TIER_LEVELS[value]
    return f'<span class="tier-tag {cls}">{name}</span>'


def cell_mods(mods):
    """["text","image"] 或 {"items": [...], "cls": "t-teal"}（输出模态高亮用）"""
    cls = ''
    if isinstance(mods, dict):
        cls, mods = mods.get('cls', ''), mods['items']
    parts = []
    for m in mods:
        icon, label = MODALITIES[m]
        parts.append(f'<span class="tag{(" " + cls) if cls else ""} mod-ico" title="{label}">{ic(icon)}</span>')
    return '<div class="mods">' + ''.join(parts) + '</div>'


def cell_reasoning(level):
    name = REASONING_NAMES[level]
    cls = 't-teal' if level >= 2 else ''
    return tag(cls, BRAIN + dots(level) + name)


def cell_speed(level):
    cls, name = SPEED_LEVELS[level]
    return tag(cls, BOLT + name)


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
    'lifecycle': lambda v: tag(*LIFECYCLE[v]),
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
    ranges/note/modalities 可按提供商覆盖（如 Qwen 用 CNY、Gemini 模态含 PDF）。"""
    def r(n):
        return tag('t-teal' if n >= 2 else '', BRAIN + dots(n) + REASONING_NAMES[n])
    def s(n):
        cls, name = SPEED_LEVELS[n]
        return tag(cls, BOLT + name)
    def t(k):
        cls, name = TIER_LEVELS[k]
        return f'<span class="tier-tag {cls}">{name}</span>'
    def m(k):
        icon, label = MODALITIES[k]
        return tag('', f'{ic(icon)}{label}')
    if ranges is None:
        ranges = {'sky': '$100+ / $500+', 'expensive': '$10-100 / $50-500', 'high': '$2-10 / $8-50',
                  'mid': '$0.5-2 / $2-8', 'low': '$0.1-0.5 / $0.4-2', 'cheap': '&lt;$0.1 / &lt;$0.4'}
    if note is None:
        note = '单位：USD / 1M tokens（输入 / 输出）'
    if modalities is None:
        modalities = ['text', 'image', 'audio', 'video', 'code']
    price_items = []
    for k in ('sky', 'expensive', 'high', 'mid', 'low', 'cheap'):
        cls, lv, name = PRICE_TIERS[k]
        price_items.append(tag(cls, bars(lv) + name + f'<span class="legend-range">{ranges[k]}</span>'))
    return [
        {'title': '定位', 'items_html': t('flagship') + t('balanced') + t('budget')},
        {'title': '响应速度', 'items_html': ''.join(s(n) for n in (5, 4, 3, 2, 1))},
        {'title': '模态能力', 'items_html': ''.join(m(k) for k in modalities)},
        {'title': '推理强度', 'items_html': ''.join(r(n) for n in (5, 4, 3, 2, 1))},
        {'title': '价格档位', 'wide': True,
         'items_html': ''.join(price_items) + f'<span class="legend-note">{note}</span>'},
    ]


def render(data, template_path=DEFAULT_TEMPLATE):
    tpl = open(template_path, encoding='utf-8').read()
    meta = data['meta']

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
        'TITLE': meta['title'],
        'EYEBROW': meta['eyebrow'],
        'H1': meta['h1'],
        'HERO_DESC': meta['hero_desc'],
        'HOME_HREF': meta.get('home_href', './index.html'),
        'HOME_TITLE': meta.get('home_title', '返回模型价格对比工具'),
        'HOME_LABEL': meta.get('home_label', '对比工具'),
        'STATS': '\n      '.join(stats),
        'NAV': nav,
        'NAV_SPY_CSS': nav_spy_css,
        'SECTIONS': '\n\n'.join(sections),
        'FOOTER_TITLE': meta['footer_title'],
        'FOOTER_UPDATED': meta['footer_updated'],
        'FOOTER_RULES': meta['footer_rules'],
        'FOOTER_SOURCES': meta['footer_sources'],
    }
    for k, v in repl.items():
        tpl = tpl.replace('{{' + k + '}}', v)
    leftover = re.findall(r'\{\{[A-Z_]+\}\}', tpl)
    if leftover:
        raise SystemExit(f'模板占位符未填充: {leftover}')
    return tpl


def main():
    data_path = sys.argv[1]
    out_path = None
    template_path = DEFAULT_TEMPLATE
    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == '-o':
            out_path = args[i + 1]; i += 2
        elif args[i] == '-t':
            template_path = args[i + 1]; i += 2
        else:
            i += 1
    if not out_path:
        out_path = os.path.splitext(os.path.basename(data_path))[0] + '.html'

    data = json.load(open(data_path, encoding='utf-8'))
    html = render(data, template_path)
    open(out_path, 'w', encoding='utf-8').write(html)
    print(f'rendered: {out_path} ({len(html)} bytes)')

    checker = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'check_html.py')
    r = os.system(f'{sys.executable} "{checker}" "{out_path}"')
    if r != 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
