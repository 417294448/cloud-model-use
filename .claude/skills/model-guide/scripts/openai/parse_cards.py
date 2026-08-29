"""【OpenAI 专用】解析 developers.openai.com 模型详情页指标卡，输出 JSON。

用法:
    python scripts/openai/parse_cards.py <目录>          # 解析目录下全部 .html
    python scripts/openai/parse_cards.py <目录> -o out.json

说明:
    本解析器针对 OpenAI 官方文档站的指标卡 DOM 结构（见 references/providers/openai.md）。
    其他提供商官方页面结构不同，需各自的 parse_<厂商>_cards.py；输出字段约定保持一致，
    便于 fill_objective_fields.py 复用。

输出字段（每个模型）:
    reasoning_label / reasoning_icons   推理等级文字与格数（Intelligence 标签说明是非推理模型）
    speed_label / speed_icons           速度等级文字与格数
    price_text                          价格原文（如 "$2.5 • $15 Input • Output"）
    price_in / price_out                解析出的输入/输出单价（USD/1M tokens，可为 None）
    input_modalities / output_modalities 模态文字（如 "Text, image"）
    reasoning_label 为 Intelligence 时，模型无推理能力（页面落档"快速"）

标签页（<100KB 的失败抓取、404 页）自动跳过并列入 skipped。
"""
import re, os, sys, json, glob

CARD_RE = re.compile(
    r'<div class="text-sm font-semibold lg:text-xs lg:text-gray-400 lg:uppercase">([^<]+)</div>'
    r'<div class="flex flex-row items-center gap-2 text-lg font-bold lg:text-2xl">(.*?)'
    r'(?=<div class="text-sm font-semibold lg:text-xs lg:text-gray-400 lg:uppercase">|</div></div></div>)',
    re.S)
PRICE_RE = re.compile(r'\$([\d.]+)\s*•\s*\$([\d.]+)')


def parse_file(path):
    src = open(path, encoding='utf-8').read()
    if 'Page not found' in src:
        return None
    data = {}
    for label, val in CARD_RE.findall(src):
        n_svg = len(re.findall(r'<svg', val))
        txt = re.sub(r'<svg.*?</svg>', '', val, flags=re.S)
        txt = re.sub(r'<[^>]+>', ' ', txt)
        data[label.strip()] = (n_svg, re.sub(r'\s+', ' ', txt).strip())
    if not data:
        return None
    out = {}
    for key in ('Reasoning', 'Intelligence'):
        if key in data:
            out['reasoning_label'] = key
            out['reasoning_level_text'], out['reasoning_icons'] = data[key][1], data[key][0]
            break
    if 'Speed' in data:
        out['speed_label'], out['speed_icons'] = data['Speed'][1], data['Speed'][0]
    if 'Price' in data:
        out['price_text'] = data['Price'][1]
        m = PRICE_RE.search(out['price_text'])
        out['price_in'] = float(m.group(1)) if m else None
        out['price_out'] = float(m.group(2)) if m else None
    if 'Input' in data:
        out['input_modalities'] = data['Input'][1]
    if 'Output' in data:
        out['output_modalities'] = data['Output'][1]
    return out


def main():
    directory = sys.argv[1]
    results, skipped = {}, []
    for path in sorted(glob.glob(os.path.join(directory, '*.html'))):
        if os.path.getsize(path) < 100000:
            skipped.append(os.path.basename(path) + ' (too small)')
            continue
        slug = os.path.basename(path)[:-5].replace('_', '.')
        parsed = parse_file(path)
        if parsed is None:
            skipped.append(os.path.basename(path) + ' (404/no cards)')
            continue
        results[slug] = parsed
    report = {'models': results, 'skipped': skipped}
    text = json.dumps(report, ensure_ascii=False, indent=1)
    if '-o' in sys.argv:
        out = sys.argv[sys.argv.index('-o') + 1]
        open(out, 'w', encoding='utf-8').write(text)
        print(f'written: {out} ({len(results)} models, {len(skipped)} skipped)')
    else:
        print(text)


if __name__ == '__main__':
    main()
