#!/usr/bin/env python3
"""
build_manifest.py — deterministic artifact inventory + observability-level derivation.

Scans a paper directory, records which artifacts are present (with hashes), and
derives the observability level by the fixed rule in references/observability-
levels.md. This is what makes "tools/ derives the level" true rather than a manual
step. Pure standard library.

Rule:
  repo + results present       -> L2
  latex present, no results     -> L1
  pdf only (or text only)       -> L0
"""
import argparse
import glob
import hashlib
import json
import os
import sys


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def detect(d):
    def has(pat):
        return sorted(glob.glob(os.path.join(d, pat)))
    tex = has("*.tex") + has("**/*.tex")
    pdf = has("*.pdf")
    bib = has("*.bib") + has("**/*.bib")
    # a repo = a code dir or loose source files
    repo_dirs = [p for p in ("code", "src", "repo") if os.path.isdir(os.path.join(d, p))]
    code_files = has("**/*.py") or has("**/*.ipynb")
    repo = bool(repo_dirs or code_files)
    # results = result dirs with data files
    res_dirs = [p for p in ("results", "outputs", "logs") if os.path.isdir(os.path.join(d, p))]
    res_files = []
    for rd in res_dirs:
        res_files += glob.glob(os.path.join(d, rd, "**", "*.json"), recursive=True)
        res_files += glob.glob(os.path.join(d, rd, "**", "*.csv"), recursive=True)
    results = bool(res_files)
    return {"tex": tex, "pdf": pdf, "bib": bib, "repo": repo,
            "repo_dirs": repo_dirs, "results": results, "res_files": res_files}


def derive_level(det, has_pdf_text):
    if det["repo"] and det["results"]:
        return 2
    if det["tex"]:
        return 1
    if det["pdf"] or has_pdf_text:
        return 0
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Inventory artifacts + derive observability level.")
    ap.add_argument("--paper-id", required=True)
    ap.add_argument("--dir", default=".", help="paper directory to scan")
    ap.add_argument("--pdf-text", default="", help="path to extracted PDF text, if any")
    ap.add_argument("--out", default="artifact_manifest.json")
    args = ap.parse_args(argv)

    d = args.dir
    det = detect(d)
    level = derive_level(det, bool(args.pdf_text))

    artifacts = []
    for kind, paths in (("latex", det["tex"]), ("pdf", det["pdf"]), ("bib", det["bib"])):
        for p in paths:
            artifacts.append({"kind": kind, "path": p, "sha256": sha256_file(p), "present": True})
    for kind, present in (("repo", det["repo"]), ("results", det["results"])):
        artifacts.append({"kind": kind,
                          "path": ",".join(det["repo_dirs"]) if kind == "repo" else None,
                          "present": present})

    manifest = {
        "paper_id": args.paper_id,
        "observability_level": level,
        "artifacts": artifacts,
        "repo": {"present": det["repo"], "rerunnable": False},  # v0 never claims rerunnable
        "notes": f"derived L{level} by rule (repo={det['repo']}, results={det['results']}, "
                 f"latex={bool(det['tex'])}, pdf={bool(det['pdf'])})",
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
    print(f"manifest: observability L{level} "
          f"(latex={len(det['tex'])} pdf={len(det['pdf'])} bib={len(det['bib'])} "
          f"repo={det['repo']} results={det['results']}) -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
