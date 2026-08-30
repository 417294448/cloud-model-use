# -*- coding: utf-8 -*-
"""临时脚本：data/qwen.json → data/qwen-en.json（英文版）。

翻译策略：语言中立字段（模型 ID、数字、档位 key、模态 key、ctx 数值、URL、
¥ 价格数值）原样保留；编辑字段按 TRANSLATE 精确匹配翻译；漏翻的中文会告警。
legend_overrides.ranges 为 ¥ 货币数值（语言中立），note 需翻译。
生成的是新文件 data/qwen-en.json，不改动中文数据源。
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(os.path.dirname(HERE))  # .claude/skills/model-guide
SRC = os.path.join(SKILL_DIR, 'data', 'qwen.json')
DST = os.path.join(SKILL_DIR, 'data', 'qwen-en.json')

CJK = re.compile(r'[\u4e00-\u9fff]')

# ===== 翻译表（完整枚举 qwen.json 中的可译编辑字段）=====
TRANSLATE = {
    # ---- meta ----
    '通义千问模型选择指南 2026': 'Tongyi Qwen Model Selection Guide 2026',
    '通义千问模型选择指南': 'Tongyi Qwen Model Selection Guide',
    '通义千问（Qwen）全系列模型解析 · 混合思考 · 全模态 · 视觉生成 · 语音全链路 · 开源部署 — 数据来源：阿里云百炼官方文档 <a href="https://help.aliyun.com/zh/model-studio/models" target="_blank" rel="noopener noreferrer">模型大全</a> · <a href="https://help.aliyun.com/zh/model-studio/billing" target="_blank" rel="noopener noreferrer">模型价格</a> · <a href="https://help.aliyun.com/zh/model-studio/vision-model" target="_blank" rel="noopener noreferrer">分类文档</a>（2026-08-29 同步）':
        'All Qwen models analyzed · hybrid thinking · omni-modal · visual generation · full speech pipeline · open-source deployment — Sources: Alibaba Cloud Bailian official docs <a href="https://help.aliyun.com/zh/model-studio/models" target="_blank" rel="noopener noreferrer">Model catalog</a> · <a href="https://help.aliyun.com/zh/model-studio/billing" target="_blank" rel="noopener noreferrer">Model pricing</a> · <a href="https://help.aliyun.com/zh/model-studio/vision-model" target="_blank" rel="noopener noreferrer">Classification docs</a> (synced 2026-08-29)',
    '数据来源：阿里云百炼官方文档 <a href="https://help.aliyun.com/zh/model-studio/models" target="_blank" rel="noopener noreferrer">模型大全</a> · <a href="https://help.aliyun.com/zh/model-studio/billing" target="_blank" rel="noopener noreferrer">模型价格</a> · <a href="https://help.aliyun.com/zh/model-studio/vision-model" target="_blank" rel="noopener noreferrer">分类文档</a>（2026-08-29 同步）':
        'Sources: Alibaba Cloud Bailian official docs <a href="https://help.aliyun.com/zh/model-studio/models" target="_blank" rel="noopener noreferrer">Model catalog</a> · <a href="https://help.aliyun.com/zh/model-studio/billing" target="_blank" rel="noopener noreferrer">Model pricing</a> · <a href="https://help.aliyun.com/zh/model-studio/vision-model" target="_blank" rel="noopener noreferrer">Classification docs</a> (synced 2026-08-29)',
    'max = 旗舰 · prime = 优速 · plus = 均衡 · flash = 省钱 · qwq = 思考 · omni = 全模态 · vl = 视觉 · realtime = 实时':
        'max = flagship · prime = faster · plus = balanced · flash = budget · qwq = thinking · omni = omni-modal · vl = vision · realtime = realtime',
    '收录模型': 'Models',
    '模型分类': 'Categories',
    '最大上下文': 'Max context',
    # ---- legend_overrides ----
    '单位：元 CNY / 1M tokens（输入 / 输出），华北2（北京）原价':
        'Unit: CNY / 1M tokens (input / output), North China 2 (Beijing) list price',

    # ---- 通用 section 字段 ----
    '快速选型': 'Quick Picks',
    '按任务类型直达推荐模型': 'Direct recommendation by task type',
    '命名规律速查': 'Naming Conventions',
    '掌握这些规律，看到任何模型名都能秒懂其定位': 'Master these patterns and instantly know any model name',
    '命名规律': 'Naming',
    '命名元素': 'Suffix',
    '含义': 'Meaning',
    '示例': 'Example',
    '文本生成模型': 'Text Generation Models',
    '千问主力文本模型，全系支持混合思考模式（<span class="mono">enable_thinking</span> 开关）与 1M 上下文；视觉输入能力见「视觉理解」章节':
        '''Qwen's core text models; the whole family supports hybrid thinking mode (the <span class="mono">enable_thinking</span> switch) and 1M context; vision input is covered in the "Vision Understanding" section''',
    'QwQ 深度思考模型': 'QwQ Deep Thinking Models',
    '仅思考模式（始终先推理再回答，不可关闭）；若需可控开关，请用文本生成模型的混合思考模式':
        'Thinking-only mode (always reasons before answering; cannot be disabled); for a controllable switch, use the hybrid thinking mode of text generation models',
    '全模态模型（Omni）': 'Omni-Modal Models (Omni)',
    '同时理解文本、音频、图片、视频，输出文本和语音；实时语音对话见「实时语音对话」行':
        '''Understands text, audio, images and video at once; outputs text and speech; for realtime voice chat see the "Realtime voice chat" row''',
    '实时语音翻译（Livetranslate）': 'Realtime Speech Translation (Livetranslate)',
    '语音同传约 3 秒延迟，开箱即用；文件模式支持音视频文件翻译':
        '~3s-latency simultaneous interpretation, works out of the box; file mode translates audio/video files',
    '视觉理解模型（VL / OCR）': 'Vision Understanding Models (VL / OCR)',
    '图像分析、视频理解、OCR 文档提取。注：文本生成章节中的 qwen3.8/3.7/3.6/3.5 全系同样支持视觉输入（1M 上下文、最长 2 小时视频），VL 系列为视觉专用增强':
        'Image analysis, video understanding, OCR document extraction. Note: all qwen3.8/3.7/3.6/3.5 models in the Text Generation section also support vision input (1M context, up to 2h video); the VL series adds vision-specialized enhancements',
    '图像生成模型': 'Image Generation Models',
    '文生图与图片编辑；qwen-image-3.0 系列支持 agent prompt 智能改写与中文文字渲染':
        'Text-to-image and image editing; the qwen-image-3.0 family supports agent prompt rewriting and Chinese text rendering',
    '视频生成模型（万相 / HappyHorse）': 'Video Generation Models (Wanxiang / HappyHorse)',
    '按输出视频秒数计费（输入不计费），部分模型按分辨率分档定价':
        'Billed by output video seconds (input free); some models tiered by resolution',
    '语音识别模型（ASR）': 'Speech Recognition Models (ASR)',
    '实时（WebSocket 流式）与非实时（HTTP 文件转写）两大路线；Qwen-Audio-3.0 系列支持热词与 Prompt 上下文注入':
        'Two paths: realtime (WebSocket streaming) and non-realtime (HTTP file transcription); the Qwen-Audio-3.0 family supports hotwords and Prompt context injection',
    '语音合成模型（TTS）': 'Speech Synthesis Models (TTS)',
    '标准合成 / 声音复刻（音频样本克隆）/ 声音设计（文字描述创建）；指令控制可用自然语言调整语气、情绪、语速':
        'Standard synthesis / voice cloning (audio sample cloning) / voice design (created from text description); instruct mode tunes tone, emotion and speaking rate in natural language',
    '向量与重排序模型': 'Embedding & Rerank Models',
    '语义搜索、RAG 检索与精度提升；重排序建议在 Embedding 检索后对 Top-N 结果二次排序':
        'Semantic search, RAG retrieval and accuracy; rerank is recommended after Embedding retrieval to re-rank Top-N results',
    '专用模型': 'Specialized Models',
    '翻译、文档解析、深度研究与文本分析等垂直场景专用模型':
        'Vertical-use models for translation, document parsing, deep research and text analysis',
    '开源模型（可私有化部署）': 'Open-Source Models (Self-Deployable)',
    '开源权重，可自行部署，无 API 调用限制，仅需硬件成本；百炼同时提供开源版托管调用':
        'Open weights, self-deployable, no API call limits, only hardware costs; Bailian also offers hosted calling of the open-source versions',
    '旧版与即将下线模型': 'Legacy & Retiring Models',
    '以下为本页已收录模型中的旧版/下线信息，请按建议迁移，勿在新项目中使用。数据来源：<a href="https://help.aliyun.com/zh/model-studio/speech-recognition" target="_blank" rel="noopener noreferrer">阿里云百炼官方文档</a>（2026-08-29 同步）':
        '''Legacy/retiring info for the models covered on this page. Migrate as recommended and don't use them in new projects. Source: <a href="https://help.aliyun.com/zh/model-studio/speech-recognition" target="_blank" rel="noopener noreferrer">Alibaba Cloud Bailian official docs</a> (synced 2026-08-29)''',
    '能力矩阵速查': 'Capability Matrix',
    '根据需求快速匹配最佳模型': 'Quickly match the best model to your needs',
    '能力矩阵': 'Capability Matrix',

    # ---- 通用列头 ----
    '模型 ID': 'Model ID',
    '定位': 'Tier',
    '价格': 'Price',
    '模态': 'Modality',
    '思考': 'Thinking',
    '速度': 'Speed',
    '上下文': 'Context',
    '最大输出': 'Max output',
    '说明': 'Notes',
    '输入': 'Input',
    '输出': 'Output',
    'API': 'API',
    '特性': 'Features',
    '类型': 'Type',
    '计费': 'Billing',
    '分辨率': 'Resolution',
    '模式': 'Mode',
    '精度增强': 'Accuracy boost',
    '说话人分离': 'Speaker diarization',
    '时长/大小': 'Duration/Size',
    '系列': 'Series',
    '声音复刻': 'Voice clone',
    '声音设计': 'Voice design',
    '指令控制': 'Instruct',
    '向量维度': 'Dimensions',
    '最大 Token': 'Max tokens',
    '用途': 'Use',
    '语言数': 'Languages',
    '编辑': 'Editing',
    '最大分辨率': 'Max resolution',
    '文生图': 'Text-to-image',
    '需求场景': 'Scenario',
    '推荐模型': 'Recommended',
    '备选模型': 'Alternatives',
    '关键能力': 'Key capability',
    '生命周期': 'Lifecycle',
    '替代方案': 'Replacement',
    '迁移建议': 'Migration advice',

    # ---- quick 卡片任务 ----
    '日常对话 / 写作': 'Chat / Writing',
    '深度思考 / 推理': 'Deep thinking / reasoning',
    '最强旗舰': 'Top flagship',
    '极致省钱': 'Cheapest',
    '专业编程': 'Expert coding',
    '超长文档处理': 'Long-document processing',
    '图像 / 视频理解': 'Image / video understanding',
    '全模态对话': 'Omni-modal chat',
    '实时语音对话': 'Realtime voice chat',
    '语音听录': 'Speech transcription',
    '语音合成': 'Speech synthesis',
    '图像生成': 'Image generation',
    '视频生成': 'Video generation',
    '语义搜索 / RAG': 'Semantic search / RAG',
    '实时语音翻译': 'Realtime speech translation',

    # ---- 命名规律表 ----
    'qwen3.X 版本号': 'qwen3.X version number',
    '数字越大，模型越新越强': 'Higher number = newer and stronger',
    'qwen3 → qwen3.5 → qwen3.8': 'qwen3 → qwen3.5 → qwen3.8',
    '旗舰版，最强能力': 'Flagship, strongest capability',
    '优速模式，更快更强更贵': 'Prime mode, faster, stronger and pricier',
    '均衡增强版': 'Balanced enhanced',
    '轻量快速，极致省钱': 'Lightweight and fast, cheapest',
    '速度优化版（旧代）': 'Speed-optimized (legacy)',
    '深度思考专用（仅思考模式）': 'Deep thinking only (thinking mode)',
    '编程专用': 'Coding',
    '超长文本专用': 'Ultra-long text only',
    '视觉语言模型': 'Vision-language model',
    '全模态（文/图/音/视频）': 'Omni-modal (text/image/audio/video)',
    '文档文字提取': 'Document text extraction',
    '语音识别 / 语音合成': 'Speech recognition / synthesis',
    'WebSocket 实时版': 'WebSocket realtime',
    '文件转写 / 流式实时': 'File transcription / streaming realtime',
    '指令控制 / 声音复刻 / 声音设计': 'Instruct / voice clone / voice design',
    '向量化 / 重排序': 'Embedding / reranking',
    '万相视觉生成（图像/视频）': 'Wanxiang visual generation (image/video)',
    '文生图/文生视频/图生视频/参考视频/声生视频': 'T2I/T2V/I2V/reference-to-video/audio-to-video',
    '最新快照 / 日期快照': 'Latest snapshot / dated snapshot',
    '语音合成 / 语音识别系列': 'Speech synthesis / recognition series',
    '快速图像 / 第三方视频生成': 'Fast image / third-party video generation',

    # ---- 文本生成 / QwQ 等 mdesc ----
    '优速模式（Prime），当前最强，¥24/¥72': 'Prime mode, currently the strongest, ¥24/¥72',
    '最新旗舰，混合思考默认开启，¥12/¥36': 'Latest flagship, hybrid thinking on by default, ¥12/¥36',
    '上代旗舰，限时 5 折': 'Previous-gen flagship, 50% off for a limited time',
    '旗舰平衡之选，¥2/¥8，内置工具+联网': 'Flagship balanced choice, ¥2/¥8, built-in tools + web',
    '稠密 27B 版（1M 上下文），¥3/¥12': 'Dense 27B (1M context), ¥3/¥12',
    '上代均衡版': 'Previous-gen balanced',
    '上代轻量版，¥0.2 起': 'Previous-gen lightweight, from ¥0.2',
    '成熟稳定': 'Mature and stable',
    '最新轻量版，混合思考默认开启，¥0.8/¥2.7': 'Latest lightweight, hybrid thinking on by default, ¥0.8/¥2.7',
    '极致省钱，¥0.2/¥0.8': 'Cheapest, ¥0.2/¥0.8',
    '上代轻量版': 'Previous-gen lightweight',
    '编程专用，Agentic 编程优化，¥4/¥16': 'Coding-specialized, agentic coding optimized, ¥4/¥16',
    '超长文本专用（千万字级），¥0.5/¥2': 'Ultra-long text (tens of millions of chars), ¥0.5/¥2',
    '机器翻译专用，多语言互译': 'Machine translation, multilingual',
    'Qwen3 代旗舰（旧代），¥2.5 起': 'Qwen3-generation flagship (legacy), from ¥2.5',
    '仅思考模式，逻辑/数学推理专用，¥1.6/¥4': 'Thinking-only mode, for logic/math reasoning, ¥1.6/¥4',

    # ---- omni mdesc ----
    '全模态旗舰，音频 3 小时 / 视频 1 小时': 'Omni-modal flagship, 3h audio / 1h video',
    '实时音视频对话': 'Realtime audio/video chat',
    '轻量全模态，¥2.2 起': 'Lightweight omni-modal, from ¥2.2',
    '实时版': 'Realtime',
    '支持思考模式，单次输入限 150 秒': 'Supports thinking mode; single input limited to 150s',
    '实时版，不支持 FC/联网/思考': 'Realtime; no FC/web/thinking',
    'S2S 语音对话旗舰，无意义附和声不打断': '''S2S voice chat flagship; meaningless backchannels won't interrupt''',
    '成本敏感版语音对话': 'Cost-sensitive voice chat',
    '旧版全模态，建议迁移 qwen3.5-omni': 'Legacy omni-modal; migrate to qwen3.5-omni',

    # ---- livetranslate ----
    '<span class="mono-dim">音频 ¥40/1M</span>': '<span class="mono-dim">Audio ¥40/1M</span>',
    '<span class="mono-dim">音频 ¥64/1M</span>': '<span class="mono-dim">Audio ¥64/1M</span>',
    '实时同传首选，29 种语音+31 种文本输出': 'Top choice for realtime interpreting; 29 speech + 31 text outputs',
    '音视频文件翻译': 'Audio/video file translation',
    '上代实时版，含 5 种中文方言': 'Previous-gen realtime, incl. 5 Chinese dialects',
    '文件模式，视频上下文感知': 'File mode, video-context aware',

    # ---- vl mdesc ----
    '视频 1 小时': '1h video',
    '视觉旗舰，¥1/¥10 起': 'Vision flagship, from ¥1/¥10',
    '轻量视觉版': 'Lightweight vision',
    '文档/表格/手写': 'Docs/tables/handwriting',
    'OCR 专用，文字提取精度优化': 'OCR-specialized, optimized text extraction accuracy',
    '旧版 OCR，建议迁移 qwen3.5-ocr': 'Legacy OCR; migrate to qwen3.5-ocr',
    '视觉推理': 'Visual reasoning',
    '旧版视觉推理，能力已并入 Qwen3-VL': 'Legacy visual reasoning; capability merged into Qwen3-VL',
    '旧版视觉推理': 'Legacy visual reasoning',
    '旧版 VL': 'Legacy VL',

    # ---- image mdesc ----
    '图像 3.0 旗舰，agent prompt 改写，小字/多语言渲染':
        'Image 3.0 flagship, agent prompt rewriting, small-text/multilingual rendering',
    '同上，生成速度更快': 'Same as above, faster generation',
    '品牌色调色盘、多图参考（9 张）、角色一致性': 'Brand color palette, multi-image reference (9 images), character consistency',
    '快 10 倍、价格约 1/5，写实人像/产品图': '10x faster, ~1/5 the price, photorealistic portraits/product shots',
    '上代专业版': 'Previous-gen pro',
    '上代标准版': 'Previous-gen standard',
    '旧版旗舰': 'Legacy flagship',
    '旧版均衡': 'Legacy balanced',
    '图片编辑专用': 'Image editing only',
    '图片编辑轻量版': 'Lightweight image editing',
    '万相文生图': 'Wanxiang text-to-image',
    '万相图像生成与编辑': 'Wanxiang image generation & editing',
    '4（连续12）': '4 (12 consecutive)',

    # ---- video mdesc ----
    '0.45-1.8元/秒': '¥0.45-1.8/sec',
    '最新万相视频旗舰': 'Latest Wanxiang video flagship',
    '0.3-1.2元/秒': '¥0.3-1.2/sec',
    '限时 7 折': '30% off for a limited time',
    '0.6-1元/秒': '¥0.6-1/sec',
    '图生视频（有声）': 'Image-to-video (with audio)',
    '参考生视频（有声）': 'Reference-to-video (with audio)',
    '0.45-1.2元/秒': '¥0.45-1.2/sec',
    '限时 6 折，最新第三方视频生成': '60% off for a limited time, latest third-party video generation',
    '图生视频': 'Image-to-video',
    '按秒计费': 'Per-second billing',
    '图片驱动视频': 'Image-driven video',
    '参考生视频': 'Reference-to-video',
    '参考图/角色驱动': 'Reference image/character driven',
    '万相文生视频': 'Wanxiang text-to-video',
    '万相图生视频': 'Wanxiang image-to-video',
    '万相参考生视频': 'Wanxiang reference-to-video',
    '首尾帧视频': 'First/last-frame video',
    '首帧+尾帧插值生成': 'Generated by interpolating first + last frames',
    '声生视频': 'Audio-to-video',
    '音频驱动数字人/动画': 'Audio-driven digital human/animation',
    '动作迁移': 'Motion transfer',
    '将视频动作迁移到图片角色': 'Transfers video motion to an image character',
    '角色替换': 'Character swap',
    '视频中角色替换/混合': 'Character replacement/swap in video',
    '经济版': 'Economy',
    '视频编辑': 'Video editing',
    '万相视频编辑': 'Wanxiang video editing',

    # ---- asr ----
    '实时': 'Realtime',
    '热词+Prompt': 'Hotwords+Prompt',
    '无限制': 'Unlimited',
    '实时识别旗舰，多语种及方言': 'Realtime recognition flagship, multilingual incl. dialects',
    '非实时': 'Non-realtime',
    '支持': 'Yes',
    '12小时/2GB': '12h/2GB',
    '文件转写旗舰，支持说话人分离': 'File transcription flagship, speaker diarization',
    '5分钟/2GB': '5 min/2GB',
    '短音频快速转写': 'Fast short-audio transcription',
    '热词': 'Hotwords',
    'FunASR 实时版': 'FunASR realtime',
    'FunASR 多语种实时版': 'FunASR multilingual realtime',
    'FunASR 文件版，支持说话人分离': 'FunASR file version, speaker diarization',
    'FunASR 多语种版': 'FunASR multilingual',
    '支持情感识别': 'Supports emotion recognition',
    'HTTP(OpenAI兼容)': 'HTTP (OpenAI-compatible)',
    '5分钟/10MB': '5 min/10MB',
    '旧版，建议迁移 Fun-ASR / Qwen-ASR': 'Legacy; migrate to Fun-ASR / Qwen-ASR',
    '旧版': 'Legacy',
    '即将下线，尽快迁移': 'Retiring soon; migrate ASAP',
    '1分钟': '1 min',

    # ---- tts ----
    '最新 TTS 旗舰，全能力': 'Latest TTS flagship, full capability',
    '轻量版': 'Lightweight',
    '支持 SSML 与 LaTeX 公式朗读': 'Supports SSML and LaTeX formula reading',
    '轻量版，1元/万字符': 'Lightweight, ¥1/10K chars',
    '第三方高保真音色': 'Third-party high-fidelity voices',
    '标准合成经济版': 'Economy standard synthesis',
    '指令控制语气/情绪/风格': 'Instructs tone/emotion/style',
    '声音复刻专用': 'Voice cloning only',
    '声音设计专用': 'Voice design only',
    'Qwen-TTS（旧版）': 'Qwen-TTS (Legacy)',
    '按 Token 计费旧版，建议迁移 Qwen3-TTS': 'Legacy token-billed version; migrate to Qwen3-TTS',
    '<span class="mono-dim">0.01元/音色</span>': '<span class="mono-dim">¥0.01/voice</span>',
    '音色管理': 'Voice management',
    '音色注册与管理（声音复刻前置）': 'Voice registration and management (prerequisite for voice cloning)',
    '<span class="mono-dim">0.2元/音色</span>': '<span class="mono-dim">¥0.2/voice</span>',
    '声音设计服务': 'Voice design service',
    '文字描述创建新音色，按个计费': 'Creates new voices from text descriptions, billed per voice',

    # ---- embed ----
    '文本 Embedding': 'Text embedding',
    '最新文本向量，维度兼容 v3，MTEB 领先': 'Latest text embedding, v3-compatible dimensions, MTEB leader',
    '新一代文本向量（Qwen3.7 代），¥0.5': 'New-gen text embedding (Qwen3.7), ¥0.5',
    '已有 v3 索引迁移': 'Migrate existing v3 indexes',
    '多模态 Embedding': 'Multimodal embedding',
    '图文混合检索（融合+独立向量）': 'Image-text hybrid retrieval (fused + independent vectors)',
    '跨模态搜索（独立向量）': 'Cross-modal search (independent vectors)',
    '低成本跨模态': 'Low-cost cross-modal',
    '重排序': 'Rerank',
    '4,000/条': '4,000/passage',
    '100+ 语言，最多 500 文档': '100+ languages, up to 500 docs',
    '多模态重排序': 'Multimodal rerank',
    '8,000/条': '8,000/passage',
    '文本/图片/视频混合排序': 'Text/image/video hybrid ranking',
    '文本语义检索': 'Text semantic retrieval',

    # ---- special ----
    '机器翻译': 'Machine translation',
    '多语言互译专用，支持术语注入': 'Multilingual translation, with terminology injection',
    '文档解析': 'Document parsing',
    '文档内容提取与结构化': 'Document content extraction and structuring',
    '深度研究': 'Deep research',
    '联网检索 + 多步推理 + 长文报告，¥54/¥163': 'Web search + multi-step reasoning + long reports, ¥54/¥163',
    '对话分析': 'Conversation analysis',
    '通义晓蜜专业版，¥1.0/¥2.7': 'Tongyi Xiaomi Pro, ¥1.0/¥2.7',
    '通义晓蜜轻量版，¥0.2/¥0.4': 'Tongyi Xiaomi Lite, ¥0.2/¥0.4',
    '数学推理': 'Math reasoning',
    '数学/竞赛题求解专用，¥4/¥12': 'Math/contest problem solving, ¥4/¥12',
    '数学推理轻量版，¥2/¥6': 'Lightweight math reasoning, ¥2/¥6',
    '轻量版，¥0.7/¥1.95': 'Lightweight, ¥0.7/¥1.95',
    '经济版，¥0.6/¥1.6': 'Economy, ¥0.6/¥1.6',
    '速度优化版，¥0.7/¥1.95': 'Speed-optimized, ¥0.7/¥1.95',
    '图像翻译': 'Image translation',
    '图片中文字翻译为多国语言，0.004元/张': 'Translates text in images into multiple languages, ¥0.004/image',
    '<span class="mono-dim">0.002元/秒</span>': '<span class="mono-dim">¥0.002/sec</span>',
    '音乐生成': 'Music generation',
    '按歌词/提示词生成音乐，按秒计费': 'Generates music from lyrics/prompts, billed per second',

    # ---- opensource ----
    '<span class="tag t-green"><svg class="ic"><use href="#i-home"/></svg>自托管</span>':
        '<span class="tag t-green"><svg class="ic"><use href="#i-home"/></svg>Self-hosted</span>',
    '最新开源旗舰，混合思考默认开启': 'Latest open-source flagship, hybrid thinking on by default',
    '开源均衡版（MoE 35B-A3B）': 'Open-source balanced (MoE 35B-A3B)',
    '开源旗舰（MoE 397B-A17B）': 'Open-source flagship (MoE 397B-A17B)',
    '开源中杯（MoE 122B-A10B）': 'Open-source mid-size (MoE 122B-A10B)',
    '开源小杯（MoE 35B-A3B）': 'Open-source small (MoE 35B-A3B)',
    '开源稠密版 27B': 'Open-source dense 27B',
    'Qwen3-Next 新一代开源 MoE 80B-A3B，¥1/¥4': 'Qwen3-Next new-gen open-source MoE 80B-A3B, ¥1/¥4',
    'Qwen3-Next 思考版（仅思考），¥1/¥10': 'Qwen3-Next thinking edition (thinking-only), ¥1/¥10',
    '开源编程新版，¥1/¥4': 'New open-source coding model, ¥1/¥4',
    'Qwen3 开源旗舰 MoE 235B-A22B': 'Qwen3 open-source flagship MoE 235B-A22B',
    'Qwen3 开源思考旗舰，¥2/¥20': 'Qwen3 open-source thinking flagship, ¥2/¥20',
    '开源视觉旗舰 MoE 235B-A22B': 'Open-source vision flagship MoE 235B-A22B',
    '开源视觉思考旗舰': 'Open-source vision thinking flagship',
    '开源全模态视频字幕/描述': 'Open-source omni-modal video captioning/description',

    # ---- deprecated 迁移建议 ----
    '即将下线，尽快迁移 Fun-ASR / Qwen-ASR': 'Retiring soon; migrate to Fun-ASR / Qwen-ASR',
    '旧版全模态，能力已全面升级': 'Legacy omni-modal; capabilities fully upgraded',
    '按 Token 计费旧版 TTS': 'Legacy token-billed TTS',
    '旧代 ASR，建议迁移': 'Legacy ASR, migration advised',
    '旧代 ASR': 'Legacy ASR',
    '旧版 OCR': 'Legacy OCR',
    '视觉推理能力已并入 Qwen3-VL': 'Visual reasoning merged into Qwen3-VL',

    # ---- matrix ----
    '<span class="tag t-teal"><svg class="ic"><use href="#i-brain"/></svg><span class="dots"><i class="on"></i><i class="on"></i><i class="on"></i><i class="on"></i><i></i></span>深度</span> <span class="plain">+ 1M 上下文</span>':
        '<span class="tag t-teal"><svg class="ic"><use href="#i-brain"/></svg><span class="dots"><i class="on"></i><i class="on"></i><i class="on"></i><i class="on"></i><i></i></span>Deep</span> <span class="plain">+ 1M context</span>',
    '<span class="tag t-teal"><svg class="ic"><use href="#i-brain"/></svg><span class="dots"><i class="on"></i><i class="on"></i><i class="on"></i><i class="on"></i><i class="on"></i></span>最强</span> <span class="plain">混合思考</span>':
        '<span class="tag t-teal"><svg class="ic"><use href="#i-brain"/></svg><span class="dots"><i class="on"></i><i class="on"></i><i class="on"></i><i class="on"></i><i class="on"></i></span>Best</span> <span class="plain">Hybrid thinking</span>',
    '<span class="ctx">¥24/¥72</span> <span class="plain">优速模式</span>':
        '<span class="ctx">¥24/¥72</span> <span class="plain">Prime mode</span>',
    '极致低成本': 'Ultra-low cost',
    'Agentic 编程工作流': 'Agentic coding workflows',
    '<span class="tag mod-ico" title="代码"><svg class="ic"><use href="#i-code"/></svg></span> <span class="plain">+ 1M 上下文</span>':
        '<span class="tag mod-ico" title="Code"><svg class="ic"><use href="#i-code"/></svg></span> <span class="plain">+ 1M context</span>',
    '千万字级': 'Tens of millions of chars',
    '<span class="ctx hi">10M 上下文</span>': '<span class="ctx hi">10M context</span>',
    '<span class="ctx">2 小时视频 · 1M 上下文</span>': '<span class="ctx">2h video · 1M context</span>',
    '全模态理解（图+音+视）': 'Omni-modal understanding (image+audio+video)',
    '<div class="mods"><span class="tag mod-ico" title="文本"><svg class="ic"><use href="#i-text"/></svg></span><span class="tag mod-ico" title="图像"><svg class="ic"><use href="#i-image"/></svg></span><span class="tag mod-ico" title="音频"><svg class="ic"><use href="#i-audio"/></svg></span><span class="tag mod-ico" title="视频"><svg class="ic"><use href="#i-video"/></svg></span></div>':
        '<div class="mods"><span class="tag mod-ico" title="Text"><svg class="ic"><use href="#i-text"/></svg></span><span class="tag mod-ico" title="Image"><svg class="ic"><use href="#i-image"/></svg></span><span class="tag mod-ico" title="Audio"><svg class="ic"><use href="#i-audio"/></svg></span><span class="tag mod-ico" title="Video"><svg class="ic"><use href="#i-video"/></svg></span></div>',
    '<span class="mono-dim">语义 VAD + WebSocket</span>': '<span class="mono-dim">Semantic VAD + WebSocket</span>',
    '语音听录 / 转写': 'Speech transcription / dictation',
    '<span class="mono-dim">12 小时 + 说话人分离</span>': '<span class="mono-dim">12h + speaker diarization</span>',
    '<span class="mono-dim">复刻 / 设计 / 指令控制</span>': '<span class="mono-dim">Clone / Design / Instruct</span>',
    '<span class="ctx">60 语言 · 3 秒延迟</span>': '<span class="ctx">60 languages · 3s latency</span>',
    '高质量图像生成': 'High-quality image generation',
    '<span class="ctx">1080P · 按秒计费</span>': '<span class="ctx">1080P · per-second billing</span>',
    '<span class="ctx">2048 维 + qwen3-rerank</span>': '<span class="ctx">2048-dim + qwen3-rerank</span>',
    '私有化部署': 'Self-hosted deployment',
    '<span class="tag t-teal">开源权重</span>': '<span class="tag t-teal">Open weights</span>',

    # ---- 单元格通用 ----
    '支持': 'Yes',
    '不支持': 'No',
    'FC+联网': 'FC+web',
    '语义VAD+FC': 'Semantic VAD+FC',
    '—': '—',

    # ---- 章节 nav 短词 / video 类型列 ----
    '文本': 'Text',
    '全模态': 'Omni-modal',
    '翻译': 'Translation',
    '视觉': 'Vision',
    '图像': 'Image',
    '视频': 'Video',
    '向量': 'Vector',
    '专用': 'Specialized',
    '文生视频': 'Text-to-video',

    # ---- 徽章（固定映射）----
    '推荐': 'Rec',
    '弃用': 'Deprecated',
    '预览': 'Preview',
    '开源': 'OSS',
    'GA': 'GA',
    '正式版': 'GA',
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
        'zh': {'href': 'qwen-model-userguide.html', 'label': '中'},
        'en': {'href': 'qwen-model-userguide-en.html', 'label': 'EN'},
    }
    for k in ('title', 'h1', 'hero_desc', 'home_title', 'home_label',
              'footer_title', 'footer_rules', 'footer_sources'):
        if k in meta:
            meta[k] = tr(meta[k])
    for s in meta['stats']:
        s['label'] = tr(s['label'])

    # legend_overrides：ranges 为 ¥ 货币数值（语言中立，tr 不会改动），note 翻译
    if 'legend_overrides' in data:
        data['legend_overrides'] = tr(data['legend_overrides'])

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
