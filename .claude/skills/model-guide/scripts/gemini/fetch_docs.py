"""【Google Gemini 专用】抓取 ai.google.dev 文档页并转为结构化文本（ROW: 格式）。

用法:
    python scripts/gemini/fetch_docs.py <别名或URL> [-o 输出.txt]
    python scripts/gemini/fetch_docs.py models pricing deprecations -o out/

说明:
    - ai.google.dev / cloud.google.com 在本项目网络下直连超时，allorigins/codetabs 等
      公共代理对 Google 源站返回 520/522；**经实测 proxy.cors.sh 通道可用**
    - 已验证可用的页面（/gemini-api/docs/ 别名）：
        models（模型清单）、pricing（价格）、deprecations（关停计划）

示例:
    python scripts/gemini/fetch_docs.py pricing -o pricing.txt
"""
import re, json, sys, os, subprocess, html as H

PROXIES = [
    "https://proxy.cors.sh/",
    "https://corsproxy.org/?",
    "https://api.allorigins.win/raw?url=",
]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def fetch(url, out_html, max_tries=6):
    """多代理轮询重试：proxy.cors.sh 与 corsproxy.org 已验证可达 Google 文档，
    但公共代理均有速率限制，需要轮询+重试"""
    for attempt in range(max_tries):
        proxy = PROXIES[attempt % len(PROXIES)]
        subprocess.run(["curl", "-sL", "--max-time", "60", "--tlsv1.2", "-A", UA,
                        proxy + url, "-o", out_html, "-w", "%{http_code}"],
                       capture_output=True, text=True)
        if os.path.exists(out_html) and os.path.getsize(out_html) > 30000:
            return True
    return False


def to_text(src):
    body = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', src, flags=re.S)
    body = re.sub(r'<tr[^>]*>', '\nROW: ', body)
    body = re.sub(r'<t[dh][^>]*>', ' | ', body)
    body = re.sub(r'<h([1-4])[^>]*>', r'\n\nH\1: ', body)
    body = re.sub(r'<li[^>]*>', '\n- ', body)
    body = re.sub(r'<p[^>]*>', '\n', body)
    body = re.sub(r'<[^>]+>', '', body)
    body = H.unescape(body)
    body = re.sub(r'[ \t]+', ' ', body)
    body = re.sub(r'\n\s*\n+', '\n', body)
    return body


def main():
    args = sys.argv[1:]
    targets, out = [], None
    i = 0
    while i < len(args):
        if args[i] == '-o':
            out = args[i + 1]; i += 2
        else:
            targets.append(args[i]); i += 1
    if not targets:
        raise SystemExit('用法: python scripts/gemini/fetch_docs.py <别名或URL> [-o 输出]')

    for t in targets:
        url = t if t.startswith('http') else f'https://ai.google.dev/gemini-api/docs/{t}'
        name = re.sub(r'[^a-z0-9]+', '_', t.lower()).strip('_') or 'page'
        tmp = f'_gemini_{name}.html'
        try:
            if not fetch(url, tmp):
                print(f'{t}: 抓取失败', flush=True)
                continue
            text = to_text(open(tmp, encoding='utf-8').read())
            if out and len(targets) == 1 and not out.endswith('/'):
                out_path = out
            else:
                os.makedirs(out or '.', exist_ok=True)
                out_path = os.path.join(out or '.', f'{name}.txt')
            open(out_path, 'w', encoding='utf-8').write(text)
            print(f'{t}: {out_path} ({len(text)} chars, {text.count("ROW:")} rows)', flush=True)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)


if __name__ == '__main__':
    main()
