#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: previewer.py
# Purpose: Simulate and visualize planned file operations
#
# Description:
# Provides preview functionality for file organization plans.
# Generates tree-structure visualizations and supports both
# JSON and text format logging for dry-run previews.
#
# Author: Tim Canady
# Created: 2025-09-28
#
# Version: 0.4.3
# Last Modified: 2025-11-06 by Tim Canady
#
# Revision History:
# - 0.4.3 (2025-11-06): Tree preview logic and log output added — Tim Canady
# - 0.1.0 (2025-09-28): Initial previewer implementation — Tim Canady
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

def print_tree_structure(plan: List[Tuple]) -> None:
    """
    Print tree structure of planned file organization.

    Args:
        plan: List of tuples (FileInfo, destination_path) or (source_path, destination_path)
    """
    if not plan:
        print("  (No files to organize)")
        return

    # Extract destination paths, handling both (FileInfo, Path) and (Path, Path) tuples
    dest_paths = []
    for item in plan:
        if len(item) == 2:
            # Could be (FileInfo, Path) or (Path, Path)
            dest_path = item[1]
            dest_paths.append(dest_path)
        else:
            continue

    if not dest_paths:
        print("  (No destination paths found)")
        return

    # Find the common base directory
    if len(dest_paths) == 1:
        base_dir = dest_paths[0].parent
    else:
        # Find common prefix of all paths
        common_parts = []
        first_parts = dest_paths[0].parts
        for i, part in enumerate(first_parts):
            if all(len(p.parts) > i and p.parts[i] == part for p in dest_paths):
                common_parts.append(part)
            else:
                break
        base_dir = Path(*common_parts) if common_parts else Path(dest_paths[0].parts[0])

    # Build tree structure relative to base
    tree = defaultdict(set)
    file_counts = defaultdict(int)

    for dest_path in dest_paths:
        try:
            # Get path relative to base
            rel_path = dest_path.relative_to(base_dir)
            parts = rel_path.parts

            # Track file count for leaf nodes
            if len(parts) > 0:
                parent_key = Path(*parts[:-1]) if len(parts) > 1 else Path()
                file_counts[parent_key] += 1

            # Build tree
            for i in range(len(parts)):
                parent = Path(*parts[:i]) if i > 0 else Path()
                child = parts[i]
                tree[parent].add(child)
        except ValueError:
            # Path is not relative to base, skip
            continue

    # Print the tree
    print(f"\n📁 {base_dir}\n")

    def _print_subtree(base: Path, prefix: str = "", depth: int = 0):
        # Limit depth to avoid huge trees
        if depth > 5:
            print(f"{prefix}└── ... (truncated for brevity)")
            return

        children = sorted(tree.get(base, []))
        for idx, name in enumerate(children):
            is_last = idx == len(children) - 1
            connector = "└── " if is_last else "├── "

            # Show file count if this is a directory with files
            current_path = base / name if base != Path() else Path(name)
            count = file_counts.get(current_path, 0)
            count_str = f" ({count} files)" if count > 0 and current_path in tree else ""

            print(f"{prefix}{connector}{name}{count_str}")
            next_base = base / name if base != Path() else Path(name)
            extension = "    " if is_last else "│   "
            _print_subtree(next_base, prefix + extension, depth + 1)

    _print_subtree(Path())

