# Security Policy

## Reporting a vulnerability

Please report security issues **privately** via GitHub's
[private vulnerability reporting](https://github.com/wanshuiyin/Anti-Autoresearch/security/advisories/new)
(Security → Report a vulnerability), not in a public issue. We aim to acknowledge within a
few days.

## Scope & threat model (please read)

Anti-Autoresearch runs on **untrusted input** — a third party's paper (PDF / LaTeX) and,
at L2, their repository. Two things to be aware of:

- **Parsing untrusted documents.** The deterministic tools are pure Python stdlib and do not
  execute paper content, but they do parse attacker-controlled text/LaTeX. The orchestrator
  also shells out to `pdftotext` / `mutool` / `pdfminer` for ingest. Run audits in an
  environment you're comfortable exposing to untrusted documents; do not assume sandboxing.
- **The cross-model reviewer sends paper text off-machine.** The semantic auditor skills pass
  excerpts of the paper to a third-party model (e.g. Codex via MCP) for the *propose-findings*
  step. Do **not** run those skills on confidential / embargoed submissions you may not share
  with an external model provider. The deterministic-core-only path (`eval/run_eval.py` and the
  `tools/` spine) sends nothing off-machine.

In-scope vulnerabilities: parser crashes/DoS on malicious input, path traversal in ingest,
any way to make the deterministic adjudicator emit a verdict that violates its gates
(unanchored/over-observability finding raising the verdict). Out of scope: false
positives/negatives in the *semantic* (LLM-proposed) layer — report those as regular issues.
