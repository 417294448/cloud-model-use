# -*- coding: utf-8 -*-
"""【OpenAI 专用】批量抓取 developers.openai.com 模型详情页（直连，参照 openai-scratch 方法）。

背景（2026-09-01 实测更新）:
    - developers.openai.com 当前可直连（requests + 浏览器 UA + 重试），无需 allorigins 代理
    - 列表页 /api/docs/models/all 自动发现全量 slug（当前 96 个），不再维护硬编码清单
    - 详情页 HTML 约 300-420KB；追加 .md 的 Markdown 版本约 3-4KB（含价格表/上下文/输入输出），
      比解析 HTML 更可靠，优先用于拿价格与 token 数，HTML 指标卡用于拿推理/速度格数
    - 重要：HTML 必须用 r.content.decode('utf-8') 解码，否则 • 等字符会变成 â€¢，
      导致 parse_cards.py 的 PRICE_RE 匹配不到价格
    - 若未来再次被 Cloudflare 拦截，可回退 allorigins 代理（见 references/providers/openai.md）

用法:
    python scripts/openai/fetch_models.py                 # 抓列表页 + 全部模型详情页(HTML)
    python scripts/openai/fetch_models.py --md            # 追加抓 .md Markdown 版本到 _model_md/
    python scripts/openai/fetch_models.py --limit 5       # 联调模式：只抓前 5 个
    python scripts/openai/fetch_models.py --refresh       # 忽略缓存强制重抓全部
    python scripts/openai/fetch_models.py --list          # 只抓列表页并打印 slug 分类清单
    python scripts/openai/fetch_models.py gpt-5.4 o3-pro  # 只抓指定 slug（默认自动发现全量）

输出（兼容 parse_cards.py）:
    - _model_pages/<slug>.html    详情页 HTML 缓存（slug 中 . → _，断点续跑）
    - _model_md/<slug>.md         Markdown 版本缓存（--md 时）
    - _openai_models_list.json    列表页 slug + 分类清单（发现新模型的途径）
    - raw_models_all.html         列表页原始 HTML 存档

退出码: 0=全部成功/缓存  1=存在失败项
"""
import argparse
import json
import os
import re
import sys
import time

import requests
from bs4 import BeautifulSoup

LIST_URL = "https://developers.openai.com/api/docs/models/all"
BASE = "https://developers.openai.com/api/docs/models"

# 分类区块 id -> 展示名（按页面顺序，与 openai-scratch 一致）
CATEGORY_IDS = [
    ("frontier", "Flagship models"),
    ("image", "Image"),
    ("realtime-audio", "Realtime & audio"),
    ("daybreak", "OpenAI Daybreak"),
    ("open", "Open-weight models"),
    ("embeddings", "Embedding models"),
    ("all", "More models"),
    ("chatgpt", "ChatGPT models"),
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

REQUEST_TIMEOUT = 30     # 单次请求超时(秒)
MAX_RETRIES = 5          # 最大重试次数
RETRY_BACKOFF = 2.0      # 重试退避基数(秒)
REQUEST_INTERVAL = 0.3   # 请求间隔(秒)，礼貌抓取
MIN_HTML_LENGTH = 100000  # 详情页 HTML 有效性下限（正常约 300-420KB，低于此视为验证页/错误页）
MIN_MD_LENGTH = 500      # Markdown 版本有效性下限（正常约 3-4KB）


class Fetcher:
    """带重试、UA 轮换与内容有效性校验的抓取器（直连，参照 openai-scratch）"""

    def __init__(self, interval=REQUEST_INTERVAL):
        self.interval = interval
        self._ua_idx = 0

    def _headers(self):
        self._ua_idx = (self._ua_idx + 1) % len(USER_AGENTS)
        return {
            "User-Agent": USER_AGENTS[self._ua_idx],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://developers.openai.com/",
        }

    def fetch(self, url, min_len=MIN_HTML_LENGTH):
        """带重试的 GET，返回按 UTF-8 解码的页面文本；校验失败抛异常。
        必须用 r.content.decode('utf-8')：requests 在无 charset 时默认按 ISO-8859-1 解码，
        会把 UTF-8 的 •（0xE2 0x80 0xA2）误读成 â€¢，破坏后续正则解析。"""
        last_err = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                r = requests.get(url, headers=self._headers(), timeout=REQUEST_TIMEOUT)
                if r.status_code == 429:
                    raise RuntimeError("HTTP 429 rate limited")
                r.raise_for_status()
                text = r.content.decode("utf-8", errors="replace")
                if len(text) < min_len:
                    raise RuntimeError(
                        f"suspicious short page ({len(text)} bytes), possible block/error page"
                    )
                return text
            except Exception as e:
                last_err = e
                print(f"  ! attempt {attempt}/{MAX_RETRIES} failed for {url}: {e}", file=sys.stderr)
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF * attempt)
        raise RuntimeError(f"all {MAX_RETRIES} attempts failed for {url}: {last_err}")


def parse_list_page(html):
    """解析列表页: 提取分类 + 模型 slug（保持页面顺序，去重），返回 [{slug, category}]"""
    soup = BeautifulSoup(html, "lxml")
    main = soup.find("main")
    models = []
    seen = set()
    for cid, cat_name in CATEGORY_IDS:
        blk = main.find(id=cid) if main else None
        if not blk:
            continue
        for a in blk.find_all("a", href=re.compile(r"^/api/docs/models/[^?#]+$")):
            slug = a["href"].rsplit("/", 1)[-1]
            if slug in seen:
                continue
            seen.add(slug)
            models.append({"slug": slug, "category": cat_name})
    return models


