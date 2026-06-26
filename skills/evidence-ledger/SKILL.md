---
name: evidence-ledger
description: "Build the deterministic evidence ledger (artifact_manifest.json + claims.json) that every other Anti-Autoresearch auditor reads. One pass inventories artifacts, derives the observability level (L0 PDF-only / L1 +LaTeX / L2 +repo+results) by fixed rule, and extracts span-anchored, hashed, checkable claims (numbers, comparisons, scope, method, baselines, citations, captions, table cells) into claims.json. An OPTIONAL additive cross-model pass ADDS span-anchored semantic claims (method/theorem/scope/baseline) — it never invents a number, emits a finding, or computes a verdict. Run FIRST, before any audit skill. Triggers: \"build the ledger\", \"extract claims\", \"prep for integrity audit\", \"evidence ledger\", \"建证据账本\"."
argument-hint: [paper-dir | arxiv-id | pdf-path]
allowed-tools: Bash(*), Read, Write, Grep, Glob, mcp__codex__codex
---

# Evidence Ledger — the spine every auditor reads

> Infrastructure skill, **not an auditor**. It produces the *only* structure the
> auditor skills are allowed to reason over, so they don't each re-read the PDF and
> hallucinate a different table and a different list of numbers. It emits **no
> findings and no verdict** — only `artifact_manifest.json` + `claims.json`. See
> `references/integrity-forensics-contract.md` §"The pipeline" (stages [1]–[2]).

Build the ledger for: **$ARGUMENTS**

> 🔁 **Not verdict-bearing — but not a polling skill either.** The deterministic
> backbone (Steps 1–2) is a *pure function of the hashed sources*: same source bytes
> → byte-identical `claims.json`. Re-run it only when the sources change, never on a
> wall-clock timer. The only non-deterministic part is the optional enrichment pass
> (Step 3), which is additive and skippable. Do **not** wrap this skill in `/loop` /
> `/schedule` / `CronCreate`; there is no verdict to re-fire and no external event to
> wait on.

## Why this exists

Five language-model auditors each independently parsing a PDF = five different
hallucinated tables and five different number lists, none reproducible — and the
obvious dismissal, *"an LLM grading another LLM's paper is just slop."* The
structural answer is **one deterministic pass** that turns the paper into:

- `artifact_manifest.json` — what was observable; this fixes the **observability
  level L**, the ceiling on every downstream finding's severity, and
- `claims.json` — a list of **span-anchored, hashed, checkable** claims
  (`schemas/claims.schema.json`).

Every downstream finding must cite a `claim_id` from this ledger and quote a verbatim
span of it. **No ledger claim → no finding** (the single most important integrity
rule of the repo, enforced again by `tools/adjudicate_findings.py`). That is what
makes the difference between "a model said so" and "here is the exact sentence, its
file, and its content hash" (`DESIGN.md` §2).

## Role in the pipeline (what this skill does and does NOT do)

| Stage | Skill / tool | Emits | Judges? |
|-------|--------------|-------|:-------:|
| **[1]–[2] ledger** | **evidence-ledger (this skill)** + `tools/build_manifest.py`, `tools/build_claim_ledger.py` | `artifact_manifest.json` + `claims.json` | **No.** States *what the paper says*. |
| [3] auditors | `consistency-audit`, `citation-forensics`, `baseline-comparison-audit`, `experiment-forensics` | `<skill>.findings.json` (read the ledger; quote its spans) | Propose findings — not the verdict. |
| [3] surface | `presentation-signals` | capped-at-`minor` surface findings (auxiliary) | Never a standalone verdict. |
| [3] memo | `adversarial-case-builder` | an evidence-bound memo | No verdict weight. |
| [4] **verdict** | `tools/adjudicate_findings.py` | `report.json` + `REPORT.md` | **Yes** — the ONLY verdict, by fixed rules, no model in the loop. |

This skill is stage [1]–[2] only. It states **what the paper says**, never **whether
it is right**. The `finding.schema.json` `skill` enum technically lists
`evidence-ledger` for completeness, but this skill never writes a finding object. If
you came here for a PASS/FAIL, you want `/anti-autoresearch` (the orchestrator), not
this skill.

## Core principle

**Deterministic first; the model may only add, never invent, never judge.**

1. The numeric/citation/table backbone comes from **code** (`tools/`), not a model —
   that is what makes the whole pipeline reproducible and defensible.
2. The optional LLM pass is an **additive claim-extractor**: it may add a
   span-anchored *semantic* claim whose `text_span` is a verbatim substring of a
   hashed source file; it may **never** introduce a number, alter an extracted value,
   propose a finding, or assign a severity/verdict. The executor validates every
   added span (Step 4) and rejects anything it cannot locate.
