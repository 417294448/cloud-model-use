"""反向提取器：把现有模型指南 HTML 页面解析回 data JSON。

用法:
    python extract_guide_data.py <页面.html> [-o data.json]

用途:
    1. 为已有页面建立"数据唯一事实源"（之后改数据文件 + 渲染，不再手改 HTML）
    2. 回归验证：render_guide.py 渲染提取结果，应与原页面语义一致

解析策略：按 class 特征识别单元格类型（model-id / ps / dots / ctx / flow / scene 等），
逐 section 提取 columns / row_types / rows；meta/nav/footer 从骨架提取。
legend 节不提取（渲染器按 default_legend() 重新生成，保证档位说明与映射表同步）。
"""
import json, re, sys
from html.parser import HTMLParser

ICON_RE = re.compile(r'<use href="#(i-[a-z-]+)"')


def strip_tags(html):
    return re.sub(r'<[^>]+>', '', html).strip()


class SectionParser(HTMLParser):
    """把 HTML 切成 token 流，按 section 边界与表格结构提取。"""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tokens = []

    def handle_starttag(self, tag, attrs):
        self.tokens.append(('start', tag, dict(attrs), self.getpos()))

    def handle_startendtag(self, tag, attrs):
        self.tokens.append(('startend', tag, dict(attrs), self.getpos()))

    def handle_endtag(self, tag):
        self.tokens.append(('end', tag, None, self.getpos()))

    def handle_data(self, data):
        if data.strip():
            self.tokens.append(('data', data, None, self.getpos()))


# ---------- 单元格类型识别（与 render_guide.CELL_RENDERERS 互逆） ----------

PRICE_BY_BARS = {6: 'sky', 5: 'expensive', 4: 'high', 3: 'mid', 2: 'low', 1: 'cheap'}
TIER_BY_TEXT = {'旗舰': 'flagship', '均衡': 'balanced', '经济': 'budget'}
SPEED_BY_TEXT = {'极速': 5, '快速': 4, '标准': 3, '较慢': 2, '很慢': 1}
REASONING_BY_TEXT = {'最强': 5, '深度': 4, '标准': 3, '基础': 2, '快速': 1}
MOD_BY_TITLE = {'文本': 'text', '图像': 'image', '音频': 'audio', '视频': 'video', '代码': 'code'}
LIFECYCLE_BY_TEXT = {'Deprecated': 'deprecated', 'Retired': 'retired', 'Legacy': 'legacy'}


