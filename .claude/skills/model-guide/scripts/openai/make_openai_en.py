# -*- coding: utf-8 -*-
"""临时脚本：data/openai.json → data/openai-en.json（英文版）。

翻译策略：语言中立字段（模型 ID、数字、档位 key、模态 key、ctx 数值、URL）
原样保留；编辑字段按 TRANSLATE 精确匹配翻译；漏翻的中文会告警。
生成的是新文件 data/openai-en.json，不改动中文数据源。
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(os.path.dirname(HERE))  # .claude/skills/model-guide
SRC = os.path.join(SKILL_DIR, 'data', 'openai.json')
DST = os.path.join(SKILL_DIR, 'data', 'openai-en.json')

CJK = re.compile(r'[\u4e00-\u9fff]')

# ===== 翻译表（完整枚举 openai.json 中的可译编辑字段）=====
TRANSLATE = {
    # ---- meta ----
    'OpenAI 模型选择指南 2026': 'OpenAI Model Selection Guide 2026',
    'OpenAI 模型选择指南': 'OpenAI Model Selection Guide',
    '78+ 模型全解析 · 多模态能力 · 推理强度 · 上下文窗口 · 价格档位 — 数据来源：<a href="https://platform.openai.com/docs/models" target="_blank" rel="noopener noreferrer">OpenAI 官方文档</a> · <a href="https://learn.microsoft.com/zh-cn/azure/ai-foundry/foundry-models/concepts/models-sold-directly-by-azure" target="_blank" rel="noopener noreferrer">Azure AI Foundry 文档</a> · <a href="https://learn.microsoft.com/en-us/azure/foundry/openai/concepts/model-retirement-schedule" target="_blank" rel="noopener noreferrer">Azure 模型退役计划</a>（2026-08-30 同步）':
        '78+ models · multimodal · reasoning · context window · price tiers — Sources: <a href="https://platform.openai.com/docs/models" target="_blank" rel="noopener noreferrer">OpenAI official docs</a> · <a href="https://learn.microsoft.com/zh-cn/azure/ai-foundry/foundry-models/concepts/models-sold-directly-by-azure" target="_blank" rel="noopener noreferrer">Azure AI Foundry docs</a> · <a href="https://learn.microsoft.com/en-us/azure/foundry/openai/concepts/model-retirement-schedule" target="_blank" rel="noopener noreferrer">Azure model retirement</a> (synced 2026-08-30)',
    '返回模型价格对比工具': 'Back to model comparison tool',
    '对比工具': 'Compare',
    '收录模型': 'Models',
    '模型分类': 'Categories',
    '最大上下文': 'Max context',
    '版本号越大越新 · mini = 省钱 · pro = 增强 · codex = 编程 · nano = 极速 · o 系列 = 推理 · realtime = 实时音频':
        'Higher version = newer · mini = budget · pro = enhanced · codex = coding · nano = fastest · o-series = reasoning · realtime = live audio',
    '数据来源：<a href="https://platform.openai.com/docs/models" target="_blank" rel="noopener noreferrer">OpenAI 官方文档</a> · <a href="https://learn.microsoft.com/zh-cn/azure/ai-foundry/foundry-models/concepts/models-sold-directly-by-azure" target="_blank" rel="noopener noreferrer">Azure AI Foundry 文档</a> · <a href="https://learn.microsoft.com/en-us/azure/foundry/openai/concepts/model-retirement-schedule" target="_blank" rel="noopener noreferrer">Azure 模型退役计划</a>（2026-08-30 同步）':
        'Sources: <a href="https://platform.openai.com/docs/models" target="_blank" rel="noopener noreferrer">OpenAI official docs</a> · <a href="https://learn.microsoft.com/zh-cn/azure/ai-foundry/foundry-models/concepts/models-sold-directly-by-azure" target="_blank" rel="noopener noreferrer">Azure AI Foundry docs</a> · <a href="https://learn.microsoft.com/en-us/azure/foundry/openai/concepts/model-retirement-schedule" target="_blank" rel="noopener noreferrer">Azure model retirement</a> (synced 2026-08-30)',

    # ---- 通用 section 字段 ----
    '快速选型': 'Quick Picks',
    '按任务类型直达推荐模型': 'Direct recommendation by task type',
    '命名规律速查': 'Naming Conventions',
    '掌握这些规律，看到任何模型名都能秒懂其定位': 'Understand these patterns and instantly grasp any model name',
    '命名规律': 'Naming',
    '命名元素': 'Suffix', '含义': 'Meaning', '示例': 'Example',
    'Frontier 前沿模型': 'Frontier Models',
    'OpenAI 最先进的模型，推荐用于大多数任务。GPT-5.6 系列为当前最新一代（2026-07 发布），支持多智能体编排（预览）与计算机使用；其工具调用请通过 <span class="mono">Responses API</span>（Chat Completions 与函数工具不能同时使用，除非 <span class="mono">reasoning_effort=none</span>）':
        "OpenAI's most advanced models, recommended for most tasks. GPT-5.6 is the current generation (released 2026-07), with multi-agent orchestration (preview) and computer use; tool calling must go through the <span class=\"mono\">Responses API</span> (Chat Completions and function tools can't be combined unless <span class=\"mono\">reasoning_effort=none</span>)",
    'Codex 编程模型': 'Codex (Coding)',
    '专为代码生成和编程任务优化，适合 Agentic 工作流，针对 Codex CLI 和 Codex VS Code 扩展优化':
        'Optimized for code generation and coding tasks, ideal for agentic workflows, tuned for Codex CLI and the Codex VS Code extension',
    'o 系列推理模型': 'o-Series Reasoning',
    '专注深度思考和复杂推理，支持可配置推理强度 <span class="mono">reasoning_effort: low/medium/high</span>':
        'Focused on deep thinking and complex reasoning, with configurable reasoning effort <span class="mono">reasoning_effort: low/medium/high</span>',
    'o 系列': 'o-Series',
    '图像 & 视频生成': 'Image & Video Generation',
    '从文本或图像生成高质量视觉内容': 'High-quality visual content from text or images',
    '图像·视频': 'Image·Video',
    '语音 & 音频模型': 'Voice & Audio',
    '语音转文字、文字转语音、实时对话与音频理解。<span class="mono">gpt-realtime-translate</span>、<span class="mono">gpt-realtime-whisper</span>、<span class="mono">gpt-live-transcribe</span> 按使用时长计费，其余实时模型按 token 计费':
        'Speech-to-text, text-to-speech, realtime chat and audio understanding. <span class="mono">gpt-realtime-translate</span>, <span class="mono">gpt-realtime-whisper</span> and <span class="mono">gpt-live-transcribe</span> are billed by duration; other realtime models by token',
    '语音·音频': 'Voice·Audio',
    '开源模型（Apache 2.0）': 'Open-Source (Apache 2.0)',
    '可自行部署，无 API 调用限制，仅需硬件成本': 'Self-hostable, no API call limits, only hardware costs',
    '开源': 'OSS',
    'Embedding & 工具模型': 'Embedding & Tool Models',
    '文本向量化，用于语义搜索、RAG 与推荐系统': 'Text embedding for semantic search, RAG and recommendation systems',
    '计算机操控模型': 'Computer-Use Models',
    '自动化操控计算机，执行鼠标键盘操作，需注册申请访问权限':
        'Automates computer operation (mouse & keyboard); access requires registration',
    '电脑操控': 'Computer Use',
    'GPT-4o 系列（旧版兼容）': 'GPT-4o Series (Legacy)',
    '仍可使用，但新项目建议使用 GPT-4.1 或 GPT-5 系列': 'Still usable, but GPT-4.1 or GPT-5 is recommended for new projects',
    '已弃用与退役计划': 'Deprecated & Retirement',
    '已弃用': 'Deprecated',
    '以下为本页已收录模型中的弃用/退役信息，请按退役日期规划迁移，勿在新项目中使用。生命周期：Deprecated = 已宣布弃用（仍可用，按期退役）；Retired = 已退役（不可用）；Legacy = 旧版（可用，建议迁移）。':
        'Retirement info for the models covered on this page. Plan migrations by retirement date and avoid new projects. Lifecycle: Deprecated = announced retirement (still usable, retires on schedule); Retired = no longer available; Legacy = older version (usable, migration advised).',
    '能力矩阵速查': 'Capability Matrix',
    '根据需求快速匹配最佳模型': 'Match the best model to your needs quickly',
    '能力矩阵': 'Capability Matrix',

    # ---- 通用列头 ----
    '模型 ID': 'Model ID', '定位': 'Tier', '价格': 'Price', '模态': 'Modality',
    '推理': 'Reasoning', '速度': 'Speed', '上下文': 'Context', '输入': 'Input',
    '输出': 'Output', '说明': 'Notes', '类型': 'Type', '特性': 'Features',
    '分辨率': 'Resolution', '参数量': 'Parameters', '硬件需求': 'Hardware',
    '用途': 'Use', '维度': 'Dimensions', '评分': 'Score',
    '需求场景': 'Scenario', '推荐模型': 'Recommended', '备选模型': 'Alternatives',
    '关键能力': 'Key capability', '版本': 'Version', '生命周期': 'Lifecycle',
    '退役日期': 'Retirement', '替代方案': 'Replacement', '迁移建议': 'Migration advice',
    '功能特性': 'Features',

    # ---- quick 卡片任务 ----
    '日常对话 / 写作': 'Chat / Writing',
    '专业编程': 'Coding',
    '图像生成': 'Image generation',
    '视频生成': 'Video generation',
    '实时语音听录': 'Live transcription',
    '文字转语音': 'Text to speech',
    '实时语音对话': 'Realtime voice chat',
    '深度研究 / 复杂推理': 'Deep research / complex reasoning',
    '最强推理': 'Top reasoning',
    '极致省钱': 'Cheapest',
    '超长文档处理': 'Long-document processing',
    '私有化部署': 'Self-hosting',

    # ---- 命名规律表 ----
    '版本号 (4→5→5.6)': 'Version number (4→5→5.6)',
    '数字越大，模型越新越强': 'Higher number = newer and stronger',
    '代号 (-sol/-terra/-luna)': 'Codename (-sol/-terra/-luna)',
    '同代模型的变体代号（如 GPT-5.6 系列）': 'Variant codename within the same generation (e.g. GPT-5.6 family)',
    '中等规模，平衡性能与成本': 'Mid-size, balanced performance and cost',
    '最小规模，极致省钱快速': 'Smallest, cheapest and fastest',
    '增强版，更多算力更精准': 'Enhanced, more compute and accuracy',
    '编程专用，代码能力强化': 'Coding-specialized',
    '长任务优化版': 'Optimized for long tasks',
    '速度优化版本': 'Speed-optimized version',
    '高清 / 高质量版本': 'HD / high-quality version',
    '开源版，XX = 参数量（十亿）': 'Open-source, XX = parameters in billions',
    '推理模型系列（深度思考型）': 'Reasoning model family (deep thinking)',
    '深度研究专用，超长推理': 'Deep-research specialized, extra-long reasoning',
    '预览版 / 最新版（自动更新）': 'Preview / latest (auto-updating)',
    '语音转文字 / 文字转语音': 'Speech-to-text / text-to-speech',
    '实时双向音频 / 实时听录': 'Realtime two-way audio / live transcription',

    # ---- frontier / codex / reasoning / legacy mdesc ----
    'GPT-5.6 系列（代号 Sol），支持多智能体编排(预览)': 'GPT-5.6 family (codename Sol), multi-agent orchestration (preview)',
    'GPT-5.6 系列（代号 Terra），支持多智能体编排(预览)': 'GPT-5.6 family (codename Terra), multi-agent orchestration (preview)',
    'GPT-5.6 系列（代号 Luna），支持多智能体编排(预览)': 'GPT-5.6 family (codename Luna), multi-agent orchestration (preview)',
    'GPT-5.6 系列（代号 Cyber），$12.5/$75': 'GPT-5.6 family (codename Cyber), $12.5/$75',
    'gpt-5.6-cyber 别名，攻防研究专用（Daybreak 计划），需单独申请访问':
        'Alias of gpt-5.6-cyber for offensive security research (Daybreak program); separate approval required',
    'gpt-5.6-sol 别名，防御型安全专用（Daybreak 计划），需单独申请访问':
        'Alias of gpt-5.6-sol for defensive security work (Daybreak program); separate approval required',
    '推理增强版，Responses API 专用（含 Batch），无缓存折扣':
        'Enhanced reasoning, Responses API only (incl. Batch); no cached-input discount',
    '已宣布弃用，2026-12-15 退役': 'Deprecated, retires 2026-12-15',
    '持续更新的对话模型（即 GPT-5.5 Instant），固定推理强度不可配置':
        'Continuously updated chat model (i.e. GPT-5.5 Instant); fixed reasoning effort',
    'Responses API 有效预算约 922K token': '~922K token effective budget via Responses API',
    '支持计算机使用，编程和智能代理任务佳选': 'Supports computer use; great for coding and agent tasks',
    '推理增强版，Responses API 专用，无上限算力': 'Enhanced reasoning, Responses API only, unlimited compute',
    '轻量版，支持计算机使用': 'Lightweight, supports computer use',
    '最快最省钱的 GPT-5.4': 'Fastest, cheapest GPT-5.4',
    '快照已退役（2026-06-29），请换用 <span class="mono-dim">gpt-chat-latest</span>':
        'Snapshot retired (2026-06-29); use <span class="mono-dim">gpt-chat-latest</span> instead',
    '上一代旗舰，稳定可靠': 'Previous flagship, stable and reliable',
    '快照已退役，请换用 <span class="mono-dim">gpt-chat-latest</span>':
        'Snapshot retired; use <span class="mono-dim">gpt-chat-latest</span> instead',
    'GPT-5.2 推理增强版，无上限算力': 'GPT-5.2 with enhanced reasoning, unlimited compute',
    '<span class="mono-dim">reasoning_effort</span> 默认 <span class="mono-dim">none</span>，需显式开启推理':
        '<span class="mono-dim">reasoning_effort</span> defaults to <span class="mono-dim">none</span>; reasoning must be enabled explicitly',
    '快照已退役，请换用 <span class="mono-dim">gpt-chat-latest</span>；内置推理，不支持 <span class="mono-dim">temperature</span> 参数':
        'Snapshot retired; use <span class="mono-dim">gpt-chat-latest</span> instead; built-in reasoning, no <span class="mono-dim">temperature</span> support',
    '支持强化微调（RFT，受限开放）': 'Supports reinforcement fine-tuning (RFT, limited rollout)',
    '推理增强版，响应更精准': 'Enhanced reasoning, more accurate responses',
    '更快更省钱，无需注册': 'Faster and cheaper, no registration needed',
    '最快最省钱的 GPT-5，无需注册': 'Fastest, cheapest GPT-5, no registration needed',
    '快照已退役，请换用持续更新的 <span class="mono-dim">gpt-chat-latest</span>':
        'Snapshot retired; use the always-current <span class="mono-dim">gpt-chat-latest</span> instead',
    '最聪明的非推理模型，支持微调': 'Smartest non-reasoning model, fine-tuning supported',
    '小型快速版，支持微调': 'Small fast version, fine-tuning supported',
    '最快最省钱的 GPT-4.1': 'Fastest, cheapest GPT-4.1',
    '最新 Codex 模型（2026-02），Responses API 专用': 'Latest Codex model (2026-02), Responses API only',
    '最智能编程模型，Codex CLI 优化': 'Most capable coding model, optimized for Codex CLI',
    'Responses API 专用，Codex CLI 优化': 'Responses API only, optimized for Codex CLI',
    '支持 <span class="mono-dim">reasoning_effort=xhigh</span>':
        'Supports <span class="mono-dim">reasoning_effort=xhigh</span>',
    '轻量版 Codex': 'Lightweight Codex',
    '微调版 o4-mini；已宣布弃用，2026-11-15 退役':
        'Fine-tuned o4-mini; deprecated, retires 2026-11-15',
    '最强推理，无上限算力': 'Top reasoning, unlimited compute',
    '最强深度研究，超长推理链（Azure 侧仅经 Foundry 代理服务提供）':
        'Best deep research, extra-long reasoning chains (Azure: via Foundry proxy service only)',
    '更多算力更精准': 'More compute, more accurate',
    '已宣布弃用，2026-10-21 退役，官方推荐 <span class="mono-dim">gpt-5.6-sol</span>':
        'Deprecated, retires 2026-10-21; official recommendation <span class="mono-dim">gpt-5.6-sol</span>',
    '复杂任务推理模型': 'Reasoning model for complex tasks',
    '更快更便宜的深度研究': 'Faster, cheaper deep research',
    '已宣布弃用，2026-10-16 退役': 'Deprecated, retires 2026-10-16',
    '已宣布弃用，2026-10-01 退役，替代 <span class="mono-dim">o4-mini</span>':
        'Deprecated, retires 2026-10-01; replacement <span class="mono-dim">o4-mini</span>',
    '2024-05/08 版本已宣布弃用（2026-10 起退役），迁移 <span class="mono-dim">gpt-5.1</span>':
        '2024-05/08 versions deprecated (retiring from 2026-10); migrate to <span class="mono-dim">gpt-5.1</span>',
    '已宣布弃用，2027-04-14 退役，迁移 <span class="mono-dim">gpt-5-mini</span>':
        'Deprecated, retires 2027-04-14; migrate to <span class="mono-dim">gpt-5-mini</span>',
    '较老的高智能模型': 'Older highly capable model',
    '经典高智能模型': 'Classic highly capable model',
    '老版 GPT，能力有限': 'Older GPT with limited capability',

    # ---- media ----
    '最高 4K': 'up to 4K',
    '最高 2K': 'up to 2K',
    '最高 1K': 'up to 1K',
    '最高 4K 60fps': 'up to 4K 60fps',
    '最高 1080p': 'up to 1080p',
    '最新一代图像生成模型': 'Latest-generation image model',
    '最先进的图像生成模型': 'Most advanced image model',
    '上一代图像生成': 'Previous-generation image model',
    '性价比图像生成': 'Budget image model',
    '最先进视频生成，同步音频': 'Most advanced video model, with synchronized audio',
    '旗舰视频生成': 'Flagship video generation',
    '旧版视频生成（官方已标 Legacy），仍可用': 'Legacy video model (officially marked Legacy); still usable',

    # ---- audio flow / plain / mdesc ----
    '实时听录': 'Live transcription',
    '实时翻译': 'Realtime translation',
    '语音转文字': 'Speech to text',
    '实时对话': 'Realtime chat',
    '音频理解': 'Audio understanding',
    '按时长计费': 'billed by duration',
    '25MB 文件': '25MB files',
    '99 种语言': '99 languages',
    '高精度': 'high accuracy',
    '说话人识别': 'speaker diarization',
    '高质量': 'high quality',
    '低延迟': 'low latency',
    '风格可控': 'controllable style',
    '实时听录场景的当前推荐模型（2026-07）': 'Current recommendation for live transcription (2026-07)',
    '实时低延迟听录（2026-05）': 'Low-latency live transcription (2026-05)',
    '实时多语言翻译，输出译文语音和文本（2026-05）': 'Realtime multilingual translation, outputting translated speech and text (2026-05)',
    '离线文件转写（/v1/audio/transcriptions），支持语言提示':
        'Offline file transcription (/v1/audio/transcriptions), with language hints',
    '通用语音识别，支持翻译': 'General speech recognition, supports translation',
    'GPT-4o 驱动转写': 'GPT-4o-powered transcription',
    '可区分多个说话人': 'Can distinguish multiple speakers',
    '最新实时对话（2026-07），静音和噪声处理改进': 'Latest realtime chat (2026-07), improved silence and noise handling',
    '轻量版实时对话': 'Lightweight realtime chat',
    '第二代实时音频（2026-05）': 'Second-generation realtime audio (2026-05)',
    '实时音频处理（2026-02）': 'Realtime audio processing (2026-02)',
    '首个正式版实时双向音频（2025-08）': 'First GA realtime two-way audio (2025-08)',
    '轻量版实时音频': 'Lightweight realtime audio',
    '最新音频理解模型（2026-02）': 'Latest audio understanding model (2026-02)',
    'Chat Completions 音频支持': 'Audio support via Chat Completions',
    '轻量版音频处理': 'Lightweight audio processing',
    '高保真文字转语音': 'High-fidelity text to speech',
    '速度优先 TTS': 'Speed-first TTS',
    '可引导语音以特定风格或语气说话': 'Can guide the voice with a specific style or tone',

    # ---- oss / embed / computer ----
    '<span class="tag t-green"><svg class="ic"><use href="#i-home"/></svg>自托管</span>':
        '<span class="tag t-green"><svg class="ic"><use href="#i-home"/></svg>Self-hosted</span>',
    '1200 亿': '120B',
    '200 亿': '20B',
    '最强开源模型，需 Foundry 部署': 'Most capable open-source model, requires Foundry deployment',
    '支持托管计算 + Foundry Local': 'Supports hosted compute + Foundry Local',
    '向量化': 'Embed',
    '最强嵌入模型': 'Most capable embedding model',
    '小型嵌入模型': 'Small embedding model',
    '旧版嵌入模型': 'Legacy embedding model',
    '<span class="mono-dim">鼠标 · 键盘 · 截图分析</span>':
        '<span class="mono-dim">Mouse · keyboard · screenshot analysis</span>',

    # ---- deprecated 迁移建议 ----
    '快照版本已退役，换用持续更新别名': 'Snapshot retired; switch to the always-current alias',
    '直接替换，API 兼容': 'Drop-in replacement, API-compatible',
    '最早 4o 版本，尽早迁移': 'Earliest 4o version; migrate early',
    '官方未列替代，可评估 gpt-5.4-mini': 'No official replacement listed; consider gpt-5.4-mini',
    '官方未列替代，可评估 gpt-realtime-2.1-mini': 'No official replacement listed; consider gpt-realtime-2.1-mini',
    '官方推荐替代，推理更强': 'Official recommendation, stronger reasoning',
    '迁移至 gpt-5.1-codex-mini': 'Migrate to gpt-5.1-codex-mini',
    '计划内迁移': 'Planned migration',
    '迁移至 gpt-5-mini 或 gpt-5.4-mini': 'Migrate to gpt-5-mini or gpt-5.4-mini',
    '仍可用，新项目建议 GPT-5.1': 'Still usable; GPT-5.1 recommended for new projects',
    '仍可用，新项目建议 GPT-5.4 系列': 'Still usable; GPT-5.4 family recommended for new projects',
    '仍可用，官方已标记 Legacy，请规划迁移': 'Still usable; officially marked Legacy, plan migration',

    # ---- matrix ----
    '超长文档处理': 'Long-document processing',
    '复杂数学 / 逻辑推理': 'Complex math / logic reasoning',
    'Agentic 编程工作流': 'Agentic coding workflows',
    '多模态理解（图 + 音）': 'Multimodal understanding (image + audio)',
    '实时语音对话': 'Realtime voice chat',
    '实时语音听录': 'Live voice transcription',
    '高质量图像生成': 'High-quality image generation',
    '视频生成': 'Video generation',
    '极致低成本': 'Ultra-low cost',
    '私有化部署': 'Self-hosted deployment',
    '语义搜索 / RAG': 'Semantic search / RAG',
    '极速响应': 'Fastest responses',
    '~100万 token': '~1M tokens',
    '~1.05M 上下文': '~1.05M context',
    '最高 4K 分辨率': 'up to 4K resolution',
    'WebSocket 双向流': 'WebSocket bidirectional',
    '3072 维向量': '3072-dim vectors',
    '<span class="tag mod-ico" title="代码"><svg class="ic"><use href="#i-code"/></svg></span> <span class="plain">+ 长任务</span>':
        '<span class="tag mod-ico" title="Code"><svg class="ic"><use href="#i-code"/></svg></span> <span class="plain">+ long tasks</span>',
    '<span class="tag mod-ico" title="视频"><svg class="ic"><use href="#i-video"/></svg></span> <span class="plain">+ 同步音频</span>':
        '<span class="tag mod-ico" title="Video"><svg class="ic"><use href="#i-video"/></svg></span> <span class="plain">+ synced audio</span>',
    '<span class="tag t-teal">Apache 2.0 开源</span>': '<span class="tag t-teal">Apache 2.0 open source</span>',

    # ---- 徽章 ----
    '推荐': 'Rec', '弃用': 'Deprecated', '预览': 'Preview', '开源': 'OSS',
}

MISSING = []


def tr(s):
    """递归翻译 str；dict/list 深入内部（覆盖 price 的 {"raw": html}、
    ctx 高亮 {"v": "…", "hi": true}、badges 数组等嵌套结构），避免漏翻。"""
    if isinstance(s, str):
        if s in TRANSLATE:
            return TRANSLATE[s]
        if CJK.search(s):
            MISSING.append(s)
        return s
    if isinstance(s, dict):
        return {k: tr(v) for k, v in s.items()}
    if isinstance(s, list):
        return [tr(x) for x in s]
    return s


def tr_cell(t, v):
    """按单元格类型翻译；dict 覆盖格取其 'v' 字段"""
    if isinstance(v, dict) and 't' in v:
        v = dict(v)
        v['v'] = tr(v['v'])
        return v
    if t == 'model_id':
        if isinstance(v, dict):
            v = dict(v)
            v['badges'] = [tr(b) for b in v.get('badges', [])]
        return v
    if t == 'flow':
        v = dict(v)
        v['label'] = tr(v['label'])
        return v
    if t == 'scene':
        v = dict(v)
        v['text'] = tr(v['text'])
        if 'note' in v:
            v['note'] = tr(v['note'])
        return v
    return tr(v)


def main():
    data = json.load(open(SRC, encoding='utf-8'))
    meta = data['meta']
    meta['lang'] = 'en'
    meta['lang_switch'] = {
        'zh': {'href': 'openai-model-userguide.html', 'label': '中'},
        'en': {'href': 'openai-model-userguide-en.html', 'label': 'EN'},
    }
    for k in ('title', 'h1', 'hero_desc', 'home_title', 'home_label',
              'footer_title', 'footer_rules', 'footer_sources'):
        meta[k] = tr(meta[k])
    for s in meta['stats']:
        s['label'] = tr(s['label'])

    for sec in data['sections']:
        for k in ('title', 'desc', 'nav'):
            if k in sec:
                sec[k] = tr(sec[k])
        if sec.get('kind') == 'quick':
            for c in sec['cards']:
                c['task'] = tr(c['task'])
        elif sec.get('kind') == 'table':
            sec['columns'] = [tr(c) for c in sec['columns']]
            rts = sec['row_types']
            for row in sec['rows']:
                for i, (t, v) in enumerate(zip(rts, row)):
                    row[i] = tr_cell(t, v)

    json.dump(data, open(DST, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)
    print(f'wrote {DST}')
    if MISSING:
        print(f'!! 以下 {len(MISSING)} 条中文未翻译（请补充 TRANSLATE）:')
        for m in sorted(set(MISSING)):
            print('  -', m)
        sys.exit(1)
    print('全部中文已翻译')


if __name__ == '__main__':
    main()
