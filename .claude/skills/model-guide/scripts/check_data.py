"""data JSON 业务规则校验：结构合法性之外的"内容对不对"检查。

用法:
    python check_data.py <data.json>

检查项:
    1. 弃用表收录规则：deprecated 节每行的模型 ID 必须存在于主表
       （规则来源见 references/providers/openai.md「弃用表收录规则」）
    2. 每行单元格数 == row_types 长度 == columns 长度
    3. 枚举值合法：price/tier/reasoning/speed/lifecycle 的取值在渲染器映射表内
    4. meta 必填字段齐全（title/eyebrow/h1/hero_desc/stats/footer_*）

与 check_html.py 的分工：check_html 管"渲染产物结构合法"，
check_data 管"数据源内容正确"——改 data JSON 后两个都应跑。
"""
import json, re, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_guide import PRICE_TIERS, TIER_LEVELS, REASONING_NAMES, SPEED_LEVELS, LIFECYCLE, MODALITIES

META_REQUIRED = ['title', 'eyebrow', 'h1', 'hero_desc', 'stats',
                 'footer_title', 'footer_updated', 'footer_rules', 'footer_sources']


def model_ids(data):
    """主表（非 deprecated）全部模型 ID 集合"""
    ids = set()
    for sec in data['sections']:
        if sec['id'] == 'deprecated' or sec.get('kind') != 'table':
            continue
        for row in sec['rows']:
            for t, v in zip(sec['row_types'], row):
                if t == 'model_id':
                    ids.add(v['id'] if isinstance(v, dict) else v)
    return ids


def check(data):
    errors, warnings = [], []

    # meta 必填
    for k in META_REQUIRED:
        if k not in data['meta']:
            errors.append(f'meta 缺字段: {k}')

    main_ids = model_ids(data)

    for sec in data['sections']:
        sid = sec.get('id', '?')
        if sec.get('kind') != 'table':
            continue
        cols, rts = sec['columns'], sec['row_types']
        if len(cols) != len(rts):
            errors.append(f'{sid}: columns({len(cols)}) != row_types({len(rts)})')

        for r_i, row in enumerate(sec['rows']):
            if len(row) != len(rts):
                errors.append(f'{sid} 行{r_i + 1}: 单元格 {len(row)} != row_types {len(rts)}')
                continue
            for t, v in zip(rts, row):
                # 逐格类型覆盖
                if isinstance(v, dict) and 't' in v:
                    t, v = v['t'], v['v']
                if t == 'price' and v is not None and not isinstance(v, dict) and v not in PRICE_TIERS:
                    errors.append(f'{sid} 行{r_i + 1}: 非法价格档位 "{v}"')
                elif t == 'tier' and v not in TIER_LEVELS:
                    errors.append(f'{sid} 行{r_i + 1}: 非法定位 "{v}"')
                elif t == 'reasoning' and v not in REASONING_NAMES:
                    errors.append(f'{sid} 行{r_i + 1}: 非法推理档 {v}')
                elif t == 'speed' and v not in SPEED_LEVELS:
                    errors.append(f'{sid} 行{r_i + 1}: 非法速度档 {v}')
                elif t == 'lifecycle' and v not in LIFECYCLE:
                    errors.append(f'{sid} 行{r_i + 1}: 非法生命周期 "{v}"')
                elif t == 'mods':
                    items = v['items'] if isinstance(v, dict) else v
                    for m in items:
                        if m not in MODALITIES:
                            errors.append(f'{sid} 行{r_i + 1}: 非法模态 "{m}"')
                elif t == 'model_id':
                    mid = v['id'] if isinstance(v, dict) else v
                    if sid != 'deprecated' and not re.match(r'^[a-z0-9.*-]+( / [a-z0-9.*-]+)*( \([^)]+\))?$', mid):
                        warnings.append(f'{sid} 行{r_i + 1}: 模型 ID 形式可疑 "{mid}"')

        # 弃用表收录规则
        if sid == 'deprecated':
            for r_i, row in enumerate(sec['rows']):
                v = row[0]
                mid = v['id'] if isinstance(v, dict) else v
                base = mid.split(' / ')[0].strip()
                if mid not in main_ids and base not in main_ids:
                    errors.append(f'deprecated 行{r_i + 1}: "{mid}" 不在主表（违反弃用表收录规则）')

    return errors, warnings


def main():
    data = json.load(open(sys.argv[1], encoding='utf-8'))
    errors, warnings = check(data)
    for w in warnings:
        print('警告:', w)
    for e in errors:
        print('错误:', e)
    if not errors:
        print(f'OK: {sys.argv[1]} 全部业务规则通过（{len(warnings)} 条警告）')
        sys.exit(0)
    sys.exit(1)


if __name__ == '__main__':
    main()
