#!/usr/bin/env python3
#
###################################################################
# Project: File Deduplication
# File: previewer.py
# Purpose: Preview planned file movements and visualize folder tree.
#
# Description:
# Displays the planned folder organization and file operations before applying.
# Also provides an ASCII tree-like view of the target folder structure.
#
# Author: Tim Canady
# Created: 2025-09-28
#
# Version: 0.2.0
# Last Modified: 2025-11-04 by Tim Canady
#
# Revision History:
# - 0.2.0 (2025-11-04): Added print_tree_structure for preview — Tim Canady
# - 0.1.0 (2025-11-04): Initial preview logic — Tim Canady
###################################################################

from collections import defaultdict
from pathlib import Path
from typing import List, Tuple

from models.file_info import FileInfo


Plan = List[Tuple[FileInfo, Path]]

def preview_plan(plan: Plan) -> None:
    print("\nPlanned File Operations:")
    for file_info, target_path in plan:
        print(f"  📁 {file_info.path} → {target_path}")

def print_tree_structure(plan: Plan) -> None:
    tree = defaultdict(list)
    for _, target_path in plan:
        parts = target_path.relative_to(target_path.anchor).parts
        for i in range(1, len(parts)+1):
            parent = Path(*parts[:i-1]) if i > 1 else Path()
            tree[parent].append(parts[i-1])

    def print_branch(base: Path, prefix=""):
        children = sorted(set(tree.get(base, [])))
        for i, name in enumerate(children):
            is_last = (i == len(children) - 1)
            connector = "└── " if is_last else "├── "
            print(f"{prefix}{connector}{name}")
            next_base = base / name
            new_prefix = prefix + ("    " if is_last else "│   ")
            print_branch(next_base, new_prefix)

    print_branch(Path())