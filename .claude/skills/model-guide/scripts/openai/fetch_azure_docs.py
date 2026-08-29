"""【Azure 专用】抓取 Microsoft Learn 文档页并转为结构化文本（ROW:/H2: 格式）。

用法:
    python scripts/openai/fetch_azure_docs.py <url> [-o 输出.txt] [--raw 保留.html]
    python scripts/openai/fetch_azure_docs.py <url> --section "Azure OpenAI"   # 只截取某 H3 章节

说明:
    - learn.microsoft.com 可直连，无需代理（与 OpenAI 官网不同）
    - 输出格式便于肉眼检索与正则解析：
        H1:/H2:/H3:/H4: 标题；ROW: 表格行（单元格以 " | " 分隔）；- 列表项
    - 已验证可用的页面：
        models-sold-directly-by-azure（模型清单+上下文/输入/输出）
        model-retirement-schedule（退役计划：生命周期/日期/替代）

示例:
    python fetch_azure_docs.py "https://learn.microsoft.com/en-us/azure/foundry/openai/concepts/model-retirement-schedule" -o retire.txt
"""
import re, html, sys, subprocess, os

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def fetch(url, out_html, max_tries=3):
    for i in range(max_tries):
        subprocess.run(["curl", "-sL", "--max-time", "60", "-A", UA, url, "-o", out_html],
                       capture_output=True, text=True)
        if os.path.exists(out_html) and os.path.getsize(out_html) > 20000:
            return True
    return False


def to_text(src):
    m = re.search(r'<main[^>]*>(.*?)</main>', src, re.S)
    body = m.group(1) if m else src
    body = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', body, flags=re.S)
    body = re.sub(r'<tr[^>]*>', '\nROW: ', body)
    body = re.sub(r'<t[dh][^>]*>', ' | ', body)
    body = re.sub(r'<h([1-4])[^>]*>', r'\n\nH\1: ', body)
    body = re.sub(r'<li[^>]*>', '\n- ', body)
    body = re.sub(r'<p[^>]*>', '\n', body)
    body = re.sub(r'<[^>]+>', '', body)
    body = html.unescape(body)
    body = re.sub(r'[ \t]+', ' ', body)
    body = re.sub(r'\n\s*\n+', '\n', body)
    return body


def cut_section(text, heading):
    """截取某 H3 标题到下一个同级/更高级标题之间的内容"""
    pat = re.compile(r'^H3: ' + re.escape(heading) + r'\s*$(.*?)(?=^H[123]: |\Z)',
                     re.S | re.M)
    m = pat.search(text)
    return m.group(1).strip() if m else None


def main():
    args = sys.argv[1:]
    url = args[0]
    out_txt = None
    raw_html = None
    section = None
    i = 1
    while i < len(args):
        if args[i] == '-o':
            out_txt = args[i + 1]; i += 2
        elif args[i] == '--raw':
            raw_html = args[i + 1]; i += 2
        elif args[i] == '--section':
            section = args[i + 1]; i += 2
        else:
            i += 1
    if not out_txt:
        out_txt = re.sub(r'[^a-z0-9]+', '_', url.split('/')[-1].lower()) + '.txt'
    tmp_html = raw_html or '_azure_tmp.html'

    try:
        if not fetch(url, tmp_html):
            raise SystemExit(f'抓取失败: {url}')
        text = to_text(open(tmp_html, encoding='utf-8').read())

        if section:
            cut = cut_section(text, section)
            if cut is None:
                raise SystemExit(f'未找到章节: {section}')
            text = cut

        open(out_txt, 'w', encoding='utf-8').write(text)
        print(f'fetched: {out_txt} ({len(text)} chars, {text.count("ROW:")} rows)')
    finally:
        if not raw_html and os.path.exists(tmp_html):
            os.remove(tmp_html)


if __name__ == '__main__':
    main()
