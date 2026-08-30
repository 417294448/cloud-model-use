"""中英文语义一致性校验：data/<厂商>.json（zh）vs data/<厂商>-en.json（en）。

用法:
    python check_bilingual.py <厂商>.json                # 自动找同目录 <厂商>-en.json
    python check_bilingual.py <厂商>.json <厂商>-en.json

检查项（任一不一致即 error，exit 1）:
    1. meta 必填字段两文件齐全；stats 的 num 逐项一致
    2. sections 结构镜像：id 集合、kind、表格 columns 长度 / row_types / 行数一一对应
    3. 语言中立单元格值一致：model_id（id）、tier、price（档位 key）、reasoning、speed、
       mods、ctx、num、lifecycle——**仅当 zh 侧值不含中文时强制逐字一致**；
       含中文的值为编辑/翻译字段（如 ctx "最高 4K"、num "1200 亿"），跳过值比较
       （其翻译完整性由 make_<厂商>_en.py 漏翻告警 + 本脚本第 5 项兜底）
    4. 模型 ID 集合（含 deprecated 表）完全一致，zh/en 不允许有差集
    5. en 数据无中文残留（meta.lang_switch.zh.label「中」为设计保留，豁免）

quick 型 section 比较卡片数量与 model；raw 型 section（html）为编辑内容，跳过。
"""
import json, os, re, sys

CJK = re.compile(r'[\u4e00-\u9fff]')
META_REQUIRED = ['title', 'eyebrow', 'h1', 'hero_desc', 'stats',
                 'footer_title', 'footer_updated', 'footer_rules', 'footer_sources']
# 语言中立、值必须逐字一致的单元格类型（mods/ctx/num 可为 dict，含中文时整体跳过）
NEUTRAL_TYPES = {'model_id', 'tier', 'price', 'reasoning', 'speed', 'mods', 'ctx', 'num', 'lifecycle'}


def comparable(v):
    """规范化值用于比较；值或其嵌套内含中文字符（已翻译/编辑过）返回 None 表示跳过比较"""
    if v is None or isinstance(v, (bool, int, float)):
        return v
    if isinstance(v, str):
        return None if CJK.search(v) else v
    if isinstance(v, (tuple, list)):
        parts = [comparable(x) for x in v]
        return None if any(x is None for x in parts) else tuple(parts)
    if isinstance(v, dict):
        parts = {k: comparable(x) for k, x in v.items()}
        return None if any(x is None for x in parts.values()) else tuple(sorted(parts.items()))
    return None


def neutral_value(t, v):
    """单元格 → 比较值；编辑字段返回 None。dict 覆盖格按实际类型递归。"""
    if isinstance(v, dict) and 't' in v:
        return neutral_value(v['t'], v['v'])
    if t == 'model_id':
        v = v['id'] if isinstance(v, dict) else v
        return comparable(v)
    if t == 'price':
        # 档位 key 必须一致；{"raw": html} 是编辑字段（语言化），跳过
        return comparable(v) if isinstance(v, str) else None
    if t in NEUTRAL_TYPES:
        return comparable(v)
    return None


def model_ids(data):
    """全部 table 型 section 的模型 ID 集合（含 deprecated）"""
    ids = set()
    for sec in data['sections']:
        if sec.get('kind') != 'table':
            continue
        for row in sec['rows']:
            for t, v in zip(sec['row_types'], row):
                if isinstance(v, dict) and 't' in v:
                    t, v = v['t'], v['v']
                if t == 'model_id':
                    ids.add(v['id'] if isinstance(v, dict) else v)
    return ids


def collect_strings(obj, out):
    if isinstance(obj, str):
        out.add(obj)
    elif isinstance(obj, dict):
        for x in obj.values():
            collect_strings(x, out)
    elif isinstance(obj, list):
        for x in obj:
            collect_strings(x, out)


