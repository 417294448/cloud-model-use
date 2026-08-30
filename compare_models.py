import json
from collections import OrderedDict, defaultdict

json_path = r'd:\xiaohongshu\cloud-model-use\.claude\skills\model-guide\data\zai.json'
with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 1. 提取 useguide 模型 ID
useguide_by_section = OrderedDict()
for sec in data.get('sections', []):
    sid = sec.get('id', 'unknown')
    sec_models = []
    for row in sec.get('rows', []):
        if not row:
            continue
        first = row[0]
        if isinstance(first, dict):
            model_id = first.get('id')
        elif isinstance(first, str):
            model_id = first
        else:
            continue
        if model_id:
            sec_models.append(model_id)
    if sec_models:
        useguide_by_section[sid] = sec_models

useguide_models = []
for sec_models in useguide_by_section.values():
    useguide_models.extend(sec_models)
useguide_set = set(useguide_models)

# 2. 构建 pricing 模型集合
pricing_modules = {
    "旗舰模型": [
        "GLM-5.3", "GLM-5.3-Flash", "GLM-5.2", "GLM-5.1", "GLM-5V-Turbo",
        "GLM-5-Turbo", "GLM-5", "GLM-4.7", "GLM-4.6V", "GLM-4.5-Air",
        "GLM-4.7-FlashX", "GLM-4.7-Flash", "GLM-4.6V-FlashX", "GLM-4.6V-Flash", "GLM-4.5V"
    ],
    "文本模型": [
        "GLM-4-Plus", "GLM-4-Air-250414", "GLM-4-AirX", "GLM-4-Long", "GLM-4-Assistant",
        "GLM-Z1-Air", "GLM-Z1-AirX", "GLM-Z1-FlashX", "GLM-4-FlashX-250414", "GLM-4-Flash-250414",
        "GLM-Z1-Flash", "GLM-4.5", "GLM-4.5-Air", "GLM-4-Air", "GLM-4-Flash",
        "GLM-4-9B", "ChatGLM3-6B", "Cogview-3", "GLM-4V", "GLM-4.6",
        "GLM-4-0520", "CogView-3"
    ],
    "视觉理解": [
        "GLM-OCR", "GLM-4V-Plus-0111", "GLM-4V-Flash", "GLM-4.1V-Thinking-FlashX", "GLM-4.1V-Thinking-Flash"
    ],
    "多模态生成": [
        "GLM-Image", "CogVideoX-3", "CogView-4", "CogVideoX-2", "ViduQ1-Text",
        "ViduQ1-Image", "ViduQ1-Start-End", "Vidu2-Image", "Vidu2-Start-End", "Vidu2-Reference",
        "CogView-3-Flash", "CogVideoX-Flash"
    ],
    "语音模型": [
        "GLM-TTS", "GLM-TTS-Clone", "GLM-ASR-2512", "GLM-4-Voice", "GLM-Realtime-Flash", "GLM-Realtime-Air"
    ],
    "向量模型": ["Embedding-3", "Embedding-2"],
    "更多模型": ["CharGLM-4", "Emohaa", "CodeGeeX-4", "Rerank"],
    "历史模型": [
        "GLM-4-0520", "GLM-4V-Plus", "GLM-4V", "GLM-4", "GLM-4-Air", "GLM-4-Flash"
    ],
}

# 标准化名称：统一 Cogview-3 / CogView-3 等大小写差异
def normalize(name):
    # 将 Cogview-3 统一视为 CogView-3（pricing 中两种写法均出现）
    return name.strip().replace("Cogview", "CogView").replace("COGVIEW", "CogView")

pricing_set = set()
pricing_modules_normalized = OrderedDict()
for mod, models in pricing_modules.items():
    norm_models = [normalize(m) for m in models]
    pricing_modules_normalized[mod] = norm_models
    pricing_set.update(norm_models)

# 处理大小写差异：将 useguide 中的 Cogview-3 视为 CogView-3（统一使用 pricing 中更常见的 CogView-3）
# 这里构建一个从标准化名到原名的映射
normalized_to_useguide = {}
for m in useguide_set:
    nm = normalize(m)
    normalized_to_useguide.setdefault(nm, m)

