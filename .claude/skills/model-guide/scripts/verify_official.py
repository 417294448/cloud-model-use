"""官方数据交叉校验：data JSON 中的模型数据 vs 官方文档文本。

用法:
    python verify_official.py <data.json> --docs <官方文本1> [官方文本2 ...]
    python verify_official.py data/qwen.json --docs billing.txt vision.txt omni.txt

检查项:
    1. 存在性：data JSON 中每个模型 ID 必须能在官方文本中找到
    2. 价格声称：说明列中的 ¥X / ¥X/¥Y 数字必须与官方价格文本一致（模型名后 400 字符窗口内）
    3. 遗漏差集：官方文本中出现、但页面未收录的模型 ID，按归因分类
       （快照/别名、第三方、工具 API、旧代 → 忽略；其余 → 候选补充清单）

与 check_data.py 的分工：check_data 校验"数据内部自洽"（结构、枚举、弃用表规则），
verify_official 校验"数据与官方一致"（存在性、价格、遗漏）。更新页面数据后两个都应跑。

提供商归因规则目前内置 qwen 预设（PROVIDER_RULES），新提供商按需扩展。
"""
import json, re, sys

# 差集归因规则（按提供商预设）
PROVIDER_RULES = {
    'qwen': {
        'snapshot': [r'-20\d{2}-\d{2}-\d{2}$', r'-latest$', r'-us$', r'-preview$'],
        'third_party_prefix': ['MiniMax/', 'siliconflow/', 'kling/', 'pixverse/', 'vidu/', 'Tripo/',
                               'ZHIPU/', 'stepfun/', 'unisound/', 'xiaomi/', 'vanchin/', 'Moonshot-'],
        'third_party_exact': ['deepseek', 'glm', 'kimi', 'mimo', 'MiniMax-M', 'aitryon', 'farui', 'gui',
                              'shoemodel', 'stepfun'],
        'tool_prefix': ['wordart', 'wanx', 'facechain', 'liveportrait', 'animate-anyone', 'emo-',
                        'emoji-', 'image-', 'video-style', 'videoretalk', 'multimodal-embedding-v1'],
        'legacy_prefix': ['qwen-max', 'qwen-plus', 'qwen-turbo', 'qwen-flash-20', 'qwen2', 'qwen-coder-plus',
                          'qwen-coder-turbo', 'qwen-audio-turbo', 'cosyvoice-v1', 'cosyvoice-v2',
                          'qwen-tts-20', 'qwen-tts-latest', 'qwen-tts-realtime', 'qwen-vl-ocr-20',
                          'qwen-omni-turbo-20', 'qwen-omni-turbo-latest', 'qwen-omni-turbo-realtime',
                          'qwen-plus-20', 'qwen-plus-character', 'qwen3-asr-flash-20', 'qwen3-vl-flash-20',
                          'qwen3.5-flash-20', 'qwen3.5-plus-20', 'qwen-long-20', 'qwen-long-latest',
                          'qwen-deep-research-20', 'qwen3-livetranslate-flash-20', 'qwen3-omni-flash-20',
                          'qwen3.5-omni-flash-20', 'qwen3.5-livetranslate-flash-realtime-20',
                          'qwen3.5-omni-plus-20', 'qwen3.6-flash-20', 'qwen3.6-plus-20', 'qwen3.7-max-20',
                          'qwen3.7-flash-20', 'qwen3-coder-plus-20', 'qwen3-coder-flash-20',
                          'qwen-image-20', 'qwen-image-max-20', 'qwen-image-plus-20', 'qwen-image-edit',
                          'qwen3-tts-', 'qwen3-coder-30b', 'qwen3-coder-480b', 'fun-asr-20', 'fun-asr-mtl-20',
                          'fun-asr-flash', 'fun-music-preview', 'qwen2.5-vl-embedding',
                          'text-embedding-async', 'tongyi-intent-detect', 'happyhorse-1.0', 'wan2.1-',
                          'wan2.2-', 'wan2.5-', 'wanx2.1-', 'wanx2.0-'],
    },
}


def load_doc_ids(text):
    """从官方文本提取模型 ID 候选（ROW 行首单元格 + 行内模型形 ID）"""
    ids = set(re.findall(r'ROW: \| \n?([A-Za-z][A-Za-z0-9./_-]*) \|', text))
    # 行内出现的模型形 ID（含版本号形态，如 qwen3.8-max / fun-asr / z-image-turbo）
    # 负向后行断言：不匹配 deepseek-r1-distill-qwen-1.5b 这类截断片段
    ids |= set(re.findall(r'(?<![a-z0-9-])((?:qwen|qvq|qwq|wan|wanx|z-image|fun-|cosyvoice|paraformer|sensevoice|gummy|happyhorse|tongyi-|gte-|text-embedding|opennlu|aitryon)[a-z0-9./_-]*)\b', text))
    return {i.strip() for i in ids if 2 < len(i.strip()) < 60}


