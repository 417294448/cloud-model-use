"""【智谱 Z.ai 专用】根据抓取到的官方文档自动对比并更新 data/zai.json。

用法:
    # 先抓取再生成差异报告（不修改数据）
    python scripts/zai/update_data.py --fetch -o _g_zai/diff.md

    # 使用已抓取的文本生成差异报告
    python scripts/zai/update_data.py -o _g_zai/diff.md

    # 抓取、对比并自动应用可安全同步的字段（上下文/最大输出/价格说明）
    python scripts/zai/update_data.py --fetch --apply

说明:
    - 自动同步字段：上下文(ctx)、最大输出(output)、价格说明(price raw)
    - 不自动修改：新增/删除模型、定位(tier)、推理/速度档位、模态列表、页面结构
    - 每次 --apply 会自动备份 data/zai.json 为 data/zai.json.bak.YYYYMMDD_HHMMSS
    - 同步后会自动更新 references/providers/zai.md 中的同步日期
"""
import re, json, sys, os, shutil, subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]  # .claude/skills/model-guide/scripts/zai -> project root
DATA_JSON = ROOT / '.claude' / 'skills' / 'model-guide' / 'data' / 'zai.json'
PROVIDER_MD = ROOT / '.claude' / 'skills' / 'model-guide' / 'references' / 'providers' / 'zai.md'
DIFF_DIR = ROOT / 'diff'
WORK_DIR = ROOT / '_g_zai'
OVERVIEW_TXT = WORK_DIR / 'overview.txt'
PRICING_TXT = WORK_DIR / 'pricing.txt'


def normalize_model_id(name):
    """统一模型名中的换行与多余空格"""
    return re.sub(r'\s+', ' ', name.strip())


MODEL_ID_RE = re.compile(r'^(GLM|CogView|CogVideoX|Vidu|Embedding|CharGLM|Emohaa|CodeGeeX|Rerank|AutoGLM|Search)[\w\.\-/]*$', re.I)


def looks_like_model_id(name):
    """判断是否像模型 ID（排除阶梯价格行、中文说明、表头、工具服务等）"""
    if not name:
        return False
    name = name.strip()
    if name in ('模型', '模型名称', 'Model', 'model', '-'):
        return False
    # 排除纯中文
    if re.match(r'^[\u4e00-\u9fff\s]+$', name):
        return False
    # 排除常见非模型文本
    if re.match(r'^(输入长度|输出长度|产品名称|工具名称|模型微调|增购|专业版|团队版)', name):
        return False
    # 排除搜索工具与知识库扩容服务
    if name.lower().startswith('search-') or name.lower() == 'knowledge_capacity':
        return False
    # 以已知前缀开头，或全为模型常见字符
    if MODEL_ID_RE.match(name):
        return True
    if re.match(r'^[A-Z][A-Za-z0-9\.\-_]+$', name):
        return True
    return False


def parse_rows(text):
    """从结构化文本中提取所有 ROW: 行，支持跨行单元格合并"""
    rows = []
    current = None
    for line in text.splitlines():
        line = line.rstrip()
        if line.startswith('ROW:'):
            if current is not None:
                rows.append(current)
            current = [c.strip() for c in line[4:].split('|')]
        elif current is not None and line and not line.startswith('H'):
            # 续行：按 | 分割后追加到当前行
            cells = [c.strip() for c in line.split('|')]
            current.extend(cells)
    if current is not None:
        rows.append(current)
    return rows


