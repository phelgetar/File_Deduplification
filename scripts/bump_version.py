#!/usr/bin/env python3

import sys
import yaml
from pathlib import Path

type_ = sys.argv[1] if len(sys.argv) > 1 else "patch"
version_file = Path("version.yaml")
data = yaml.safe_load(version_file.read_text())
major, minor, patch = map(int, data["version"].split("."))

if type_ == "major":
    major += 1
    minor = patch = 0
elif type_ == "minor":
    minor += 1
    patch = 0
else:
    patch += 1

new_version = f"{major}.{minor}.{patch}"
data["version"] = new_version
version_file.write_text(yaml.dump(data))
print(f"✅ Updated version to {new_version}")