3. **No span → no claim.** Every `text_span` in the ledger must be locatable in a
   hashed source. This is the same gate the adjudicator enforces on findings, applied
   one stage upstream.

## Constants

- **LEDGER_VERSION = `0.1`** — stamped into `claims.json` by `build_claim_ledger.py`; never hand-edit.
- **TAXONOMY_VERSION = `0.2`** — the ledger is **taxonomy-agnostic** (it tags no `pattern_id`); patterns are applied *post-hoc* by auditors (`references/hack-pattern-taxonomy.md`). Never tag a claim with a `pattern_id` here.
- **OBSERVABILITY = derived** — `L0` (PDF/text only) · `L1` (LaTeX, no results) · `L2` (repo + results). **`L3` is never emitted in v0** (we never promise reproduction). The rule is deterministic (`references/observability-levels.md`).
- **EMITS_FINDINGS = `false` · EMITS_VERDICT = `false`** — load-bearing. This skill produces a ledger, not judgments.
- **DETECT_ONLY = `true`** — never edits the audited paper; only reads sources and writes its own outputs (this is why `Edit` is absent from `allowed-tools`).
- **ENRICH = `true`** (default) — run the additive semantic pass (Step 3). Set `false` (or pass `— enrich: false`) to ship the deterministic backbone alone. Enrichment is **non-blocking**: if the Codex MCP is unavailable it is skipped and the deterministic ledger is the canonical output.
- **REVIEWER (enrichment only)** — model `gpt-5.5`, `model_reasoning_effort: xhigh`, `sandbox: read-only`, **different model family** from the executor (`references/reviewer-independence.md` Layer 1). **CONTEXT_POLICY = fresh**: a new `mcp__codex__codex` thread per run, **never** `mcp__codex__codex-reply`. Told only source paths + the existing ledger, never the executor's opinions or any prior finding.
- **OUTPUTS** — `artifact_manifest.json`, `claims.json` (+ enrichment trace under `.aris/traces/evidence-ledger/<date>_run<NN>/` when Step 3 runs), all written into the paper directory.

> Resolve the repo root once and reuse it for every tool call:
> `ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)`. **Shell variables do
> not persist between separate Bash calls**, so Step 0 persists the resolved values
> to a `run.env`; every later block re-sources it (or run a Step's commands in one
> Bash call). Always use absolute paths.

---

## Step 0 — Resolve the input & set up the run

`$ARGUMENTS` is a **paper directory**, a **PDF path**, or an **arXiv id**. Resolve it
to one absolute `PAPER_DIR` + a stable `PAPER_ID`, extract PDF text if there is no
LaTeX, and persist the values. **Never fabricate inputs**; if no source text can be
produced, stop (a fake `claims.json` is worse than none).

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
ARG="$ARGUMENTS"

if [ -d "$ARG" ]; then                                   # (a) paper directory
    PAPER_DIR="$(cd "$ARG" && pwd)"; PAPER_ID="$(basename "$PAPER_DIR")"
elif [ -f "$ARG" ] && printf '%s' "$ARG" | grep -qiE '\.pdf$'; then   # (b) lone PDF
    PAPER_ID="$(basename "${ARG%.*}")"
    PAPER_DIR="$(pwd)/.aa_work/$PAPER_ID"; mkdir -p "$PAPER_DIR"; cp "$ARG" "$PAPER_DIR/paper.pdf"
elif printf '%s' "$ARG" | grep -qE '^[0-9]{4}\.[0-9]{4,5}(v[0-9]+)?$'; then   # (c) arXiv id
    PAPER_ID="${ARG//./_}"
    PAPER_DIR="$(pwd)/.aa_work/$PAPER_ID"; mkdir -p "$PAPER_DIR"
    ( curl -fsSL "https://arxiv.org/e-print/$ARG" -o "$PAPER_DIR/src.tar" \
        && tar -xf "$PAPER_DIR/src.tar" -C "$PAPER_DIR" 2>/dev/null ) \
      || curl -fsSL "https://arxiv.org/pdf/$ARG.pdf" -o "$PAPER_DIR/paper.pdf"   # source preferred (better spans)
else
    echo "ERROR: cannot resolve '$ARG' (need a dir, a .pdf path, or an arXiv id like 2401.01234)"; exit 1
fi