def check(zh_path, en_path):
    zh = json.load(open(zh_path, encoding='utf-8'))
    en = json.load(open(en_path, encoding='utf-8'))
    errors = []

    # 1. meta 必填 + stats num
    for k in META_REQUIRED:
        if k not in zh['meta']:
            errors.append(f'zh meta 缺字段: {k}')
        if k not in en['meta']:
            errors.append(f'en meta 缺字段: {k}')
    zn = [s['num'] for s in zh['meta'].get('stats', [])]
    enm = [s['num'] for s in en['meta'].get('stats', [])]
    if zn != enm:
        errors.append(f'stats num 不一致: zh={zn} en={enm}')

    # 2/3. sections 结构镜像 + 语言中立值
    zs = {s['id']: s for s in zh['sections']}
    es = {s['id']: s for s in en['sections']}
    if set(zs) != set(es):
        errors.append(f'section id 不一致: 仅 zh {sorted(set(zs) - set(es))}, 仅 en {sorted(set(es) - set(zs))}')
    for sid, z in zs.items():
        e = es.get(sid)
        if e is None:
            continue
        if z.get('kind') != e.get('kind'):
            errors.append(f'{sid}: kind 不一致 zh={z.get("kind")} en={e.get("kind")}')
            continue
        kind = z.get('kind')
        if kind == 'table':
            if len(z['columns']) != len(e['columns']):
                errors.append(f'{sid}: columns 长度不一致 zh={len(z["columns"])} en={len(e["columns"])}')
            if z['row_types'] != e['row_types']:
                errors.append(f'{sid}: row_types 不一致')
            if len(z['rows']) != len(e['rows']):
                errors.append(f'{sid}: 行数不一致 zh={len(z["rows"])} en={len(e["rows"])}')
            for ri, (zr, er) in enumerate(zip(z['rows'], e['rows'])):
                if len(zr) != len(er):
                    errors.append(f'{sid} 行{ri + 1}: 单元格数不一致 zh={len(zr)} en={len(er)}')
                    continue
                for ci, (t, zv, ev) in enumerate(zip(z['row_types'], zr, er)):
                    a, b = neutral_value(t, zv), neutral_value(t, ev)
                    if a is not None and a != b:
                        errors.append(f'{sid} 行{ri + 1} 列{ci + 1}({t}): 值不一致 zh={zv!r} en={ev!r}')
        elif kind == 'quick':
            zc, ec = z['cards'], e['cards']
            if len(zc) != len(ec):
                errors.append(f'{sid}: quick 卡片数不一致 zh={len(zc)} en={len(ec)}')
            for zi, (zc_, ec_) in enumerate(zip(zc, ec)):
                if zc_['model'] != ec_['model']:
                    errors.append(f'{sid} 卡片{zi + 1}: model 不一致 zh={zc_["model"]} en={ec_["model"]}')

    # 4. 模型 ID 集合
    zi, ei = model_ids(zh), model_ids(en)
    if zi != ei:
        errors.append(f'模型 ID 集合不一致: 仅 zh {sorted(zi - ei)}, 仅 en {sorted(ei - zi)}')

    # 5. en 数据无中文残留（lang_switch.zh.label「中」为设计保留）
    en_strs = set()
    collect_strings(en, en_strs)
    leftover = sorted(s for s in en_strs if CJK.search(s)
                      and not (s == '中' and en.get('meta', {}).get('lang_switch', {}).get('zh', {}).get('label') == '中'))
    for s in leftover:
        errors.append(f'en 数据中文残留: {s!r}')

    return errors


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    zh_path = sys.argv[1]
    en_path = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(zh_path)[0] + '-en.json'
    if not os.path.exists(en_path):
        print(f'跳过: 未找到英文数据 {en_path}（该厂商未双语化）')
        sys.exit(0)
    errors = check(zh_path, en_path)
    for e in errors:
        print('错误:', e)
    if errors:
        print(f'FAIL: {os.path.basename(zh_path)} 中英文语义不一致（{len(errors)} 处）')
        sys.exit(1)
    print(f'OK: {os.path.basename(zh_path)} 中英文语义一致')


if __name__ == '__main__':
    main()
