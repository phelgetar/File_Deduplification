#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: executor.py
# Purpose: Apply deduplication and sorting plan to filesystem
#
# Author: Tim Canady
# Created: 2025-09-28
#
# Version: 0.4.3
# Last Modified: 2025-11-06 by Tim Canady
#
# Revision History:
# - 0.4.3 (2025-11-06): Basic file operation logger added — Tim Canady
###################################################################

import shutil
from pathlib import Path
from typing import List, Tuple

def execute_plan(plan: List[Tuple[Path, Path]]) -> None:
    for src, dest in plan:
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            print(f"✅ Copied: {src} -> {dest}")
        except Exception as e:
            print(f"❌ Failed to move {src} -> {dest}: {e}")
