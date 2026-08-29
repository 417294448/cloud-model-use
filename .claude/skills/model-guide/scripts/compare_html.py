"""HTML 语义对比：忽略注释与空白，找出第一处差异。

用法:
    python compare_html.py <a.html> <b.html>

用途（回归验证的标准工具）:
    - extract → render 互逆回归：compare_html.py 原页面.html 渲染页面.html
    - 改 data JSON 后确认渲染输出与预期一致

判定规则:
    - 忽略 HTML 注释（装饰性内容，渲染器生成的注释与手写注释文本不同属正常）
    - 忽略标签间空白与连续空格（渲染器与手写的缩进风格不同）
    输出 IDENTICAL（语义一致）或第一处差异的上下文（exit 1）。
"""
import re, sys


def normalize(html):
    s = re.sub(r'<!--.*?-->', '', html, flags=re.S)
    s = re.sub(r'>\s+<', '><', s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()


def main():
    a = normalize(open(sys.argv[1], encoding='utf-8').read())
    b = normalize(open(sys.argv[2], encoding='utf-8').read())
    if a == b:
        print('IDENTICAL: 两个文件语义完全一致（忽略注释与空白）')
        sys.exit(0)
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            print(f'DIFF @char{i}:')
            print(f'  A: {a[max(0, i - 120):i + 120]}')
            print(f'  B: {b[max(0, i - 120):i + 120]}')
            sys.exit(1)
    print(f'DIFF: 前缀一致，长度不同 A={len(a)} B={len(b)}')
    longer, name = (b, 'B') if len(b) > len(a) else (a, 'A')
    print(f'  {name} 多出: {longer[n:n + 200]}')
    sys.exit(1)


if __name__ == '__main__':
    main()
