#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: previewer.py
# Purpose: Simulate and visualize planned file actions
#
# Author: Tim Canady
# Created: 2025-09-28
#
# Version: 0.4.3
# Last Modified: 2025-11-06 by Tim Canady
#
# Revision History:
# - 0.4.3 (2025-11-06): Tree preview logic and log output added — Tim Canady
###################################################################

from pathlib import Path
from typing import List, Tuple, Union
from collections import defaultdict
import json

def preview_plan(plan: List[Tuple[Path, Path]], log_path: Union[Path, None] = None, fmt: str = "txt") -> None:
    if fmt == "json":
        log = [{"from": str(src), "to": str(dst)} for src, dst in plan]
        output = json.dumps(log, indent=2)
    else:
        output = "\n".join([f"{src} -> {dst}" for src, dst in plan])

    print("\nProposed Directory Structure\n")
    print_tree_structure(plan)

    if log_path:
        log_path.write_text(output)
        print(f"📝 Preview written to {log_path}")

def print_tree_structure(plan: List[Tuple[Path, Path]]) -> None:
    tree = defaultdict(set)
    for _, target_path in plan:
        parts = target_path.parts
        for i in range(1, len(parts)):
            parent = Path(*parts[:i])
            child = parts[i]
            tree[parent].add(child)

    def _print_subtree(base: Path, prefix: str = ""):
        children = sorted(tree.get(base, []))
        for idx, name in enumerate(children):
            is_last = idx == len(children) - 1
            connector = "└── " if is_last else "├── "
            print(f"{prefix}{connector}{name}")
            next_base = base / name
            _print_subtree(next_base, prefix + ("    " if is_last else "│   "))

    _print_subtree(Path())