def out_name(slug, ext):
    """slug → 缓存文件名（. → _，与 parse_cards.py 的还原逻辑一致）"""
    return slug.replace(".", "_") + ext


def fetch_one(fetcher, slug, out_dir, use_md, refresh, verbose=False):
    """抓单个模型: HTML（必抓，供 parse_cards.py 解析指标卡）+ .md（--md 时）。
    返回状态描述字符串。"""
    statuses = []
    jobs = [("html", ".html", MIN_HTML_LENGTH, "_model_pages", False)]
    if use_md:
        jobs.append(("md", ".md", MIN_MD_LENGTH, "_model_md", True))
    for kind, ext, min_len, sub, is_md in jobs:
        d = os.path.join(out_dir, sub)
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, out_name(slug, ext))
        if not refresh and os.path.exists(path) and os.path.getsize(path) > min_len:
            statuses.append(f"{kind}:cached")
            continue
        url = f"{BASE}/{slug}" + (".md" if is_md else "")
        try:
            text = fetcher.fetch(url, min_len=min_len)
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            statuses.append(f"{kind}:ok")
        except Exception as e:
            statuses.append(f"{kind}:FAIL")
            print(f"  ! {slug} {kind} FAILED: {e}", file=sys.stderr)
        time.sleep(fetcher.interval)
    return " ".join(statuses)


def fetch_list(fetcher, out_dir, refresh):
    """抓列表页，返回 (list_html, model_items)；列表页已缓存且非 refresh 时复用"""
    list_path = os.path.join(out_dir, "raw_models_all.html")
    os.makedirs(out_dir, exist_ok=True)
    if refresh or not os.path.exists(list_path):
        print(f"fetching list page: {LIST_URL}")
        list_html = fetcher.fetch(LIST_URL, min_len=MIN_HTML_LENGTH)
        with open(list_path, "w", encoding="utf-8") as f:
            f.write(list_html)
        print(f"list page saved ({len(list_html)} bytes)")
    else:
        list_html = open(list_path, encoding="utf-8").read()
        print(f"reuse cached list page ({len(list_html)} bytes)")
    model_items = parse_list_page(list_html)
    print(f"list page parsed: {len(model_items)} models")
    return list_html, model_items


def cmd_fetch(args):
    out_dir = args.out_dir
    os.makedirs(out_dir, exist_ok=True)
    fetcher = Fetcher(interval=args.interval)

    list_html, model_items = fetch_list(fetcher, out_dir, args.refresh)

    # slug 清单落盘（发现新模型的途径）
    list_json = os.path.join(out_dir, "_openai_models_list.json")
    json.dump({"source_url": LIST_URL, "model_count": len(model_items),
               "models": model_items}, open(list_json, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"slug list -> {list_json} ({len(model_items)} models)")

    # 指定 slug 或全量
    if args.slugs:
        items = [{"slug": s, "category": ""} for s in args.slugs]
        print(f"using {len(items)} specified slug(s)")
    else:
        items = model_items
        if args.limit:
            items = items[: args.limit]
            print(f"--limit={args.limit} applied, processing {len(items)} models")

    # 逐个抓取
    failed = []
    for i, item in enumerate(items, 1):
        slug = item["slug"]
        res = fetch_one(fetcher, slug, out_dir, args.md, args.refresh, verbose=args.verbose)
        print(f"[{i}/{len(items)}] {slug}: {res}", flush=True)
        if "FAIL" in res:
            failed.append(slug)

    if failed:
        print(f"\n失败 {len(failed)} 个（可重跑本脚本补漏）: {', '.join(failed)}", file=sys.stderr)
        return 1
    print("\n全部完成，0 失败")
    return 0


def cmd_list(args):
    """仅抓列表页并打印 slug 分类清单（发现新模型的途径）"""
    out_dir = args.out_dir
    fetcher = Fetcher(interval=args.interval)
    list_html, model_items = fetch_list(fetcher, out_dir, args.refresh)
    by_cat = {}
    for m in model_items:
        by_cat.setdefault(m["category"], []).append(m["slug"])
    for cat, slugs in by_cat.items():
        print(f"{cat} ({len(slugs)}):")
        for s in slugs:
            print(f"  - {s}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="fetch_models",
        description="批量抓取 developers.openai.com 模型详情页（直连，自动发现全量 slug）",
    )
    parser.add_argument("slugs", nargs="*", help="指定 slug（默认自动发现列表页全部模型）")
    parser.add_argument("--md", action="store_true", help="同时抓 .md Markdown 版本到 _model_md/")
    parser.add_argument("--refresh", action="store_true", help="忽略缓存强制重新抓取")
    parser.add_argument("--limit", type=int, default=0, help="仅处理前 N 个模型（联调模式）")
    parser.add_argument("--interval", type=float, default=REQUEST_INTERVAL,
                        help="请求间隔秒数（默认 %.1f）" % REQUEST_INTERVAL)
    parser.add_argument("--out-dir", default=".", help="输出目录（默认当前目录）")
    parser.add_argument("--verbose", action="store_true", help="输出 DEBUG 信息")
    parser.add_argument("--list", action="store_true", help="仅抓列表页并打印 slug 分类清单")
    args = parser.parse_args(argv)
    try:
        code = cmd_list(args) if args.list else cmd_fetch(args)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        code = 130
    except Exception as e:
        print(f"unexpected error: {e}", file=sys.stderr)
        code = 2
    sys.exit(code)


if __name__ == "__main__":
    main()
