# -*- coding: utf-8 -*-
"""临时脚本：data/zai.json → data/zai-en.json（英文版）。

翻译策略：语言中立字段（模型 ID、数字、档位 key、模态 key、ctx 数值、URL、
HTML 标签、legend_overrides 的 ranges 数值）原样保留；编辑字段按 TRANSLATE
精确匹配翻译；legend_overrides 的 note（CNY 单位说明）单独翻译；
漏翻的中文会告警。生成的是新文件 data/zai-en.json，不改动中文数据源。
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(os.path.dirname(HERE))  # .claude/skills/model-guide
SRC = os.path.join(SKILL_DIR, 'data', 'zai.json')
DST = os.path.join(SKILL_DIR, 'data', 'zai-en.json')

CJK = re.compile(r'[\u4e00-\u9fff]')

# ===== 翻译表（完整枚举 zai.json 中的可译编辑字段）=====
TRANSLATE = {
    # ---- meta ----
    'Z.ai 模型选择指南 2026': 'Z.ai Model Selection Guide 2026',
    'Z.ai 模型选择指南': 'Z.ai Model Selection Guide',
    '智谱 Z.ai 全系列模型解析 · 文本生成 · 多模态理解 · 图像/视频/语音 · 向量检索 — 数据来源：<a href="https://docs.bigmodel.cn/cn/guide/start/model-overview" target="_blank" rel="noopener noreferrer">BigModel 模型概览</a> · <a href="https://open.bigmodel.cn/pricing" target="_blank" rel="noopener noreferrer">产品价格</a>（2026-08-30 同步）':
        'Zhipu Z.ai full lineup · text generation · multimodal understanding · image/video/voice · vector retrieval — Sources: <a href="https://docs.bigmodel.cn/cn/guide/start/model-overview" target="_blank" rel="noopener noreferrer">BigModel model overview</a> · <a href="https://open.bigmodel.cn/pricing" target="_blank" rel="noopener noreferrer">Pricing</a> (synced 2026-08-30)',
    '数据来源：<a href="https://docs.bigmodel.cn/cn/guide/start/model-overview" target="_blank" rel="noopener noreferrer">BigModel 模型概览</a> · <a href="https://open.bigmodel.cn/pricing" target="_blank" rel="noopener noreferrer">产品价格</a>（2026-08-30 同步）':
        'Sources: <a href="https://docs.bigmodel.cn/cn/guide/start/model-overview" target="_blank" rel="noopener noreferrer">BigModel model overview</a> · <a href="https://open.bigmodel.cn/pricing" target="_blank" rel="noopener noreferrer">Pricing</a> (synced 2026-08-30)',
    '收录模型': 'Models',
    '模型分类': 'Categories',
    '最大上下文': 'Max context',
    'GLM = 智谱大模型 · 数字越大越新 · 5.x = 最新一代 · Flash = 省钱快速 · Turbo = 速度优化 · Air = 轻量均衡 · V = 视觉 · Cog = 生成模型':
        'GLM = Zhipu LLM · higher number = newer · 5.x = latest gen · Flash = budget & fast · Turbo = speed-optimized · Air = lightweight & balanced · V = vision · Cog = generative models',

    # ---- legend_overrides ----
    '单位：元 CNY / 1M tokens（输入 / 输出），按官方原价':
        'Unit: CNY / 1M tokens (input / output), at official list price',

    # ---- 通用 section 字段 ----
    '快速选型': 'Quick Picks',
    '按任务类型直达推荐模型': 'Direct recommendation by task type',
    '命名规律速查': 'Naming Conventions',
    '命名规律': 'Naming',
    '掌握这些规律，看到任何模型名都能秒懂其定位': 'Understand these patterns and instantly grasp any model name',
    '前沿旗舰模型': 'Frontier Flagship Models',
    '前沿旗舰': 'Frontier Flagship',
    '文本模型': 'Text Models',
    '视觉理解模型': 'Vision understanding model',
    '视觉理解': 'Vision Understanding',
    '图像生成模型': 'Image Generation Models',
    '视频生成模型': 'Video Generation Models',
    '音视频模型': 'Audio & Video Models',
    '音视频': 'Audio & Video',
    '向量模型与其他': 'Embedding & Others',
    '向量与其他': 'Embedding & Others',
    '历史模型': 'Legacy Models',
    '场景能力矩阵': 'Capability Matrix',
    '能力矩阵': 'Capability Matrix',

    # ---- 通用列头 ----
    '模型 ID': 'Model ID', '定位': 'Tier', '价格': 'Price', '模态': 'Modality',
    '推理': 'Reasoning', '速度': 'Speed', '上下文': 'Context', '输入': 'Input',
    '输出': 'Output', '说明': 'Notes',
    '场景': 'Scenario', '推荐模型': 'Recommended', '备选模型': 'Alternatives',
    '关键能力': 'Key capability',

    # ---- quick 卡片任务 ----
    '日常对话 / 写作': 'Chat / Writing',
    '复杂推理 / 长程 Agent': 'Complex reasoning / long-horizon Agent',
    '专业编程 / 软件工程': 'Coding / software engineering',
    '图像 / 视频理解': 'Image / video understanding',
    '极致省钱': 'Cheapest',
    '超长文档处理': 'Long-document processing',
    '图像生成': 'Image generation',
    '视频生成': 'Video generation',
    '实时语音对话': 'Realtime voice chat',
    '语音识别': 'Speech recognition',
    '语音合成': 'Speech synthesis',
    '语义搜索 / RAG': 'Semantic search / RAG',

    # ---- 命名规律表 ----
    '命名元素': 'Element', '含义': 'Meaning', '示例': 'Example',
    'GLM 前缀': 'GLM prefix',
    '智谱通用语言模型系列': 'Zhipu general-purpose LLM family',
    '版本号 (4→5→5.3)': 'Version number (4→5→5.3)',
    '数字越大，模型越新越强': 'Higher number = newer and stronger',
    '轻量快速，普惠省钱': 'Lightweight and fast, budget-friendly',
    'Flash 增强高速版': 'Enhanced high-speed Flash',
    '速度优化版': 'Speed-optimized version',
    '轻量均衡版': 'Lightweight, balanced',
    '极速低延迟版': 'Ultra-fast, low-latency',
    '超长上下文专用': 'Built for ultra-long context',
    '视觉推理模型': 'Vision reasoning model',
    '实时音视频对话': 'Realtime audio-video conversation',
    '自动语音识别': 'Automatic speech recognition',
    '文本转语音': 'Text to speech',
    '视频生成（合作）': 'Video generation (partner)',
    '文本向量化': 'Text embedding',
    '日期快照': 'Date snapshot',

    # ---- frontier / text / vision / historical mdesc ----
    '智谱最新一代旗舰模型，推荐用于复杂推理、编程、Agent 与多模态任务':
        "Zhipu's latest flagship generation, recommended for complex reasoning, coding, agents and multimodal tasks",
    '最新旗舰，面向复杂软件工程与长程 Agent 任务，编程体验较前代提升 50%':
        'Latest flagship for complex software engineering and long-horizon agent tasks; coding experience 50% better than the previous generation',
    '原生多模态普惠模型，原生理解图片/视频/文件，限时 5 折':
        'Native multimodal budget model; natively understands images/videos/files; limited-time 50% off',
    '支撑复杂长程任务稳定执行，Coding 能力大幅提升':
        'Stable execution of complex long-horizon tasks; significantly improved coding',
    'Coding 能力对齐 Claude Opus 4.6，长程任务可自主工作长达 8 小时；输入 ≥32K 时 ¥8/¥28':
        'Coding on par with Claude Opus 4.6; autonomous long-horizon tasks for up to 8 hours; ¥8/¥28 when input ≥32K',
    '编程能力对齐 Claude Opus 4.5，擅长 Agentic 长程规划与执行；输入 ≥32K 时 ¥6/¥22':
        'Coding on par with Claude Opus 4.5; excels at agentic long-horizon planning and execution; ¥6/¥22 when input ≥32K',
    '多模态 Coding 基座，兼顾视觉理解、推理与代码生成；输入 ≥32K 时 ¥7/¥26':
        'Multimodal coding base, balancing vision understanding, reasoning and code generation; ¥7/¥26 when input ≥32K',
    '长任务核心需求专项优化，复杂长任务执行连续性好；输入 ≥32K 时 ¥7/¥26':
        'Optimized for long-task core needs; good continuity on complex long tasks; ¥7/¥26 when input ≥32K',
    '专注于自然语言理解与生成的文本模型，覆盖对话、写作、推理与代码场景':
        'Text models focused on natural-language understanding and generation, covering chat, writing, reasoning and code',
    '通用对话、推理与智能体能力升级；输入 &lt;32K 且输出 &lt;0.2K 时 ¥2/¥8':
        'Upgraded general chat, reasoning and agent capabilities; ¥2/¥8 when input <32K and output <0.2K',
    'Flash 增强高速版，推理速度快，适合高并发调用场景':
        'Enhanced high-speed Flash; fast reasoning; ideal for high-concurrency calls',
    '免费文本模型，延续 GLM-4.7 基座的通用能力':
        'Free text model carrying over the general capabilities of the GLM-4.7 base',
    '擅长高级编码、复杂推理与工具调用；按量计费价格未公开，可通过私有实例部署':
        'Excels at advanced coding, complex reasoning and tool calling; pay-as-you-go pricing not public; deployable via private instances',
    '轻量模型，推理、编码与智能体任务表现稳定':
        'Lightweight model; stable on reasoning, coding and agent tasks',
    '轻量高速 Flash 增强版，推理速度快，适合高并发调用；输入 ¥0.5/输出 ¥3':
        'Lightweight high-speed Flash; fast reasoning; ideal for high-concurrency calls; ¥0.5 in / ¥3 out',
    '原生多模态普惠模型，原生理解图片/视频/文件；原价 ¥0.8/¥2.8，限时 5 折（¥0.4/¥1.4）':
        'Native multimodal budget model; natively understands images/videos/files; list price ¥0.8/¥2.8, limited-time 50% off (¥0.4/¥1.4)',
    '极速版本，适合低延迟、高响应要求的业务场景':
        'Ultra-fast version for low-latency, high-response business scenarios',
    '专为超长文本和记忆型任务设计': 'Designed for ultra-long text and memory-intensive tasks',
    'Flash 增强高速版本，适合高并发调用场景': 'Enhanced high-speed Flash; ideal for high-concurrency calls',
    '免费文本模型，支持最长 128K 上下文处理': 'Free text model; handles up to 128K context',
    '免费文本模型': 'Free text model',
    '高智能旗舰，全自研第四代基座大模型，支持高级 Agent 能力':
        'High-intelligence flagship; fully self-developed 4th-gen base model; supports advanced agent capabilities',
    'GLM-4-Air 日期快照 250414，高性价比文本模型':
        'GLM-4-Air date snapshot 250414; cost-effective text model',
    '极速推理版本，适合低延迟高响应场景': 'Ultra-fast reasoning version for low-latency, high-response scenarios',
    '面向智能体应用优化的文本模型': 'Text model optimized for agent applications',
    '高性价比推理模型': 'Cost-effective reasoning model',
    '极速推理模型，兼顾推理深度与响应速度': 'Ultra-fast reasoning model, balancing depth and response speed',
    '高速低价推理模型，适合高并发推理场景': 'High-speed, low-cost reasoning model for high-concurrency reasoning',
    '免费推理模型': 'Free reasoning model',
    '通用对话、推理与智能体能力': 'General chat, reasoning and agent capabilities',
    '轻量均衡，高性价比': 'Lightweight and balanced, great value',
    '开源 9B 文本模型': 'Open-source 9B text model',
    '开源对话模型（第三代）': 'Open-source chat model (3rd gen)',
    '图像与视频理解、视觉推理及移动端智能体模型':
        'Image and video understanding, vision reasoning and mobile agent models',
    '原生支持工具调用，前端代码复刻效果更稳定；输入 &lt;32K 时 ¥1/¥3，[32,128) 时 ¥2/¥6':
        'Native tool calling; stable frontend code replication; ¥1/¥3 when input <32K, ¥2/¥6 for [32,128)',
    '视觉理解模型；输入 &lt;32K 时 ¥2/¥6': 'Vision understanding model; ¥2/¥6 when input <32K',
    '视觉推理模型，¥4/1M tokens': 'Vision reasoning model, ¥4/1M tokens',
    '手机智能助理框架，支持自然语言完成 App 操作任务':
        'Mobile AI assistant framework; completes app operations via natural language',
    '擅长复杂场景理解与多步骤分析，适合高并发视觉推理场景':
        'Excels at complex-scene understanding and multi-step analysis; ideal for high-concurrency vision reasoning',
    '轻量图文解析模型，兼顾高精度、高效率文档理解；输入：单图 ≤10MB / PDF ≤50MB / 100页':
        'Lightweight image-text parsing model balancing high-accuracy, high-efficiency document understanding; input: single image ≤10MB / PDF ≤50MB / 100 pages',
    '高速视觉推理模型；输入 &lt;32K 时 ¥0.15/¥1.5，[32,128) 时 ¥0.3/¥3':
        'High-speed vision reasoning model; ¥0.15/¥1.5 when input <32K, ¥0.3/¥3 for [32,128)',
    '免费模型，支持视觉推理': 'Free model with vision reasoning',
    '免费模型，支持图像理解': 'Free model with image understanding',
    '视觉理解模型（历史版本）': 'Vision understanding model (legacy)',
    'GLM-4 0520 历史版本': 'GLM-4 0520 legacy version',
    'GLM-4V Plus 历史版本': 'GLM-4V Plus legacy version',
    'GLM-4 基础历史版本': 'GLM-4 base legacy version',
    'GLM-4V 历史版本': 'GLM-4V legacy version',
    'GLM-4-Air 历史版本': 'GLM-4-Air legacy version',
    'GLM-4-Flash 历史版本，免费': 'GLM-4-Flash legacy version, free',
    '按量 API 已下架，仅提供微调与私有化部署':
        'Pay-as-you-go API retired; available via fine-tuning and private deployment',
    '按量 API 已下架，仅支持私有化部署；历史按量 ¥0.06/次':
        'Pay-as-you-go API retired; private deployment only; historical price ¥0.06/request',

    # ---- image / video 价格 raw HTML 与 mdesc ----
    '<span class="tag t-green">¥0.1 / 次</span>': '<span class="tag t-green">¥0.1 / request</span>',
    '<span class="tag t-green">¥0.06 / 次</span>': '<span class="tag t-green">¥0.06 / request</span>',
    '<span class="tag t-teal">免费</span>': '<span class="tag t-teal">Free</span>',
    '<span class="tag t-amber">¥1 / 次</span>': '<span class="tag t-amber">¥1 / request</span>',
    '<span class="tag t-amber">¥2.5 / 次</span>': '<span class="tag t-amber">¥2.5 / request</span>',
    '<span class="tag t-green">¥1.25 / 次</span>': '<span class="tag t-green">¥1.25 / request</span>',
    '<span class="tag t-green">¥0.5 / 次</span>': '<span class="tag t-green">¥0.5 / request</span>',
    '<span class="tag t-amber">¥6 / 次</span>': '<span class="tag t-amber">¥6 / request</span>',
    '<span class="tag t-green">¥2 / 万字符</span>': '<span class="tag t-green">¥2 / 10K chars</span>',
    '文生图与图像编辑模型，按请求次数计费':
        'Text-to-image and image editing models, billed per request',
    '旗舰图像生成模型，复杂指令遵循与知识密集生成更强，文字渲染表现突出，支持多分辨率':
        'Flagship image generation model; stronger complex-instruction following and knowledge-dense generation; outstanding text rendering; multi-resolution',
    '通用图像生成模型，生成质量高，画面细节更完整，适合多类创意场景，支持多分辨率':
        'General image generation model; high quality with richer detail; suits diverse creative scenarios; multi-resolution',
    '免费模型，适合轻量图像创作，支持多分辨率':
        'Free model for lightweight image creation; multi-resolution',
    '通用图像生成模型': 'General image generation model',
    '文生视频、图生视频与首尾帧生成模型，按请求次数计费':
        'Text-to-video, image-to-video and first/last-frame generation models, billed per request',
    '旗舰视频模型，指令遵循与物理模拟更强，现实与 3D 场景表现提升，支持首尾帧生成':
        'Flagship video model; stronger instruction following and physics simulation; improved realism and 3D scenes; supports first/last-frame generation',
    'Vidu Q1 文生视频，1080p': 'Vidu Q1 text-to-video, 1080p',
    'Vidu Q1 图生视频，1080p': 'Vidu Q1 image-to-video, 1080p',
    'Vidu Q1 首尾帧生成，1080p': 'Vidu Q1 first/last-frame generation, 1080p',
    'Vidu 2 图生视频，720p': 'Vidu 2 image-to-video, 720p',
    'Vidu 2 首尾帧生成，720p': 'Vidu 2 first/last-frame generation, 720p',
    'Vidu 2 参考生视频，720p': 'Vidu 2 reference-to-video, 720p',
    '通用视频生成模型，支持多分辨率': 'General video generation model; multi-resolution',
    '免费视频生成模型，支持图像、文本输入': 'Free video generation model; accepts image and text input',

    # ---- audio 价格 raw HTML 与 mdesc ----
    '<span class="tag t-green">音频 ¥0.18/分钟 · 视频 ¥1.2/分钟</span>':
        '<span class="tag t-green">Audio ¥0.18/min · Video ¥1.2/min</span>',
    '<span class="tag t-amber">音频 ¥0.3/分钟 · 视频 ¥2.1/分钟</span>':
        '<span class="tag t-amber">Audio ¥0.3/min · Video ¥2.1/min</span>',
    '<span class="tag t-green">输入 ¥16/1M tokens（约 ¥0.0002/秒），输出免费</span>':
        '<span class="tag t-green">Input ¥16/1M tokens (~¥0.0002/sec), free output</span>',
    '语音识别、语音合成、实时语音/视频对话与音色克隆模型，计费单位各异':
        'Speech recognition, speech synthesis, realtime voice/video conversation and voice cloning models, with varying billing units',
    '实时音视频模型，低延迟版本，支持视频、音频、文本多模态输入':
        'Realtime audio-video model, low-latency version; accepts video, audio and text multimodal input',
    '实时音视频模型，轻量均衡版本，支持视频、音频、文本多模态输入':
        'Realtime audio-video model, lightweight balanced version; accepts video, audio and text multimodal input',
    '实时语音对话模型，支持文本、音频；音频 token 单价，不可与文本档直接比较':
        'Realtime voice chat model; supports text and audio; audio token unit price, not directly comparable to text tiers',
    '音色克隆模型，3 秒音频即可快速生成相似音色':
        'Voice cloning model; 3 seconds of audio is enough to clone a similar voice',
    '语音合成模型，支持超拟人语音生成与情感表达，提供非流式与流式接口':
        'Speech synthesis model; ultra-humanlike voice with emotion; offers streaming and non-streaming APIs',
    '高精度语音识别模型，字符错误率低，支持自定义词汇，覆盖多种主流语言与方言场景':
        'High-accuracy speech recognition; low character error rate; custom vocabulary; covers major languages and dialects',

    # ---- embed ----
    '向量检索、重排序、角色扮演、心理陪伴与代码补全等专用模型':
        'Specialized models for vector retrieval, reranking, roleplay, emotional support and code completion',
    '第三代文本向量化模型（V3），适用于语义检索、聚类、主题建模与分类等场景':
        '3rd-gen text embedding model (V3) for semantic retrieval, clustering, topic modeling and classification',
    '第二代文本向量化模型（V2）': '2nd-gen text embedding model (V2)',
    '文本重排序模型': 'Text reranking model',
    '文本重排序模型，输入 ¥0.8/百万 tokens': 'Text reranking model, ¥0.8/1M input tokens',
    '代码补全模型': 'Code completion model',
    '拟人对话模型': 'Humanlike chat model',
    '心理情感支持模型': 'Emotional support model',

    # ---- historical ----
    '已停止推荐或进入维护期的旧版模型，仅作兼容参考':
        'Older models no longer recommended or under maintenance; for compatibility reference only',

    # ---- matrix ----
    '按典型场景快速找到首选与备选模型':
        'Find the primary and alternative model for each typical scenario',
    '复杂编程 / 软件工程': 'Complex coding / software engineering',
    '深度推理 / 数学推导': 'Deep reasoning / math derivation',
    '<span class="tag t-teal">推理</span> <span class="tag t-green">长上下文</span> <span class="mono-dim">Agent</span>':
        '<span class="tag t-teal">Reasoning</span> <span class="tag t-green">Long context</span> <span class="mono-dim">Agent</span>',
    '<span class="tag t-teal">最强推理</span> <span class="tag t-green">128K 输出</span>':
        '<span class="tag t-teal">Best reasoning</span> <span class="tag t-green">128K output</span>',
    '<span class="tag t-green">1M 上下文</span> <span class="mono-dim">低成本</span>':
        '<span class="tag t-green">1M context</span> <span class="mono-dim">Low cost</span>',
    '<span class="tag t-teal">原生多模态</span> <span class="tag t-green">视频理解</span>':
        '<span class="tag t-teal">Native multimodal</span> <span class="tag t-green">Video understanding</span>',
    '<span class="tag t-teal">文字渲染</span> <span class="tag t-green">多分辨率</span>':
        '<span class="tag t-teal">Text rendering</span> <span class="tag t-green">Multi-resolution</span>',
    '<span class="tag t-teal">首尾帧</span> <span class="tag t-green">物理模拟</span>':
        '<span class="tag t-teal">First/last frame</span> <span class="tag t-green">Physics simulation</span>',
    '<span class="tag t-teal">实时</span> <span class="tag t-green">音视频</span>':
        '<span class="tag t-teal">Realtime</span> <span class="tag t-green">Audio-video</span>',
    '<span class="tag t-teal">高精度</span> <span class="tag t-green">方言</span>':
        '<span class="tag t-teal">High accuracy</span> <span class="tag t-green">Dialects</span>',
    '<span class="tag t-teal">8K 上下文</span> <span class="tag t-green">语义检索</span>':
        '<span class="tag t-teal">8K context</span> <span class="tag t-green">Semantic retrieval</span>',
    '<span class="tag t-teal">免费</span> <span class="tag t-green">200K 上下文</span>':
        '<span class="tag t-teal">Free</span> <span class="tag t-green">200K context</span>',

    # ---- 徽章 ----
    '推荐': 'Rec', '弃用': 'Deprecated', '预览': 'Preview', '开源': 'OSS',
    'GA': 'GA', '正式版': 'GA',
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
        'zh': {'href': 'zai-model-userguide.html', 'label': '中'},
        'en': {'href': 'zai-model-userguide-en.html', 'label': 'EN'},
    }
    for k in ('title', 'eyebrow', 'h1', 'hero_desc', 'footer_title', 'footer_rules',
              'footer_sources'):
        meta[k] = tr(meta[k])
    for s in meta['stats']:
        s['label'] = tr(s['label'])

    # legend_overrides：ranges 为语言中立数值（不译），note 为可译单位说明
    if 'legend_overrides' in data:
        ov = data['legend_overrides']
        if 'note' in ov:
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