def parse_cell(html):
    """输入 td 的内层 HTML，输出 (row_type, value)"""
    # model-id
    m = re.search(r'<span class="model-id">([^<]+)</span>', html)
    if m:
        badges = re.findall(r'<span class="badge [^"]*">([^<]+)</span>', html)
        return 'model_id', {'id': m.group(1), 'badges': badges}
    # price 档位（阶梯条：数实心格数）
    if 'class="bars"' in html:
        ons = len(re.findall(r'<i class="on">', html))
        return 'price', PRICE_BY_BARS.get(ons, {'raw': html.strip()})
    # 兼容旧版 $ 符号药丸（历史页面）
    m = re.search(r'<span class="tag( (t-[a-z]+))?"><span class="ps">([^<]*)</span>([^<]*)</span>', html)
    if m:
        legacy = {'$$$$$': 'sky', '$$$$': 'expensive', '$$$': 'high', '$$': 'mid', '$': 'low', '¢': 'cheap'}
        sym = m.group(3)
        if sym in legacy:
            return 'price', legacy[sym]
        return 'price', {'raw': html.strip()}
    if '自托管' in html:
        return 'price', {'raw': html.strip()}
    if html.strip() in ('<span class="mono-dim">—</span>', '—'):
        return 'price', None
    # 定位 tier（新版 tier-tag 轻标记 / 旧版 tag 药丸，无图标无点阵）
    m = re.fullmatch(r'<span class="(?:tag|tier-tag)(?: (t-[a-z]+))?">(旗舰|均衡|经济)</span>', html.strip())
    if m:
        return 'tier', TIER_BY_TEXT[m.group(2)]
    # 生命周期 tag（退役计划表）
    m = re.fullmatch(r'<span class="tag (t-[a-z]+)">(Deprecated|Retired|Legacy)</span>', html.strip())
    if m:
        return 'lifecycle', LIFECYCLE_BY_TEXT[m.group(2)]
    # scene（须先于 reasoning/speed 判断——scene 内也含 i-brain/i-bolt 图标）
    if 'class="scene"' in html:
        icon = ICON_RE.search(html)
        note = re.search(r'<span class="scene-note">([^<]*)</span>', html)
        text = strip_tags(re.sub(r'<span class="scene-note">[^<]*</span>', '', html))
        sc = {'icon': icon.group(1) if icon else 'i-doc', 'text': text}
        if note and note.group(1):
            sc['note'] = note.group(1)
        return 'scene', sc
    # reasoning（整格须为纯推理 tag；含 plain/文字后缀等混合内容时归 raw）
    if 'i-brain' in html:
        residual = re.sub(r'<span class="tag[^"]*"><svg class="ic"><use href="#i-brain"/></svg>(?:<span class="dots">.*?</span>)?[^<]*</span>', '', html, flags=re.S).strip()
        if residual:
            return 'raw', html.strip()
        ons = len(re.findall(r'<i class="on">', html))
        return 'reasoning', max(ons, 1)
    # speed（同理，整格须为纯速度 tag）
    if 'i-bolt' in html:
        residual = re.sub(r'<span class="tag[^"]*"><svg class="ic"><use href="#i-bolt"/></svg>[^<]*</span>', '', html, flags=re.S).strip()
        if residual:
            return 'raw', html.strip()
        text = strip_tags(html)
        for name, lv in SPEED_BY_TEXT.items():
            if name in text:
                return 'speed', lv
    # mod-ico 组（只有单元格完全由 mod-ico 标签组成时才算 mods；混入其他内容则归 raw）
    if 'mod-ico' in html:
        residual = re.sub(r'<span class="tag[^"]* mod-ico"[^>]*><svg class="ic"><use href="#i-[a-z-]+"/></svg></span>', '', html)
        residual = re.sub(r'<div class="mods">|</div>', '', residual).strip()
        if not residual:
            titles = re.findall(r'mod-ico" title="([^"]+)"', html)
            items = [MOD_BY_TITLE[t] for t in titles]
            # 输出模态列的高亮变体（tag t-teal mod-ico）
            if re.search(r'class="tag t-teal mod-ico"', html):
                return 'mods', {'items': items, 'cls': 't-teal'}
            return 'mods', items
        return 'raw', html.strip()
    # flow
    if 'class="flow"' in html:
        icons = ICON_RE.findall(html)
        icons = [i for i in icons if i != 'i-arrow-right']
        label = re.search(r'<span class="fl">([^<]+)</span>', html)
        flow = {'label': label.group(1) if label else ''}
        if len(icons) >= 2:
            flow['from'], flow['to'] = icons[0], icons[1]
        elif icons:
            flow['icon'] = icons[0]
        return 'flow', flow
    # ctx
    m = re.fullmatch(r'<span class="ctx( hi)?">([^<]+)</span>', html.strip())
    if m:
        v = m.group(2)
        return 'ctx', {'v': v, 'hi': True} if m.group(1) else v
    # replacement（弃用表替代方案）
    if 'arrow-sep' in html:
        text = re.search(r'<span class="mono-dim">([^<]+)</span>', html)
        return 'replacement', text.group(1) if text else strip_tags(html)
    # num / mono / plain / mdesc / mono-dim td 由调用方按 td class 决定
    m = re.fullmatch(r'<span class="num">([^<]+)</span>', html.strip())
    if m:
        return 'num', m.group(1)
    m = re.fullmatch(r'<span class="mono-dim">([^<]+)</span>', html.strip())
    if m:
        return 'mono', m.group(1)
    m = re.fullmatch(r'<span class="tag"><svg class="ic"><use href="#(i-[a-z]+)"/></svg>([^<]*)</span>', html.strip())
    if m:
        # 无文字的裸图标 tag（如 matrix 里的代码/视频 tag 带文字则走 raw）
        return 'raw', html.strip()
    return 'raw', html.strip()


# ---------- 结构提取 ----------

def split_sections(src):
    """按 <section class="sec" id="..."> 切分，返回 [(id, html)]"""
    parts = []
    for m in re.finditer(r'<section class="sec" id="([^"]+)">', src):
        start = m.start()
        end = src.find('</section>', m.end())
        parts.append((m.group(1), src[start:end]))
    return parts