# No LaTeX? Extract PDF text now (best spans available at L0). -layout preserves table columns.
if ! find "$PAPER_DIR" -name '*.tex' -not -path '*/.aris/*' | grep -q .; then
    PDF=$(find "$PAPER_DIR" -maxdepth 2 -name '*.pdf' | head -n1)
    [ -n "$PDF" ] && { pdftotext -layout "$PDF" "$PAPER_DIR/paper.txt" 2>/dev/null \
      || mutool draw -F txt -o "$PAPER_DIR/paper.txt" "$PDF" 2>/dev/null \
      || python3 -c 'import sys,fitz;open(sys.argv[2],"w").write("\n".join(p.get_text() for p in fitz.open(sys.argv[1])))' "$PDF" "$PAPER_DIR/paper.txt" 2>/dev/null; }
fi

mkdir -p "$PAPER_DIR/.aris/evidence-ledger"
cat > "$PAPER_DIR/.aris/evidence-ledger/run.env" <<EOF
ROOT="$ROOT"
PAPER_DIR="$PAPER_DIR"
PAPER_ID="$PAPER_ID"
EOF
echo "PAPER_DIR=$PAPER_DIR  PAPER_ID=$PAPER_ID  ROOT=$ROOT"
find "$PAPER_DIR" \( -name '*.tex' -o -name '*.pdf' -o -name '*.txt' \) -not -path '*/.aris/*' | sort
```

Every later Bash block begins with `source "<PAPER_DIR>/.aris/evidence-ledger/run.env"`
— substitute the absolute `PAPER_DIR` printed above.

**Validation gate.** `"$PAPER_DIR"` must now contain at least one of `*.tex`,
`*.pdf`, or `*.txt`.

**Failure handling.**
- No `*.tex`, `*.pdf`, **or** `*.txt` → **STOP**: report exactly what was searched; there is no source to anchor spans against, so there can be no ledger.
- arXiv `curl` failed (network/proxy) → **STOP**: report the exit and ask the caller for a local paper-dir or PDF. Do **not** fabricate a ledger.
- A near-empty / garbled `paper.txt` (scanned image, heavy math) → say so explicitly and treat the run as L0 with `confidence: low` throughout; do not silently proceed as if you had clean text.

## Step 1 — Artifact manifest + observability level (deterministic)

Inventory what is available and **derive** L by the fixed rule — a tool, not a manual
judgment. The level caps every downstream finding's severity, so it must be honest.

```bash
source "<PAPER_DIR>/.aris/evidence-ledger/run.env"
MAN_ARGS=(--paper-id "$PAPER_ID" --dir "$PAPER_DIR" --out "$PAPER_DIR/artifact_manifest.json")
[ -f "$PAPER_DIR/paper.txt" ] && MAN_ARGS+=(--pdf-text "$PAPER_DIR/paper.txt")
python3 "$ROOT/tools/build_manifest.py" "${MAN_ARGS[@]}"
# -> manifest: observability L1 (latex=1 pdf=0 bib=0 repo=False results=False) -> .../artifact_manifest.json

L=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["observability_level"])' "$PAPER_DIR/artifact_manifest.json")
case "$L" in 0|1|2) : ;; *) echo "ERROR: unexpected level '$L' (v0 operates only at L0/L1/L2)"; exit 1;; esac
echo "L=$L" >> "$PAPER_DIR/.aris/evidence-ledger/run.env"   # carry L forward to Step 2
echo "observability level = L$L"
```

The derivation rule (`references/observability-levels.md`; `build_manifest.py`
implements exactly this):

| Present | Level | Means |
|---------|:-----:|-------|
| repo (`code/`,`src/`,`repo/` or loose `*.py`/`*.ipynb`) **and** results (`*.json`/`*.csv` under `results/`,`outputs/`,`logs/`) | **L2** | code + results checkable: fake GT, self-norm, phantom results, paper↔result match |
| LaTeX present, **no** results | **L1** | source-level checks on stable spans (file:line, real cells, real `.bib`) |
| PDF / text only | **L0** | internal self-consistency, arithmetic, citation existence/context only |

**Validation gate — never over-state the level.** If you only have a PDF, `L` MUST be
`0`; do not hand `--observability-level 2` to Step 2 because a repo "exists somewhere
else." `build_manifest.py` **never** sets `repo.rerunnable: true` (no L3 in v0) — do
not edit it to true. Edge cases the rule handles correctly: an empty `results/` dir
(no data files) stays **L1**; a repo present **without** results stays **L1** (you can
read code but have no outputs to reconcile against).

**Failure handling.** `build_manifest.py` non-zero exit or empty/invalid JSON →
**STOP**: without a derived level you cannot legally cap severity downstream; do not
guess a level.

## Step 2 — Extract the deterministic ledger (no LLM)

The numeric/citation/table backbone comes from **code**, not a model. **LaTeX-first**
(stable spans + real line numbers); the PDF-text path is a lower-confidence fallback.
Pass the **same `L`** derived in Step 1.

**Branch A — LaTeX present (L1/L2; preferred):**

```bash
source "<PAPER_DIR>/.aris/evidence-ledger/run.env"
TEX=$(find "$PAPER_DIR" -type f -name '*.tex' -not -path '*/.aris/*' | sort)   # if any path has spaces, list files explicitly
python3 "$ROOT/tools/build_claim_ledger.py" --paper-id "$PAPER_ID" \
    --latex $TEX \
    --observability-level "$L" \
    --out "$PAPER_DIR/claims.json"
