"""【阿里云百炼专用】抓取 help.aliyun.com 文档页并转为结构化文本（ROW: 格式）。

用法:
    python scripts/qwen/fetch_docs.py <别名或URL> [-o 输出.txt]
    python scripts/qwen/fetch_docs.py vision-model image-model omni -o out/

说明:
    - help.aliyun.com 可直连（与 OpenAI 官网不同，无需代理）
    - 页面是 ICE 框架 SPA，正文内嵌在 window.__ICE_PAGE_PROPS__ 的
      docDetailData.storeData.data.content 字段中，本脚本负责提取
    - 已验证可用的页面（/zh/model-studio/ 别名）：
        models（模型总览）、billing（价格）、vision-model、image-model、omni、
        s2s-model、tts-model、speech-recognition、embedding-rerank-model、
        qwq、text-generation、fun-music、tripo-3d-generation-guide

示例:
    python scripts/qwen/fetch_docs.py billing -o billing.txt
    python scripts/qwen/fetch_docs.py vision-model -o pages/
"""
import re, json, sys, os, subprocess, html as H

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def fetch(url, out_html, max_tries=3):
    for _ in range(max_tries):
        subprocess.run(["curl", "-sL", "--max-time", "40", "-A", UA, url, "-o", out_html],
                       capture_output=True, text=True)
        if os.path.exists(out_html) and os.path.getsize(out_html) > 20000:
            return True
    return False


def extract_content(src):
    i = src.find('window.__ICE_PAGE_PROPS__=')
    if i < 0:
        return None
    j = src.find('</script>', i)
    raw = src[i + len('window.__ICE_PAGE_PROPS__='):j].strip().rstrip(';')
    try:
        data = json.loads(raw)
        return data['docDetailData']['storeData']['data']['content']
    except Exception:
        return None


def to_text(content):
    body = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', content, flags=re.S)
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
        raise SystemExit('用法: python scripts/qwen/fetch_docs.py <别名或URL> [-o 输出]')

    for t in targets:
        url = t if t.startswith('http') else f'https://help.aliyun.com/zh/model-studio/{t}'
        name = re.sub(r'[^a-z0-9]+', '_', t.lower()).strip('_') or 'page'
        tmp = f'_aliyun_{name}.html'
        try:
            if not fetch(url, tmp):
                print(f'{t}: 抓取失败', flush=True)
                continue
            content = extract_content(open(tmp, encoding='utf-8').read())
            if content is None:
                print(f'{t}: __ICE_PAGE_PROPS__ 提取失败', flush=True)
                continue
            text = to_text(content)
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
