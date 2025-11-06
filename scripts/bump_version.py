#!/usr/bin/env python3
# File: scripts/bump_version.py

import yaml
from pathlib import Path

version_file = Path("version.yaml")

def bump_patch():
    with version_file.open() as f:
        data = yaml.safe_load(f)

    major, minor, patch = map(int, data["version"].split("."))
    patch += 1
    new_version = f"{major}.{minor}.{patch}"
    data["version"] = new_version

    with version_file.open("w") as f:
        yaml.dump(data, f)

    print(f"\U0001F527 Bumped patch version to {new_version}")

def main():
    bump_patch()

if __name__ == "__main__":
    main()
