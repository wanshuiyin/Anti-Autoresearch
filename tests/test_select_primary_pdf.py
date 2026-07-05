#!/usr/bin/env python3
"""
Unit tests for the deterministic primary-PDF selection (issue #11) — these lock in
the honest-none guarantee: a figures-only directory must never yield a "paper PDF",
and the confident pick must not depend on filesystem enumeration order.

Run: python3 tests/test_select_primary_pdf.py   (also pytest-compatible)
"""
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import select_primary_pdf as S  # noqa: E402
import build_manifest as M      # noqa: E402

TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools",
                    "select_primary_pdf.py")


def _mk(d, *relpaths):
    for r in relpaths:
        p = os.path.join(d, r)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as fh:
            fh.write(b"%PDF-1.4 stub\n")
    return [os.path.join(d, r) for r in relpaths]


def test_root_beats_figure_subdir():
    with tempfile.TemporaryDirectory() as d:
        paths = _mk(d, "paper.pdf", os.path.join("figures", "fig1.pdf"))
        assert S.select_primary(paths, d) == os.path.join(d, "paper.pdf")


def test_positive_name_rescues_asset_dir():
    # the issue-#9 layout: the actual paper lives at figures/paper.pdf
    with tempfile.TemporaryDirectory() as d:
        paths = _mk(d, os.path.join("figures", "paper.pdf"),
                    os.path.join("figures", "fig1.pdf"))
        assert S.select_primary(paths, d) == os.path.join(d, "figures", "paper.pdf")


def test_figures_only_yields_none():
    with tempfile.TemporaryDirectory() as d:
        paths = _mk(d, os.path.join("figures", "fig1.pdf"),
                    os.path.join("supplement", "extra.pdf"))
        assert S.select_primary(paths, d) is None


def test_unnamed_root_pdf_is_confident():
    # a lone root PDF with a non-figure name is the paper (pre-fix behavior kept)
    with tempfile.TemporaryDirectory() as d:
        paths = _mk(d, "response-letter.pdf")
        assert S.select_primary(paths, d) == os.path.join(d, "response-letter.pdf")


def test_figure_named_root_pdf_is_not_confident():
    # root location does not launder a figure-like basename (codex review finding):
    # fig1.pdf at root loses to a positive-name subdir PDF, and alone it is no pick
    with tempfile.TemporaryDirectory() as d:
        paths = _mk(d, "fig1.pdf", os.path.join("sections", "main.pdf"))
        assert S.select_primary(paths, d) == os.path.join(d, "sections", "main.pdf")
    with tempfile.TemporaryDirectory() as d:
        paths = _mk(d, "fig1.pdf")
        assert S.select_primary(paths, d) is None


def test_positive_subdir_name_beats_unnamed_root():
    with tempfile.TemporaryDirectory() as d:
        paths = _mk(d, "zz.pdf", os.path.join("sections", "main.pdf"))
        assert S.select_primary(paths, d) == os.path.join(d, "sections", "main.pdf")


def test_rank_is_input_order_independent():
    with tempfile.TemporaryDirectory() as d:
        paths = _mk(d, "zz.pdf", os.path.join("figures", "fig.pdf"),
                    os.path.join("sections", "main.pdf"))
        fwd = S.rank_pdfs(paths, d)
        rev = S.rank_pdfs(list(reversed(paths)), d)
        assert fwd == rev
        # paper-like name beats unnamed root beats asset PDF
        rels = [os.path.relpath(p, d) for p in fwd]
        assert rels == [os.path.join("sections", "main.pdf"), "zz.pdf",
                        os.path.join("figures", "fig.pdf")]


def test_scan_skips_dot_dirs():
    with tempfile.TemporaryDirectory() as d:
        _mk(d, "paper.pdf", os.path.join(".aris", "cache.pdf"))
        rels = [os.path.relpath(p, d) for p in S.scan(d)]
        assert rels == ["paper.pdf"]


def test_cli_prints_primary_and_exit_codes():
    with tempfile.TemporaryDirectory() as d:
        _mk(d, "main.pdf", os.path.join("figures", "fig1.pdf"))
        r = subprocess.run([sys.executable, TOOL, d], capture_output=True, text=True)
        assert r.returncode == 0
        assert r.stdout.strip() == os.path.join(os.path.realpath(d), "main.pdf") or \
            r.stdout.strip() == os.path.join(d, "main.pdf")
    with tempfile.TemporaryDirectory() as d:
        _mk(d, os.path.join("figures", "fig1.pdf"))
        r = subprocess.run([sys.executable, TOOL, d], capture_output=True, text=True)
        assert r.returncode == 1 and r.stdout.strip() == ""


def test_manifest_marks_exactly_one_primary():
    with tempfile.TemporaryDirectory() as d:
        _mk(d, "paper.pdf", os.path.join("figures", "fig1.pdf"))
        out = os.path.join(d, "m.json")
        M.main(["--paper-id", "t", "--dir", d, "--out", out])
        arts = json.load(open(out))["artifacts"]
        pdfs = [a for a in arts if a["kind"] == "pdf"]
        flagged = [a for a in pdfs if a.get("primary")]
        assert len(flagged) == 1
        assert flagged[0]["path"].endswith("paper.pdf")
        assert pdfs[0] is flagged[0]  # primary-first ordering: [0] is the pick


def test_manifest_asset_only_has_no_primary():
    with tempfile.TemporaryDirectory() as d:
        _mk(d, os.path.join("figures", "fig1.pdf"))
        out = os.path.join(d, "m.json")
        M.main(["--paper-id", "t", "--dir", d, "--out", out])
        arts = json.load(open(out))["artifacts"]
        assert not any(a.get("primary") for a in arts)
        # the figure PDF is still inventoried (detection ≠ primary selection)
        assert any(a["kind"] == "pdf" for a in arts)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok {fn.__name__}")
    print(f"{len(fns)} passed")
