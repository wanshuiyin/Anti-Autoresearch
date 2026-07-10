#!/usr/bin/env python3
"""
attach_refutation.py — the ONLY sanctioned way to write a refutation back into a
findings file (workflow Step 3.5).

Why a tool instead of a prose rule: "the executor writes it back mechanically and
never edits the finding itself" is unenforceable as an instruction. This tool makes
it structural:

- the target finding is located by finding_id (must be unique in the file);
- counter-evidence spans are verified against the ledger (same whitespace-normalized
  `span in claim` rule as findings) — entries that fail are DROPPED, loudly;
- every field of the finding except `refutation` is digest-compared before/after —
  any drift aborts the write;
- a pre-existing refutation is refused (one attempt per finding; --force-overwrite
  for the explicit retry path);
- the reviewer stamp comes from ARIS_RESOLVED_MODEL / ARIS_RESOLVED_REASONING
  (fail LOUD when unset — reviewer-independence.md), plus --thread-id;
- the file is replaced atomically (same-dir tmp + rename).

Usage:
  ARIS_RESOLVED_MODEL=... ARIS_RESOLVED_REASONING=... \\
  python3 tools/attach_refutation.py \\
      --findings-file paper/consistency-audit.findings.json \\
      --finding-id F3 --ledger paper/claims.json \\
      --status completed --refuted true --reason "same value under rounding" \\
      --counter-evidence '[{"claim_id": "C012", "span": "..."}]' \\
      --thread-id 019f...
  (for a dead refuter: --status unavailable, no payload needed)
"""
import argparse
import hashlib
import json
import os
import re
import sys
import tempfile


def _norm_ws(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def _digest_without_refutation(finding):
    clone = {k: v for k, v in finding.items() if k != "refutation"}
    return hashlib.sha256(
        json.dumps(clone, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Atomically attach a refutation result to one finding.")
    ap.add_argument("--findings-file", required=True)
    ap.add_argument("--finding-id", required=True)
    ap.add_argument("--ledger", required=True, help="claims.json — counter-spans are verified against it")
    ap.add_argument("--status", required=True, choices=["completed", "unavailable", "malformed"])
    ap.add_argument("--refuted", choices=["true", "false"], help="required when --status completed")
    ap.add_argument("--reason", default="")
    ap.add_argument("--counter-evidence", default="[]",
                    help='JSON array of {"claim_id", "span"} — unanchored entries are dropped')
    ap.add_argument("--thread-id", default="")
    ap.add_argument("--force-overwrite", action="store_true",
                    help="replace an existing refutation (explicit retry only)")
    args = ap.parse_args(argv)

    if args.status == "completed" and args.refuted is None:
        ap.error("--refuted true|false is required when --status completed")

    try:
        model = os.environ["ARIS_RESOLVED_MODEL"]
        reasoning = os.environ["ARIS_RESOLVED_REASONING"]
    except KeyError as e:
        print(f"FATAL: {e.args[0]} unset — export the pair that ACTUALLY ran "
              "(reviewer-independence.md); refusing to stamp a default.", file=sys.stderr)
        return 2

    with open(args.findings_file, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    items = data.get("findings", data) if isinstance(data, dict) else data
    if not isinstance(items, list):
        print(f"FATAL: {args.findings_file} has no findings array", file=sys.stderr)
        return 2

    matches = [f for f in items if isinstance(f, dict) and f.get("finding_id") == args.finding_id]
    if len(matches) != 1:
        print(f"FATAL: finding_id {args.finding_id!r} matches {len(matches)} findings "
              f"in {args.findings_file} — need exactly 1", file=sys.stderr)
        return 2
    finding = matches[0]
    if "refutation" in finding and not args.force_overwrite:
        print("FATAL: finding already carries a refutation (one attempt per finding); "
              "use --force-overwrite only for an explicit retry.", file=sys.stderr)
        return 2

    with open(args.ledger, "r", encoding="utf-8") as fh:
        ledger = json.load(fh)
    ledger_map = {c.get("claim_id"): c.get("text_span", "")
                  for c in ledger.get("claims", []) if c.get("claim_id")}

    kept, dropped = [], 0
    for ev in json.loads(args.counter_evidence):
        cid, span = ev.get("claim_id"), _norm_ws(ev.get("span"))
        base = ledger_map.get(cid)
        if base is not None and span and span in _norm_ws(base):
            kept.append({"claim_id": cid, "span": ev.get("span")})
        else:
            dropped += 1
    if dropped:
        print(f"note: dropped {dropped} counter-evidence entr(ies) that failed the "
              "ledger anchor check (an opinion is not a counter-anchor)", file=sys.stderr)

    before = _digest_without_refutation(finding)
    refutation = {"attempt_status": args.status}
    if args.status == "completed":
        refutation.update({
            "refuted": args.refuted == "true",
            "reason": args.reason,
            "counter_evidence": kept,
            "reviewer": {"model": model, "reasoning": reasoning,
                         "thread_id": args.thread_id, "deterministic": False},
        })
    finding["refutation"] = refutation
    if _digest_without_refutation(finding) != before:
        print("FATAL: finding mutated beyond the refutation field — aborting write",
              file=sys.stderr)
        return 2

    d = os.path.dirname(os.path.abspath(args.findings_file)) or "."
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        os.replace(tmp, args.findings_file)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    print(f"refutation attached: {args.finding_id} status={args.status}"
          + (f" refuted={args.refuted} anchors={len(kept)}" if args.status == "completed" else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
