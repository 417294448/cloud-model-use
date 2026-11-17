# -*- coding: utf-8 -*-
"""【Anthropic 专用】从 anthropic.com 官方模型页发现各系列最新版本与价格，
并与 data/anthropic.json 比对，报告「官方已发布但页面未收录」的模型。

背景（2026-11-17 踩坑沉淀）：
    - platform.claude.com 文档站在本环境再次受地域限制（307 → app-unavailable-in-region），
      requests / curl 均拿不到正文，只能依赖 WebFetch/WebSearch 快照；
    - 仅核对 pricing / model-deprecations / models-overview 三页会漏掉刚发布的模型：
      2026-11-09 发布的 claude-fable-5-2 未及时出现在这三页的摘要中，导致上一轮误判「无变更」；
    - www.anthropic.com 的系列页（/claude/fable|opus|sonnet|haiku）与发布公告可直连，
      正文含「Claude Fable 5.2」「priced at $8 per million input tokens and $40 ...」等最新信息，
      是发现新版本最可靠的通道。

用法（在项目根目录执行）：
    python .claude/skills/model-guide/scripts/anthropic/fetch_models.py
    python .claude/skills/model-guide/scripts/anthropic/fetch_models.py --write-json _anthropic_latest.json
    python .claude/skills/model-guide/scripts/anthropic/fetch_models.py --offline-dir _anthropic_pages

退出码：0=数据已覆盖官方最新版本；1=存在未收录的新版本；2=抓取失败。
"""
import argparse
import glob
import json
import os
import re
import sys
import time

import requests
from bs4 import BeautifulSoup

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(os.path.dirname(HERE))  # .claude/skills/model-guide
DATA = os.path.join(SKILL_DIR, 'data', 'anthropic.json')

FAMILIES = ['fable', 'opus', 'sonnet', 'haiku']
BASE = 'https://www.anthropic.com/claude/'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')
TIMEOUT = 30
RETRIES = 3


def fetch(url):
    """抓取页面 HTML（带重试）；失败返回 None。"""
    for attempt in range(1, RETRIES + 1):
        try:
            r = requests.get(url, headers={'User-Agent': UA, 'Accept-Language': 'en-US,en;q=0.9'},
                             timeout=TIMEOUT)
            r.raise_for_status()
            if len(r.content) < 20000:
                raise RuntimeError(f'suspicious short page ({len(r.content)} bytes)')
            return r.content.decode('utf-8', errors='replace')
        except Exception as e:
            print(f'  ! {attempt}/{RETRIES} {url}: {e}', file=sys.stderr)
            if attempt < RETRIES:
                time.sleep(2 * attempt)
    return None


def page_text(html):
    return re.sub(r'\s+', ' ', BeautifulSoup(html, 'lxml').get_text(' '))


def version_key(v):
    return tuple(int(x) for x in v.split('.'))


def latest_in_family(text, family):
    """返回页面中出现的该系列最高版本，如 '5.2'。"""
    pat = re.compile(r'Claude\s+' + family.capitalize() + r'\s+(\d+(?:\.\d+)?)')
    versions = [m.group(1) for m in pat.finditer(text)]
    if not versions:
        return None, []
    uniq = sorted(set(versions), key=version_key, reverse=True)
    return uniq[0], uniq


def parse_price(text, family, version):
    """尽量解析最新版本的输入/输出价（USD / 1M tokens）。"""
    label = f'{family.capitalize()} {version}'
    # 例：Claude Fable 5.2 is priced at $8 per million input tokens and $40 per million output tokens
    for m in re.finditer(r'\$(\d+(?:\.\d+)?)\s+per million input tokens and \$(\d+(?:\.\d+)?)\s+per million output tokens', text):
        ctx = text[max(0, m.start() - 260):m.end()]
        if label in ctx:
            return {'input': m.group(1), 'output': m.group(2)}
    # 回退：取页面第一处价格表述（首页通常即最新款）
    m = re.search(r'\$(\d+(?:\.\d+)?)\s+per million input tokens and \$(\d+(?:\.\d+)?)\s+per million output tokens', text)
    if m:
        return {'input': m.group(1), 'output': m.group(2)}
    return None


def model_id(family, version):
    return f'claude-{family}-{version.replace(".", "-")}'


def data_model_ids():
    d = json.load(open(DATA, encoding='utf-8'))
    ids = set()
    for sec in d.get('sections', []):
        for row in sec.get('rows', []):
            if not row:
                continue
            cell = row[0]
            if isinstance(cell, dict) and cell.get('type') == 'model_id':
                ids.add(cell['v'])
            elif isinstance(cell, dict) and 'id' in cell:
                ids.add(cell['id'])
            elif isinstance(cell, str):
                ids.add(cell)
    return {i for i in ids if i.startswith('claude-')}


def offline_text(directory, family):
    for ext in ('html', 'htm', 'txt', 'md'):
        for p in glob.glob(os.path.join(directory, f'{family}*.{ext}')):
            raw = open(p, encoding='utf-8', errors='replace').read()
            return page_text(raw) if '<' in raw[:200] else re.sub(r'\s+', ' ', raw)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--offline-dir', help='从已保存的系列页（fable/opus/sonnet/haiku.html|txt）解析，不联网')
    ap.add_argument('--write-json', help='把抓取结果写入 JSON 文件')
    args = ap.parse_args()

    results, failed = [], []
    for fam in FAMILIES:
        if args.offline_dir:
            text = offline_text(args.offline_dir, fam)
            if text is None:
                failed.append(fam)
                continue
        else:
            html = fetch(BASE + fam)
            if html is None:
                failed.append(fam)
                continue
            text = page_text(html)
        ver, all_vers = latest_in_family(text, fam)
        results.append({
            'family': fam,
            'latest': ver,
            'versions': all_vers,
            'model_id': model_id(fam, ver) if ver else None,
            'price': parse_price(text, fam, ver) if ver else None,
            'source': (args.offline_dir or BASE + fam),
        })

    print('== anthropic.com 系列页最新版本 ==')
    for r in results:
        price = r['price']
        price_s = f"${price['input']}/${price['output']}" if price else '价格未解析'
        print(f"  {r['family']:8s} 最新 {r['latest'] or '-':6s} → {r['model_id'] or '-':24s} {price_s}")

    if failed:
        print(f'!! 抓取失败：{", ".join(failed)}（网络受限时可用 --offline-dir 传入浏览器保存的页面）',
              file=sys.stderr)
        if len(failed) == len(FAMILIES):
            return 2

    ids = data_model_ids()
    missing = [r for r in results if r['model_id'] and r['model_id'] not in ids]
    if missing:
        print('\n!! 官方已发布但 data/anthropic.json 未收录：')
        for r in missing:
            print(f"  - {r['model_id']}（{r['family'].capitalize()} {r['latest']}，"
                  f"来源 {r['source']}）")
    else:
        print('\nOK: 各系列最新版本均已收录')

    if args.write_json:
        json.dump(results, open(args.write_json, 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=2)
        print(f'wrote {args.write_json}')

    return 1 if missing else 0


if __name__ == '__main__':
    sys.exit(main())
