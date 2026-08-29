"""同步日期统一器：把 data JSON 中的「更新信息」对齐为同一日期。

用法:
    python sync_dates.py <data.json> [<data2.json> ...]            # 报告各文件同步日期分布
    python sync_dates.py <data.json> --write [--date YYYY-MM-DD]   # 统一为指定日期（缺省取文件内最新）

背景:
    页面的更新信息出现在多处——hero_desc / footer_sources 尾部的「（YYYY-MM-DD 同步）」括注、
    meta.footer_updated 字段、deprecated 区块 desc 的同步括注。手工逐处改容易漏（曾出现
    openai 页头 08-28 而页脚 08-27 的不一致）。本脚本只动「同步括注」与 footer_updated：
    表格行内的退役/关停日期（如 2026-08-17 退役）是官方数据，绝不替换。

    直接在 JSON 文本上做正则替换（不经 parse→dump），不扰动文件其余字节。
    工作流：更新数据后跑 --write（日期取最新或 --date 指定），再 render_guide.py 渲染。
"""
import os, re, sys

SYNC_RE = re.compile(r'（(\d{4}-\d{2}-\d{2}) 同步）')              # 全角括注，仅匹配「同步」后缀
FU_RE = re.compile(r'("footer_updated"\s*:\s*")(\d{4}-\d{2}-\d{2})(")')
DATE_RE = re.compile(r'^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$')  # 格式+合法月日


def collect(path):
    """返回 [(来源描述, 日期)]。文本级扫描，来源用行号标注。"""
    hits = []
    with open(path, encoding='utf-8') as f:
        for ln, line in enumerate(f, 1):
            for m in SYNC_RE.finditer(line):
                hits.append((f'第{ln}行 同步括注', m.group(1)))
            m = FU_RE.search(line)
            if m:
                hits.append(('footer_updated', m.group(2)))
    return hits


def report(path):
    hits = collect(path)
    name = os.path.basename(path)
    if not hits:
        print(f'{name}: 未找到任何同步日期')
        return False
    uniq = sorted({d for _, d in hits})
    ok = len(uniq) == 1
    print(f'{name}: {"一致" if ok else "不一致!"}  最新 {uniq[-1]}  分布 ' +
          ', '.join(f'{d}×{sum(1 for _, dd in hits if dd == d)}' for d in uniq))
    if not ok:
        for src, d in hits:
            print(f'    {src} → {d}')
    return ok


def sync(path, target=None):
    hits = collect(path)
    name = os.path.basename(path)
    if not hits:
        print(f'{name}: 无同步日期可统一，跳过')
        return False
    target = target or max(d for _, d in hits)
    if not DATE_RE.match(target):
        print(f'{name}: 目标日期 {target} 不合法（应为真实存在的 YYYY-MM-DD），已中止')
        return False
    with open(path, encoding='utf-8') as f:
        text = f.read()
    text = SYNC_RE.sub(f'（{target} 同步）', text)
    text = FU_RE.sub(rf'\g<1>{target}\g<3>', text)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f'{name}: 已统一为 {target}（{len(hits)} 处）')
    return True


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    write = '--write' in args
    date = None
    files = []
    i = 0
    while i < len(args):
        if args[i] == '--write':
            i += 1
        elif args[i] == '--date':
            date = args[i + 1]
            if not DATE_RE.match(date):
                print(f'--date 格式应为 YYYY-MM-DD，收到: {date}')
                sys.exit(1)
            i += 2
        else:
            files.append(args[i])
            i += 1
    if not files:
        print('未指定 data.json')
        sys.exit(1)
    ok = True
    for f in files:
        ok = (sync(f, date) if write else report(f)) and ok
    sys.exit(0 if ok else 1)