def is_row_continuation(line):
    """判断一行是否可能是表格 ROW 的续行（排除章节说明文字与页脚导航）"""
    if '|' in line:
        return True
    # 全中文/标点的整行视为说明文字
    if re.match(r'^[\u4e00-\u9fff\s\uff00-\uffef，。、；：？！“”‘’（）【】《》—\-]+$', line):
        return False
    # 页脚、导航、反馈组件等非表格内容
    footer_tokens = ('Powered by', 'Mintlify', 'Was this page helpful', 'page helpful',
                     'Skip to main content', 'Search...', 'Navigation', 'Copy page')
    low = line.lower()
    for tok in footer_tokens:
        if tok.lower() in low:
            return False
    # 单独的 Yes/No/平台介绍 等反馈/导航按钮
    if re.match(r'^(Yes|No|平台介绍|快速开始|API 文档|场景示例|编码套餐|更新日志|条款与协议|常见问题)$', line.strip()):
        return False
    return True


def parse_overview(path):
    """解析模型概览，返回 {model_id: {'ctx': str, 'output': str, 'desc': str}}

    按 H 标题分段，每段内解析表格 ROW；表格结构：
    模型 | 特点（可能跨多列）| 上下文 | 最大输出
    因此从右往左取最后两个单元格作为 ctx/output，中间合并为描述。
    """
    text = open(path, encoding='utf-8').read()
    # 按 H 标题分段，避免上一段表格行合并到下一段说明文字
    segments = re.split(r'\n(?=H[1-6]:)', text)
    result = {}
    for seg in segments:
        lines = seg.splitlines()
        rows = []
        current = None
        for line in lines:
            line = line.rstrip()
            if line.startswith('ROW:'):
                if current is not None:
                    rows.append(current)
                current = [c.strip() for c in line[4:].split('|')]
            elif current is not None and line and not line.startswith('H'):
                # 过滤跨段落的说明文字，防止合并到上一表格行
                if not is_row_continuation(line):
                    continue
                cells = [c.strip() for c in line.split('|')]
                current.extend(cells)
        if current is not None:
            rows.append(current)
        for cells in rows:
            if len(cells) < 4:
                continue
            name = normalize_model_id(cells[0])
            if name.lower() in ('模型', 'model'):
                continue
            # 过滤明显不是模型 ID 的导航/说明行
            if not looks_like_model_id(name) and not re.match(r'^[A-Z][A-Za-z0-9\.\-_]+$', name):
                continue
            ctx = cells[-2] if len(cells) >= 2 else None
            out = cells[-1] if len(cells) >= 1 else None
            desc = ' '.join(cells[1:-2]) if len(cells) > 3 else (cells[1] if len(cells) > 1 else '')
            result[name] = {
                'ctx': ctx if ctx and ctx != '-' else None,
                'output': out if out and out != '-' else None,
                'desc': desc,
            }
    return result


def section_from_heading(line):
    """根据 H3 标题识别 pricing 区段"""
    if '旗舰模型' in line:
        return 'frontier'
    if '模型推理' in line:
        return 'text'  # 模型推理区默认从文本模型开始
    if '文本模型' in line:
        return 'text'
    if '视觉理解' in line:
        return 'vision'
    if '多模态生成' in line:
        return 'image_video'
    if '语音模型' in line or '实时' in line:
        return 'audio'
    if '向量模型' in line:
        return 'embedding'
    if '更多模型' in line:
        return 'more'
    if '历史模型' in line:
        return 'historical'
    if '搜索工具服务' in line or '知识库扩容服务' in line:
        return 'tools'
    return None


def infer_section_from_header(cells, current_section):
    """根据表格表头推断模型所属分类"""
    header = ' | '.join(cells)
    if '分辨率' in header:
        return 'image_video'
    if '多模态支持' in header:
        return 'audio'
    if '训练版本' in header or '部署版本' in header or '私有实例' in header:
        return 'private'
    if '上下文' in header and '单价' in header:
            if current_section == 'historical' or '历史' in header:
                return 'historical'
            if current_section == 'more':
                return 'more'
            if current_section == 'embedding':
                return 'embedding'
            # 模型推理区默认文本模型
            return current_section or 'text'
    return current_section


