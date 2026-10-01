# zh-webnovel-style-lint

中文网文章节稿件的风格检查小工具：纯汉字数、段落分布、禁用句式一键审计。

## 两档检查

| 档位 | 说明 |
|---|---|
| ✗ FAIL（硬性违规） | 退出码 1，必须修 |
| ~ WARN（AI 味告警） | 退出码仍为 0，按“每千字密度”判定，供人工复核 |

## 它检查什么

| 检查项 | 口径（`novel_lint.py` 顶部 `CONFIG` 可调） |
|---|---|
| 章节纯汉字数 | 2000–2400（只计 `\u4e00–\u9fff`，不计标点/数字/拉丁字母） |
| 段落分布 | ≥90% 段落 150–300 字；全章均段 200–250 字 |
| 第四面墙（✗） | `第X章` 式章节自指锚点 |
| AI 腔（✗） | `不是……而是……`、`深吸一口气` |
| 分析标签体（✗） | `情报检索` / `风险计算` / `选最稳` / `选最苟` |
| 职场系梗（✗） | `社畜` / `996` / `KPI` / `内卷` / `摸鱼` 等（默认删除口径） |
| 比喻三件套（~） | `仿佛` / `宛如` / `犹如` / `如同`，上限 2/千字 |
| 缓冲副词（~） | `微微` / `缓缓` / `徐徐` / `悄然` / `不禁` / `似乎` 等，上限 3/千字 |
| 惊讶副词（~） | `竟然` / `居然`，上限 2/千字 |
| 模板微表情（~） | `嘴角勾起一抹` / `眼底闪过一丝` / `瞳孔骤缩` / `倒吸一口凉气` / `如遭雷击` 等，零容忍 |
| 套话连接（~） | `值得注意的是` / `综上所述` / `与此同时` / `就在这时` 等，零容忍 |
| 解释腔（~） | `换句话说` / `说白了` / `事实上` / `毫无疑问` 等，零容忍 |
| 文青滥调（~） | `殊不知` / `果不其然` / `在这一刻` / `无声的呐喊` / `命途的齿轮` 等，零容忍 |
| 公文腔（~） | `赋能` / `抓手` / `闭环` / `顶层设计` / `至关重要` 等，零容忍 |
| 机械排比（~） | `不仅如此……更是……`、`与其说……不如说……` |

设计上参考了“看聚簇、不看孤证”的思路：单个词出现一次不算病，
同一类在千字内反复出现才告警，避免误杀正常行文。

## 用法

```bash
python novel_lint.py 001.txt 002.txt
python novel_lint.py chapters/
python novel_lint.py chapters/ --json > report.json
```

示例输出：

```
[FAIL] 002.txt  汉字1876  段落9
       ✗ 纯汉字 1876，超出 2000-2400
       ✗ AI腔：不是……而是……：2 处（如「不是退缩，而是」）
       ~ 比喻三件套：6 处（密度 3.2/千字，上限 2/千字；如「仿佛/宛如」）
       ~ 模板微表情：1 处（如「嘴角勾起一抹弧度」）

0/1 章通过硬性检查，1 章有 AI 味告警
```

## 设计说明

- 零依赖，只用 Python 标准库，哪里都能跑。
- 规则全部收敛在 `CONFIG` 一个字典里：换一套文风口径只改一处。
- 黑名单是正则列表，加一条新禁用句式就是加一行元组。
- AI 味词库整理自下列公开清单（排名不分先后）：
  - [网文套路词与 AI 机械句式粉碎指南](https://github.com/guojy1997/novel-flow/blob/HEAD/skills/novel-anti-cliche/SKILL.md)
  - [网文去 AI 味检测流程](https://github.com/nigh/show-me-the-story/blob/HEAD/internal/story/embeds/skills/story-deslop.md)
  - [中文小说去 AI 味专业规则](https://github.com/mochocyang/qmai/blob/HEAD/skills/de-ai-writing/references/novel-de-ai-rules.md)
  - [去 AI 味判据](https://github.com/xiaoyangy/novel-studio/blob/HEAD/assets/references/anti-ai-tone.md)
  - [AI 味病灶清单（中文）](https://github.com/zizhanovo/doubaoya-community/blob/HEAD/skills/dby-deai/references/病灶清单.md)
  - [中文 AI 写作模式](https://github.com/daidaij/my-skills/blob/HEAD/context-standards/stop-slop/references/ai-patterns-zh.md)

## Roadmap

- 代词检查：特定角色名后 N 字内出现错性别代词时告警
- `--fix`：对可自动改的项（如多余空行）直接落盘修复
