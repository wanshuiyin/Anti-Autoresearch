# Anti-Autoresearch（反自动科研）

**面向研究论文的"实质性诚信取证"工具 —— 尤其针对机器生成（autoresearch /
AI-Scientist 式）的论文产出。**

> 🛡️ **[ARIS](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep)（~12.5k★ 自动科研 agent 平台）的对偶。** ARIS 做自动科研是**负责任**的:它内置了多层审计栈(experiment-integrity · result-to-claim · 零上下文 paper-claim 审 · citation 审),让自己的产出保持诚实。**Anti-Autoresearch 就是这枚硬币的另一面** —— 把同一套审计 DNA 朝外,抓那些**没有**这些护栏就产出的自动科研论文。([什么是 ARIS?](#-什么是-aris) · English [README.md](README.md))

> 不管论文是谁、是什么写的,它的科学结论是否自洽、是否被自己的证据支撑?
> Anti-Autoresearch 审查一篇投稿的**自洽性**与**造假迹象**,产出带证据锚点、
> 可供审稿人直接使用的报告。它**不是** AI 文本检测器,也**不下学术不端的结论**——
> 它只把"值得人去核实的矛盾点"摆出来。

English: [README.md](README.md)。本仓库复用并改造了
[ARIS](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep) 的审计
DNA —— 由"从生成端见过这些失败模式"的人来做。

---

## 为什么需要它

机器生成的论文/审稿已成为文献中可测量的一部分,但对 AC 真正要紧的,从来不是
"这段文字是不是 LLM 写的"(人能写出造假论文,LLM 也能写出诚实论文),而是:

> **论文是否自相矛盾、是否被它自己的证据支撑?**

这恰恰是 autoresearch 流水线最容易出错的地方 —— 它们为叙事做优化,幻觉出
**局部**自洽:摘要里一个任何表格都没有的数字、号称"提升 16%"而操作数算出来只有
6%、为某条主张引用了一篇根本没这么说的论文、方法描述与实际评测不一致。这些都是
**可核查**的,本仓库就核查它们。

**这不是假想。** 转述自 NeurIPS 2026 周期一则公开的审稿人吐槽(示意,非正式引用),
一批稿件几乎逐条命中本仓库编码的 taxonomy:

> - *第一篇* — "数据表和正文对不上,好几行错位,不同 backbone 间明显的加减乘除
>   规律性,不像跑出来的。" → consistency · `HP-SUSPICIOUS-REGULARITY`
> - *第二篇* — "两张表占满一页且一模一样,唯一的图还是大模型生成的,就这还没写满
>   9 页。" → `HP-DUP-TABLE` · 表象信号
> - *第三篇* — "公式推导不通,关键问题数学上不正确,实验看着完整但公式错了结果不知
>   道怎么对上的。" → claim 与推导不一致
> - *第四篇* — "开源了,结构完整绘图精美书写流畅 —— 但我把代码跑了,和正文结果南辕
>   北辙。" → experiment-forensics (L2)

第四篇就是本仓库的论点一句话版:**表面光鲜 ≠ 诚信。**(审稿人自己的总结:"llm 和
多模态是重灾区;理论也是 —— 结论看着很 solid,一看附录是 gpt 大法,一坨。")

## 它是什么 / 不是什么

| | |
|---|---|
| ✅ **是** | 自洽性 + 造假取证;证据账本锚定;可观测性分层;面向审稿人/AC 的决策支持;**+ 辅助的表象/AI 味信号(封顶,永不单独定罪)** |
| ❌ **不是** | AI 文本分类器(Pangram/GPTZero/Binoculars)、AI 审稿检测器、学术不端判决、会改论文的"合著者" |

> 关于表象信号(AI 味文风、重复表格、LLM 配图、凑页数):我们**确实会报告**它们
> ——审稿人要看——但只作为**弱、高假阳的上下文**,被裁决器封顶在 `minor`(所以它们
> 最多说"再看一眼",绝不会说"这是错的"或"这是 AI 写的")。这个封顶是**代码强制**的
> (`SURFACE_ONLY_SKILLS`),不是口头承诺。

### 它填补的空白

现有工作分三簇:(A) **AI 文本检测**(文体学,"是不是 LLM 写的");(B) **AI 审稿
检测**;(C) **通用 claim/严谨性核查**(FactReview、RIGOURATE、引用造假分类法)。
**没有人做 autoresearch 专属的实质性诚信取证** —— 即"内部自洽取证 + autoresearch
专属 hack-pattern 分类法"。我们把论文**与它自己**对照(不需要外部 ground truth,
而这正是机器产出露馅的地方),并把失败目录专门化到 autoresearch。
详见 [docs/positioning.md](docs/positioning.md)。

## 它如何保持诚实(反"LLM 互查互骗"设计)

对这类工具最常见的质疑是"一个 LLM 给另一个 LLM 的论文打分,就是噪声"。我们有三道
**结构性**防线,而非一句免责声明:

1. **证据账本(evidence ledger)**:一次确定性抽取把论文变成 `claims.json` ——
   带 span 锚点、带哈希的 claim。每条 finding 必须引用 `claim_id` + 原文 span,
   **没有 span 就不能是高严重度 finding**。
2. **LLM 永不打分**:审计 skill 只**提出** finding;**确定性裁决器**
   (`tools/adjudicate_findings.py`,纯规则)算出 verdict。相同 finding → 相同
   verdict,最终决策里没有任何模型。
3. **可观测性分层**:每次运行声明它能看到什么(L0 仅 PDF → L2 含代码+结果);
   需要代码才能判的 finding 在仅 PDF 运行时**自动降级** —— 你永远无法"从一份
   PDF 喊造假"。见 [references/observability-levels.md](references/observability-levels.md)。

外加一个 **eval 测试台**(`eval/`):每次改动都在干净 + 人工注入缺陷的 fixture 上
验证确定性核心 —— 量出假阳/召回,而不是凭感觉。

## 快速开始

确定性核心**零依赖**(Python 3 标准库):

```bash
# 1) 在干净 + 注入缺陷的 fixture 上验证流水线(回归门)
python3 eval/run_eval.py

# 2) 从真实论文的 LaTeX 构建证据账本
python3 tools/build_claim_ledger.py --paper-id mypaper \
    --latex main.tex sections/*.tex --observability-level 1 --out claims.json

# 3) 跑确定性自洽检查
python3 tools/check_numeric_consistency.py --ledger claims.json --out findings.json

# 4) 裁决成报告(确定性 verdict)。--ledger 是必填:每条 above-info finding 必须
#    引用证据账本里的逐字 span,否则 fail-closed 降到 info(反 slop 保证)。
python3 tools/adjudicate_findings.py --findings findings.json --ledger claims.json \
    --paper-id mypaper --observability-level 1 --out report.json --md REPORT.md
```

要跑**完整**取证(加上经 Claude + codex 的跨模型语义审计),运行 agent workflow
`/anti-autoresearch <paper-dir>`,见
[workflows/anti-autoresearch/SKILL.md](workflows/anti-autoresearch/SKILL.md)。

## 局限(信任任何报告前必读)

- **取证 ≠ 学术不端的证明**,所有 finding 都是"待核实的矛盾"。
- **仅 PDF(L0)只能查自洽性与迹象,查不了全部造假**(无法验证外部 GT、无法跑代码)。
- **假阳是真实存在的**(合理的整数、单 seed 试点、有意的范围选择)—— 所以有分层、
  有 FP-risk 标注、有 eval 测试台,而非二元"有罪"。
- **分类法会被绕过**:它是活的、带版本的文档,是安全网而非证明系统。
  详见 [docs/limitations.md](docs/limitations.md)。

## 🌟 什么是 ARIS

[**ARIS — Auto Research in Sleep**](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep)
是一个广泛使用的 AI 科研 agent 技能平台(2025–2026)。它跑端到端科研流水线(文献 →
想法 → 实验 → 论文)——而且**内置诚信护栏**,这让它成为这把"审计刀"可信的基座:

- ⭐ **~12.5k GitHub stars**、HuggingFace Daily Papers #1、78+ 技能跨 7+ 平台。
- 🛡️ **三层审计栈**让 ARIS *自己*的产出保持诚实:`experiment-audit`(假 GT /
  归一化作弊 / 幽灵结果)、`result-to-claim`(claim 科学上成立吗)、零上下文
  `paper-claim-audit` + `citation-audit`(数字和引用站得住吗)。Anti-Autoresearch
  就是这套审计**朝外**。
- 🔬 **跨模型对抗审**是核心教条:executor 与 reviewer 必须来自不同模型家族
  (Claude × GPT-5.5 xhigh × Gemini),没有 LLM 给自己的产出打分。Anti-Autoresearch
  继承并**加固**了它 —— 这里模型只**提出** finding,确定性裁决器**裁决**。

**一体两面。** ARIS 是如何*负责任*地做自动科研;Anti-Autoresearch 是如何*标记出*那些
不负责任的。一个公开了自己审计栈的生成器,最清楚这些流水线会怎么坏 —— 因为它就是
从内部对抗这些坏法的。这正是本仓库带来的视角。

👉 **ARIS 主仓库**:https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep

技能映射:Anti-Autoresearch 的 skill 就是 ARIS 的审计 skill,改造成"第三方审未知
投稿":`consistency-audit` ← `paper-claim-audit`、`experiment-forensics` ←
`experiment-audit`、`citation-forensics` ← `citation-audit`、
`baseline-comparison-audit` ← `paper-claim-audit`、`adversarial-case-builder` ←
`kill-argument`,外加新的 `evidence-ledger` 脊柱与 `presentation-signals`。

## 引用 Citation

Anti-Autoresearch **派生自 ARIS**,复用了它的审计 DNA。如果本仓库对你的研究 / 论文 /
审稿有帮助,请引用 ARIS 方法论论文:

```bibtex
@article{yang2026aris,
  title={ARIS: Autonomous Research via Adversarial Multi-Agent Collaboration},
  author={Yang, Ruofeng and Li, Yongcan and Li, Shuai},
  journal={arXiv preprint arXiv:2605.03042},
  year={2026}
}
```

## 许可证

MIT,见 [LICENSE](LICENSE)。
