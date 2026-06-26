# Anti-Autoresearch 🛡️（反自动科研）

**面向研究论文的"实质性诚信取证"工具 —— 尤其针对机器生成（autoresearch /
AI-Scientist 式）的论文产出。**

> **[ARIS](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep)（~12.5k★ 自动科研 agent 平台）的对偶。** ARIS 做自动科研是**负责任**的:它内置了多层审计栈(experiment-integrity · result-to-claim · 零上下文 paper-claim 审 · citation 审),让自己的产出保持诚实。**Anti-Autoresearch 就是这枚硬币的另一面** —— 把同一套审计 DNA 朝外,抓那些**没有**这些护栏就产出的自动科研论文。(English [README.md](README.md) · ARIS 来源见下文)

> 不管论文是谁、是什么写的,它的科学结论是否自洽、是否被自己的证据支撑?
> Anti-Autoresearch 审查一篇投稿的**自洽性**与**造假迹象**,产出带证据锚点、
> 可供审稿人直接使用的报告。它**不是** AI 文本检测器,也**不下学术不端的结论**——
> 它只把"值得人去核实的矛盾点"摆出来。

---

## 🎯 为什么需要它

机器生成的论文/审稿已成为文献中可测量的一部分,但对 AC 真正要紧的,从来不是
"这段文字是不是 LLM 写的"(人能写出造假论文,LLM 也能写出诚实论文),而是:

> **论文是否自相矛盾、是否被它自己的证据支撑?**

这恰恰是 autoresearch 流水线最容易出错的地方 —— 它们为叙事做优化,幻觉出
**局部**自洽:摘要里一个任何表格都没有的数字、号称"提升 16%"而操作数算出来只有
6%、为某条主张引用了一篇根本没这么说的论文、方法描述与实际评测不一致。

这些都是在**声明的可观测性层级下可核查**的。具体地,taxonomy v0.2 编码了
**6 个家族、27 个 hack-pattern**(数值自洽 · 方法/范围 · baseline 诚信 · 实验诚信 ·
引用诚信 · 表象/surface 信号)。请把它当作本仓库的**覆盖词表(coverage vocabulary)**,
而**不是**一个"27 个检测器的 benchmark":零依赖的确定性 eval 目前只把关其中 **3 个**
(`HP-DELTA-ERROR`、`HP-NUM-INFLATE`、`HP-DUP-TABLE`);其余 **24 个**是 agent 层检查 ——
跨模型审计员提出带 span 锚点的 finding,再由确定性裁决器按证据、可观测性、假阳风险
打分或降级。

代表性的一小撮(✓ = 当前已被确定性 eval 把关;其余为 agent 层;完整目录见
[taxonomy](references/hack-pattern-taxonomy.md)):

- `HP-NUM-INFLATE` — 头条数字大于它自己的表格 ✓
- `HP-DELTA-ERROR` — 相对提升的算术对不上 ✓
- `HP-DUP-TABLE` — 重复 / 近乎一样的表格 ✓
- `HP-METHOD-DRIFT` — 描述的方法 ≠ 实际评测的方法
- `HP-SCOPE-INFLATE` — 范围措辞超过证据
- `HP-MISSING-BASELINE` — 该有的 SOTA 对比缺席
- `HP-FAKE-GT` — "ground truth" 由模型输出派生(L2)
- `HP-PHANTOM-RESULT` — 报告的数字没有任何产物支撑(L2)
- `HP-SUSPICIOUS-REGULARITY` — 结果太规整,不像真跑出来的
- `HP-CITE-HALLUC` — 编造 / 不存在的引用

<details>
<summary><b>……另外 17 个,覆盖全部 6 个家族</b></summary>

- **A · 数值自洽** — `HP-AGG-DRIFT`(best 当 mean 报)· `HP-DENOM-DRIFT`(统计口径漂移)· `HP-UNIT-DIR-MISMATCH`(单位/方向混淆)· `HP-CAPTION-MISMATCH`(caption ≠ 内容)· `HP-APPENDIX-CONTRA`(附录与正文矛盾)
- **B · 方法 & 范围** — `HP-ABLATION-ATTRIB`(增益未被 ablation 隔离)· `HP-THEOREM-SCOPE-DRIFT`(摘要泛化、定理却很窄)
- **C · baseline 诚信** — `HP-WEAK-BASELINE`(baseline 欠调 / 配置不一致)· `HP-SIG-OVERLAP`("超过"但误差棒重叠)
- **D · 实验诚信(L2)** — `HP-SELF-NORM`(用模型自己的统计量归一化分数)· `HP-DEAD-METRIC`(指标定义了却从未计算)
- **E · 引用诚信** — `HP-CITE-CONTEXT`(真论文,却被用来支持它没说的主张)
- **F · 表象 / surface — 封顶在 `minor`** — `HP-THIN-FLOAT`(图表太少)· `HP-LLM-FIGURE`(机器生成的图)· `HP-PAGE-PADDING`(凑页数的填充)· `HP-JARGON-STUFF`(堆砌名词)· `HP-AI-FLAVOR`(泛泛的 LLM 文风)

