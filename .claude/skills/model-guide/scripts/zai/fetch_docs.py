"""【智谱 Z.ai 专用】抓取 BigModel 官方文档并转为结构化文本（ROW: 格式）。

用法:
    python scripts/zai/fetch_docs.py <别名或URL> [-o 输出.txt]
    python scripts/zai/fetch_docs.py overview pricing -o out/

说明:
    - docs.bigmodel.cn 与 open.bigmodel.cn 均可直连，无需代理
    - overview 为静态 HTML，直接抓取解析
    - pricing 是 Vue SPA，需要 Playwright 渲染；若未安装可用手动保存的 HTML：
      python scripts/zai/fetch_docs.py --local-pricing pricing.html -o out/
    - 已验证可用的页面别名：
        overview（模型总览） = docs.bigmodel.cn/cn/guide/start/model-overview
        pricing（产品价格）  = open.bigmodel.cn/pricing

示例:
    python scripts/zai/fetch_docs.py overview -o _g_zai_overview.txt
    python scripts/zai/fetch_docs.py pricing -o _g_zai_pricing.txt
    python scripts/zai/fetch_docs.py overview pricing -o _g_zai/
"""
import re, sys, os, html as H
from urllib.request import Request, urlopen
from urllib.error import URLError

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

ALIASES = {
    'overview': 'https://docs.bigmodel.cn/cn/guide/start/model-overview',
    'pricing': 'https://open.bigmodel.cn/pricing',
}


def fetch(url, out_html, max_tries=3):
    req = Request(url, headers={
        'User-Agent': UA,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    })
    for attempt in range(max_tries):
        try:
            with urlopen(req, timeout=60) as resp:
                data = resp.read()
            with open(out_html, 'wb') as f:
                f.write(data)
            if os.path.getsize(out_html) > 20000:
                return True
        except URLError as e:
            print(f'  重试 {attempt + 1}/{max_tries}: {e}', flush=True)
    return False


def fetch_with_playwright(url, out_html, wait_selector='table', timeout=60000):
    """使用 Playwright 渲染 SPA 页面并保存完整 HTML"""
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        return False, '未安装 playwright（pip install playwright）'
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--disable-logging', '--log-level=3', '--no-sandbox', '--disable-setuid-sandbox']
            )
            page = browser.new_page(user_agent=UA, viewport={'width': 1280, 'height': 900})
            page.goto(url, wait_until='networkidle', timeout=timeout)
            try:
                page.wait_for_selector(wait_selector, timeout=timeout)
            except PWTimeout:
                pass
            page.wait_for_timeout(2000)  # 等待表格/卡片动画完成
            html = page.content()
            browser.close()
        with open(out_html, 'w', encoding='utf-8') as f:
            f.write(html)
        if len(html) > 50000:
            return True, ''
        return False, '渲染后内容过短，可能页面结构变化'
    except Exception as e:
        return False, str(e)


def clean_cell(cell):
    """清理单元格 HTML 为单行文本"""
    cell = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', cell, flags=re.S)
    cell = re.sub(r'<br\s*/?>', '\n', cell, flags=re.I)
    cell = re.sub(r'</p>|<div[^>]*>', '\n', cell, flags=re.I)
    cell = re.sub(r'<[^>]+>', ' ', cell)
    cell = H.unescape(cell)
    cell = re.sub(r'[ \t]+', ' ', cell)
    cell = re.sub(r'\n\s*\n+', '\n', cell).strip()
    return cell


def table_to_rows(html):
    """提取 <table> 为 ROW: 格式文本"""
    rows = []
    for table in re.findall(r'<table[^>]*>(.*?)</table>', html, flags=re.S | re.I):
        for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', table, flags=re.S | re.I):
            cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, flags=re.S | re.I)
            if not cells:
                continue
            cells = [clean_cell(c) for c in cells]
            if any(c for c in cells):
                rows.append('ROW: ' + ' | '.join(cells))
    return rows


