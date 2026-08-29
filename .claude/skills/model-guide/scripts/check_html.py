"""HTML 结构校验：标签配对 + 每张表「表头列数 == 数据行单元格数」。

用法:
    python check_html.py <file.html>

模型指南页改动后必跑。两类错误：
    1. 标签未配对（漏闭合/多余闭合）
    2. 表格列数不一致（增删列或插行时常见；会列出具体表与行）

注意: thead 的 <tr> 不含 <td>，只核对 tbody 内的数据行。
"""
import re, sys
from html.parser import HTMLParser

VOID = {'meta', 'link', 'br', 'hr', 'img', 'input', 'rect', 'circle', 'path', 'stop', 'use'}


class TagChecker(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.errors = [], []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append((tag, self.getpos()))

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.errors.append(f'多余的 </{tag}> @line{self.getpos()[0]}')
            return
        if self.stack[-1][0] == tag:
            self.stack.pop()
        else:
            names = [t for t, _ in self.stack]
            if tag in names:
                idx = len(names) - 1 - names[::-1].index(tag)
                unclosed = [t for t, _ in self.stack[idx + 1:]]
                self.errors.append(f'</{tag}> @line{self.getpos()[0]} 内有未闭合: {unclosed}')
                del self.stack[idx:]
            else:
                self.errors.append(f'无匹配 </{tag}> @line{self.getpos()[0]}')


def check_tables(src):
    problems = []
    for t_i, tbl in enumerate(re.finditer(r'<table[^>]*>(.*?)</table>', src, re.S)):
        t = tbl.group(1)
        ths = len(re.findall(r'<th>', t))
        tbody = re.search(r'<tbody>(.*?)</tbody>', t, re.S)
        if not tbody:
            continue
        for r_i, row in enumerate(re.finditer(r'<tr>(.*?)</tr>', tbody.group(1), re.S)):
            tds = len(re.findall(r'<td', row.group(1)))
            if tds != ths:
                mid = re.search(r'model-id">([^<]+)', row.group(1))
                problems.append(
                    f'表#{t_i + 1} 行{r_i + 1} ({mid.group(1) if mid else "?"}): 表头 {ths} 列 != 数据 {tds} 格')
    return problems


def main():
    path = sys.argv[1]
    src = open(path, encoding='utf-8').read()
    c = TagChecker()
    c.feed(src)
    c.close()
    for e in c.errors[:15]:
        print('标签错误:', e)
    if c.stack:
        print('未闭合:', [(t, p[0]) for t, p in c.stack][:15])
    problems = check_tables(src)
    for p in problems:
        print('列数错误:', p)
    if not c.errors and not c.stack and not problems:
        print(f'OK: {path} 标签配对正确，全部表格列数一致')
        sys.exit(0)
    sys.exit(1)


if __name__ == '__main__':
    main()
