# -*- coding: utf-8 -*-
"""临时脚本：data/gemini.json → data/gemini-en.json（英文版）。

翻译策略：语言中立字段（模型 ID、数字、档位 key、模态 key、ctx 数值、URL）
原样保留；编辑字段按 TRANSLATE 精确匹配翻译；漏翻的中文会告警。
生成的是新文件 data/gemini-en.json，不改动中文数据源。
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(os.path.dirname(HERE))  # .claude/skills/model-guide
SRC = os.path.join(SKILL_DIR, 'data', 'gemini.json')
DST = os.path.join(SKILL_DIR, 'data', 'gemini-en.json')

CJK = re.compile(r'[\u4e00-\u9fff]')

# ===== 翻译表（完整枚举 gemini.json 中的可译编辑字段）=====
TRANSLATE = {
    # ---- meta ----
    'Google Gemini 模型选择指南 2026': 'Google Gemini Model Selection Guide 2026',
    'Google Gemini 模型选择指南': 'Google Gemini Model Selection Guide',
    'Gemini 3 / 2.5 全系 · Nano Banana 图像 · Veo 视频 · Lyria 音乐 · 智能体与机器人模型 — 数据来源：Google AI for Developers 官方文档 <a href="https://ai.google.dev/gemini-api/docs/models" target="_blank" rel="noopener noreferrer">模型清单</a> · <a href="https://ai.google.dev/gemini-api/docs/pricing" target="_blank" rel="noopener noreferrer">价格</a> · <a href="https://ai.google.dev/gemini-api/docs/deprecations" target="_blank" rel="noopener noreferrer">关停计划</a>（2026-08-30 同步）':
        'Gemini 3 / 2.5 family · Nano Banana image · Veo video · Lyria music · agents & robotics models — Sources: Google AI for Developers official docs <a href="https://ai.google.dev/gemini-api/docs/models" target="_blank" rel="noopener noreferrer">Model list</a> · <a href="https://ai.google.dev/gemini-api/docs/pricing" target="_blank" rel="noopener noreferrer">Pricing</a> · <a href="https://ai.google.dev/gemini-api/docs/deprecations" target="_blank" rel="noopener noreferrer">Deprecations</a> (synced 2026-08-30)',
    '数据来源：Google AI for Developers 官方文档 <a href="https://ai.google.dev/gemini-api/docs/models" target="_blank" rel="noopener noreferrer">模型清单</a> · <a href="https://ai.google.dev/gemini-api/docs/pricing" target="_blank" rel="noopener noreferrer">价格</a> · <a href="https://ai.google.dev/gemini-api/docs/deprecations" target="_blank" rel="noopener noreferrer">关停计划</a>（2026-08-30 同步）':
        'Sources: Google AI for Developers official docs <a href="https://ai.google.dev/gemini-api/docs/models" target="_blank" rel="noopener noreferrer">Model list</a> · <a href="https://ai.google.dev/gemini-api/docs/pricing" target="_blank" rel="noopener noreferrer">Pricing</a> · <a href="https://ai.google.dev/gemini-api/docs/deprecations" target="_blank" rel="noopener noreferrer">Deprecations</a> (synced 2026-08-30)',
    'pro = 旗舰 · flash = 快速均衡 · lite = 省钱 · nano-banana = 图像 · veo = 视频 · live = 实时 · preview = 预览':
        'pro = flagship · flash = fast & balanced · lite = budget · nano-banana = image · veo = video · live = realtime · preview = preview',
    '收录模型': 'Models',
    '模型分类': 'Categories',
    '最大上下文': 'Max context',

    # ---- 通用 section 字段 ----
    '快速选型': 'Quick Picks',
    '按任务类型直达推荐模型': 'Direct recommendation by task type',
    '命名规律速查': 'Naming Conventions',
    '掌握这些规律，看到任何模型名都能秒懂其定位': 'Understand these patterns and instantly grasp any model name',
    '命名规律': 'Naming',
    '命名元素': 'Element', '含义': 'Meaning', '示例': 'Example',
    'Gemini 3 前沿模型': 'Gemini 3 Frontier Models',
    '最新一代，全系支持思考（输出价含思考 token）与 1M 上下文；缓存输入最高省 90%，Batch 半价；标注价格为 2026 促销价（2027-01-01 起恢复原价约 2 倍）；均支持 PDF 文档输入':
        'Latest generation; all support thinking (output price includes thinking tokens) and 1M context; cached input saves up to 90%, Batch at half price; listed prices are 2026 promotional rates (roughly 2x from 2027-01-01); all support PDF input',
    'Gemini 2.5 主力模型': 'Gemini 2.5 Workhorses',
    '当前主力生产模型（Stable），1M 上下文，支持思考与 Function Calling；主力模型均支持 PDF 文档输入':
        'Current production workhorses (Stable), 1M context, thinking & Function Calling; all support PDF input',
    '音频模型（Transcribe / TTS / Live / Translate）': 'Audio Models (Transcribe / TTS / Live / Translate)',
    '音频': 'Audio',
    '语音转文字、文字转语音、实时对话与实时翻译；Live 系列经 WebSocket 双向流式交互':
        'Speech-to-text, text-to-speech, realtime chat & realtime translation; Live series streams bidirectionally over WebSocket',
    '图像生成（Nano Banana 🍌）': 'Image Generation (Nano Banana 🍌)',
    '图像': 'Image',
    'Nano Banana 系列为当前图像生成主力；Imagen 4 已并入并关停':
        'Nano Banana is the current image-generation workhorse; Imagen 4 has been merged and shut down',
    '视频生成（Veo / Omni）': 'Video Generation (Veo / Omni)',
    '视频': 'Video',
    '按输出视频秒数计费，含同步音频；Veo 3.1 支持最高 4K，Omni 支持生成/编辑/补帧/延展':
        'Billed by output video seconds, includes synced audio; Veo 3.1 supports up to 4K, Omni supports generate/edit/interpolate/extend',
    '音乐生成（Lyria）': 'Music Generation (Lyria)',
    '音乐': 'Music',
    '按生成的歌曲次数计费': 'Billed per generated song',
    '智能体模型（Agents）': 'Agent Models',
    '智能体': 'Agents',
    '自主规划与执行的智能体模型；预览阶段，价格以官方后续公布为准':
        'Agent models with autonomous planning & execution; preview stage, pricing TBD by Google',
    '机器人模型（Gemini Robotics）': 'Robotics Models (Gemini Robotics)',
    '机器人': 'Robotics',
    '具身推理（Embodied Reasoning）：理解物理空间、规划多步任务、多机协作':
        'Embodied reasoning: understand physical space, plan multi-step tasks, multi-robot collaboration',
    '向量模型（Embedding）': 'Embedding Models',
    '向量': 'Embedding',
    '语义搜索与 RAG；Embedding 2 为首个多模态向量模型（文本/图像/音频/视频/PDF 统一向量空间）':
        'Semantic search & RAG; Embedding 2 is the first multimodal embedding model (unified vector space for text/image/audio/video/PDF)',
    'Gemma 开源模型': 'Gemma Open-Source Models',
    '开源': 'OSS',
    '与 Gemini 同源的轻量开源模型，免费使用，可私有化部署':
        'Lightweight open-source models sharing Gemini\'s lineage, free to use, self-hostable',
    'Gemini 2.0（已关停）': 'Gemini 2.0 (Shut Down)',
    '已于 2026-06-01 全部关停，请迁移至 Gemini 3.x 对应替代模型；均支持 PDF 文档输入':
        'All shut down 2026-06-01; migrate to the corresponding Gemini 3.x replacements; all support PDF input',
    '已弃用与关停计划': 'Deprecated & Shutdown Schedule',
    '已弃用': 'Deprecated',
    '以下为本页已收录模型中的弃用/关停信息（关停日期为官方公布的最早可能日期）。数据来源：Gemini 官方弃用计划（2026-08-30 同步）':
        'Retirement info for the models covered on this page (shutdown dates are the earliest official dates). Source: Gemini official deprecation schedule (synced 2026-08-30)',
    '能力矩阵速查': 'Capability Matrix',
    '能力矩阵': 'Capability Matrix',
    '根据需求快速匹配最佳模型': 'Match the best model to your needs quickly',

    # ---- 通用列头 ----
    '模型 ID': 'Model ID', '定位': 'Tier', '价格': 'Price', '模态': 'Modality',
    '推理': 'Reasoning', '速度': 'Speed', '上下文': 'Context', '输入': 'Input',
    '输出': 'Output', '说明': 'Notes', '类型': 'Type', '特性': 'Features',
    '计费': 'Billing', '时长': 'Duration', '用途': 'Use', '分辨率': 'Resolution',
    '生命周期': 'Lifecycle', '关停日期': 'Shutdown date', '替代方案': 'Replacement',
    '迁移建议': 'Migration advice',
    '需求场景': 'Scenario', '推荐模型': 'Recommended', '备选模型': 'Alternatives',
    '关键能力': 'Key capability',

    # ---- quick 卡片任务 ----
    '日常对话 / 写作': 'Chat / Writing',
    '深度推理': 'Deep reasoning',
    '专业编程 / Agentic': 'Coding / Agentic',
    '极致省钱': 'Cheapest',
    '图像生成': 'Image generation',
    '视频生成': 'Video generation',
    '音乐生成': 'Music generation',
    '实时语音对话': 'Realtime voice chat',
    '语音转文字': 'Speech to text',
    '文字转语音': 'Text to speech',
    '实时语音翻译': 'Realtime translation',
    '语义搜索 / RAG': 'Semantic search / RAG',
    '计算机操控': 'Computer use',
    '机器人控制': 'Robotics control',
    '开源 / 边缘设备': 'OSS / Edge devices',

    # ---- 命名规律表 ----
    'gemini-X.Y 版本号': 'gemini-X.Y version number',
    '数字越大，模型越新越强': 'Higher number = newer and stronger',
    '旗舰增强版，最强推理': 'Flagship enhanced, top reasoning',
    '速度优化均衡版': 'Speed-optimized, balanced',
    '最省最快轻量版': 'Cheapest and fastest lite',
    '预览版（可用于生产，提前 2 周通知弃用）': 'Preview (production-ready; 2-week deprecation notice)',
    '最新别名，随版本热替换': 'Latest alias, hot-swaps with versions',
    '图像生成系列代号': 'Image-generation family codename',
    '支持图像生成输出': 'Supports image output',
    'Live API 实时音视频对话': 'Live API realtime audio/video chat',
    '原生音频处理（Live API）': 'Native audio processing (Live API)',
    '实时语音翻译': 'Realtime speech translation',
    '文字转语音': 'Text to speech',
    '语音转文字': 'Speech to text',
    '视频全能：生成/编辑/补帧/延展+原生音频': 'All-in-one video: generate/edit/interpolate/extend + native audio',
    '视频生成系列': 'Video generation family',
    '音乐生成系列': 'Music generation family',
    '机器人具身推理（Embodied Reasoning）': 'Robotics embodied reasoning',
    '深度研究智能体': 'Deep research agent',
    '托管通用智能体（沙箱内自主执行）': 'Hosted general agent (autonomous in sandbox)',
    '计算机操控': 'Computer use',
    '开源轻量模型系列': 'Open-source lightweight family',
    '正式版本号 / 实验版': 'Stable version number / experimental',

    # ---- gemini3 / gemini25 mdesc ----
    '当前最强推理，Agentic 与复杂编程，$2/$12': 'Current top reasoning, agentic & complex coding, $2/$12',
    '最新最强 Flash（Stable），复杂编程与多步执行，$0.75/$3.75':
        'Newest, strongest Flash (Stable), complex coding & multi-step execution, $0.75/$3.75',
    '上代 Flash（Stable），搜索与 Grounding 增强，$0.75/$3.75':
        'Previous Flash (Stable), enhanced search & grounding, $0.75/$3.75',
    '基础版 Flash（Stable），高吞吐常规任务，$1.5/$9':
        'Base Flash (Stable), high-throughput general tasks, $1.5/$9',
    '3.5 最快最省（Stable），$0.3/$2.5': 'Fastest, cheapest 3.5 (Stable), $0.3/$2.5',
    '前沿级廉价（Stable），$0.25/$1.5；已宣布 2027-05 退役':
        'Frontier-grade at budget price (Stable), $0.25/$1.5; announced retirement 2027-05',
    '早期预览版，$0.5/$3；建议迁移 gemini-3.6-flash':
        'Early preview, $0.5/$3; migrating to gemini-3.6-flash recommended',
    '2.5 代最强，复杂任务与编程首选，$1.25/$10':
        'Strongest of the 2.5 generation, top choice for complex tasks & coding, $1.25/$10',
    '最佳性价比，低延迟高吞吐，$0.3/$2.5': 'Best value, low latency high throughput, $0.3/$2.5',
    '2.5 代最省，大规模调用，$0.1/$0.4': 'Cheapest of the 2.5 generation, large-scale calls, $0.1/$0.4',
    'Nano Banana（🍌）上代图像生成，$0.3 输入；已宣布 2026-10 退役':
        'Previous Nano Banana (🍌) image generation, $0.3 input; announced retirement 2026-10',
    '计算机操控专用，看屏幕执行点击/输入/导航，$1.25/$10':
        'Dedicated computer use: watch screen, click/type/navigate, $1.25/$10',

    # ---- audio flow / plain / mdesc ----
    '实时转写': 'Live transcription',
    '实时对话': 'Realtime chat',
    '实时翻译': 'Realtime translation',
    '说话人分离/词级时间戳': 'Speaker diarization / word-level timestamps',
    '流式实时': 'Streaming live',
    '音频标签精细控制': 'Fine-grained audio tags control',
    '风格/语速可控': 'Style/speed controllable',
    '高保真': 'High fidelity',
    '原生音频推理': 'Native audio reasoning',
    '70+ 语言': '70+ languages',
    '低延迟转写，$2/$12': 'Low-latency transcription, $2/$12',
    '实时流式转写，$3.5/$21': 'Realtime streaming transcription, $3.5/$21',
    '最新 TTS，$1/$20': 'Latest TTS, $1/$20',
    '上代 TTS，$0.5/$10': 'Previous TTS, $0.5/$10',
    '播客/有声书级，$1/$20': 'Podcast/audiobook grade, $1/$20',
    '实时语音对话旗舰，$0.75/$4.5': 'Realtime voice chat flagship, $0.75/$4.5',
    'Live API 上代，$0.5/$2': 'Previous Live API model, $0.5/$2',
    '语音到语音实时翻译，$3.5/$21': 'Speech-to-speech realtime translation, $3.5/$21',

    # ---- image ----
    '最高 4K': 'up to 4K',
    '标准': 'Standard',
    'Nano Banana Pro：SOTA 图像生成与编辑，复杂排版/文字渲染，$2/$12':
        'Nano Banana Pro: SOTA image generation & editing, complex layouts/text rendering, $2/$12',
    'Nano Banana 2：高效量产，$0.5/$3': 'Nano Banana 2: high-efficiency volume generation, $0.5/$3',
    'Nano Banana 2 Lite：超低延迟低成本，$0.25/$1.5':
        'Nano Banana 2 Lite: ultra-low latency & cost, $0.25/$1.5',
    'Nano Banana 上代（🍌），$0.3 输入；已宣布 2026-10 退役':
        'Previous Nano Banana (🍌), $0.3 input; announced retirement 2026-10',
    '已于 2026-08-17 关停，迁移 Nano Banana': 'Shut down 2026-08-17; migrate to Nano Banana',

    # ---- video ----
    '$0.4-0.6/秒': '$0.4-0.6/sec',
    '$0.1-0.3/秒': '$0.1-0.3/sec',
    '$0.05-0.08/秒': '$0.05-0.08/sec',
    '$0.2-0.4/秒': '$0.2-0.4/sec',
    '文生视频': 'Text to video',
    '视频生成/编辑/补帧/延展': 'Video generate/edit/interpolate/extend',
    '视频生成/编辑': 'Video generate/edit',
    '电影级画质+原生同步音频': 'Cinematic quality + native synced audio',
    '快速生成，性价比首选': 'Fast generation, best value',
    '开发者友好低成本版（无 4K）': 'Developer-friendly low-cost version (no 4K)',
    '原生音频，功能最全面': 'Native audio, most complete features',
    '已于 2026-06-30 关停，迁移 Veo 3.1': 'Shut down 2026-06-30; migrate to Veo 3.1',
    '预览版，2026-09-30 退役，迁移 gemini-omni-1.1-flash':
        'Preview; retires 2026-09-30; migrate to gemini-omni-1.1-flash',

    # ---- music ----
    '完整歌曲': 'Full songs',
    '短片段/循环': 'Clips / loops',
    '实时流式': 'Realtime streaming',
    '$0.08/首': '$0.08/song',
    '$0.04/首': '$0.04/song',
    '实验版': 'Experimental',
    '完整曲目': 'Full track',
    '30 秒': '30 sec',
    '流式': 'Streaming',
    '旗舰音乐生成，复杂结构完整性': 'Flagship music generation, complex structure integrity',
    '片段、循环与预览生成': 'Clips, loops and previews',
    '高保真实时音乐生成，细粒度创作控制': 'High-fidelity realtime music generation, fine-grained creative control',

    # ---- agents ----
    '深度研究': 'Deep research',
    '通用智能体': 'General agent',
    '最强自动研究：数百来源检索与综合，生成可交互引用报告':
        'Strongest automated research: retrieves & synthesizes hundreds of sources, produces interactive cited reports',
    '自主规划执行多步研究任务': 'Autonomously plans and executes multi-step research',
    '隔离 Linux 沙箱内自主规划/推理/执行代码/管理文件/浏览网页':
        'Autonomous planning/reasoning/code execution/file management/web browsing in an isolated Linux sandbox',

    # ---- robotics ----
    '最新具身推理：视频理解/空间推理/多步工具编排/多机协作，$2/$10':
        'Latest embodied reasoning: video understanding/spatial reasoning/multi-step tool orchestration/multi-robot collaboration, $2/$10',
    '上代 ER，2026-08-31 退役，迁移 ER 2，$1/$5':
        'Previous ER, retires 2026-08-31, migrate to ER 2, $1/$5',

    # ---- embed ----
    '多模态向量': 'Multimodal embedding',
    '向量化': 'Embed',
    '文本$0.2 / 图$0.45 / 音$6.5 / 视$12': 'Text $0.2 / Image $0.45 / Audio $6.5 / Video $12',
    '首个多模态 Embedding，统一向量空间': 'First multimodal Embedding, unified vector space',
    '高维文本向量，2028-05-14 退役': 'High-dim text vectors, retires 2028-05-14',

    # ---- gemma ----
    '<span class="tag t-green"><svg class="ic"><use href="#i-home"/></svg>开源免费</span>':
        '<span class="tag t-green"><svg class="ic"><use href="#i-home"/></svg>Open source & free</span>',
    '最新开源旗舰，同源自 Gemini 技术': 'Latest open-source flagship, same lineage as Gemini',
    '文本/图像理解/推理': 'Text/image understanding & reasoning',
    '多模态输入，移动设备优化': 'Multimodal input, optimized for mobile',
    '文本生成/摘要/提取（9B/27B）': 'Text generation/summarization/extraction (9B/27B)',
    '代码生成与补全（2B/7B）': 'Code generation & completion (2B/7B)',
    '安全分类与内容过滤专用': 'Safety classification & content filtering',
    '治疗预测/药物发现/基因组学': 'Therapy prediction/drug discovery/genomics',
    '医学影像分析（DICOM）': 'Medical imaging analysis (DICOM)',
    '图像描述与视觉问答（3B）': 'Image captioning & visual QA (3B)',

    # ---- gemini20 ----
    '已关停（2026-06-01），迁移 gemini-3.6-flash': 'Shut down (2026-06-01); migrate to gemini-3.6-flash',
    '已关停（2026-06-01），迁移 gemini-3.1-flash-lite':
        'Shut down (2026-06-01); migrate to gemini-3.1-flash-lite',

    # ---- deprecated 迁移建议 ----
    '已关停，直接替换': 'Shut down; drop-in replacement',
    '已关停，迁移 Nano Banana 2': 'Shut down; migrate to Nano Banana 2',
    '即将退役，尽快迁移': 'Retiring soon; migrate promptly',
    '已宣布退役，规划迁移': 'Retirement announced; plan migration',
    '预览版按期退役': 'Preview; retires on schedule',
    'Stable 但已宣布退役，规划迁移': 'Stable but announced retirement; plan migration',
    '仍可用（至 2028），新项目建议 Embedding 2': 'Still usable (until 2028); Embedding 2 recommended for new projects',
    'Gemini 3 Pro 预览版，已关停（2026-03-09），迁移 gemini-3.1-pro-preview':
        'Gemini 3 Pro preview, shut down (2026-03-09); migrate to gemini-3.1-pro-preview',
    '3.1 Lite 预览版，已关停（2026-05-25），迁移 gemini-3.1-flash-lite':
        '3.1 Lite preview, shut down (2026-05-25); migrate to gemini-3.1-flash-lite',
    '上代 ER，已关停（2026-04-30），迁移 gemini-robotics-er-1.6-preview':
        'Previous ER, shut down (2026-04-30); migrate to gemini-robotics-er-1.6-preview',

    # ---- matrix ----
    '复杂推理 / 数学': 'Complex reasoning / Math',
    'Agentic 编程工作流': 'Agentic coding workflows',
    '极致低成本': 'Ultra-low cost',
    '超长文档处理': 'Long-document processing',
    '多模态理解（图+音+视）': 'Multimodal understanding (image+audio+video)',
    '高质量图像生成': 'High-quality image generation',
    '音乐创作': 'Music creation',
    '计算机操控自动化': 'Computer use automation',
    '私有化 / 边缘部署': 'Private / edge deployment',
    '~100万 token': '~1M tokens',
    '<span class="ctx hi">1M 上下文</span> <span class="plain">$0.75/$3.75</span>':
        '<span class="ctx hi">1M context</span> <span class="plain">$0.75/$3.75</span>',
    '<span class="tag t-teal"><svg class="ic"><use href="#i-brain"/></svg><span class="dots"><i class="on"></i><i class="on"></i><i class="on"></i><i class="on"></i><i class="on"></i></span>最强</span>':
        '<span class="tag t-teal"><svg class="ic"><use href="#i-brain"/></svg><span class="dots"><i class="on"></i><i class="on"></i><i class="on"></i><i class="on"></i><i class="on"></i></span>Top</span>',
    '<span class="tag mod-ico" title="代码"><svg class="ic"><use href="#i-code"/></svg></span> <span class="plain">+ 多步执行</span>':
        '<span class="tag mod-ico" title="Code"><svg class="ic"><use href="#i-code"/></svg></span> <span class="plain">+ multi-step execution</span>',
    '<span class="ctx hi">1M 上下文</span>': '<span class="ctx hi">1M context</span>',
    '<div class="mods"><span class="tag mod-ico" title="图像"><svg class="ic"><use href="#i-image"/></svg></span><span class="tag mod-ico" title="音频"><svg class="ic"><use href="#i-audio"/></svg></span><span class="tag mod-ico" title="视频"><svg class="ic"><use href="#i-video"/></svg></span><span class="tag mod-ico" title="文本"><svg class="ic"><use href="#i-text"/></svg></span></div>':
        '<div class="mods"><span class="tag mod-ico" title="Image"><svg class="ic"><use href="#i-image"/></svg></span><span class="tag mod-ico" title="Audio"><svg class="ic"><use href="#i-audio"/></svg></span><span class="tag mod-ico" title="Video"><svg class="ic"><use href="#i-video"/></svg></span><span class="tag mod-ico" title="Text"><svg class="ic"><use href="#i-text"/></svg></span></div>',
    '<span class="mono-dim">Live API 双向流</span>': '<span class="mono-dim">Live API two-way streaming</span>',
    '<span class="mono-dim">说话人分离/词级时间戳</span>':
        '<span class="mono-dim">Speaker diarization / word-level timestamps</span>',
    '<span class="mono-dim">音频标签精细控制</span>': '<span class="mono-dim">Fine-grained audio tags control</span>',
    '<span class="ctx">70+ 语言</span>': '<span class="ctx">70+ languages</span>',
    '<span class="ctx">最高 4K · Nano Banana Pro</span>': '<span class="ctx">up to 4K · Nano Banana Pro</span>',
    '<span class="ctx">4K + 同步音频</span>': '<span class="ctx">4K + synced audio</span>',
    '<span class="ctx">$0.04-0.08/首</span>': '<span class="ctx">$0.04-0.08/song</span>',
    '<span class="mono-dim">多模态统一向量空间</span>': '<span class="mono-dim">Multimodal unified vector space</span>',
    '<span class="mono-dim">看屏幕执行 UI 操作</span>': '<span class="mono-dim">Watch screen, perform UI actions</span>',
    '<span class="mono-dim">具身推理 · 多机协作</span>': '<span class="mono-dim">Embodied reasoning · multi-robot collaboration</span>',
    '<span class="tag t-teal">开源免费</span>': '<span class="tag t-teal">Open source & free</span>',

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
        'zh': {'href': 'gemini-model-userguide.html', 'label': '中'},
        'en': {'href': 'gemini-model-userguide-en.html', 'label': 'EN'},
    }
    for k in ('title', 'eyebrow', 'h1', 'hero_desc',
              'footer_title', 'footer_rules', 'footer_sources'):
        meta[k] = tr(meta[k])
    for s in meta['stats']:
        s['label'] = tr(s['label'])

    # legend_overrides：note（单位说明）翻译，ranges 数值不译
    if isinstance(data.get('legend_overrides'), dict):
        ov = data['legend_overrides']
        if isinstance(ov.get('note'), str):
            ov['note'] = tr(ov['note'])

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
