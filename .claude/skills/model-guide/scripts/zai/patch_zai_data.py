"""【智谱 Z.ai 专用】根据 pricing 页面抓取的缺失模型清单，补充到 data/zai.json。

用法:
    python scripts/zai/patch_zai_data.py [--write]

说明:
    - 读取 data/zai.json 并在对应 section 插入缺失模型
    - 新增 historical section 存放历史模型（不占用 deprecated 语义，避免与"必须在主表存在"的弃用表校验规则冲突）
    - 更新 meta.stats 中的收录模型数
    - 默认只打印变更摘要，使用 --write 才写入文件
"""
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
DATA_JSON = ROOT / '.claude' / 'skills' / 'model-guide' / 'data' / 'zai.json'
DIFF_DIR = ROOT / 'diff'


def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_diff(date_str, inserted, skipped, model_count, old_count):
    """将本次补丁变更追加到 diff/YYYY-MM-DD.md（只记录模型数据变更）"""
    DIFF_DIR.mkdir(exist_ok=True)
    diff_path = DIFF_DIR / f'{date_str}.md'
    provider = 'Z.ai（补丁）'

    section_lines = [f'## {provider}\n\n']
    section_lines.append('### 模型数据变更\n')
    for sec_id, model_id in inserted:
        section_lines.append(f'- 新增 {model_id}（{sec_id}）\n')
    section_text = ''.join(section_lines)

    if diff_path.exists():
        content = open(diff_path, encoding='utf-8').read()
        if any(line.strip() == f'## {provider}' for line in content.splitlines()):
            print(f'警告: {diff_path} 中已存在 {provider} 记录，未重复写入')
            return diff_path
        content = content.rstrip() + '\n\n' + section_text
    else:
        content = f'# {date_str} 模型指南更新记录\n\n' + section_text

    with open(diff_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return diff_path


def find_section(data, sec_id):
    for sec in data['sections']:
        if sec.get('id') == sec_id:
            return sec
    return None


def row_exists(sec, model_id):
    """检查 section 中是否已存在指定模型 ID"""
    if not sec:
        return False
    for row in sec.get('rows', []):
        first = row[0] if row else None
        if isinstance(first, dict):
            if first.get('id') == model_id:
                return True
        elif first == model_id:
            return True
    return False


# 从 pricing 页面补充的缺失模型（按 section 分组）
# 字段顺序与各 section row_types 保持一致
PATCH_MODELS = {
    'text': [
        # model_id, tier, price, mods, reasoning, speed, ctx, input, output, mdesc
        ["GLM-4-Plus", "flagship", "high", ["text"], 4, 3, "128K", "128K", "128K", "高智能旗舰，全自研第四代基座大模型，支持高级 Agent 能力"],
        ["GLM-4-Air-250414", "balanced", "mid", ["text"], 3, 3, "128K", "128K", "128K", "GLM-4-Air 日期快照 250414，高性价比文本模型"],
        ["GLM-4-AirX", "balanced", "expensive", ["text"], 3, 4, "8K", "8K", "8K", "极速推理版本，适合低延迟高响应场景"],
        ["GLM-4-Assistant", "balanced", "high", ["text"], 3, 3, "128K", "128K", "128K", "面向智能体应用优化的文本模型"],
        ["GLM-Z1-Air", "balanced", "mid", ["text"], 4, 3, "128K", "128K", "128K", "高性价比推理模型"],
        ["GLM-Z1-AirX", "balanced", "high", ["text"], 4, 4, "32K", "32K", "32K", "极速推理模型，兼顾推理深度与响应速度"],
        ["GLM-Z1-FlashX", "budget", "low", ["text"], 3, 5, "128K", "128K", "16K", "高速低价推理模型，适合高并发推理场景"],
        ["GLM-Z1-Flash", "budget", "cheap", ["text"], 3, 5, "128K", "128K", "16K", "免费推理模型"],
        ["GLM-4.5", "balanced", "mid", ["text"], 3, 3, "128K", "128K", "128K", "通用对话、推理与智能体能力"],
        ["GLM-4-Air", "balanced", "mid", ["text"], 3, 3, "128K", "128K", "128K", "轻量均衡，高性价比"],
        ["GLM-4-Flash", "budget", "cheap", ["text"], 2, 5, "128K", "128K", "16K", "免费文本模型"],
        ["GLM-4-9B", "balanced", "low", ["text"], 2, 3, "128K", "128K", "128K", "开源 9B 文本模型"],
        ["ChatGLM3-6B", "balanced", "low", ["text"], 2, 3, "8K", "8K", "8K", "开源对话模型（第三代）"],
    ],
    'vision': [
        # model_id, tier, price, mods, reasoning, speed, ctx, input, output, mdesc
        ["GLM-4V", "balanced", "high", ["text", "image"], 3, 3, "8K", "8K", "8K", "视觉理解模型（历史版本）"],
    ],
    'image': [
        # model_id, tier, price, mods, mdesc
        ["CogView-3", "balanced", {"raw": "<span class=\"tag t-green\">¥0.06 / 次</span>"}, ["text", "image"], "通用图像生成模型"],
    ],
}

HISTORICAL_SECTION = {
    "id": "historical",
    "kind": "table",
    "title": "历史模型",
    "icon": "i-circle-off",
    "nav": "历史模型",
    "desc": "已停止推荐或进入维护期的旧版模型，仅作兼容参考",
    "columns": ["模型 ID", "定位", "价格", "模态", "推理", "速度", "上下文", "输入", "输出", "说明"],
    "row_types": ["model_id", "tier", "price", "mods", "reasoning", "speed", "ctx", "ctx", "ctx", "mdesc"],
    "rows": [
        ["GLM-4-0520", "balanced", "high", ["text"], 3, 3, "128K", "128K", "128K", "GLM-4 0520 历史版本"],
        ["GLM-4V-Plus", "balanced", "mid", ["text", "image"], 3, 3, "8K", "8K", "8K", "GLM-4V Plus 历史版本"],
        ["GLM-4", "balanced", "sky", ["text"], 3, 3, "128K", "128K", "128K", "GLM-4 基础历史版本"],
    ],
}


def patch_data(data, write=False):
    date_str = datetime.now().strftime('%Y-%m-%d')

    # 1. 插入缺失模型到对应 section
    inserted = []
    skipped = []
    for sec_id, rows in PATCH_MODELS.items():
        sec = find_section(data, sec_id)
        if not sec:
            skipped.extend([r[0] for r in rows])
            continue
        for row in rows:
            model_id = row[0]
            if row_exists(sec, model_id):
                skipped.append(model_id)
                continue
            sec['rows'].append(row)
            inserted.append((sec_id, model_id))

    # 2. 新增 historical section（如果不存在）
    hist_sec = find_section(data, 'historical')
    if hist_sec:
        for row in HISTORICAL_SECTION['rows']:
            model_id = row[0]
            if row_exists(hist_sec, model_id):
                skipped.append(model_id)
            else:
                hist_sec['rows'].append(row)
                inserted.append(('historical', model_id))
    else:
        # 插入到 matrix 之前
        insert_idx = len(data['sections'])
        for i, sec in enumerate(data['sections']):
            if sec.get('id') == 'matrix':
                insert_idx = i
                break
        data['sections'].insert(insert_idx, HISTORICAL_SECTION)
        for row in HISTORICAL_SECTION['rows']:
            inserted.append(('historical', row[0]))

    # 3. 更新 meta 统计数字
    model_count = sum(
        len(sec.get('rows', []))
        for sec in data['sections']
        if sec.get('kind') == 'table' and sec.get('id') not in ('naming', 'matrix')
    )
    data['meta']['stats'][0]['num'] = f"{model_count}+"
    data['meta']['footer_updated'] = date_str
    data['meta']['hero_desc'] = data['meta']['hero_desc'].replace(
        '（2026-08-29 同步）', f'（{date_str} 同步）'
    )
    data['meta']['footer_sources'] = data['meta']['footer_sources'].replace(
        '（2026-08-29 同步）', f'（{date_str} 同步）'
    )

    return inserted, skipped, model_count


def main():
    write = '--write' in sys.argv
    data = load_json(DATA_JSON)
    old_count = sum(
        len(sec.get('rows', []))
        for sec in data['sections']
        if sec.get('kind') == 'table' and sec.get('id') not in ('naming', 'matrix')
    )
    inserted, skipped, model_count = patch_data(data, write=write)
    date_str = datetime.now().strftime('%Y-%m-%d')

    print(f'可插入模型: {len(inserted)} 个')
    for sec_id, model_id in inserted:
        print(f'  [{sec_id}] {model_id}')
    if skipped:
        print(f'\n已存在/跳过: {len(skipped)} 个')
        for m in skipped:
            print(f'  - {m}')
    print(f'\n更新后 Z.ai 收录模型数: {model_count}')

    if write:
        save_json(DATA_JSON, data)
        diff_path = write_diff(date_str, inserted, skipped, model_count, old_count)
        print(f'\n已写入: {DATA_JSON}')
        print(f'变更记录：{diff_path}')
    else:
        print(f'\n预览模式，未写入。使用 --write 应用变更。')


if __name__ == '__main__':
    main()