# 标准化后的 useguide 集合
useguide_set_normalized = set(normalize(m) for m in useguide_models)

# 3. 缺失：在 pricing 中但不在 useguide 中
missing = pricing_set - useguide_set_normalized
# 4. 多余：在 useguide 中但不在 pricing 中
extra = useguide_set_normalized - pricing_set

# naming section 是命名规则，不是真实模型 ID
naming_models = set(normalize(m) for m in useguide_by_section.get('naming', []))
extra_real_models = extra - naming_models
extra_naming_rules = extra & naming_models

# 5. 按模块分类缺失（模块内也去重）
missing_by_module = OrderedDict()
seen_for_module = set()
for mod, models in pricing_modules_normalized.items():
    mod_list = []
    for m in models:
        if m in missing and m not in seen_for_module:
            mod_list.append(m)
            seen_for_module.add(m)
    if mod_list:
        missing_by_module[mod] = mod_list

# 自定义分类说明
def classify(name):
    if name in ["GLM-4-0520", "GLM-4V-Plus", "GLM-4V", "GLM-4", "GLM-4-Air", "GLM-4-Flash"]:
        return "历史模型"
    if name.startswith("GLM-Z1-"):
        return "Z1 系列（推理/Thinking）"
    if name.startswith("GLM-4.1V-Thinking"):
        return "视觉推理模型"
    if name.startswith("GLM-4.") or name.startswith("GLM-4-") or name in ["GLM-4V", "GLM-4", "GLM-4-Air", "GLM-4-Flash"]:
        return "GLM-4 基础/进阶系列"
    if name.startswith("CogView") or name.startswith("CogVideoX") or name.startswith("Vidu"):
        return "图像/视频生成模型"
    if name.startswith("GLM-Realtime") or name.startswith("GLM-TTS") or name.startswith("GLM-ASR") or name == "GLM-4-Voice":
        return "语音模型"
    if name.startswith("Embedding"):
        return "向量模型"
    if name in ["CharGLM-4", "Emohaa", "CodeGeeX-4", "Rerank"]:
        return "更多/垂直模型"
    return "其他"

missing_classified = defaultdict(list)
for m in sorted(missing):
    missing_classified[classify(m)].append(m)

print("=" * 60)
print("模型覆盖对比分析结果")
print("=" * 60)
print(f"\npricing 模型总数（去重后）: {len(pricing_set)}")
print(f"useguide 模型总数（去重后）: {len(useguide_set)}")
print(f"useguide 各 section 收录数（含重复）: {len(useguide_models)}")
print(f"\n缺失模型数量: {len(missing)}")
print(f"多余模型数量（含 naming 规则）: {len(extra)}")
print(f"多余真实模型数量（排除 naming 规则）: {len(extra_real_models)}")

print("\n" + "-" * 60)
print("缺失模型列表（按 pricing 模块分类）")
print("-" * 60)
for mod, models in missing_by_module.items():
    print(f"\n【{mod}】({len(models)} 个):")
    for m in models:
        print(f"  - {m}")

print("\n" + "-" * 60)
print("缺失模型分类说明")
print("-" * 60)
for cat, models in sorted(missing_classified.items()):
    print(f"\n{cat} ({len(models)} 个):")
    for m in models:
        print(f"  - {m}")

print("\n" + "-" * 60)
print("多余真实模型列表（在 useguide 中但不在 pricing 中）")
print("-" * 60)
if extra_real_models:
    for m in sorted(extra_real_models):
        # 还原为 useguide 中的原始写法
        orig = normalized_to_useguide.get(m, m)
        print(f"  - {orig}")
else:
    print("  （无）")

print("\n" + "-" * 60)
print("naming section 中的规则项（非真实模型 ID）")
print("-" * 60)
for m in sorted(extra_naming_rules):
    orig = normalized_to_useguide.get(m, m)
    print(f"  - {orig}")

print("\n" + "-" * 60)
print("useguide 各 section 模型详情")
print("-" * 60)
for sid, models in useguide_by_section.items():
    print(f"\n[{sid}] ({len(models)} 行):")
    for m in models:
        print(f"  - {m}")