def parse_pricing(path):
    """解析产品价格，返回 {model_id: {'section': str, 'ctx': str, 'input': str, 'output': str, 'unit': str, 'modality': str, 'desc': str}}"""
    text = open(path, encoding='utf-8').read()
    result = {}
    section = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith('H3:'):
            sec = section_from_heading(line)
            if sec:
                section = sec
            continue
        if not line.startswith('ROW:'):
            continue
        cells = [c.strip() for c in line[4:].split('|')]
        if not cells:
            continue
        head = normalize_model_id(cells[0]).lower()
        # 表头行：根据表头细化当前区段
        if head in ('模型名称', '模型', 'model', '工具名称', '产品名称'):
            section = infer_section_from_header(cells, section)
            continue
        # 跳过工具服务、私有实例等非公共 API 模型区域
        if section in ('tools', 'private'):
            continue
        name = normalize_model_id(cells[0])
        if not looks_like_model_id(name):
            continue
        info = {'section': section, 'ctx': None, 'input': None, 'output': None, 'unit': None, 'modality': None, 'desc': None}
        # 旗舰模型区：模型名称 | 上下文 | 输入单价 | 输出单价 | 缓存存储 | 缓存命中 | 输入模态
        if len(cells) >= 7:
            info['ctx'] = cells[1] if cells[1] else None
            info['input'] = cells[2] if cells[2] else None
            info['output'] = cells[3] if cells[3] else None
            info['modality'] = cells[6] if cells[6] else None
        # 文本/视觉/向量/更多/历史：模型 | 简介 | 上下文 | 单价 | Batch API 定价
        elif len(cells) == 5:
            info['desc'] = cells[1] if cells[1] else None
            info['ctx'] = cells[2] if cells[2] else None
            info['input'] = cells[3] if cells[3] else None
        # 语音模型：模型 | 简介 | 单价 | 多模态支持
        elif len(cells) == 4:
            info['desc'] = cells[1] if cells[1] else None
            info['input'] = cells[2] if cells[2] else None
            info['modality'] = cells[3] if cells[3] else None
        # 历史模型 4 列也走上面逻辑
        result[name] = info
    return result


def extract_price_from_desc(desc):
    """从说明文字中提取价格信息"""
    if not desc:
        return None
    # 匹配 ¥x/单位、x元/单位 等
    m = re.search(r'(¥[\d.]+\s*/\s*[^\s，,；;]+)', desc)
    if m:
        return m.group(1)
    m = re.search(r'([\d.]+\s*元\s*/\s*[^\s，,；;]+)', desc)
    if m:
        return m.group(1)
    return None


def ctx_to_value(ctx):
    """将上下文字符串转换为 zai.json 中的 ctx 值格式。

    对 OCR/图像/视频/语音等非 token 长度的描述性上下文返回 None，
    避免把"单图 ≤10 MB / 最大 100 页"这类说明误判为上下文长度。
    """
    if not ctx:
        return None
    ctx = ctx.strip()
    if ctx in ('-', '—', ''):
        return None
    # 非标准上下文描述（文件大小、页数、时长、字符、请求次数等）
    if re.search(r'(MB|KB|页|输入[:：]|图片|图像|视频|音频|秒|分钟|次|字符|tokens?\s*/\s*秒)', ctx, re.I):
        return None
    hi = ctx.upper() in ('1M', '10M')
    return {'v': ctx, 'hi': hi} if hi else ctx


def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def iter_models(data):
    """遍历 zai.json 中真实模型所在表行，yield (section_id, row_index, row)"""
    model_sections = {'frontier', 'text', 'vision', 'image', 'video', 'audio', 'embed', 'historical'}
    for sec in data.get('sections', []):
        if sec.get('kind') != 'table' or sec['id'] not in model_sections:
            continue
        for idx, row in enumerate(sec.get('rows', [])):
            yield sec['id'], idx, row


def get_model_id(row):
    """从 row 中提取模型 ID"""
    first = row[0] if row else None
    if isinstance(first, dict):
        return first.get('id')
    return first


