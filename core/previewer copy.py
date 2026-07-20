#!/usr/bin/env python3
#
###################################################################
# Project: File Deduplication
# File: previewer.py
# Purpose: Display proposed file structure and file moves to user.
#
# Description of code and how it works:
# Formats the file move plan into a readable CLI preview using
# indentation and grouping by folder. Highlights duplicates and changes.
#
# Author: Tim Canady
# Created: 2025-09-28
#
# Version: 0.1.0
# Last Modified: 2025-11-04 by Tim Canady
#
# Revision History:
# - 0.1.0 (2025-11-04): Initial preview logic — Tim Canady
###################################################################

from pathlib import Path
from models.file_info import FileInfo
from rich.console import Console
from rich.tree import Tree


def preview_plan(plan: dict[Path, list[FileInfo]]):
    console = Console()
    tree = Tree("[bold blue]Proposed Directory Structure[/bold blue]")

    for folder, files in sorted(plan.items()):
        folder_node = tree.add(f"[green]{folder}[/green]")
        for fi in files:
            label = f"[white]{fi.path.name}[/white]"
            if fi.is_duplicate:
                label += " [red](DUPLICATE)[/red]"
            folder_node.add(label)

    console.print(tree)
    console.print("\nTo proceed, run: [bold yellow]python executor.py --execute[/bold yellow]\n")