def parse_table_section(sec_id, html):
    m = re.search(r'<div class="sec-head">.*?<use href="#(i-[a-z-]+)"/>.*?<h2 class="sec-title">([^<]+)</h2>', html, re.S)
    icon, title = (m.group(1), m.group(2)) if m else ('i-doc', sec_id)
    m = re.search(r'<p class="sec-desc">(.*?)</p>', html, re.S)
    desc = m.group(1).strip() if m else None

    thead = re.search(r'<thead>(.*?)</thead>', html, re.S)
    columns = re.findall(r'<th>([^<]*)</th>', thead.group(1)) if thead else []

    table_cls_m = re.search(r'<table(?:\s+class="([^"]*)")?>', html)
    table_class = table_cls_m.group(1) if table_cls_m and table_cls_m.group(1) else None

    tbody = re.search(r'<tbody>(.*?)</tbody>', html, re.S)
    rows, all_types = [], []
    for tr in re.finditer(r'<tr>(.*?)</tr>', tbody.group(1), re.S):
        tds = re.findall(r'<td(?:\s+class="([^"]*)")?>(.*?)</td>', tr.group(1), re.S)
        vals, types = [], []
        for td_cls, inner in tds:
            rt, v = parse_cell_with_cls(td_cls or '', inner)
            types.append(rt)
            vals.append(v)
        all_types.append(types)
        rows.append(vals)
    # 行类型取第一行（要求全表一致；不一致时逐格覆盖 dict 已处理）
    # 注意必须复制，否则后续标 MIXED 会污染 all_types[0]
    row_types = list(all_types[0]) if all_types else []
    for types in all_types[1:]:
        for i, (a, b) in enumerate(zip(row_types, types)):
            if a != b:
                # 混合列：标 raw，要求提取方逐格带 {"t":..., "v":...}
                row_types[i] = 'MIXED'
    # MIXED 处理：把每格改成显式 {"t":..,"v":..}
    if 'MIXED' in row_types:
        for r_i, vals in enumerate(rows):
            for c_i, v in enumerate(vals):
                if row_types[c_i] == 'MIXED':
                    rt, _ = parse_cell_with_cls('', re_cell_html(all_types, r_i, c_i, vals)) if False else (all_types[r_i][c_i], None)
                    vals[c_i] = {'t': all_types[r_i][c_i], 'v': v}
        row_types = ['raw' if t == 'MIXED' else t for t in row_types]

    return {
        'id': sec_id, 'title': title, 'icon': icon, 'desc': desc,
        'kind': 'table', 'columns': columns, 'row_types': row_types, 'rows': rows,
        **({'table_class': table_class} if table_class else {}),
    }


def re_cell_html(*a):
    return ''


def parse_cell_with_cls(td_cls, inner):
    inner_s = inner.strip()
    if td_cls == 'mdesc':
        return 'mdesc', inner_s
    if td_cls == 'plain':
        return 'plain', inner_s
    if td_cls == 'mono-dim':
        return 'mono_td', inner_s
    return parse_cell(inner_s)


def parse_quick(html):
    m = re.search(r'<h2 class="sec-title">([^<]+)</h2>', html)
    title = m.group(1) if m else '快速选型'
    m = re.search(r'<div class="sec-head">.*?<use href="#(i-[a-z-]+)"/>', html, re.S)
    icon = m.group(1) if m else 'i-bolt'
    m = re.search(r'<p class="sec-desc">([^<]*)</p>', html)
    desc = m.group(1) if m else None
    cards = []
    for cm in re.finditer(
            r'<div class="quick-card">\s*<span class="quick-task"><svg class="ic"><use href="#(i-[a-z-]+)"/></svg>([^<]+)</span>\s*'
            r'<span class="quick-model">([^<]+)</span>', html):
        cards.append({'icon': cm.group(1), 'task': cm.group(2), 'model': cm.group(3)})
    return {'id': 'quick', 'title': title, 'icon': icon, 'desc': desc, 'kind': 'quick', 'cards': cards}


