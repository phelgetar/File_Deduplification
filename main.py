#!/usr/bin/env python3

###################################################################
# Project: File_Deduplification
# File: main.py
# Purpose: Application entry point
#
# Author: Tim Canady
# Created: 2025-09-28
#
# Version: 0.4.4
# Last Modified: 2025-11-06 by Tim Canady
#
# Revision History:
# - 0.4.4 (2025-11-06): Filter argument alignment fix — Tim Canady
###################################################################

import argparse
from core.scanner import scan_directory
# other imports omitted for brevity

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("--base-dir", required=True)
    parser.add_argument("--filter", nargs="*", help="List of folder name patterns to include")
    args = parser.parse_args()

    files = scan_directory(args.source, filter_names=args.filter)
    print(f"Files scanned: {len(files)}")

if __name__ == "__main__":
    main()
