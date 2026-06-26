# Anti-Autoresearch 🛡️（反自动科研）

[![Parent ARIS stars](https://img.shields.io/github/stars/wanshuiyin/Auto-claude-code-research-in-sleep?style=flat&logo=github&logoColor=white&color=gold&label=Parent%20ARIS%20%E2%98%85)](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/stargazers) · [![ARIS Report arXiv:2605.03042](https://img.shields.io/badge/ARIS%20Report-arXiv%3A2605.03042-b31b1b?style=flat&logo=arxiv)](https://arxiv.org/abs/2605.03042) · [![ARIS · HF Daily #1](https://img.shields.io/badge/ARIS%20%F0%9F%A4%97%20HF%20Daily-%231-ffcc4d?style=flat)](https://huggingface.co/papers/2605.03042) · [![ARIS on PaperWeekly](https://img.shields.io/badge/ARIS%20on-PaperWeekly-red?style=flat)](https://mp.weixin.qq.com/s/tDniVryVGjDkkkWl-5sTkQ) · [![ARIS in awesome-agent-skills](https://img.shields.io/badge/ARIS%20in-awesome--agent--skills-blue?style=flat&logo=github)](https://github.com/VoltAgent/awesome-agent-skills) · [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat)](LICENSE) · [![README English](https://img.shields.io/badge/README-English-blue?style=flat)](README.md)

<div align="center">

### 🔬 天下苦 autoresearch 久矣 —— Anti-Autoresearch 替审稿人一眼看穿不靠谱的工作。

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

## 🎯 为什么需要它

机器生成的论文/审稿已成为文献中可测量的一部分,但对 AC 真正要紧的,从来不是
"这段文字是不是 LLM 写的"(人能写出造假论文,LLM 也能写出诚实论文),而是:

> **论文是否自相矛盾、是否被它自己的证据支撑?**

这恰恰是 autoresearch 流水线最容易出错的地方 —— 它们为叙事做优化,幻觉出
**局部**自洽:摘要里一个任何表格都没有的数字、号称"提升 16%"而操作数算出来只有
6%、为某条主张引用了一篇根本没这么说的论文、方法描述与实际评测不一致。

这些都是在**声明的可观测性层级下可核查**的。具体地,taxonomy v0.2 编码了
**6 个家族、27 个 hack-pattern**(数值自洽 · 方法/范围 · baseline 诚信 · 实验诚信 ·
引用诚信 · 表象/surface 信号)—— 这是本仓库的**覆盖词表**,而不是"27 个检测器的
benchmark"。

> **已交付 v0:**确定性脊柱 + 下面带 ✓ 的 3 个模式经 eval 测试;其余 24 个是 agent
> 层合同(跨模型 reviewer 提出带 span 锚点的 finding,确定性裁决器打分或降级)——
> 不是"自带 eval 的检测器"承诺。

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
- `HP-SUSPICIOUS-REGULARITY` — (L2) 行与行差一个太整齐的常数 —— 先看文件再说"假"。
- `HP-CITE-HALLUC` — DOI / arXiv 号 / venue / 作者名,根本查无此文。

<details>
<summary><b>……另外 17 个,逐条列全(覆盖全部 6 个家族)</b></summary>

**A · 数值自洽**
- `HP-AGG-DRIFT` — 写着"多 seed 平均",那个数其实是最好的一个 seed。
- `HP-DENOM-DRIFT` — 一张表对所有任务平均,结论却偷换成"适用任务"子集。
- `HP-UNIT-DIR-MISMATCH` — 百分点悄悄变百分比,或把"越低越好"的指标当越高越好夸。
- `HP-CAPTION-MISMATCH` — caption 说 N=5、方法 B,图里两样都没有。
- `HP-APPENDIX-CONTRA` — 附录把同一个量重算一遍,和正文对不上。

**B · 方法 & 范围**
- `HP-ABLATION-ATTRIB` — 把功劳记给组件 X,但每个 ablation 里 X 都和 Y 绑在一起。
- `HP-THEOREM-SCOPE-DRIFT` — 摘要卖一个通用定理,真正干活的全是那些假设。

**C · baseline 诚信**
- `HP-WEAK-BASELINE` — 新方法拿到的调参和算力,baseline 明显没给。
- `HP-SIG-OVERLAP` — "超过"就那么一点点,误差棒重叠、或干脆没报 seed。

**D · 实验诚信**(需要代码/结果 —— L2)
- `HP-SELF-NORM` — (L2) 分数接近 1.0,因为除以了模型自己的 max。
- `HP-DEAD-METRIC` — (L2) 指标函数有定义、没调用、没结果,却还在正文里讨论。

**E · 引用诚信**
- `HP-CITE-CONTEXT` — 真论文,用错地方:拿来支持一个它明确没说的主张。

**F · 表象 / surface 信号**(封顶在 `minor` —— 永不定罪)
- `HP-THIN-FLOAT` — "大规模实证"全文就两张表加一张孤零零的图。
- `HP-LLM-FIGURE` — 那张"图"是装饰性的模型作画,不是图表也不是真示意图。
- `HP-PAGE-PADDING` — 超大浮动图、重复段落、空话,都在替页数干活。
- `HP-JARGON-STUFF` — 名词堆成山,周围的论证几乎没贡献什么。
- `HP-AI-FLAVOR` — 模板化过渡 + 整齐划一的段落节奏;当上下文,不当证据。

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
