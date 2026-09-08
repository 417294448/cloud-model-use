# -*- coding: utf-8 -*-
"""从 data/<厂商>.json 汇总模型统计并同步到根目录 index.html。

背景：index.html 通过 iframe Tab 聚合各厂商指南页，其 hero 三处统计
（收录模型 Models / 厂商数 Vendors / 最大上下文 Max context）与各厂商
meta.stats 相关。曾出现"新增 Anthropic 后 Vendors 仍为 4"的手工漏改，
故沉淀本脚本：从各 data JSON 事实源汇总，默认仅报告差异，--write 才写回。

汇总口径（与各子页页眉/README 一致）：
- Vendors      = data/ 下中文厂商 JSON 文件数（排除 *-en.json）
- Models       = Σ 各厂商 meta.stats「收录模型」num（'69+'→69；向下取整到 10，显示 'N+'）
- Max context  = max 各厂商 meta.stats「最大上下文」num（1.05M→1.05e6 换算后取原始串）
- meta 描述中的 'N+ LLMs' / '共 N+ 模型' 一并同步到 Models 显示值

用法（在项目根目录执行）：
    python .claude/skills/model-guide/scripts/sync_index_stats.py            # 仅报告差异
    python .claude/skills/model-guide/scripts/sync_index_stats.py --write    # 写回 index.html

注意：本脚本只同步统计数字；新增厂商的 Tab 按钮 / iframe 面板 / I18N 文案 /
品牌 logo symbol / meta 厂商枚举 仍须按 SKILL.md「接入 index.html 厂商 Tab」手工维护。
"""
import json, glob, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)            # .claude/skills/model-guide
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(SKILL_DIR)))  # 项目根（model-guide→skills→.claude→根）
DATA_DIR = os.path.join(SKILL_DIR, 'data')
INDEX = os.path.join(ROOT, 'index.html')

NUM_RE = re.compile(r'([0-9]+(?:\.[0-9]+)?)\s*([MK]?)', re.I)


def parse_num(s):
    """'83'/'69+'/'1.05M'/'10M'/'200K' → 归一数值（无单位按 1）"""
    s = str(s).replace('+', '').replace(',', '').strip()
    m = NUM_RE.match(s)
    if not m:
        return None
    v = float(m.group(1))
    u = m.group(2).upper()
    return v * (1e6 if u == 'M' else 1e3 if u == 'K' else 1)


def collect():
    """返回 (vendors, models_total, max_ctx_raw)；并打印各家明细"""
    zh = [f for f in sorted(glob.glob(os.path.join(DATA_DIR, '[a-z]*.json')))
          if not f.endswith('-en.json')]
    models_total = 0
    max_ctx = None   # (数值, 原始串)
    print('== 各厂商 data JSON meta.stats 收录模型 / 最大上下文 ==')
    for f in zh:
        d = json.load(open(f, encoding='utf-8'))
        st = d['meta'].get('stats', [])
        label_model = next((s for s in st if s['label'] in ('收录模型', 'Models')), None)
        label_ctx = next((s for s in st if s['label'] in ('最大上下文', 'Max context')), None)
        nm = parse_num(label_model['num']) if label_model else None
        cv = parse_num(label_ctx['num']) if label_ctx else None
        models_total += int(nm) if nm else 0
        if cv is not None and (max_ctx is None or cv > max_ctx[0]):
            max_ctx = (cv, label_ctx['num'])
        print(f'  {os.path.basename(f):22s} 收录={label_model["num"] if label_model else "-"}'
              f'  上下文={label_ctx["num"] if label_ctx else "-"}')
    vendors = len(zh)
    models_display = f'{(models_total // 10) * 10}+'
    max_ctx_display = max_ctx[1] if max_ctx else None
    return vendors, models_display, max_ctx_display, models_total


def apply_or_report(vendors, models_disp, maxctx_disp, write):
    t = open(INDEX, encoding='utf-8').read()
    orig = t

    # --- 定位/替换三处 stat-num（以 icon 锚定，避免误伤 SVG path 中的数字） ---
    def set_stat(t, icon, value):
        pat = re.compile(r'(class="stat-num">)[^<]*(</span><span class="stat-label">'
                         r'<svg class="ic"><use href="#' + icon + r'"/>)')
        m = pat.search(t)
        if not m:
            print(f'!! 未找到 icon #{icon} 对应 stat-num，跳过')
            return t
        cur = _cur(m)
        if str(cur) != str(value) and value is not None:
            print(f'  [{icon}] stat-num  {cur}  →  {value}')
            return pat.sub(lambda mm: mm.group(1) + str(value) + mm.group(2), t, count=1)
        print(f'  [{icon}] stat-num  {cur}  （一致）')
        return t

    def _cur(m):
        return m.group(0).split('>')[1].split('<')[0]

    print('== 拟更新（--write 时写入） ==')
    t = set_stat(t, 'i-models', models_disp)   # Models
    t = set_stat(t, 'i-modes', vendors)        # Vendors
    if maxctx_disp:
        t = set_stat(t, 'i-ruler', maxctx_disp)  # Max context

    # --- meta / I18N 描述中的 'N+ LLMs' 与 '共 N+ 模型' ---
    llms_re = re.compile(r'([0-9]+)\+ LLMs')
    new_t, n = llms_re.subn(f'{models_disp} LLMs', t)
    if n:
        print(f'  [meta]  {n} 处 "N+ LLMs" → "{models_disp} LLMs"')
    t = new_t
    mod_re = re.compile(r'(共 )([0-9]+)\+( 模型)')
    new_t, n2 = mod_re.subn(f'\\g<1>{models_disp}\\g<3>', t)
    if n2:
        print(f'  [meta]  {n2} 处 "共 N+ 模型" → "共 {models_disp} 模型"')
    t = new_t

    # --- 写回 / 报告差异 ---
    if t == orig:
        print('== 无差异：index.html 统计已与 data JSON 一致 ==')
        return 0
    if write:
        open(INDEX, 'w', encoding='utf-8').write(t)
        print('== 已写回 index.html ==')
        return 0
    print('== 存在差异（未写入；加 --write 应用） ==')
    return 1


def main():
    write = '--write' in sys.argv
    vendors, models_disp, maxctx_disp, models_total = collect()
    print(f'\n== 汇总：Vendors={vendors}  Models(加和)={models_total} → "{models_disp}"  '
          f'Max context="{maxctx_disp}" ==\n')
    sys.exit(apply_or_report(vendors, models_disp, maxctx_disp, write))


if __name__ == '__main__':
    main()