def infer_section_from_model_id(model_id, pricing_section=None):
    """根据模型 ID 与 pricing 区段推断应归属的 zai.json section"""
    name = model_id.lower()
    # 搜索工具与知识库服务不属于模型
    if name.startswith('search-') or name == 'knowledge_capacity':
        return None
    # 根据模型名推断比 pricing_section 更可靠
    if name.startswith('cogview'):
        return 'image'
    if name.startswith('cogvideox') or name.startswith('vidu'):
        return 'video'
    if name in ('glm-tts', 'glm-tts-clone', 'glm-asr-2512', 'glm-4-voice', 'glm-realtime-flash', 'glm-realtime-air'):
        return 'audio'
    if name.startswith('embedding') or name in ('rerank', 'codegeex-4', 'charglm-4', 'emohaa'):
        return 'embed'
    if name.startswith('glm-4v') or name == 'glm-4v':
        return 'vision'
    if name in ('glm-4-0520', 'glm-4'):
        return 'historical'
    # pricing_section 兜底映射
    if pricing_section:
        mapping = {
            'frontier': 'frontier',
            'text': 'text',
            'vision': 'vision',
            'image_video': 'image',
            'audio': 'audio',
            'embedding': 'embed',
            'more': 'embed',
            'historical': 'historical',
        }
        if pricing_section in mapping:
            return mapping[pricing_section]
    return 'text'


SECTION_SCHEMA = {
    'frontier': {
        'columns': ["模型 ID", "定位", "价格", "模态", "推理", "速度", "上下文", "输入", "输出", "说明"],
        'row_types': ["model_id", "tier", "price", "mods", "reasoning", "speed", "ctx", "ctx", "ctx", "mdesc"],
    },
    'text': {
        'columns': ["模型 ID", "定位", "价格", "模态", "推理", "速度", "上下文", "输入", "输出", "说明"],
        'row_types': ["model_id", "tier", "price", "mods", "reasoning", "speed", "ctx", "ctx", "ctx", "mdesc"],
    },
    'vision': {
        'columns': ["模型 ID", "定位", "价格", "模态", "推理", "速度", "上下文", "输入", "输出", "说明"],
        'row_types': ["model_id", "tier", "price", "mods", "reasoning", "speed", "ctx", "ctx", "ctx", "mdesc"],
    },
    'image': {
        'columns': ["模型 ID", "定位", "价格", "模态", "说明"],
        'row_types': ["model_id", "tier", "price", "mods", "mdesc"],
    },
    'video': {
        'columns': ["模型 ID", "定位", "价格", "模态", "说明"],
        'row_types': ["model_id", "tier", "price", "mods", "mdesc"],
    },
    'audio': {
        'columns': ["模型 ID", "定位", "价格", "模态", "说明"],
        'row_types': ["model_id", "tier", "price", "mods", "mdesc"],
    },
    'embed': {
        'columns': ["模型 ID", "定位", "价格", "模态", "上下文", "输出", "说明"],
        'row_types': ["model_id", "tier", "price", "mods", "ctx", "ctx", "mdesc"],
    },
    'historical': {
        'columns': ["模型 ID", "定位", "价格", "模态", "推理", "速度", "上下文", "输入", "输出", "说明"],
        'row_types': ["model_id", "tier", "price", "mods", "reasoning", "speed", "ctx", "ctx", "ctx", "mdesc"],
    },
}


