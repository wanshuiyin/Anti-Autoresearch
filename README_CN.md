# Anti-Autoresearch 🛡️（反自动科研）

[![Join Community](https://img.shields.io/badge/💬_Join-Community-7C3AED?style=flat)](#community) · [![Cite](https://img.shields.io/badge/📖_Cite-BibTeX-2E7D32?style=flat)](#citation) · [![Parent ARIS stars](https://img.shields.io/github/stars/wanshuiyin/Auto-claude-code-research-in-sleep?style=flat&logo=github&logoColor=white&color=gold&label=Parent%20ARIS%20%E2%98%85)](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/stargazers) · [![ARIS Report arXiv:2605.03042](https://img.shields.io/badge/ARIS%20Report-arXiv%3A2605.03042-b31b1b?style=flat&logo=arxiv)](https://arxiv.org/abs/2605.03042) · [![ARIS · HF Daily #1](https://img.shields.io/badge/ARIS%20%F0%9F%A4%97%20HF%20Daily-%231-ffcc4d?style=flat)](https://huggingface.co/papers/2605.03042) · [![ARIS on PaperWeekly](https://img.shields.io/badge/ARIS%20on-PaperWeekly-red?style=flat)](https://mp.weixin.qq.com/s/tDniVryVGjDkkkWl-5sTkQ) · [![ARIS in awesome-agent-skills](https://img.shields.io/badge/ARIS%20in-awesome--agent--skills-blue?style=flat&logo=github)](https://github.com/VoltAgent/awesome-agent-skills) · [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat)](LICENSE) · [![README English](https://img.shields.io/badge/README-English-blue?style=flat)](README.md)

<div align="center">

### 🔬 天下苦 autoresearch 久矣 —— Anti-Autoresearch 替研究者们一眼看穿不靠谱的工作。

***The field has tolerated unreliable autoresearch long enough — Anti-Autoresearch is the read that finally catches it.***

</div>

> 🏆 **建立在久经考验的根基上:[ARIS](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep)**(~12.5k★ · HuggingFace Daily Papers #1 · 78+ 技能 / 7+ 平台)。Anti-Autoresearch 把 ARIS 的生产级审计 DNA(experiment-audit · paper-claim-audit · citation-audit · kill-argument)**朝外** —— 审第三方的投稿,而不是你自己的。

自动科研(autoresearch)正在泛滥,投稿堆里越来越多的论文出自机器之手 —— 而其中相当
一部分**经不起细看**:表格和正文对不上、该有的 baseline 不见了、开源的代码跑出来和
论文南辕北辙。审稿人、AC、以及诚实的作者,越来越需要一种办法去**验证**这件事,而不
只是凭感觉怀疑。

> 不管论文是谁、是什么写的,它的科学结论是否自洽、是否被自己的证据支撑?
> Anti-Autoresearch 审查一篇投稿的**自洽性**与**造假迹象**,产出带证据锚点、
> 可供审稿人直接使用的报告。它**不是** AI 文本检测器,也**不下学术不端的结论**——
> 它只把"值得人去核实的矛盾点"摆出来。

---

## 📰 动态

- **v0.4 (2026-06)** — Taxonomy v0.4:48 个 hard pattern、8 个家族,新增家族 H(评测设计有效性:数据泄漏、LLM 裁判、选择性报告)。确定性 eval 门控由 3→7 个(含 GRIM / GRIMMER / statcheck);新增 CI、`eval-design-forensics` skill、先行工作致谢。
- **v0.1 (2026-06)** — 首次发布:面向 autoresearch / AI-Scientist 论文的审稿侧诚信取证。证据账本 + 确定性裁决器 + 可观测性分层。不是 AI 文本检测器。

## 🚀 快速开始

### Agent 工作流(常规用法)

Anti-Autoresearch 是作为 Claude Code skill 工作流运行的 —— Python 工具是工作流
**内部**的确定性脊柱,不是常规用户接口。

```bash
# 1) 安装 skills + workflow(全局,或传入某个项目的 .claude/skills 目录)
git clone https://github.com/wanshuiyin/Anti-Autoresearch.git
./Anti-Autoresearch/tools/install_anti_autoresearch.sh              # → ~/.claude/skills
# 项目内安装:./Anti-Autoresearch/tools/install_anti_autoresearch.sh ./.claude/skills

# 2) 接上跨模型 reviewer(最终状态:Claude Code 暴露 mcp__codex__codex)
claude mcp add codex -- codex mcp-server
claude mcp list

# 3) 审一篇论文
claude
> /anti-autoresearch ~/papers/submission
```

这次运行会把 `REPORT.md` + `report.json` + `claims.json` + 各 skill 的
`*.findings.json` 写进论文目录。把代码/结果产物和论文放一起即可解锁 L2 检查;仅
PDF/源码的运行按设计受可观测性限制。

### 单 skill 用法

每个 auditor 也都是独立 skill —— 安装脚本会把它们和 workflow 一起装上,所以你可以只跑
你关心的那个轴。它们共享同一条契约,按顺序来:

```text
claude
# 1) 先建一次证据账本 —— 所有 auditor 都锚定它。不建的话任一 auditor 会停在:
#    NO_LEDGER: claims.json not found. Run /evidence-ledger FIRST
> /evidence-ledger ~/papers/submission        # → claims.json + 可观测层级(L0/L1/L2)

# 2) 然后针对该账本,跑下面任意一个 auditor → <skill>.findings.json
```

**各 auditor** —— 都接收论文目录、读账本、写 `<skill>.findings.json`:

| Skill | 抓什么 |
|-------|--------|
| `/consistency-audit` | 论文与自身比对:数字虚高 / 对不上、方法与范围漂移、附录与正文矛盾 |
| `/citation-forensics` | 引用:查无此文的伪造引用,以及"真论文被拿来支持它没说过的主张" |
| `/baseline-comparison-audit` | "SOTA" / "超过" 背后缺失 / 偏弱 / 调参不公的 baseline |
| `/experiment-forensics` | *(L2 —— 需代码+结果)* 假 / 派生 GT、分数自归一化、幽灵结果、placeholder 数据、代码产出 ≠ 报告数字 |
| `/proof-derivation-forensics` | *(L1 —— 需 LaTeX 源)* 写出来的证明:跳过的义务、循环论证、无效步骤、符号漂移、偷藏假设 |
| `/presentation-signals` | *(封顶 `minor`)* 表象迹象:重复表、LLM 配图、页数注水、AI 味文风 —— 当上下文,永不定罪 |
| `/adversarial-case-builder` | *(memo,不定罪)* 一个敌意审稿人会写的、最致命的、有证据支撑的拒稿段落 |
| `/novelty-duplication-advisory` | *(memo,不定罪)* 与前作的重叠:trivial 组合("缝合")和重复发表候选,摆出来给人判断 |

单个 skill 只**提出**带 span 锚点的 findings,**永远不给 verdict**。要判决,把 findings
喂给确定性裁决器(下一节那条 `python3 tools/adjudicate_findings.py … --ledger …`)——
模型从不打分。另外两点:`consistency-audit` 和 `presentation-signals` 还会写一份
`*.deterministic.findings.json`(没接跨模型 reviewer 也能用);而 **`/anti-autoresearch`**
一把跑完上面所有 auditor,并额外做 ingest(arxiv-id / pdf → 工作目录 + `pdftotext`)、
自动定可观测层级、自动选哪些 auditor 适用、以及最后的跨维度判决 + `REPORT.md`。

### 确定性内核(CI / 离线 / 零依赖)

它绕过 agent 层,只跑经 eval 测试过的确定性检查 —— 用于 CI、回归测试,或没有跨模型
reviewer 的环境(Python 3 标准库,无需安装):

```bash
# 在干净 + 注入缺陷的 fixture 上验证流水线(回归门)
python3 eval/run_eval.py
#   clean / delta_inflate / dup_table / headline_inflate  → 全部 PASS
#   injected-defect recall: 100% (7 个确定性模式) · 干净假阳: 无
python3 tests/test_adjudicator.py        # 裁决门单元测试(反 slop 保证)

# 或手动在真实论文上跑脊柱:
python3 tools/build_claim_ledger.py --paper-id mypaper --latex main.tex sections/*.tex \
    --observability-level 1 --out claims.json
python3 tools/check_numeric_consistency.py --ledger claims.json --out findings.json
python3 tools/adjudicate_findings.py --findings findings.json --ledger claims.json \
    --paper-id mypaper --observability-level 1 --out report.json --md REPORT.md
#   --ledger 必填:finding 必须引用逐字 ledger span,否则 fail-closed 降到 info。
```

## 🎯 为什么需要它

机器生成的论文/审稿已成为文献中可测量的一部分,但对 AC 真正要紧的,从来不是
"这段文字是不是 LLM 写的"(人能写出造假论文,LLM 也能写出诚实论文),而是:

> **论文是否自相矛盾、是否被它自己的证据支撑?**

这恰恰是 autoresearch 流水线最容易出错的地方 —— 它们为叙事做优化,幻觉出
**局部**自洽:摘要里一个任何表格都没有的数字、号称"提升 16%"而操作数算出来只有
6%、为某条主张引用了一篇根本没这么说的论文、方法描述与实际评测不一致。

这些都是在**声明的可观测性层级下可核查**的。具体地,taxonomy v0.4 编码了
**8 个家族、48 个 hack-pattern**(数值自洽 · 方法/范围 · baseline 诚信 · 实验诚信 ·
引用诚信 · 表象/surface 信号 · 证明 & 推导诚信 · 评测设计与有效性)—— 这是本仓库的
**覆盖词表**,而不是 "48 个检测器的 benchmark"。

> **已交付 v0:**确定性脊柱 + 带 ✓ 的 **7 个**模式(分布在下面的代表性列表和完整目录里)
> 经 eval 测试;其余 41 个是 agent 层合同(跨模型 reviewer 提出带 span 锚点的 finding,
> 确定性裁决器打分或降级)—— 不是"自带 eval 的检测器"承诺。

完整目录(含检测信号与假阳案例)见 [taxonomy](references/hack-pattern-taxonomy.md)。
下面是代表性的十个(✓ = 当前已被确定性 eval 把关):

- `HP-NUM-INFLATE` — 摘要写 85.3%,可表 2 最高才 84.7%。✓
- `HP-DELTA-ERROR` — 号称"提升 16%",73.1→78.0 其实只有 6.7%。✓
- `HP-DUP-TABLE` — 两张表数字逐位相同 —— 多半是复制粘贴凑数。✓
- `HP-METHOD-DRIFT` — 方法说"不用标签",评测却悄悄用了 gold-label 校准。
- `HP-SCOPE-INFLATE` — "comprehensive" 一看就是两个数据集、一个领域、可能就一个 seed。
- `HP-MISSING-BASELINE` — 号称 SOTA,可那个该有的近期 baseline 表里压根没出现。
- `HP-FAKE-GT` — (L2) "参考答案"是模型自己的输出,却当成 ground truth 报。
- `HP-PHANTOM-RESULT` — (L2) 头条数字指向一个并不存在的结果文件 / 指标键。
- `HP-PROOF-CIRCULARITY` — (L1) "证明"把结论换种说法复述一遍就算完 —— 等于什么都没证。
- `HP-CITE-HALLUC` — DOI / arXiv 号 / venue / 作者名,根本查无此文。

<details>
<summary><b>……另外 38 个,逐条列全(覆盖全部 8 个家族)</b></summary>

**A · 数值自洽**
- `HP-AGG-DRIFT` — 写着"多 seed 平均",那个数其实是最好的一个 seed。
- `HP-DENOM-DRIFT` — 一张表对所有任务平均,结论却偷换成"适用任务"子集。
- `HP-UNIT-DIR-MISMATCH` — 百分点悄悄变百分比,或把"越低越好"的指标当越高越好夸。
- `HP-CAPTION-MISMATCH` — caption 说 N=5、方法 B,图里两样都没有。
- `HP-APPENDIX-CONTRA` — 附录把同一个量重算一遍,和正文对不上。
- `HP-GRANULARITY-IMPOSSIBLE` — "500 道题 84.7%" 算术上不可能 —— 没有整数 k/500 能四舍五入到它(GRIM)。✓
- `HP-VARIANCE-IMPOSSIBLE` — 报出的标准差超过有界指标在该均值下的上限(如均值 98% 报 SD 18%,上限 ≈15.7%)。✓
- `HP-STAT-INCONSISTENCY` — 报告的 p 和它自己的检验统计量矛盾、且夸大了显著性("z=1.10, p=.036" 实则 p≈.27)。✓

**B · 方法 & 范围**
- `HP-ABLATION-ATTRIB` — 把功劳记给组件 X,但每个 ablation 里 X 都和 Y 绑在一起。
- `HP-THEOREM-SCOPE-DRIFT` — 摘要卖一个通用定理,真正干活的全是那些假设。
- `HP-ARGUMENT-CHAIN-BREAK` — 实质性的断链:动机引出的问题不是方法解决的那个,或实验测的量不是机制能预测的。
- `HP-CAUSAL-EVIDENCE-LEAP` — 下了一个因果 / 等价的结论,可全文没有哪个实验真的去变量去测它。
- `HP-RESOURCE-IDENTITY-MISMATCH` — 命名的数据集/模型/基准被描述的属性与其公开记录矛盾("ImageNet-1k,5000 类" —— 实为 1000)。

**C · baseline 诚信**
- `HP-WEAK-BASELINE` — 新方法拿到的调参和算力,baseline 明显没给。
- `HP-SIG-OVERLAP` — "超过"就那么一点点,误差棒重叠、或干脆没报 seed。

**D · 实验诚信**(需要代码/结果 —— L2)
- `HP-SELF-NORM` — (L2) 分数接近 1.0,因为除以了模型自己的 max。
- `HP-DEAD-METRIC` — (L2) 指标函数有定义、没调用、没结果,却还在正文里讨论。
- `HP-SUSPICIOUS-REGULARITY` — (L2) 行与行差一个太整齐的常数 —— 先看文件再说"假"。
- `HP-PLACEHOLDER-DATA` — (L2) 开源代码里还留着 placeholder/dummy/假数据,且喂给了某个报告出来的图或数。
- `HP-RESULT-ARTIFACT-MISMATCH` — (L2) 开源代码 / 工件照着跑,产出的数和论文报告的对不上。
- `HP-MISSING-REPRO-ARTIFACT` — (L2) 一篇实证论文,代码、和结果所依赖的 prompt/config 一样都没放。

**E · 引用诚信**
- `HP-CITE-CONTEXT` — 真论文,用错地方:拿来支持一个它明确没说的主张(含语义幻觉 + support/contrast/mention 意图标签)。
- `HP-CITE-RETRACTED` — 一条作为论据的引用,指向的是已**撤稿**的论文,且全文未提撤稿(Crossref / Retraction Watch)。

**F · 表象 / surface 信号**(封顶在 `minor` —— 永不定罪)
- `HP-THIN-FLOAT` — "大规模实证"全文就两张表加一张孤零零的图。
- `HP-LLM-FIGURE` — 那张"图"是装饰性的模型作画,不是图表也不是真示意图。
- `HP-PAGE-PADDING` — 超大浮动图、重复段落、空话,都在替页数干活。
- `HP-JARGON-STUFF` — 名词堆成山,周围的论证几乎没贡献什么。
- `HP-AI-FLAVOR` — 模板化过渡 + 整齐划一的段落节奏;当上下文,不当证据。
- `HP-DEFENSIVE-HEDGE` — 通篇"本文不是 X 而是 Y"的防御式对冲,光在挡反对意见,不直接说做了什么。
- `HP-NARRATIVE-ARC-BREAK` — 摘要读着像实验日志堆砌,没有"背景 → 贡献 → 证据"的弧线。
- `HP-PIPELINE-ARTIFACT` — 残留的流水线/模板字符串("As an AI language model"、"regenerate response"、"[INSERT X]")漏进了成稿正文。✓(精确匹配,低误报)

**G · 证明 & 推导诚信**(在 L1 可定罪 —— 从写出来的数学判定)
- `HP-PROOF-OBLIGATION-GAP` — (L1) 一个必需的引理 / 分支 / 过渡被"显然"一句话跨过了真实的缺口。
- `HP-DERIVATION-INVALID` — (L1) 某个代数 / 概率 / 微积分步骤根本不成立(不等式用反、极限取错)。
- `HP-SYMBOL-SEMANTIC-DRIFT` — (L1) 某个符号 / 算子 / 不等号方向在定义、公式、证明之间换了意思。
- `HP-ASSUMPTION-SMUGGLE` — (L1) 证明悄悄用了定理陈述里从没列出的假设(独立性、凸性……)。

**H · 评测设计与有效性**(L0/L1 stated → L2 confirmed)
- `HP-EVAL-LEAKAGE` — 训练/测试泄漏(先预处理再切分、跨切分重复、时间泄漏、预训练污染)使分数可能并不衡量泛化。采用 Kapoor–Narayanan 泄漏分类法。
- `HP-JUDGE-VALIDITY` — 作为论据的指标是个 LLM 裁判,但*同族*(与被比系统同模型)或*未校验*(没有人类一致性验证)。
- `HP-SELECTIVE-REPORTING` — setup 声明过的条件(某数据集 / baseline / 指标 / seed 数)在结果里被悄悄丢掉,或换指标以利于本方法。

</details>

**这不是假想。** 转述自 NeurIPS 2026 周期一则公开的审稿人吐槽(示意,非正式引用),
一批稿件几乎逐条命中本仓库编码的 taxonomy:

> - *第一篇* — "数据表和正文对不上,好几行错位,不同 backbone 间明显的加减乘除
>   规律性,不像跑出来的。" → consistency · `HP-SUSPICIOUS-REGULARITY`
> - *第二篇* — "两张表占满一页且一模一样,唯一的图还是大模型生成的,就这还没写满
>   9 页。" → `HP-DUP-TABLE` · 表象信号
> - *第三篇* — "公式推导不通,关键问题数学上不正确,实验看着完整但公式错了结果不知
>   道怎么对上的。" → proof-derivation-forensics · `HP-DERIVATION-INVALID`
> - *第四篇* — "开源了,结构完整绘图精美书写流畅 —— 但我把代码跑了,和正文结果南辕
>   北辙。" → experiment-forensics (L2)

第四篇就是本仓库的论点一句话版:**表面光鲜 ≠ 诚信。**

## 🔒 它如何保持诚实(反"LLM 互查互骗"设计)

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

**表象 / AI 味信号有一道单独的防火墙。** AI 味文风、重复表格、LLM 配图、凑页数,只作为
**高假阳的上下文**报告:裁决器把 `presentation-signals` 以及所有 taxonomy-F 的
`pattern_id` **硬封顶在 `minor`**,所以它们最多触发 `SOFT_FLAGS` —— 绝不会成为作者身份
或学术不端的判决。这个封顶是**代码强制**的(`tools/adjudicate_findings.py` 里的
`SURFACE_ONLY_SKILLS`),不是口头承诺。

外加一个 **eval 测试台**(`eval/`):每次改动都在干净 + 人工注入缺陷的 fixture 上
验证确定性核心 —— 量出假阳/召回,而不是凭感觉。

## ⚠️ 局限(信任任何报告前必读)

- **取证 ≠ 学术不端的证明**,所有 finding 都是"待核实的矛盾"。
- **仅 PDF(L0)只能查自洽性与迹象,查不了全部造假**(无法验证外部 GT、无法跑代码)。
- **假阳是真实存在的**(合理的整数、单 seed 试点、有意的范围选择)—— 所以有分层、
  有 FP-risk 标注、有 eval 测试台,而非二元"有罪"。
- **分类法会被绕过**:它是活的、带版本的文档,是安全网而非证明系统。
  详见 [docs/limitations.md](docs/limitations.md)。

## 🧬 来源:派生自 ARIS

[**ARIS — Auto Research in Sleep**](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep)
是一个 AI 科研 agent 技能平台,跑端到端科研流水线(文献 → 想法 → 实验 → 论文)——
而且**内置诚信护栏**,这让它成为这把"审计刀"可信的基座:

- 🛡️ **三层审计栈**让 ARIS *自己*的产出保持诚实:`experiment-audit`(假 GT /
  归一化作弊 / 幽灵结果)、`result-to-claim`(claim 科学上成立吗)、零上下文
  `paper-claim-audit` + `citation-audit`(数字和引用站得住吗)。Anti-Autoresearch
  就是这套审计**朝外**。
- 🔬 **跨模型对抗审**是核心教条:executor 与 reviewer 必须来自不同模型家族,没有
  LLM 给自己的产出打分。Anti-Autoresearch 继承并**加固**了它 —— 这里模型只**提出**
  finding,确定性裁决器**裁决**。

**一体两面。** ARIS 是如何*负责任*地做自动科研;Anti-Autoresearch 是如何*标记出*那些
不负责任的。一个公开了自己审计栈的生成器,最清楚这些流水线会怎么坏 —— 因为它就是
从内部对抗这些坏法的。这正是本仓库带来的视角。

👉 **ARIS 主仓库**:https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep

技能映射:Anti-Autoresearch 的 skill 就是 ARIS 的审计 skill,改造成"第三方审未知
投稿":`consistency-audit` ← `paper-claim-audit`、`experiment-forensics` ←
`experiment-audit`、`citation-forensics` ← `citation-audit`、
`baseline-comparison-audit` ← `paper-claim-audit`、`proof-derivation-forensics` ←
`proof-checker`、`adversarial-case-builder` ← `kill-argument`、
`novelty-duplication-advisory` ← `novelty-check`,外加新的 `evidence-ledger` 脊柱
与 `presentation-signals`。

## 🤝 先行工作与致谢

Anti-Autoresearch 的设计借鉴了一批早于它的诚信、可复现性与评测卫生工作的思路 ——
有些地方还借用了其分类法结构。我们在此明确致谢。**这里采纳的是分类法与思路,均已注明
出处;没有 vendoring 任何外部代码** —— 凡 GPL/AGPL 的工具,我们都是从其论文重新实现
*方法*,而非拷贝源码;凡闭源的,只做概念性致谢。

**确定性自洽(方法上最近的"表亲")。**
- **statcheck** —— Nuijten & Epskamp。从检验统计量重算论文报告的 NHST *p* 值;最经典的
  "论文与自身比对"检查。*(GPL-3 —— 方法按论文重新实现,未 vendoring 源码。)* 启发 `HP-STAT-INCONSISTENCY`。
- **GRIM / GRIMMER** —— Brown & Heathers(GRIM);Anaya(GRIMMER)。检验报告的均值/标准差在给定样本量下是否算术可能。启发 `HP-GRANULARITY-IMPOSSIBLE` / `HP-VARIANCE-IMPOSSIBLE`。
- **scrutiny** —— Jung。把 GRIM/GRIMMER 式一致性检验打包的 R 工具包。*(MIT。)*

  它们启发了分类法家族 A(数值自洽);`tools/check_stat_consistency.py` 是面向 autoresearch 的独立纯 stdlib 重新实现。

**评测诚信与 LLM-judge 有效性(为什么模型从不打分)。**
- **泄漏分类法** —— Kapoor & Narayanan,《Leakage and the Reproducibility Crisis in ML-based Science》。计划中的家族 H 评测诚信模式背后的首要参考。
- **LLM-as-judge 有效性** —— Zheng 等、Panickssery 等(评测者偏爱自己的生成)、Wang 等(位置/身份偏置)。这正是我们的裁决器为何**确定性**、模型只**提出** finding 的原因。
- **《Show Your Work》** —— Dodge 等。*计划中*的选择性报告检查背后的报告卫生准则。

**引用与主张诚信。**
- **Retraction Watch** —— 撤稿记录项目;引用状态意识的概念基础。
- **Problematic Paper Screener** —— Cabanac、Labbé、Magazinov。语料级筛查迹象;`HP-PIPELINE-ARTIFACT` 的来源。
- **scite** —— 支持 / 反驳式引用上下文。*(闭源 —— 仅概念致谢;启发 HP-CITE-CONTEXT。)*
- **SciFact** —— Wadden 等。主张-证据框架背后的科学主张验证数据集/模型。
- **伪造引用分类法** —— Ansari。启发 `HP-CITE-HALLUC` / `HP-CITE-CONTEXT`。

**可复现性检测**(*计划中*的 L2 复现模式的先行工作 —— 尚未实现)。
- **ODDPub** —— Riedel 等。检测论文中的开放数据 / 开放代码声明。*(AGPL-3 —— 概念/方法先行工作;未 vendoring 代码;任何实现都将是独立的。)*
- **RTransparent** —— Serghiou 等。大规模数据/代码共享透明度检测。*(GPL-3 —— 同上。)*
- **SciScore** —— 自动化方法严谨性 / 可复现性检查器。*(闭源 —— 仅概念致谢。)*

Anti-Autoresearch 自身的贡献不是上述任何单一检查,而是把它们**组合**进一套面向
autoresearch 的分类法,置于确定性裁决器与显式可观测性分层之下(见
[docs/positioning.md](docs/positioning.md))。

## 🔭 相关项目

Anti-Autoresearch 相对于邻近工具的位置(stars / 最后更新于 2026-06-27 采集,非排名)。

| 项目 | ★ | 更新 | 与 Anti-Autoresearch 的关系 |
|------|---|------|------------------------------|
| [SakanaAI/AI-Scientist](https://github.com/SakanaAI/AI-Scientist) | 14.1k | 2025-12 | 我们审计其产出的生成器 —— 本仓库正是为审查这类流水线而建。 |
| [karpathy/autoresearch](https://github.com/karpathy/autoresearch) | 88.8k | 2026-03 | 我们审计其产出的生成器;也是这一失败面的命名来源。 |
| [scienceverse/metacheck](https://github.com/scienceverse/metacheck) | 45 | 2026-06 | 最近的"表亲":模块化确定性论文检查。我们额外加上 autoresearch 分类法 + 可观测性分层 + 跨模型提议者。 |
| [MicheleNuijten/statcheck](https://github.com/MicheleNuijten/statcheck) | 189 | 2026-03 | 确定性自洽(NHST *p* 值)—— 窄,但正合我们的精神;启发家族 A。 |
| [lhdjung/scrutiny](https://github.com/lhdjung/scrutiny) | 8 | 2026-05 | GRIM/GRIMMER 一致性检验(R);同属确定性自洽家族。 |
| [allenai/scifact](https://github.com/allenai/scifact) | 265 | 2023-10 | 针对证据的主张验证 —— 主张-证据框架,只是针对外部文献而非论文自身。 |
| [DEFENSE-SEU/FactReview](https://github.com/DEFENSE-SEU/FactReview) | 70 | 2026-06 | **定位上最近的邻居**:审计论文实证主张、**不**做接收/拒稿判断的 LLM reviewer。区别在于它对照外部文献 + **跑论文仓库的代码**(我们拒绝的 L3 复现)且裁决由模型给出 —— 我们靠确定性自洽 + 可观测性分类法。*(AGPL-3.0)* |
| [ahans30/Binoculars](https://github.com/ahans30/Binoculars) | 390 | 2024-05 | AI 文本检测器 —— **我们不是它**:它回答"这是不是 LLM 写的",与诚信正交。 |
| [baoguangsheng/fast-detect-gpt](https://github.com/baoguangsheng/fast-detect-gpt) | 414 | 2026-02 | AI 文本检测器 —— 同一条边界;stylometry ≠ 诚信。 |

少数与定位相关的工作**没有开放仓库**,仅以名字致谢:Pangram、GPTZero,以及
Problematic Paper Screener。

<a id="community"></a>

## 💬 交流群

**这套分类法靠社区一起长大。** 看到某篇 autoresearch / AI-Scientist 论文耍了个
[48 模式目录](references/hack-pattern-taxonomy.md)里还没有的花招?那是这里最有价值的贡献
—— 开个 issue 贴上具体例子,或直接发 PR 把这个模式补进去(配一条 eval fixture + 一个假阳
案例,免得它乱开火)。新的 auditor skill、裁决器 gate、corruption fixture 同样欢迎。
**[CONTRIBUTING.md](CONTRIBUTING.md)** 讲清了一个 pattern 怎么写、以及每条 flag 必须守的
诚实底线(描述可核查的矛盾,绝不臆断学术不端或作者身份)。

加入微信群(与 [ARIS](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep)
社区共享),一起交流 autoresearch 的各种翻车现象:

<p align="center">
  <img src="docs/wechat_group.jpg" alt="微信群二维码(与 ARIS 社区共享)" width="300">
</p>

*(群二维码每周轮换 —— 过期了就开个 issue,我们会贴新的。)*

<a id="citation"></a>

## 📖 引用 Citation

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

## ⚖️ 许可证

MIT,见 [LICENSE](LICENSE)。