def page_models(data):
    out = []
    for sec in data['sections']:
        if sec.get('kind') != 'table':
            continue
        for row in sec['rows']:
            for t, v in zip(sec['row_types'], row):
                if t == 'model_id':
                    out.append((sec['id'], v['id'] if isinstance(v, dict) else v))
    return out


def find_prices(model, text, window=400):
    """模型名后 window 字符内的 ¥ 数字（与 verify 流程一致）"""
    for m in re.finditer(re.escape(model) + r'\b', text):
        seg = text[m.start():m.start() + window]
        prices = re.findall(r'(\d+(?:\.\d+)?)元', seg)
        if prices:
            return prices[:4]
    return None


def categorize(mid, rules):
    for pat in rules['snapshot']:
        if re.search(pat, mid):
            return '快照/别名'
    for p in rules['third_party_prefix']:
        if mid.startswith(p):
            return '第三方'
    for p in rules['third_party_exact']:
        if mid.startswith(p):
            return '第三方'
    for p in rules['tool_prefix']:
        if mid.startswith(p):
            return '工具API'
    for p in rules['legacy_prefix']:
        if mid.startswith(p):
            return '旧代'
    return '候选补充'


def main():
    args = sys.argv[1:]
    data_path = args[0]
    docs = []
    i = 1
    while i < len(args):
        if args[i] == '--docs':
            docs.extend(args[i + 1:])
            break
        i += 1
    if not docs:
        raise SystemExit('用法: verify_official.py <data.json> --docs <官方文本...>')

    data = json.load(open(data_path, encoding='utf-8'))
    provider = data['meta']['h1'] and ('qwen' if 'qwen' in data_path.lower() or '千问' in data['meta']['h1'] else 'qwen')
    rules = PROVIDER_RULES.get(provider, PROVIDER_RULES['qwen'])
    alldocs = ''.join(open(d, encoding='utf-8').read() for d in docs)
    doc_ids = load_doc_ids(alldocs)

    errors, warnings = [], []

    # 1. 存在性
    pm = page_models(data)
    page_ids = {m for _, m in pm}
    for sec_id, mid in pm:
        base = mid.split(' / ')[0]
        if mid not in alldocs and base not in alldocs:
            errors.append(f'存在性: [{sec_id}] {mid} 未在官方文本中出现')

    # 2. 价格声称（mdesc 中的 ¥ 数字 vs 官方）
    for sec in data['sections']:
        if sec.get('kind') != 'table':
            continue
        for row in sec['rows']:
            mid = None
            desc = ''
            for t, v in zip(sec['row_types'], row):
                if t == 'model_id':
                    mid = v['id'] if isinstance(v, dict) else v
                if t == 'mdesc':
                    desc = v if isinstance(v, str) else ''
            if not mid or '¥' not in desc:
                continue
            claim_nums = re.findall(r'¥(\d+(?:\.\d+)?)', desc)
            if not claim_nums:
                continue
            official = find_prices(mid, alldocs)
            if not official:
                warnings.append(f'价格: {mid} 页面声称 ¥{"、¥".join(claim_nums)}，官方窗口内未取到价格')
            elif not all(c in official for c in claim_nums):
                errors.append(f'价格: {mid} 页面声称 ¥{"、¥".join(claim_nums)} ≠ 官方 {official}')

    # 3. 遗漏差集
    buckets = {}
    for mid in sorted(doc_ids - page_ids):
        cat = categorize(mid, rules)
        buckets.setdefault(cat, []).append(mid)

    print(f'== 存在性: {len(page_ids)} 个页面模型，{sum(1 for e in errors if e.startswith("存在性"))} 个未命中官方')
    print(f'== 价格: {sum(1 for e in errors if e.startswith("价格"))} 处不一致，{len(warnings)} 处未取到')
    print(f'== 官方差集归因:')
    for cat in ('候选补充', '旧代', '第三方', '工具API', '快照/别名'):
        lst = buckets.get(cat, [])
        mark = '⚠️' if cat == '候选补充' and lst else '  '
        print(f'  {mark} {cat}: {len(lst)}' + (f' → {lst}' if cat == '候选补充' and lst else ''))

    for w in warnings:
        print('警告:', w)
    for e in errors:
        print('错误:', e)
    if not errors:
        print('OK: 存在性/价格全部通过' + ('；但有候选补充待评估' if buckets.get('候选补充') else ''))
        sys.exit(0 if not buckets.get('候选补充') else 2)
    sys.exit(1)


if __name__ == '__main__':
    main()