def infer_price_tier(model_id, input_price, output_price):
    """根据价格字符串推断价格档位 key"""
    def extract_num(s):
        if not s:
            return None
        s = s.replace(' ', '')
        # 提取第一个 ¥ 后的数字
        m = re.search(r'¥\s*(\d+(?:\.\d+)?)', s)
        if m:
            return float(m.group(1))
        m = re.search(r'(\d+(?:\.\d+)?)\s*元', s)
        if m:
            return float(m.group(1))
        return None

    inp = extract_num(input_price) or 0
    out = extract_num(output_price) or 0
    # 免费
    if '免费' in (input_price or '') and '免费' in (output_price or ''):
        return 'cheap'
    # 按次/按分钟/按字符计费的音视频图像模型，归入 mid
    if re.search(r'(次|分钟|字符|万字符)', input_price or ''):
        return 'mid'
    # 按 1M tokens 计价
    max_price = max(inp, out)
    if max_price >= 20:
        return 'sky'
    if max_price >= 8:
        return 'expensive'
    if max_price >= 2:
        return 'high'
    if max_price >= 0.5:
        return 'mid'
    if max_price >= 0.1:
        return 'low'
    return 'cheap'


def infer_modality(model_id, pricing_modality=None):
    """根据模型 ID 与 pricing 模态说明推断 mods 列表"""
    name = model_id.lower()
    mods = []
    if pricing_modality:
        pm = pricing_modality.lower()
        if '文本' in pm or 'text' in pm:
            mods.append('text')
        if '图片' in pm or '图像' in pm or 'image' in pm:
            mods.append('image')
        if '视频' in pm or 'video' in pm:
            mods.append('video')
        if '音频' in pm or 'audio' in pm:
            mods.append('audio')
        if 'pdf' in pm or '文件' in pm:
            mods.append('pdf')
    if not mods:
        # 默认推断
        if name.startswith('cogview') or name == 'glm-image':
            mods = ['text', 'image']
        elif name.startswith('cogvideox') or name.startswith('vidu'):
            mods = ['text', 'image', 'video']
        elif name.startswith('glm-4v') or name == 'glm-4v':
            mods = ['text', 'image']
        elif name in ('glm-tts', 'glm-tts-clone'):
            mods = ['text', 'audio']
        elif name == 'glm-asr-2512':
            mods = ['audio']
        elif name == 'glm-4-voice':
            mods = ['text', 'audio']
        elif name in ('glm-realtime-flash', 'glm-realtime-air'):
            mods = ['text', 'audio', 'video']
        elif name.startswith('codegeex'):
            mods = ['text', 'code']
        else:
            mods = ['text']
    return mods


def infer_reasoning_speed(model_id):
    """根据模型命名推断推理与速度档位"""
    name = model_id.lower()
    reasoning = 3
    speed = 3
    if 'z1' in name or 'thinking' in name:
        reasoning = 4
    if 'flashx' in name:
        speed = 5
        if reasoning > 3:
            reasoning = 3
    elif 'flash' in name:
        speed = 5
        if reasoning > 3:
            reasoning = 3
    elif 'airx' in name:
        speed = 4
    elif 'turbo' in name:
        speed = 4
    elif 'plus' in name and '4v-plus' not in name:
        reasoning = max(reasoning, 4)
    return reasoning, speed


def infer_ctx_output(model_id, ctx_str):
    """根据上下文字符串推断 ctx / input / output 值"""
    ctx = ctx_to_value(ctx_str) if ctx_str else None
    if ctx is None:
        # 默认上下文
        if 'airx' in model_id.lower():
            ctx = '8K'
        elif 'long' in model_id.lower():
            ctx = {'v': '1M', 'hi': True}
        else:
            ctx = '128K'
    inp = ctx
    out = ctx
    # Flash 系列通常输出较短
    if 'flash' in model_id.lower() and not ctx_str:
        out = '16K'
    return ctx, inp, out


def infer_tier(model_id):
    """根据模型命名推断定位档位"""
    name = model_id.lower()
    if name.startswith('glm-5') or 'plus' in name:
        return 'flagship'
    if 'flash' in name or name.startswith('embedding') or name in ('rerank', 'codegeex-4'):
        return 'budget'
    if 'air' in name:
        return 'balanced'
    return 'balanced'


