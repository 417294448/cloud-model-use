"""批量抓取 developers.openai.com 模型详情页（经 allorigins 代理 + 重试）。

用法:
    python scripts/openai/fetch_models.py [slug ...] [--md] [--out DIR]
    python scripts/openai/fetch_models.py            # 抓取内置默认清单
    python scripts/openai/fetch_models.py --md       # 抓取 .md Markdown 版本

说明:
    - developers.openai.com 被 Cloudflare 拦截，必须经 api.allorigins.win 代理
    - 代理约 70% 概率返回 52x 错误（响应体 16 字节），每个页面重试 MAX_TRIES 次
    - 已成功（>100KB 的 HTML 或 >500B 的 md）的页面自动跳过，可反复运行补漏
    - 批量抓取建议放后台：30+ 页面约需 10-20 分钟
"""
import subprocess, sys, time, os

DEFAULT_SLUGS = [
    # Frontier
    "gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-5.6-cyber",
    "gpt-5.5", "gpt-5.4", "gpt-5.4-pro", "gpt-5.4-mini", "gpt-5.4-nano",
    "gpt-5.3-codex", "gpt-5.2", "gpt-5.2-pro", "gpt-5.1",
    "gpt-5", "gpt-5-pro", "gpt-5-mini", "gpt-5-nano",
    "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano",
    # Codex
    "gpt-5.2-codex", "gpt-5.1-codex", "gpt-5.1-codex-max", "gpt-5.1-codex-mini", "gpt-5-codex",
    # o 系列
    "o1", "o1-pro", "o3", "o3-pro", "o3-mini", "o4-mini", "o4-mini-deep-research",
    # 图像/视频
    "gpt-image-2", "gpt-image-1.5", "gpt-image-1", "gpt-image-1-mini", "sora-2", "sora-2-pro",
    # 音频
    "gpt-realtime-2.1", "gpt-realtime-2.1-mini", "gpt-realtime-2", "gpt-realtime-1.5",
    "gpt-realtime-mini", "gpt-realtime-translate", "gpt-realtime-whisper",
    "gpt-live-transcribe", "gpt-transcribe", "gpt-4o-transcribe",
    "gpt-4o-mini-transcribe", "gpt-4o-mini-tts", "gpt-audio-mini",
    # 其他
    "gpt-oss-120b", "gpt-oss-20b", "gpt-4o", "gpt-4o-mini",
    "text-embedding-3-small", "text-embedding-ada-002",
]

PROXY = "https://api.allorigins.win/raw?url=developers.openai.com/api/docs/models/"
MAX_TRIES = 8


def fetch(slug, out_dir, use_md):
    suffix = ".md" if use_md else ""
    ext = ".md" if use_md else ".html"
    out = os.path.join(out_dir, slug.replace(".", "_") + ext)
    min_size = 500 if use_md else 100000
    if os.path.exists(out) and os.path.getsize(out) > min_size:
        return "cached"
    url = PROXY + slug + suffix
    for i in range(MAX_TRIES):
        subprocess.run(
            ["curl", "-sL", "--max-time", "40", "--tlsv1.2", "-A", "Mozilla/5.0",
             url, "-o", out, "-w", "%{http_code}"],
            capture_output=True, text=True)
        size = os.path.getsize(out) if os.path.exists(out) else 0
        if size > min_size:
            return f"ok(try{i+1})"
        time.sleep(3)
    return "FAIL"


def main():
    args = sys.argv[1:]
    use_md = "--md" in args
    out_dir = "_model_md" if use_md else "_model_pages"
    if "--out" in args:
        i = args.index("--out")
        out_dir = args[i + 1]
        del args[i:i + 2]
    slugs = [a for a in args if not a.startswith("--")] or DEFAULT_SLUGS
    os.makedirs(out_dir, exist_ok=True)
    failed = []
    for slug in slugs:
        res = fetch(slug, out_dir, use_md)
        print(f"{slug}: {res}", flush=True)
        if res == "FAIL":
            failed.append(slug)
    if failed:
        print(f"\n失败 {len(failed)} 个（可重跑本脚本补漏）: {', '.join(failed)}")


if __name__ == "__main__":
    main()