def section_cards(html):
    """提取价格页中卡片式模型信息（非表格部分）。

    pricing 页面除表格外，部分区域以卡片/列表展示模型，本函数作为表格补充。
    识别策略：在 <section> 或 <div> 块内，若连续出现"模型名称/Model"与"价格/Pricing"
    等标签，则把键值对提取为 CARD。
    """
    cards = []
    # 按语义块切分（section / 大卡片容器 / 独立 div）
    chunks = re.split(r'</(?:section|article|main)>', html, flags=re.S | re.I)
    for chunk in chunks:
        # 只保留包含模型相关标签的块
        if not re.search(r'(模型名称|Model|模型 ID|模型ID|价格|Pricing|单价)', chunk, re.I):
            continue
        # 提取键值对：标签在一对标签内，值在下一对标签内
        pairs = []
        for m in re.finditer(r'<(?:div|span|p|label)[^>]*>([^<]{1,40}?)</(?:div|span|p|label)>\s*<(?:div|span|p)[^>]*>([^<]{1,120}?)</(?:div|span|p|label)>', chunk, flags=re.S | re.I):
            lab, val = m.group(1).strip(), m.group(2).strip()
            if lab and val and lab not in ('', '—', '-'):
                pairs.append(f'{lab}: {val}')
        if len(pairs) >= 2:
            cards.append('CARD: ' + ' · '.join(pairs[:10]))
    return cards


def to_text(html):
    body = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.S)

    # 标题
    body = re.sub(r'<h([1-4])[^>]*>', r'\n\nH\1: ', body, flags=re.S)
    body = re.sub(r'</h[1-4]>', '\n', body, flags=re.S)

    # 列表
    body = re.sub(r'<li[^>]*>', '\n- ', body, flags=re.S)

    # 段落
    body = re.sub(r'<p[^>]*>', '\n', body, flags=re.S)
    body = re.sub(r'</p>', '\n', body, flags=re.S)

    # 表格单独处理：先占位，避免被 strip tags 破坏
    tables = []
    def store_table(m):
        tables.append(m.group(0))
        return f'\n__TABLE_{len(tables)-1}__\n'
    body = re.sub(r'<table[^>]*>.*?</table>', store_table, body, flags=re.S | re.I)

    body = re.sub(r'<[^>]+>', ' ', body)
    body = H.unescape(body)
    body = re.sub(r'[ \t]+', ' ', body)
    body = re.sub(r'\n\s*\n+', '\n', body)

    # 还原表格
    for i, tbl in enumerate(tables):
        rows = table_to_rows(tbl)
        body = body.replace(f'__TABLE_{i}__', '\n'.join(rows) if rows else '')

    # 额外提取价格页卡片
    cards = section_cards(html)
    if cards:
        body += '\n\nCARDS:\n' + '\n'.join(cards)

    return body.strip()


def main():
    args = sys.argv[1:]
    targets, out, local_pricing = [], None, None
    i = 0
    while i < len(args):
        if args[i] == '-o':
            out = args[i + 1]; i += 2
        elif args[i] == '--local-pricing':
            local_pricing = args[i + 1]; i += 2
        else:
            targets.append(args[i]); i += 1
    if not targets:
        raise SystemExit('用法: python scripts/zai/fetch_docs.py <别名或URL> [-o 输出] [--local-pricing pricing.html]')

    for t in targets:
        url = ALIASES.get(t, t)
        name = re.sub(r'[^a-z0-9]+', '_', t.lower()).strip('_') or 'page'
        tmp = f'_g_zai_{name}.html'
        try:
            if t == 'pricing' and local_pricing:
                if not os.path.exists(local_pricing):
                    print(f'{t}: 本地文件不存在 {local_pricing}', flush=True)
                    continue
                html = open(local_pricing, encoding='utf-8').read()
            else:
                if not fetch(url, tmp):
                    if t == 'pricing':
                        print(f'{t}: 静态抓取失败，尝试 Playwright 渲染...', flush=True)
                        ok, err = fetch_with_playwright(url, tmp)
                        if not ok:
                            print(f'{t}: Playwright 渲染失败: {err}', flush=True)
                            print(f'      可手动保存页面后使用: python scripts/zai/fetch_docs.py --local-pricing pricing.html pricing -o _g_zai/', flush=True)
                            continue
                    else:
                        print(f'{t}: 抓取失败', flush=True)
                        continue
                html = open(tmp, encoding='utf-8').read()
            text = to_text(html)
            if out and len(targets) == 1 and not out.endswith('/'):
                out_path = out
            else:
                os.makedirs(out or '.', exist_ok=True)
                out_path = os.path.join(out or '.', f'{name}.txt')
            open(out_path, 'w', encoding='utf-8').write(text)
            print(f'{t}: {out_path} ({len(text)} chars, {text.count("ROW:")} rows, {text.count("CARD:")} cards)', flush=True)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)


if __name__ == '__main__':
    main()
