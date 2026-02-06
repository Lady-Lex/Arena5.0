#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from collections import Counter
from io import StringIO
from pxr import Usd

def build_tree_lines(stage: Usd.Stage, max_depth: int = 6):
    pseudo = stage.GetPseudoRoot()
    lines = []
    lines.append(f"Stage root layer: {stage.GetRootLayer().identifier}")
    lines.append("Prim Tree (limited depth):")

    def _walk(prim, depth: int):
        if depth > max_depth:
            return
        children = prim.GetChildren()
        for i, c in enumerate(children):
            is_last = (i == len(children) - 1)
            branch = "└── " if is_last else "├── "
            indent = "    " * depth
            name = c.GetName()
            tname = c.GetTypeName() or "<?>"
            lines.append(f"{indent}{branch}{name}   [{tname}]")
            _walk(c, depth + 1)

    _walk(pseudo, 0)
    return lines

def top_level_groups(stage: Usd.Stage):
    pseudo = stage.GetPseudoRoot()
    names = [c.GetName() for c in pseudo.GetChildren()]
    types = [c.GetTypeName() or "<?>" for c in pseudo.GetChildren()]
    return names, types

def count_by_prefix(stage: Usd.Stage, depth: int = 2, topk: int = 50):
    cnt = Counter()
    for prim in stage.Traverse():
        if not prim.IsActive():
            continue
        path = str(prim.GetPath())
        parts = [p for p in path.split("/") if p]
        if len(parts) >= depth:
            prefix = "/" + "/".join(parts[:depth])
        elif len(parts) == 1:
            prefix = "/" + parts[0]
        else:
            prefix = "/"
        cnt[prefix] += 1
    return cnt.most_common(topk)

def parse_args(argv):
    if len(argv) < 2:
        print("Usage: python inspect_usd.py /path/to/scene.usd [max_depth] [--out output.txt]")
        sys.exit(1)

    usd_path = argv[1]
    max_depth = 6
    out_path = None

    # positional max_depth
    if len(argv) >= 3 and not argv[2].startswith("--"):
        max_depth = int(argv[2])

    # optional --out
    if "--out" in argv:
        i = argv.index("--out")
        out_path = argv[i + 1]

    # default output: same dir as usd file
    if out_path is None:
        out_path = os.path.join(os.path.dirname(os.path.abspath(usd_path)), "prim_tree.txt")

    return usd_path, max_depth, out_path

def main():
    usd_path, max_depth, out_path = parse_args(sys.argv)

    stage = Usd.Stage.Open(usd_path)
    if not stage:
        raise RuntimeError(f"Failed to open USD: {usd_path}")

    buf = StringIO()

    # 1) Top-level
    names, types = top_level_groups(stage)
    buf.write("Top-level prims under pseudo-root:\n")
    for n, t in zip(names, types):
        buf.write(f"  - {n:30s} [{t}]\n")
    buf.write("\n")

    # 2) Tree
    tree_lines = build_tree_lines(stage, max_depth=max_depth)
    buf.write("\n".join(tree_lines))
    buf.write("\n\n")

    # 3) Prefix counts
    buf.write("Prim counts by 2-level prefix (rough grouping indicator):\n")
    for k, v in count_by_prefix(stage, depth=2, topk=50):
        buf.write(f"  {k:40s} {v}\n")
    buf.write("\n")

    # Write file
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(buf.getvalue())

    # Also print to stdout
    print(buf.getvalue(), end="")
    print(f"Wrote full report to: {out_path}")

if __name__ == "__main__":
    main()
