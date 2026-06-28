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
    # a verbatim assistant/pipeline leftover string survives into a caption
    # (cosmetic — it feeds NO number; a leftover feeding a number is HP-PLACEHOLDER-DATA / family D)
    "pipeline_artifact": [
        ("\\caption{Main results on BarBench (accuracy, \\%, mean of 5 seeds).}",
         "\\caption{Main results on BarBench (accuracy, \\%, mean of 5 seeds). "
         "As an AI language model, I cannot independently verify these numbers.}"),
    ],
    # GRIM: 84.6% over 500 items is achievable (k=423); 84.7% is not (k=423.5)
    "grim_impossible": [
        ("FooNet's accuracy is 84.6\\%", "FooNet's accuracy is 84.7\\%"),
    ],
    # GRIMMER/Bhatia-Davis: at mean 98% over 5 seeds the max SD is ~15.7%; 18% is impossible
    "variance_impossible": [
        ("standard\ndeviation of 12.0\\%", "standard\ndeviation of 18.0\\%"),
    ],
    # statcheck: z=1.10 gives two-tailed p~.27, so "p = 0.036" overstates significance
    "stat_inconsistency": [
        ("(z = 2.10, p = 0.036)", "(z = 1.10, p = 0.036)"),
    ],
    # defensive-hedge density: 4 strong "we do not claim / not X but rather Y" constructions
    # injected across Introduction and Method — a *pattern*, not the one legitimate scoping
    # sentence the clean paper already has ("we make no claim of broad generality").
    "defensive_hedge": [
        ("improvement evaluated on one benchmark.",
         "improvement evaluated on one benchmark. We do not claim that this routing module "
         "is optimal. This does not mean that simpler designs cannot work."),
        ("is performed on the training split only.",
         "is performed on the training split only. We are not proposing a fundamentally new "
         "architecture. Our goal is not to maximize raw accuracy, but rather to isolate the "
         "routing effect."),
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
