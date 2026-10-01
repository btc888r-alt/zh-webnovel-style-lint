#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zh-webnovel-style-lint —— 中文网文章节稿件风格检查

两档检查：
  FAIL（硬性违规，退出码 1）
    - 每章纯汉字数 2000–2400（只计 \\u4e00–\\u9fff，不计标点/数字/拉丁字母）
    - ≥90% 的段落落在 150–300 字；全章平均段长 200–250 字
    - 黑名单正则：第四面墙“第X章”锚点、AI 腔句式、职场系梗、分析标签体
  WARN（AI 味告警，不影响退出码，按“每千字密度”判定）
    - 比喻三件套、缓冲副词、模板微表情、套话连接、解释腔、
      文青滥调、公文腔、机械排比句式

用法：
    python novel_lint.py 001.txt 002.txt
    python novel_lint.py chapters/
    python novel_lint.py chapters/ --json > report.json

退出码：硬性违规为 1；只有 AI 味告警时为 0。
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

    # 硬性违规：命中即 FAIL
    "forbidden": [
        (r"第[一二三四五六七八九十百千零\d\s]+章", "第四面墙：章节自指锚点"),
        (r"不是[^，。；！？]{0,30}而是", "AI腔：不是……而是……"),
        (r"深吸一口气", "AI腔：深吸一口气"),
        (r"情报检索|风险计算|选最稳|选最苟", "分析标签体"),
        (r"社畜|996|007|KPI|绩效|打卡|加班|排期|辞职|内卷|摸鱼|画饼",
         "职场系梗（默认删除）"),
    ],

    # AI 味：按密度告警。per_1000 为每千字允许上限，0 表示零容忍。
    "ai_style": [
        {"name": "比喻三件套",
         "words": ["仿佛", "宛如", "犹如", "如同"], "per_1000": 2},
        {"name": "缓冲副词",
         "words": ["微微", "缓缓", "徐徐", "悄然", "轻轻", "慢慢",
                   "不禁", "不由得", "不由自主", "似乎"], "per_1000": 3},
        {"name": "惊讶副词",
         "words": ["竟然", "居然"], "per_1000": 2},
        {"name": "模板微表情",
         "words": ["嘴角勾起", "嘴角上扬", "勾起一抹", "眼底闪过", "眼中闪过",
                   "瞳孔", "倒吸一口凉气", "如遭雷击", "僵立在原地",
                   "戏谑的冷笑", "不易察觉"], "per_1000": 0},
        {"name": "套话连接",
         "words": ["值得注意的是", "需要注意的是", "综上所述", "总而言之",
                   "总的来说", "由此可见", "毋庸置疑", "众所周知",
                   "与此同时", "在此基础上", "紧接着", "就在这时",
                   "恰在此时", "正当此刻", "不难看出"], "per_1000": 0},
        {"name": "解释腔",
         "words": ["换句话说", "说白了", "简单来说", "通俗点讲", "事实上",
                   "实际上", "毫无疑问", "无可否认", "显而易见",
                   "可以说", "某种程度上", "在某种程度上"], "per_1000": 0},
        {"name": "文青滥调",
         "words": ["无声的呐喊", "历史的尘埃", "命途的齿轮", "五味杂陈",
                   "空气仿佛凝固", "目光交汇的瞬间", "意味深长", "若有所思",
                   "在这一刻", "就在此时", "殊不知", "果不其然",
                   "时间一分一秒过去", "这未尝不是一种解脱",
                   "让人不寒而栗", "心中升起一股莫名的情绪"], "per_1000": 0},
        {"name": "公文腔",
         "words": ["赋能", "抓手", "闭环", "顶层设计", "底层逻辑",
                   "深度融合", "多维度", "全方位", "里程碑", "划时代",
                   "至关重要", "不可或缺", "前所未有", "史无前例"], "per_1000": 0},
    ],
    "ai_style_regex": [
        (r"不仅如此[^，。！？]{0,20}更是", "递进排比：不仅如此……更是……"),
        (r"与其说[^，。！？]{0,20}不如说", "对比定义：与其说……不如说……"),
        (r"嘴角勾起一抹.{0,6}", "模板微表情：嘴角勾起一抹X"),
        (r"眼底闪过一丝.{0,8}", "模板微表情：眼底闪过一丝X"),
        (r"瞳孔骤缩.{0,10}", "模板微表情：瞳孔骤缩X"),
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
    issues, warnings = [], []

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
            issues.append(f"{label}：{len(hits)} 处（如「{hits[0][:14]}」）")

    # AI 味：按每千字密度告警
    per_k = total / 1000 if total else 1
    for group in CONFIG["ai_style"]:
        n = sum(text.count(w) for w in group["words"])
        limit = group["per_1000"] * per_k
        if n > limit:
            hit_words = [w for w in group["words"] if w in text][:3]
            warnings.append(
                f"{group['name']}：{n} 处（密度 {n / per_k:.1f}/千字，"
                f"上限 {group['per_1000']}/千字；如「{'/'.join(hit_words)}」）")
    for pattern, label in CONFIG["ai_style_regex"]:
        hits = re.findall(pattern, text)
        if hits:
            warnings.append(f"{label}：{len(hits)} 处（如「{hits[0][:14]}」）")

    return {"file": os.path.basename(path), "hanzi": total,
            "paragraphs": len(counts), "ok": not issues,
            "issues": issues, "warnings": warnings}


def main(argv):
    as_json = "--json" in argv
    paths = [a for a in argv[1:] if a != "--json"]
    if not paths:
        print("用法: python novel_lint.py <文件或目录>... [--json]")
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
            print(f"[{mark}] {r['file']}  汉字{r['hanzi']}  段落{r['paragraphs']}")
            for issue in r["issues"]:
                print(f"       ✗ {issue}")
            for w in r["warnings"]:
                print(f"       ~ {w}")
        n_ok = sum(1 for r in results if r["ok"])
        n_warn = sum(1 for r in results if r["warnings"])
        print(f"\n{n_ok}/{len(results)} 章通过硬性检查，{n_warn} 章有 AI 味告警")
    return 0 if all(r["ok"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
