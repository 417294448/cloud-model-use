"""客观字段自动填充：把 openai/parse_cards.py 的官方数据写回 data JSON。

用法:
    python fill_objective_fields.py <data.json> <cards.json> [--write]

    cards.json 由 openai/parse_cards.py 生成（含 models 字典 + skipped）。
    默认只打印将发生的变更（dry-run）；--write 才真正改写 data.json。

自动填充的字段（只动"客观字段"，说明文字/徽章/定位等编辑性内容一律不碰）:
    - 推理档位：官方 Reasoning 图标格数 → 5/4/3/2 档；
      官方标 Intelligence 的模型是非推理模型 → 1 档（快速），与页面约定一致
    - 速度档位：官方 Speed 格数 → 5..1 档
    - 价格档位：官方输入价（USD/1M）→ sky/expensive/high/mid/low/cheap

匹配方式：按行内 model_id 与 cards 的 slug 精确匹配；
找不到官方数据的模型（如 Azure-only 的 chat 变体）跳过并列出，由人工确认。
"""
import json, sys

PRICE_TIER_BY_INPUT = [
    (100, 'sky'), (10, 'expensive'), (2, 'high'),
    (0.5, 'mid'), (0.1, 'low'), (0, 'cheap'),
]


def price_tier(price_in):
    if price_in is None:
        return None
    for threshold, tier in PRICE_TIER_BY_INPUT:
        if price_in >= threshold:
            return tier
    return 'cheap'


def fill(data, cards):
    models = cards.get('models', {})
    changed, skipped = [], []
    for sec in data['sections']:
        if sec.get('kind') != 'table':
            continue
        types = sec['row_types']
        for row in sec['rows']:
            # 找 model_id 单元格
            mid = None
            for t, v in zip(types, row):
                if t == 'model_id':
                    mid = v['id'] if isinstance(v, dict) else v
                    break
            if not mid:
                continue
            card = models.get(mid)
            if not card:
                skipped.append(mid)
                continue
            for i, (t, v) in enumerate(zip(types, row)):
                if t == 'reasoning':
                    # Intelligence → 非推理 → 1；Reasoning 格数 → 档位
                    if card.get('reasoning_label') == 'Intelligence':
                        new_lv = 1
                    else:
                        new_lv = card.get('reasoning_icons')
                    if new_lv and new_lv != v:
                        changed.append(f'{mid}: 推理 {v} → {new_lv}')
                        row[i] = new_lv
                elif t == 'speed':
                    new_lv = card.get('speed_icons')
                    if new_lv and new_lv != v:
                        changed.append(f'{mid}: 速度 {v} → {new_lv}')
                        row[i] = new_lv
                elif t == 'price' and not isinstance(v, dict):
                    new_tier = price_tier(card.get('price_in'))
                    if new_tier and new_tier != v:
                        changed.append(f'{mid}: 价格 {v} → {new_tier} (官方 ${card["price_in"]})')
                        row[i] = new_tier
    return changed, sorted(set(skipped))


def main():
    data_path, cards_path = sys.argv[1], sys.argv[2]
    write = '--write' in sys.argv
    data = json.load(open(data_path, encoding='utf-8'))
    cards = json.load(open(cards_path, encoding='utf-8'))
    changed, skipped = fill(data, cards)
    for c in changed:
        print(' ', c)
    print(f'\n变更 {len(changed)} 处；无官方数据跳过 {len(skipped)} 个:')
    for s in skipped:
        print(f'  - {s}')
    if write:
        json.dump(data, open(data_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print(f'\n已写回 {data_path}（之后用 render_guide.py 重新渲染页面）')
    else:
        print('\n(dry-run，加 --write 写回)')


if __name__ == '__main__':
    main()
