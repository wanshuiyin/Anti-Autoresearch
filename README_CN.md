# Anti-Autoresearch（反自动科研）

**面向研究论文的"实质性诚信取证"工具 —— 尤其针对机器生成（autoresearch /
AI-Scientist 式）的论文产出。**

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

## 它是什么 / 不是什么

| | |
|---|---|
| ✅ **是** | 自洽性 + 造假取证;证据账本锚定;可观测性分层;面向审稿人/AC 的决策支持 |
| ❌ **不是** | AI 文本分类器(Pangram/GPTZero/Binoculars)、AI 审稿检测器、学术不端判决、会改论文的"合著者" |

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

# 4) 裁决成报告(确定性 verdict)
python3 tools/adjudicate_findings.py --findings findings.json \
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

## 与 ARIS 的关系

ARIS 是一个 autoresearch **系统**;Anti-Autoresearch 是它的对抗性姊妹仓库:复用并
改造 ARIS 的审计 skill(`experiment-audit`、`paper-claim-audit`、`citation-audit`、
`kill-argument`)与跨模型审查纪律,但把视角从"作者自查"改造成"第三方审一篇未知
投稿"。护城河正是这份"知道生成器如何失败"的内部知识。

## 许可证

MIT,见 [LICENSE](LICENSE)。
