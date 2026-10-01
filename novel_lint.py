#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zh-webnovel-style-lint —— 中文网文章节稿件风格检查

检查口径（顶部 CONFIG 可调）：
  - 每章纯汉字数 2000–2400（只计 \\u4e00–\\u9fff，不计标点/数字/拉丁字母）
  - ≥90% 的段落落在 150–300 字；全章平均段长 200–250 字
  - 黑名单正则：第四面墙“第X章”锚点、AI 腔句式、职场系梗、分析标签体

用法：
    python novel_lint.py 001.txt 002.txt
    python novel_lint.py chapters/
    python novel_lint.py chapters/ --json > report.json

退出码：全部通过为 0，任一章节不达标为 1。
"""

import json
import os
import re
import sys

CONFIG = {
    "hanzi_min": 2000,
    "hanzi_max": 2400,
    "para_min": 150,
    "para_max": 300,
    "para_ratio": 0.90,      # 达标段落占比下限
    "avg_para_min": 200,
    "avg_para_max": 250,
    # (正则, 说明)：命中即记一条问题
    "forbidden": [
        (r"第[一二三四五六七八九十百千零\d\s]+章", "第四面墙：章节自指锚点"),
        (r"不是[^，。；！？]{0,30}而是", "AI腔：不是……而是……"),
        (r"深吸一口气", "AI腔：深吸一口气"),
        (r"情报检索|风险计算|选最稳|选最苟", "分析标签体"),
        (r"社畜|996|007|KPI|绩效|打卡|加班|排期|辞职|内卷|摸鱼|画饼",
         "职场系梗（默认删除）"),
    ],
}

HANZI = re.compile(r"[\u4e00-\u9fff]")


def hanzi_count(s):
    return len(HANZI.findall(s))


def iter_files(paths):
    for p in paths:
        if os.path.isdir(p):
            for root, _dirs, files in os.walk(p):
                for f in sorted(files):
                    if f.endswith(".txt"):
                        yield os.path.join(root, f)
        elif os.path.isfile(p):
            yield p
        else:
            print(f"跳过：找不到 {p}", file=sys.stderr)


def check_file(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    issues = []

    total = hanzi_count(text)
    if not (CONFIG["hanzi_min"] <= total <= CONFIG["hanzi_max"]):
        issues.append(
            f"纯汉字 {total}，超出 {CONFIG['hanzi_min']}-{CONFIG['hanzi_max']}")

    paras = [p.strip() for p in text.splitlines() if p.strip()]
    counts = [hanzi_count(p) for p in paras]
    if counts:
        ok = sum(1 for c in counts
                 if CONFIG["para_min"] <= c <= CONFIG["para_max"])
        ratio = ok / len(counts)
        if ratio < CONFIG["para_ratio"]:
            issues.append(
                f"段落达标率 {ratio:.0%}（{ok}/{len(counts)}），"
                f"要求 ≥{CONFIG['para_ratio']:.0%}")
        avg = sum(counts) / len(counts)
        if not (CONFIG["avg_para_min"] <= avg <= CONFIG["avg_para_max"]):
            issues.append(
                f"均段 {avg:.0f} 字，要求 "
                f"{CONFIG['avg_para_min']}-{CONFIG['avg_para_max']}")
    else:
        issues.append("无有效段落")

    for pattern, label in CONFIG["forbidden"]:
        hits = re.findall(pattern, text)
        if hits:
            sample = hits[0][:14]
            issues.append(f"{label}：{len(hits)} 处（如「{sample}」）")

    return {"file": os.path.basename(path), "hanzi": total,
            "paragraphs": len(counts), "ok": not issues, "issues": issues}


def main(argv):
    as_json = "--json" in argv
    paths = [a for a in argv[1:] if a != "--json"]
    if not paths:
        print(__doc__.strip().split("\n\n")[3])
        return 2
    results = [check_file(p) for p in iter_files(paths)]
    if not results:
        print("没有可检查的 txt 文件", file=sys.stderr)
        return 2

    if as_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for r in results:
            mark = "PASS" if r["ok"] else "FAIL"
            print(f"[{mark}] {r['file']}  汉字{ r['hanzi']}  段落{r['paragraphs']}")
            for issue in r["issues"]:
                print(f"       - {issue}")
        n_ok = sum(1 for r in results if r["ok"])
        print(f"\n{n_ok}/{len(results)} 章通过")
    return 0 if all(r["ok"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
