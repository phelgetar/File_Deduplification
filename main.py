#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: main.py
# Purpose: Root entry point — delegates to core.main
#
# Description:
# Thin wrapper so the documented CLI usage (`python main.py ...`)
# keeps working after the application code moved into core/.
###################################################################

from core.main import main

if __name__ == "__main__":
    main()