# -> ledger: 13 claims {'caption': 1, 'citation': 3, 'number': 7, 'table_cell': 2} -> .../claims.json
```

**Branch B — PDF/text only (L0; `paper.txt` from Step 0):**

```bash
source "<PAPER_DIR>/.aris/evidence-ledger/run.env"
test -s "$PAPER_DIR/paper.txt" || { echo "ERROR: no extracted text"; exit 1; }
python3 "$ROOT/tools/build_claim_ledger.py" --paper-id "$PAPER_ID" \
    --pdf-text "$PAPER_DIR/paper.txt" --observability-level 0 \
    --out "$PAPER_DIR/claims.json"
```

What it extracts (each claim carries `claim_id`, `type`, verbatim `text_span`,
`location{file,line,section}`, `evidence_anchor` = sha256 of the source text,
`extractor`, `confidence`; numeric claims also carry a parsed `value`):

| `type` | From | `extractor` | `confidence` |
|--------|------|-------------|--------------|
| `table_cell` | numbers inside `tabular` | `table_parser` | medium |
| `number` | numeric prose (`%`, points, `x`, or near a metric word) | `latex_regex` | high |
| `citation` | `\cite{...}` (keys in `refs[]`) | `latex_regex` | high |
| `scope` | scope/SOTA language (`comprehensive`, `robust`, `outperform…`, `first to`, …) | `latex_regex` | high |
| `caption` | `\caption{...}` | `latex_regex` | medium |
| (PDF path) `number` / `scope` | sentence text from `paper.txt` | `pdf_text` | **low** |

The section tracker labels each span `abstract | intro | method | experiments |
table:N | figure:N | appendix | body` (section names lowercased from `\section{...}`);
the **PDF-text path cannot track sections or lines** and labels them `unknown`.
Numeric claims carry `value{raw,normalized,unit,metric,direction,aggregation}` so the
deterministic layer can do arithmetic (delta/coherence checks) downstream **without** a
model. Omit `--generated-at` for **byte-reproducible** output (the eval harness does
this); pass `--generated-at "$(date -u +%Y-%m-%dT%H:%M:%SZ)"` for run provenance — the
*claims* are identical either way.

**Worked example** (clean fixture `eval/fixtures/clean/sample_paper.tex` as `main.tex`)
— the stdout above, then two real claims (`location.file` mirrors the path you pass to
`--latex`):

```json
{ "claim_id": "C001", "type": "table_cell",
  "text_span": "Baseline \\cite{smith2024bar} & 73.1 \\\\",
  "location": {"file": "main.tex", "line": 36, "section": "table:1"},
  "value": {"raw":"73.1","normalized":73.1,"unit":null,"metric":null,"direction":"unknown","aggregation":"unspecified"},
  "evidence_anchor": "e6186efa…0460", "extractor": "table_parser", "confidence": "medium" }

{ "claim_id": "C003", "type": "number",
  "text_span": "FooNet reaches 78.0\\% accuracy, improving from a 73.1\\% baseline to 78.0\\% accuracy, a 6.7\\% relative improvement.",
  "location": {"file": "main.tex", "line": 9, "section": "abstract"},
  "value": {"raw":"78.0","normalized":78.0,"unit":"%","metric":"accuracy","direction":"unknown","aggregation":"unspecified"},
  "evidence_anchor": "e6186efa…0460", "extractor": "latex_regex", "confidence": "high" }
```

> **The ledger states, it does not judge.** Run the extractor on the *corrupted*
> `eval/fixtures/synthetic_corruptions/delta_inflate.tex` (abstract says "16.7%
> relative improvement") and you get an **identical 13-claim shape** — only C003's
> verbatim text changes. Spotting that 16.7% contradicts 73.1→78.0 is
> **consistency-audit**'s job (HP-DELTA-ERROR), not the ledger's; the ledger just
> captures the span faithfully.

**Validation gate.** Confirm the ledger is well-formed, the level matches, and report
the claim mix:

```bash
source "<PAPER_DIR>/.aris/evidence-ledger/run.env"
python3 - "$PAPER_DIR/claims.json" "$L" <<'PY'
import json,sys
d=json.load(open(sys.argv[1],encoding="utf-8")); L=int(sys.argv[2])
for k in ("ledger_version","paper_id","observability_level","source_files","claims"):
    assert k in d, f"ledger missing top-level key: {k}"