def infer_fields(model_id, pricing_info):
    """为新模型推断完整的 zai.json 行数据；若模型不应纳入指南（如搜索工具），返回 (None, None, None)"""
    section = infer_section_from_model_id(model_id, pricing_info.get('section'))
    if section is None:
        return None, None, None
    schema = SECTION_SCHEMA[section]
    row_types = schema['row_types']
    price = infer_price_tier(model_id, pricing_info.get('input'), pricing_info.get('output'))
    mods = infer_modality(model_id, pricing_info.get('modality'))
    reasoning, speed = infer_reasoning_speed(model_id)
    ctx, inp, out = infer_ctx_output(model_id, pricing_info.get('ctx'))
    tier = infer_tier(model_id)
    desc = pricing_info.get('desc') or ''

    if section in ('image', 'video', 'audio'):
        # 价格列使用 raw 展示具体计费单位
        price_raw = pricing_info.get('input') or price
        if price_raw and price_raw != price:
            price = {'raw': f'<span class="mono-dim">{price_raw}</span>'}
        row = [model_id, tier, price, mods, desc]
    elif section == 'embed':
        row = [model_id, tier, price, mods, ctx, out, desc]
    else:
        row = [model_id, tier, price, mods, reasoning, speed, ctx, inp, out, desc]
    return section, row_types, row


def get_ctx_index(row_types):
    """根据 row_types 返回上下文和输出列的索引。

    row_types 中可能有 2~3 个 'ctx'：
    - 2 个：第 1 个是上下文，最后 1 个是输出
    - 3 个：第 1 个是上下文，中间是输入，最后 1 个是输出
    因此输出列取最后一个 'ctx' 的索引。
    """
    ctx_idx = None
    out_idx = None
    for i, t in enumerate(row_types):
        if t == 'ctx':
            if ctx_idx is None:
                ctx_idx = i
            out_idx = i
    return ctx_idx, out_idx


def compare(data, overview, pricing):
    """对比抓取结果与现有 zai.json，返回变更列表"""
    changes = []
    seen = set()
    for sec_id, idx, row in iter_models(data):
        model_id = get_model_id(row)
        if not model_id:
            continue
        seen.add(model_id)
        ov = overview.get(model_id, {})
        pr = pricing.get(model_id, {})
        if not ov and not pr:
            changes.append({
                'type': 'missing_in_source',
                'model': model_id,
                'section': sec_id,
                'message': '在官方文档（overview/pricing）中均未找到，可能已下架'
            })
            continue
        row_types = None
        for sec in data['sections']:
            if sec['id'] == sec_id:
                row_types = sec.get('row_types', [])
                break
        ctx_idx, out_idx = get_ctx_index(row_types)
        # 上下文变更：仅当解析出有效值时才同步，避免用 None 覆盖现有值
        if ctx_idx is not None and ov.get('ctx'):
            new_ctx = ctx_to_value(ov['ctx'])
            old_ctx = row[ctx_idx]
            if new_ctx is not None and json.dumps(new_ctx, ensure_ascii=False, sort_keys=True) != json.dumps(old_ctx, ensure_ascii=False, sort_keys=True):
                changes.append({
                    'type': 'ctx',
                    'model': model_id,
                    'section': sec_id,
                    'row': idx,
                    'index': ctx_idx,
                    'old': old_ctx,
                    'new': new_ctx,
                })
        # 最大输出变更
        if out_idx is not None and ov.get('output'):
            new_out = ctx_to_value(ov['output'])
            old_out = row[out_idx]
            if new_out is not None and json.dumps(new_out, ensure_ascii=False, sort_keys=True) != json.dumps(old_out, ensure_ascii=False, sort_keys=True):
                changes.append({
                    'type': 'output',
                    'model': model_id,
                    'section': sec_id,
                    'row': idx,
                    'index': out_idx,
                    'old': old_out,
                    'new': new_out,
                })
        # 价格变更：仅更新说明中的价格描述（raw 字段）
        if pr.get('input'):
            price_idx = None
            for i, t in enumerate(row_types):
                if t == 'price':
                    price_idx = i
                    break
            if price_idx is not None:
                old_price = row[price_idx]
                new_price_raw = f'<span class="mono-dim">{pr["input"]}' + (f' / 输出 {pr["output"]}' if pr.get('output') else '') + '</span>'
                # 如果旧的是字符串档位或 raw，我们不自动替换档位，只在说明中追加价格提示
                # 这里改为：如果说明中已包含价格，更新说明中的价格片段
                pass
    # 新增模型：按 pricing 信息推断完整行，方便人工复核或直接插入
    for model_id in set(overview.keys()) | set(pricing.keys()):
        if model_id not in seen:
            pr = pricing.get(model_id, {})
            try:
                suggested_section, suggested_row_types, suggested_row = infer_fields(model_id, pr)
            except Exception as e:
                suggested_section, suggested_row_types, suggested_row = None, None, None
            changes.append({
                'type': 'new_model',
                'model': model_id,
                'overview': overview.get(model_id, {}),
                'pricing': pr,
                'suggested_section': suggested_section,
                'suggested_row_types': suggested_row_types,
                'suggested_row': suggested_row,
                'message': '官方文档中有，但 zai.json 中未收录，需人工判断分类与档位'
            })
    return changes


