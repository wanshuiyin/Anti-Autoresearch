#!/usr/bin/env python3
"""
select_primary_pdf.py — deterministic "which PDF is the paper" selection.

One ranking, consumed everywhere a pipeline needs THE paper PDF (evidence-ledger
Step 0 text extraction; build_manifest primary-first artifact ordering). Scan scope
is root + one subdirectory level, matching build_manifest.detect(). Pure stdlib.

Rule (issue #11): a PDF that looks like an asset — it lives in an asset directory
(figures/, images/, ...) OR carries a figure-like basename (fig1.pdf, supplement.pdf)
— and has no paper-like basename is never selected; on a figures-only directory the
honest answer is "no primary PDF", not "extract text from a figure". Silent-wrong
is worse than no-signal in an integrity tool. Among non-assets, a paper-like
basename anywhere beats an unnamed root PDF; root beats subdirs on ties.

CLI: python3 tools/select_primary_pdf.py DIR
     prints the primary PDF path (absolute) and exits 0; exits 1 with no output
     when there is no confident candidate.
"""
import glob
import os
import re
import sys

ASSET_DIRS = {"figures", "figs", "fig", "assets", "images", "img", "plots",
              "graphics", "media", "supplement", "supplementary", "supp", "appendix"}
POSITIVE_NAME = re.compile(
    r"(?i)^(paper|main|manuscript|submission|article|camera[-_]?ready|preprint|final)"
    r"([-_.].*)?$")
FIGURE_NAME = re.compile(
    r"(?i)^(fig(ure)?s?\d*|plot\d*|supp(lement(ary)?)?|appendix|poster|slides?)"
    r"([-_.].*)?$")


def _is_positive(relpath):
    stem = os.path.splitext(os.path.basename(relpath))[0]
    return bool(POSITIVE_NAME.match(stem))


def _is_assetlike(relpath):
    if any(seg.lower() in ASSET_DIRS for seg in relpath.split(os.sep)[:-1]):
        return True
    stem = os.path.splitext(os.path.basename(relpath))[0]
    return bool(FIGURE_NAME.match(stem))


def rank_pdfs(paths, base):
    """Deterministic primary-first ordering of PDF paths (relative or absolute).
    Asset-looking PDFs (asset dir or figure-like basename) demoted; paper-like
    basenames promoted even from a subdir; root beats subdirs on ties."""
    def key(p):
        rel = os.path.relpath(p, base)
        return (_is_assetlike(rel),             # non-asset beats asset (dir or name)
                not _is_positive(rel),          # paper-like name beats other names
                rel.count(os.sep) > 0,          # root beats subdirs on ties
                rel.count(os.sep), rel)         # shallower, then lexicographic
    return sorted(paths, key=key)


def select_primary(paths, base):
    """Best candidate, or None when no candidate is confident (every PDF is
    asset-looking without a paper-like name)."""
    ranked = rank_pdfs(paths, base)
    for p in ranked:
        rel = os.path.relpath(p, base)
        if not _is_assetlike(rel) or _is_positive(rel):
            return p
    return None


def scan(d):
    """Root + one subdirectory level, same scope as build_manifest.detect()
    (glob without recursive=True: ** matches one level; dot-dirs are skipped)."""
    return sorted(glob.glob(os.path.join(d, "*.pdf")) +
                  glob.glob(os.path.join(d, "**", "*.pdf")))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1 or not os.path.isdir(argv[0]):
        print("usage: select_primary_pdf.py DIR", file=sys.stderr)
        return 2
    d = argv[0]
    primary = select_primary(scan(d), d)
    if primary is None:
        return 1
    print(os.path.abspath(primary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