assert d["observability_level"]==L, f"level drift: ledger={d['observability_level']} manifest={L}"
assert d["source_files"] and all(s.get("sha256") for s in d["source_files"]), "missing source hash"
for c in d["claims"]:
    assert {"claim_id","type","text_span","location"} <= c.keys(), f"claim {c.get('claim_id')} missing field"
    assert c["location"].get("file"), f"claim {c['claim_id']} has no location.file"
by={t:sum(1 for c in d["claims"] if c["type"]==t) for t in sorted({c['type'] for c in d['claims']})}
print(f"OK ledger L{L}: {len(d['claims'])} claims {by}")
PY
```

**Failure handling.**
- `build_claim_ledger.py` errors with "provide at least one --latex or --pdf-text" → your file glob matched nothing; re-check the branch (use Branch B if `$TEX` is empty).
- **0 claims** on a paper that visibly has numbers/citations → the wrong files were passed or the `.tex` is a stub. Re-inspect inputs (read the head of the `.tex`/`.txt`) and re-run; do **not** fabricate claims. A genuinely claim-free paper is rare — ship the empty ledger only after confirming inputs.
- A single malformed `.tex` → prefer dropping that one file over abandoning the run (regex extraction is best-effort, per-file).

## Step 3 — Optional additive semantic enrichment (cross-model, fresh thread)

> Skip entirely when `ENRICH = false`. This step **adds** claims; it never edits or
> removes a deterministic claim, never adds a number, never proposes a finding.

The regex backbone has high recall on the *numeric/citation* surface but misses the
*semantic* spans auditors need: the **method-definition** span, **theorem statements
with their assumptions**, explicit **scope** sentences, the **baseline** list, and
**comparison framings** (these feed `consistency-audit`'s `HP-METHOD-DRIFT` /
`HP-THEOREM-SCOPE-DRIFT`, `baseline-comparison-audit`, etc.). Make **one** cross-model
call to *add* such span-anchored candidate claims. This is **extraction help, not a
review**: the model proposes candidate *claims* (verbatim spans); the executor's
deterministic substring gate (Step 4) decides what is admitted — nothing here is a
finding or a verdict (`references/reviewer-independence.md`).

Set up the trace run dir and list the exact source paths to hand the reviewer:

```bash
source "<PAPER_DIR>/.aris/evidence-ledger/run.env"
DATE=$(date -u +%Y-%m-%d); TB="$PAPER_DIR/.aris/traces/evidence-ledger"; mkdir -p "$TB"
NN=$(printf "%02d" $(( $(find "$TB" -maxdepth 1 -type d -name "${DATE}_run*" 2>/dev/null | wc -l) + 1 )))
RUNDIR="$TB/${DATE}_run${NN}"; mkdir -p "$RUNDIR"
echo "RUNDIR=\"$RUNDIR\"" >> "$PAPER_DIR/.aris/evidence-ledger/run.env"
echo "RUNDIR=$RUNDIR"
python3 -c 'import json,sys;[print(s["path"]) for s in json.load(open(sys.argv[1]))["source_files"]]' "$PAPER_DIR/claims.json"
```

Call the reviewer with a **fresh `mcp__codex__codex` thread** (never `codex-reply`),
`cwd` = `PAPER_DIR`. Paste the source paths and the existing ledger's
`claim_id + text_span` list into the prompt:

```text
mcp__codex__codex:
  model: gpt-5.5
  config: {"model_reasoning_effort": "xhigh"}
  sandbox: read-only
  cwd: <PAPER_DIR>
  prompt: |
    You are an ADDITIVE claim extractor for an evidence ledger. You are NOT a
    reviewer and NOT a judge: do not assess correctness, do not propose findings, do
    not assign severity or any verdict. Your ONLY job is to surface SEMANTIC claims a
    regex pass misses, each anchored to a VERBATIM span of a real source file.

    Source files (use these EXACT path strings in location.file):
    [list the paths from claims.json -> source_files[].path]

    The deterministic ledger already extracted these (do NOT duplicate them):
    [paste the claim_id + text_span list from claims.json]

    ADD claims ONLY of these types (numbers and table cells are already covered by the
    deterministic layer — do NOT emit `number` or `table_cell`):
      - method      : the sentence(s) that DEFINE the proposed method / its key
                      conditions (e.g. "no test-time labels", backbone, training data).
      - scope       : an explicit scope/generality/limitation sentence the regex missed.
      - baseline    : the sentence or list naming the baselines compared against.
      - comparison  : a sentence ASSERTING a comparison ("our method outperforms X") —
                      the framing, not the numbers.
      - citation    : a sentence whose citation is load-bearing for a specific claim.
      - caption     : a table/figure caption the extractor missed.
      - artifact_ref: a reference to a named result file / table / appendix item.

    HARD RULES (a violation gets your item silently dropped by the merger):
      - text_span MUST be copied CHARACTER-FOR-CHARACTER from the named file
        (including LaTeX markup like \cite{...}, \%). If unsure it is verbatim, OMIT it.
      - NEVER introduce, alter, or "tidy" a number. Do NOT emit a `value` field.
      - For a theorem, the span MUST include the stated assumptions, not just the claim.
      - location.file MUST be one of the source paths above.

    Output ONLY a strict JSON array (no prose, no markdown fence) of objects:
      {"type":"...","text_span":"<verbatim>",
       "location":{"file":"<one of the listed paths>","line":<int optional>,
                   "section":"abstract|method|experiments|appendix|..."}}
    Output [] if you find nothing new.