</details>

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

第四篇就是本仓库的论点一句话版:**表面光鲜 ≠ 诚信。**

## 🧩 它填补的空白

现有工作分三簇:(A) **AI 文本检测**(文体学,"是不是 LLM 写的");(B) **AI 审稿
检测**;(C) **通用 claim/严谨性核查**(FactReview、RIGOURATE、引用造假分类法)。
本仓库瞄准的空白是它们的**组合**:**autoresearch 专属的实质性诚信取证** —— 即"内部
自洽取证 + autoresearch 专属 hack-pattern 分类法"。我们把论文**与它自己**对照(不需要
外部 ground truth,而这正是机器产出露馅的地方),并把失败目录专门化到 autoresearch。
它**不是** AI 文本分类器(Pangram/GPTZero/Binoculars)、不是 AI 审稿检测器、不下学术
不端判决、也不是会改论文的"合著者"。详见 [docs/positioning.md](docs/positioning.md)。

## 🚦 状态 —— v0 到底交付了什么

把"今天就能跑"和"agent 编排合同"分清楚(这正是本仓库的要点 —— 见 [DESIGN.md](DESIGN.md)):

- **确定性内核 —— 现在就能跑、零依赖、有测试。** 证据账本抽取器、artifact-manifest /
  可观测性推导、数值自洽检查(`HP-DELTA-ERROR`、`HP-NUM-INFLATE`)、规则裁决器。`eval/`
  测试台为它们把关:在自带 fixture 上对 **3 个确定性模式**(`HP-DELTA-ERROR`、
  `HP-NUM-INFLATE`、`HP-DUP-TABLE`)**100% 召回、零干净假阳**,每条 above-info finding
  都有 ledger 锚点。这是承重的、可复现的部分 —— 全程无模型。
- **agent 层审计 —— alpha,需要 Claude + 跨模型 reviewer。** 语义 skill(方法漂移、
  ablation 归因、错引上下文、baseline 充分性、实验代码诚信,以及辅助的表象/AI 味信号)
  是经 `/anti-autoresearch` 由 agent 执行的 `SKILL.md` 合同。它们提出带 span 锚点的
  finding,交由**同一个**确定性裁决器打分;**目前还没进自带的确定性 eval** —— 为这些
  语义模式补 fixture 是 roadmap,不是已交付的 claim。

**裁决机制和数值内核是真实且经测试的**;语义覆盖是一份随 taxonomy 与 eval 一起生长的
agent 合同。v0 已交付的 claim 刻意收窄、可测试;更广义的"造假取证"是方向,如上诚实标注。

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

### 确定性内核(CI / 离线 / 零依赖)

它绕过 agent 层,只跑经 eval 测试过的确定性检查 —— 用于 CI、回归测试,或没有跨模型
reviewer 的环境(Python 3 标准库,无需安装):

```bash
# 在干净 + 注入缺陷的 fixture 上验证流水线(回归门)
python3 eval/run_eval.py
#   clean / delta_inflate / dup_table / headline_inflate  → 全部 PASS
#   injected-defect recall: 100% (3 个确定性模式) · 干净假阳: 无
python3 tests/test_adjudicator.py        # 裁决门单元测试(反 slop 保证)

# 或手动在真实论文上跑脊柱:
python3 tools/build_claim_ledger.py --paper-id mypaper --latex main.tex sections/*.tex \
    --observability-level 1 --out claims.json
python3 tools/check_numeric_consistency.py --ledger claims.json --out findings.json
python3 tools/adjudicate_findings.py --findings findings.json --ledger claims.json \
    --paper-id mypaper --observability-level 1 --out report.json --md REPORT.md
#   --ledger 必填:finding 必须引用逐字 ledger span,否则 fail-closed 降到 info。
```

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
`baseline-comparison-audit` ← `paper-claim-audit`、`adversarial-case-builder` ←
`kill-argument`,外加新的 `evidence-ledger` 脊柱与 `presentation-signals`。

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