def parse_meta(src):
    meta = {}
    m = re.search(r'<title>([^<]+)</title>', src)
    meta['title'] = m.group(1)
    m = re.search(r'<div class="hero-eyebrow">([^<]+)</div>', src)
    meta['eyebrow'] = m.group(1)
    m = re.search(r'<h1>([^<]+)</h1>', src)
    meta['h1'] = m.group(1)
    m = re.search(r'<p class="hero-desc">(.*?)</p>', src, re.S)
    meta['hero_desc'] = m.group(1).strip()
    m = re.search(r'<a class="home-btn" href="([^"]+)" title="([^"]+)">\s*<svg class="ic"><use href="#i-home"/></svg><span>([^<]+)</span>', src)
    if m:
        meta['home_href'], meta['home_title'], meta['home_label'] = m.group(1), m.group(2), m.group(3)
    stats = []
    for sm in re.finditer(
            r'<span class="stat-num">([^<]+)</span><span class="stat-label"><svg class="ic"><use href="#(i-[a-z-]+)"/></svg><span>([^<]+)</span>',
            src):
        stats.append({'num': sm.group(1), 'icon': sm.group(2), 'label': sm.group(3)})
    meta['stats'] = stats
    m = re.search(r'<footer class="footer">\s*<p><b>([^<]+)</b> · 最后更新 ([^<]+)</p>', src)
    meta['footer_title'], meta['footer_updated'] = m.group(1), m.group(2)
    m = re.search(r'<p class="rules">([^<]+)</p>', src)
    meta['footer_rules'] = m.group(1)
    m = re.search(r'<footer class="footer">.*?<p>(数据来源：.*?)</p>', src, re.S)
    meta['footer_sources'] = m.group(1).strip() if m else ''
    return meta


NAV_SHORT = {}  # section id -> nav 短名（从原页面 nav 提取）


DEFAULT_RANGES = {'sky': '$100+ / $500+', 'expensive': '$10-100 / $50-500', 'high': '$2-10 / $8-50',
                  'mid': '$0.5-2 / $2-8', 'low': '$0.1-0.5 / $0.4-2', 'cheap': '<$0.1 / <$0.4'}
DEFAULT_NOTE = '单位：USD / 1M tokens（输入 / 输出）'


def parse_legend_overrides(src):
    """从图例区反向读取价格区间/单位注释 → legend_overrides（与默认 USD 一致则省略）"""
    i = src.find('id="legend"')
    if i < 0:
        return {}
    seg = src[i:src.find('</section>', i)]
    ranges = re.findall(r'<span class="legend-range">([^<]+)</span>', seg)
    note_m = re.search(r'<span class="legend-note">([^<]+)</span>', seg)
    keys = ['sky', 'expensive', 'high', 'mid', 'low', 'cheap']
    if len(ranges) >= 6:
        ov_ranges = dict(zip(keys, ranges[:6]))
        ov = {}
        if ov_ranges != DEFAULT_RANGES:
            ov['ranges'] = ov_ranges
        if note_m and note_m.group(1) != DEFAULT_NOTE:
            ov['note'] = note_m.group(1)
        return ov
    return {}


def main():
    path = sys.argv[1]
    out = sys.argv[sys.argv.index('-o') + 1] if '-o' in sys.argv else None
    src = open(path, encoding='utf-8').read()

    data = {'meta': parse_meta(src), 'sections': []}

    # 图例价格区间覆盖（CNY 等非默认计价时保留）
    ov = parse_legend_overrides(src)
    if ov:
        data['legend_overrides'] = ov

    # nav 短名
    nav_map = {}
    nav_m = re.search(r'<div class="nav-inner">(.*?)</div>', src, re.S)
    if nav_m:
        for am in re.finditer(r'<a href="#([^"]+)">([^<]+)</a>', nav_m.group(1)):
            nav_map[am.group(1)] = am.group(2)

    for sec_id, html in split_sections(src):
        if sec_id == 'legend':
            continue  # 由渲染器 default_legend() 生成
        if sec_id == 'quick':
            sec = parse_quick(html)
        else:
            sec = parse_table_section(sec_id, html)
        if sec_id in nav_map:
            sec['nav'] = nav_map[sec_id]
        data['sections'].append(sec)

    # naming 表的特殊行类型（首列样式）
    for sec in data['sections']:
        if sec['id'] == 'naming':
            sec['table_class'] = 'rules'

    text = json.dumps(data, ensure_ascii=False, indent=2)
    if out:
        open(out, 'w', encoding='utf-8').write(text)
        n_models = sum(1 for s in data['sections'] if s['kind'] == 'table'
                       for r in s['rows'] if r and isinstance(r[0], dict) and 'id' in r[0])
        print(f'extracted: {out}')
        print(f'sections: {len(data["sections"])}, models: {n_models}')
    else:
        print(text)


if __name__ == '__main__':
    main()
