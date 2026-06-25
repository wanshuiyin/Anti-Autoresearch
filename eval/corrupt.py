#!/usr/bin/env python3
"""
corrupt.py — inject a KNOWN integrity defect into a clean fixture.

Each corruption is a list of (find, replace) edits. Every `find` MUST be present
in the source (asserted) so a corruption can never silently no-op — that would
make the eval pass for the wrong reason. The eval harness asserts the matching
pattern is then caught by the deterministic checkers.
"""
import argparse
import sys

CORRUPTIONS = {
    # stated relative improvement no longer matches 73.1 -> 78.0 (= 6.7%)
    "delta_inflate": [
        ("a 6.7\\% relative improvement", "a 16.7\\% relative improvement"),
    ],
    # headline accuracy number no longer appears in any results table
    "headline_inflate": [
        ("FooNet reaches\n78.0\\% accuracy", "FooNet reaches\n85.3\\% accuracy"),
    ],
    # a second table with identical numeric content (padding / un-updated copy)
    "dup_table": [
        ("\\section{Conclusion}",
         "\\begin{table}[t]\n"
         "\\caption{Additional results on BarBench (accuracy, \\%).}\n"
         "\\begin{tabular}{lc}\n\\toprule\nMethod & Accuracy \\\\\n\\midrule\n"
         "Baseline \\cite{smith2024bar} & 73.1 \\\\\nFooNet (ours) & 78.0 \\\\\n"
         "\\bottomrule\n\\end{tabular}\n\\end{table}\n\n\\section{Conclusion}"),
    ],
}


def apply_corruption(text, name):
    if name not in CORRUPTIONS:
        raise SystemExit(f"unknown corruption '{name}'; known: {sorted(CORRUPTIONS)}")
    for find, repl in CORRUPTIONS[name]:
        if find not in text:
            raise SystemExit(
                f"corruption '{name}': target not found in source — fixture drifted:\n  {find!r}")
        text = text.replace(find, repl, 1)
    return text


def main(argv=None):
    ap = argparse.ArgumentParser(description="Inject a known defect into a fixture.")
    ap.add_argument("--src", required=True)
    ap.add_argument("--name", required=True, choices=sorted(CORRUPTIONS))
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    with open(args.src, "r", encoding="utf-8") as fh:
        text = fh.read()
    out = apply_corruption(text, args.name)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(out)
    print(f"corrupted [{args.name}] -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
