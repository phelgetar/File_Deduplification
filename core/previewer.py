#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: previewer.py
# Purpose: Preview and simulate directory organization plans
#
# Author: Tim Canady
# Created: 2025-09-28
#
# Version: 0.4.3
# Last Modified: 2025-11-06 by Tim Canady
#
# Revision History:
# - 0.4.3 (2025-11-06): Fix TypeError when unpacking plan elements — Tim Canady
###################################################################

from pathlib import Path
from typing import List, Tuple, Union

def print_tree_structure(plan: List[Union[Tuple[Path, Path], Path]]) -> None:
    from collections import defaultdict

    tree = defaultdict(set)

    for item in plan:
        if isinstance(item, tuple):
            _, target_path = item
        else:
            target_path = item

        parts = target_path.parts
        for i in range(1, len(parts)):
            tree[parts[i - 1]].add(parts[i])

    def print_branch(branch: str, depth: int = 0):
        print("  " * depth + f"- {branch}")
        for child in sorted(tree.get(branch, [])):
            print_branch(child, depth + 1)

    roots = set(k for k in tree if k not in {v for values in tree.values() for v in values})
    for root in sorted(roots):
        print_branch(root)