def apply_changes(data, changes):
    """将变更应用到 zai.json"""
    applied = []
    for ch in changes:
        if ch['type'] == 'ctx':
            for sec in data['sections']:
                if sec['id'] == ch['section']:
                    sec['rows'][ch['row']][ch['index']] = ch['new']
                    applied.append(ch)
                    break
        elif ch['type'] == 'output':
            for sec in data['sections']:
                if sec['id'] == ch['section']:
                    sec['rows'][ch['row']][ch['index']] = ch['new']
                    applied.append(ch)
                    break
    return applied


def _format_diff_body(changes, applied=False):
    """生成差异报告正文（不含顶层标题）：只体现模型数据变更"""
    lines = []
    if applied:
        lines.append('状态：已应用 --apply\n')
    else:
        lines.append('状态：仅生成报告，未修改数据\n')
    lines.append('\n### 模型数据变更\n')
    for ch in changes:
        if ch['type'] == 'new_model':
            sec = ch.get('suggested_section') or '?'
            lines.append(f"- 新增 {ch['model']}（{sec}）\n")
        elif ch['type'] == 'ctx':
            lines.append(f"- 变更 {ch['model']} 上下文：{ch['old']} → {ch['new']}\n")
        elif ch['type'] == 'output':
            lines.append(f"- 变更 {ch['model']} 最大输出：{ch['old']} → {ch['new']}\n")
        elif ch['type'] == 'missing_in_source':
            lines.append(f"- 可能下架 {ch['model']}（{ch['section']}）\n")
    return lines


def write_diff_report(changes, path, applied=False):
    """生成独立的 Z.ai 差异报告（保留 -o 覆盖用途）"""
    lines = ['# Z.ai 数据核对报告\n', f'生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n']
    lines.extend(_format_diff_body(changes, applied))
    open(path, 'w', encoding='utf-8').writelines(lines)


def write_daily_diff(changes, provider='Z.ai', applied=False, diff_path=None):
    """将本次变更追加到 diff/YYYY-MM-DD.md；同一天多提供商会按 ## 提供商 分节记录"""
    date_str = datetime.now().strftime('%Y-%m-%d')
    if diff_path is None:
        DIFF_DIR.mkdir(exist_ok=True)
        diff_path = DIFF_DIR / f'{date_str}.md'

    body = _format_diff_body(changes, applied)
    section_lines = [f'## {provider}\n', '\n'] + body
    section_text = ''.join(section_lines)

    if diff_path.exists():
        content = open(diff_path, encoding='utf-8').read()
        if any(line.strip() == f'## {provider}' for line in content.splitlines()):
            print(f'警告: {diff_path} 中已存在 {provider} 记录，未重复写入')
            return diff_path
        content = content.rstrip() + '\n\n' + section_text
    else:
        content = f'# {date_str} 模型指南更新记录\n\n' + section_text

    open(diff_path, 'w', encoding='utf-8').write(content)
    return diff_path