```

Then, using the **Write** tool: save the reviewer's full response verbatim to
`"$RUNDIR/codex_raw.md"` (forensic; never silently dropped) and the parsed JSON array
to `"$RUNDIR/enrichment_candidates.json"` (strip any code fence; if the reviewer
returned `[]`, write `[]`).

**Failure handling (non-blocking).** If the Codex MCP hangs/stalls → re-invoke the
**same** prompt as a fresh thread (still `mcp__codex__codex`, never `codex-reply`). If
it fails twice, returns non-JSON, or the MCP is unavailable → **skip enrichment**,
write `[]` to `enrichment_candidates.json`, note the skip in the trace, and ship the
deterministic ledger. Enrichment is strictly additive and optional.

## Step 4 — Validate + merge enrichment (the anti-hallucination gate)

The executor validates **every** candidate before it enters the ledger — the same
"no span → no claim" discipline the adjudicator applies to findings. This fails open
(a missing/invalid candidates file leaves the deterministic ledger untouched).

```bash
source "<PAPER_DIR>/.aris/evidence-ledger/run.env"
python3 - "$PAPER_DIR/claims.json" "$RUNDIR/enrichment_candidates.json" "$RUNDIR/enrichment_rejects.json" <<'PY'
import json, re, sys, pathlib
ledger_p, cand_p, rej_p = sys.argv[1], sys.argv[2], sys.argv[3]
ledger = json.load(open(ledger_p, encoding="utf-8"))
src = {s["path"]: s for s in ledger["source_files"]}     # source_files[].sha256 = the text-hash anchor
norm = lambda t: re.sub(r"\s+", " ", t).strip()          # extractor collapses newlines to spaces; match likewise
srctext = {p: norm(pathlib.Path(p).read_text(encoding="utf-8", errors="replace")) for p in src}
ALLOWED = {"method", "scope", "baseline", "comparison", "citation", "caption", "artifact_ref"}  # never number/table_cell
try:
    cands = json.load(open(cand_p, encoding="utf-8")); cands = cands if isinstance(cands, list) else []
except (OSError, json.JSONDecodeError):
    cands = []                                           # fail open: no enrichment admitted
kept, rejected = [], []
for c in cands:
    f = (c.get("location") or {}).get("file"); span = c.get("text_span", ""); t = c.get("type")
    if t not in ALLOWED:                          rejected.append({"reason":"bad_type","candidate":c}); continue
    if f not in srctext:                          rejected.append({"reason":"file_not_in_ledger","candidate":c}); continue
    if not span or norm(span) not in srctext[f]:  rejected.append({"reason":"span_not_verbatim","candidate":c}); continue
    c.pop("value", None); c.pop("claim_id", None)        # never trust a model number; we re-id below
    c["evidence_anchor"] = src[f]["sha256"]              # anchor to the same hash deterministic claims use
    c["extractor"] = "manual"; c["confidence"] = "medium"
    kept.append(c)
