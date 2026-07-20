#!/usr/bin/env python3
# File: scripts/read_version.py

import yaml
from pathlib import Path

def read_version():
    version_file = Path(__file__).parent / "version.yaml"
    with version_file.open() as f:
        return yaml.safe_load(f)["version"]

if __name__ == "__main__":
    print(read_version())