def update_provider_doc(date_str):
    """更新 providers/zai.md 中的同步日期与修正记录"""
    if not PROVIDER_MD.exists():
        return
    text = open(PROVIDER_MD, encoding='utf-8').read()
    # 更新 hero_desc / footer_sources 风格的同步日期
    text = re.sub(r'（\d{4}-\d{2}-\d{2} 同步）', f'（{date_str} 同步）', text)
    # 在修正记录表末尾追加自动同步记录（同一天只追加一次）
    new_line = f"| {date_str} | 自动同步上下文/最大输出/价格字段 | update_data.py |"
    if new_line in text:
        open(PROVIDER_MD, 'w', encoding='utf-8').write(text)
        return
    if '| 时间 | 修正内容 | 依据 |' in text:
        lines = text.splitlines()
        insert_idx = len(lines)
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].startswith('| 20'):
                insert_idx = i + 1
                break
        lines.insert(insert_idx, new_line)
        text = '\n'.join(lines) + '\n'
    open(PROVIDER_MD, 'w', encoding='utf-8').write(text)


def update_meta_dates(data, date_str):
    """更新 zai.json 中的日期字段"""
    data['meta']['footer_updated'] = date_str
    data['meta']['hero_desc'] = re.sub(r'（\d{4}-\d{2}-\d{2} 同步）', f'（{date_str} 同步）', data['meta']['hero_desc'])
    data['meta']['footer_sources'] = re.sub(r'（\d{4}-\d{2}-\d{2} 同步）', f'（{date_str} 同步）', data['meta']['footer_sources'])


def main():
    args = sys.argv[1:]
    do_fetch = '--fetch' in args
    do_apply = '--apply' in args
    out_report = None
    if '-o' in args:
        out_report = args[args.index('-o') + 1]

    if do_fetch:
        WORK_DIR.mkdir(exist_ok=True)
        subprocess.run([sys.executable, str(ROOT / '.claude' / 'skills' / 'model-guide' / 'scripts' / 'zai' / 'fetch_docs.py'),
                        'overview', 'pricing', '-o', str(WORK_DIR)], check=False)

    if not OVERVIEW_TXT.exists() or not PRICING_TXT.exists():
        raise SystemExit(f'找不到抓取文件：{OVERVIEW_TXT} 或 {PRICING_TXT}，请先运行 --fetch')

    overview = parse_overview(OVERVIEW_TXT)
    pricing = parse_pricing(PRICING_TXT)
    data = load_json(DATA_JSON)
    changes = compare(data, overview, pricing)

    date_str = datetime.now().strftime('%Y-%m-%d')

    if do_apply:
        applied = apply_changes(data, changes)
        backup = DATA_JSON.with_suffix(f'.json.bak.{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        shutil.copy2(DATA_JSON, backup)
        update_meta_dates(data, date_str)
        save_json(DATA_JSON, data)
        update_provider_doc(date_str)
        print(f'已应用 {len(applied)} 条 ctx/output 变更，备份：{backup}', flush=True)
    else:
        print(f'发现 {len(changes)} 条差异，未应用。使用 --apply 应用。', flush=True)

    # 默认将差异报告追加到 diff/YYYY-MM-DD.md（所有提供商共用一个日期文件）
    if not out_report:
        diff_path = write_daily_diff(changes, provider='Z.ai', applied=do_apply)
        print(f'差异报告：{diff_path}', flush=True)
    else:
        write_diff_report(changes, out_report, applied=do_apply)
        print(f'差异报告：{out_report}', flush=True)


if __name__ == '__main__':
    main()