merged = ledger["claims"] + kept                         # deterministic claims keep their order/ids; enrichment appended
for i, c in enumerate(merged, 1): c["claim_id"] = f"C{i:03d}"
ledger["claims"] = merged
json.dump(ledger, open(ledger_p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
json.dump(rejected, open(rej_p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"enrichment: kept {len(kept)}, rejected {len(rejected)} -> {ledger_p}")
PY
```

The gate enforces, all mandatory:

1. **Type allow-list** — only the seven semantic types; `number`/`table_cell` are rejected (the deterministic layer owns numbers).
2. **Span is verbatim** — `text_span` must be a substring of the source after whitespace-normalization (the extractor itself joins lines with single spaces, so normalize both sides). Paraphrase → reject.
3. **No invented numbers** — any `value` field is stripped; a number can only enter the ledger via Step 2.
4. **Real source** — `location.file` must be one of the ledger's `source_files`.

Re-id is append-only: deterministic claims keep their `C001…` ids; admitted
enrichment claims continue the sequence, tagged `extractor: "manual"`,
`confidence: "medium"`. The merge **never** removes or edits a deterministic claim.
`enrichment_rejects.json` lands in the trace (the `REJECT` count is expected — it is
the anchoring guard working).

**Failure handling.** Every candidate rejected (or `[]`) → acceptable; the ledger is
just the deterministic backbone. If a later self-check fails (non-contiguous ids, a
value crept in), re-run the merger from the deterministic ledger; never hand-patch
`claims.json`. If `claims.json` was already overwritten, rebuild from Step 2 then
re-merge.

## Step 5 — Self-check the ledger (it is the spine, so verify it)

Confirm `claims.json` is well-formed, the level still matches the manifest, ids are
contiguous, and the sources are byte-for-byte untouched (detect-only proof). The
re-hash replicates `build_claim_ledger.py`'s **text** hash (decode→re-encode UTF-8),
not a raw-byte hash, so it matches `source_files[].sha256`.

```bash
source "<PAPER_DIR>/.aris/evidence-ledger/run.env"
python3 - "$PAPER_DIR/claims.json" "$PAPER_DIR/artifact_manifest.json" <<'PY'
import json, sys, hashlib, os
L = json.load(open(sys.argv[1], encoding="utf-8")); M = json.load(open(sys.argv[2], encoding="utf-8"))
assert {"ledger_version","paper_id","observability_level","source_files","claims"} <= L.keys(), "missing top-level field"
assert L["observability_level"] == M["observability_level"], "ledger level != manifest level"
ids = [c["claim_id"] for c in L["claims"]]
assert ids == [f"C{i:03d}" for i in range(1, len(ids)+1)], "claim_ids not unique/sequential"
for c in L["claims"]:
    assert {"claim_id","type","text_span","location"} <= c.keys(), f"{c.get('claim_id')} missing field"
    assert c["location"].get("file"), f"{c['claim_id']} has no location.file"
def text_sha(p):  # mirror build_claim_ledger.sha256_text
    return hashlib.sha256(open(p, encoding="utf-8", errors="replace").read().encode("utf-8")).hexdigest()
for s in L["source_files"]:
    if os.path.exists(s["path"]):
        assert text_sha(s["path"]) == s["sha256"], f"source changed since extraction: {s['path']}"
by = {t: sum(1 for c in L["claims"] if c["type"]==t) for t in sorted({c["type"] for c in L["claims"]})}
print(f"== Evidence Ledger built ==  L{L['observability_level']}  {len(ids)} claims {by}  "
      f"({sum(1 for c in L['claims'] if c.get('extractor')=='manual')} from enrichment)")
PY
echo "Outputs: $PAPER_DIR/artifact_manifest.json  +  $PAPER_DIR/claims.json"
```

A non-empty, conformant `claims.json` is the green light for the auditor fan-out. Do
**not** run any auditor, numeric check, or the adjudicator from here. **Failure
handling.** A source-hash mismatch means a file changed mid-run — rebuild from Step 1
against the current files so the anchors are honest.

## Output contract

Written into the paper directory (the paths every downstream auditor and the
orchestrator expect):

- **`artifact_manifest.json`** — `schemas/artifact_manifest.schema.json`. Records the observable inputs (hashed) and the derived **observability level** that caps all downstream severity (`repo.rerunnable` is always `false` in v0).
- **`claims.json`** — `schemas/claims.schema.json`. **The evidence ledger:** span-anchored, hashed, deterministic backbone (+ any validated enrichment claims tagged `extractor: manual, confidence: medium`). The *only* structure auditors may reason over; `source_files[]` carry content hashes so every finding is reproducible against an immutable input.
- **`.aris/traces/evidence-ledger/<date>_run<NN>/`** — **only when Step 3 ran**: `codex_raw.md` (raw reviewer reply), `enrichment_candidates.json` (parsed array), `enrichment_rejects.json` (the anchoring guard's rejects).

Explicitly **NOT** emitted: any `<skill>.findings.json`, any `overall_verdict`, any
`pattern_id` tagging, any accusation. Those belong to the auditors and
`tools/adjudicate_findings.py`.

## What consumes the ledger downstream (integration)

You normally reach these via `/anti-autoresearch`; the exact contracts are:

```bash
# consistency-audit's deterministic arithmetic layer (HP-DELTA-ERROR, HP-NUM-INFLATE):
python3 "$ROOT/tools/check_numeric_consistency.py" --ledger "$PAPER_DIR/claims.json" \
    --out consistency-audit.deterministic.findings.json

# presentation-signals' surface checks (HP-DUP-TABLE via table_cell claims, etc.) —
# AUXILIARY, capped at minor by the adjudicator, default false_positive_risk:high,
# NOT an AI-text classifier, never a standalone verdict:
python3 "$ROOT/tools/check_presentation.py" --ledger "$PAPER_DIR/claims.json" \
    --out presentation-signals.deterministic.findings.json

# the deterministic adjudicator — --ledger is REQUIRED:
python3 "$ROOT/tools/adjudicate_findings.py" --findings *.findings.json \
    --ledger "$PAPER_DIR/claims.json" --paper-id "$PAPER_ID" \
    --observability-level "$L" --taxonomy-version 0.2 --out report.json --md REPORT.md
```

`adjudicate_findings.py` **requires** `--ledger`: it re-verifies that each
above-`info` finding quotes a verbatim ledger span; without it every such finding
**fails closed to `info`** — a missing or wrong ledger silently neuters the whole
audit. The ledger you build here is load-bearing for every verdict. **This skill does
not run any of these** — stop at a validated ledger.

## Key rules

- **Deterministic first.** The numeric/citation/table backbone comes from code, not a model — that reproducibility is the whole credibility argument. Same source bytes → byte-identical ledger (omit `--generated-at`).
- **Spans are real.** Every `text_span` is a verbatim substring of a hashed source. The executor rejects any enrichment span it cannot match (Step 4); the adjudicator rejects unanchored findings again downstream.
- **Enrichment adds, never invents.** Only the seven semantic types; never a number, never an altered value, never a removed/edited deterministic claim. The numeric/citation backbone stays 100% deterministic.
- **Never over-state the level.** `L` is derived from the artifacts present and caps all downstream severity. A PDF-only run is L0 — full stop. Never set `repo.rerunnable: true` (no L3 in v0).
- **No judgment here.** The ledger states *what the paper says*, never *whether it is right*. `EMITS_FINDINGS = false`, `EMITS_VERDICT = false`; no `pattern_id` tagging.
- **Cross-model, fresh thread, no leakage.** The one enrichment call is `gpt-5.5` @ `xhigh`, `read-only`, a *different* family from the executor, a new `mcp__codex__codex` thread (never `codex-reply`), told only source paths + the ledger.
- **Detect-only.** Never edit the audited paper; only read sources and write this skill's own outputs (Step 5's hash check proves it).

## When NOT to use (and limits)

- **Not an auditor.** No PASS/FAIL, no findings. For a verdict, run the auditor skills + `tools/adjudicate_findings.py` (or `/anti-autoresearch`).
- **Don't skip it before an audit.** Every auditor reads `claims.json`; running one without the ledger means it re-reads the PDF and hallucinates structure — exactly what this repo exists to prevent.
- **Don't loop/schedule it.** A deterministic transform, not a poller and not a verdict; re-run only when sources change.
- **Recall, not certification.** The extractor is best-effort regex: high recall on the *checkable surface*, not a guarantee every claim was found. Low-confidence (PDF/OCR) numbers are tagged `confidence: low` for the human and adjudicator to weight; the ledger is a foundation, not a proof of completeness.

## Review tracing

Step 3 (the only model call) saves its trace under
`.aris/traces/evidence-ledger/<date>_run<NN>/` following the forensic policy
(Policy C — never silently dropped), mirroring ARIS review-tracing and
`references/integrity-forensics-contract.md` §"Output contract per skill": the raw
`mcp__codex__codex` reply (`codex_raw.md`), the parsed candidates
(`enrichment_candidates.json`), and the executor's keep/drop decisions
(`enrichment_rejects.json`) — so a later reader can see exactly which enrichment spans
were admitted and why. Fresh thread per run; full reply preserved. When `ENRICH =
false` or enrichment is skipped (reviewer unavailable), note the skip inline and ship
the deterministic ledger — no trace dir is required. Steps 0–2 and 4–5 are
deterministic and need no trace beyond their own stdout and the hashed `source_files`.
