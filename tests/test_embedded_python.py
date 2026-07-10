#!/usr/bin/env python3
"""
Embedded-python syntax lint for SKILL.md validator blocks.

SKILL.md files carry executable `python3 - <<'PY' ... PY` here-docs (the span/schema
validators every auditor runs). A SyntaxError there ships a broken contract that only
explodes at audit time — exactly the bug class a reviewer caught when a reviewer-stamp
edit landed INSIDE a dict literal. This test extracts every PY here-doc and:

1. ast-parses it (pure syntax; undefined runtime names are fine), and
2. for blocks that stamp reviewer provenance, requires RESOLVED_MODEL to be ASSIGNED
   before its first use.

Run: python3 tests/test_embedded_python.py   (also pytest-compatible)
"""
import ast
import glob
import os
import re
import sys

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
HEREDOC_RE = re.compile(r"<<'PY'\n(.*?)\nPY\b", re.S)


def _blocks():
    paths = glob.glob(os.path.join(REPO, "skills", "**", "SKILL.md"), recursive=True)
    paths += glob.glob(os.path.join(REPO, "workflows", "**", "SKILL.md"), recursive=True)
    for path in sorted(paths):
        text = open(path, encoding="utf-8").read()
        for i, m in enumerate(HEREDOC_RE.finditer(text), 1):
            yield os.path.relpath(path, REPO), i, m.group(1)


def check_repo():
    problems = []
    for rel, i, block in _blocks():
        if "<" in block.split("\n", 1)[0] and "argv" not in block:
            pass  # template-ish first lines are still parsed below; placeholders rare in PY blocks
        try:
            ast.parse(block)
        except SyntaxError as e:
            problems.append(f"{rel} [PY block #{i}]: SyntaxError line {e.lineno}: {e.msg}")
            continue
        if "RESOLVED_MODEL" in block:
            tree = ast.parse(block)
            assign_line, use_line = None, None
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for t in node.targets:
                        for n in ast.walk(t):
                            if isinstance(n, ast.Name) and n.id == "RESOLVED_MODEL":
                                assign_line = min(assign_line or node.lineno, node.lineno)
                elif isinstance(node, ast.Name) and node.id == "RESOLVED_MODEL" \
                        and isinstance(node.ctx, ast.Load):
                    use_line = min(use_line or node.lineno, node.lineno)
            if use_line is not None and (assign_line is None or assign_line > use_line):
                problems.append(f"{rel} [PY block #{i}]: RESOLVED_MODEL used (line {use_line}) "
                                f"before assignment ({assign_line})")
    return problems


def test_all_embedded_python_blocks_parse():
    problems = check_repo()
    assert not problems, "\n".join(problems)


if __name__ == "__main__":
    ps = check_repo()
    n = sum(1 for _ in _blocks())
    if ps:
        print("\n".join(ps))
        sys.exit(1)
    print(f"ok: {n} embedded PY blocks parse; reviewer stamps define-before-use")
