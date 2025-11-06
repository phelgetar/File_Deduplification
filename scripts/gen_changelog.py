#!/usr/bin/env python3
import re

CHANGELOG_PATH = "CHANGELOG.md"

def extract_latest_changelog():
    with open(CHANGELOG_PATH, "r") as f:
        content = f.read()

    match = re.split(r'^## \[v?[\d\.]+\]', content, flags=re.MULTILINE)
    headers = re.findall(r'^## \[v?([\d\.]+)\]', content, flags=re.MULTILINE)

    if len(headers) >= 1 and len(match) >= 2:
        latest = match[1].strip()
        version = headers[0]
        return f"## [v{version}]\n{latest}"
    return "⚠️ No recent changelog entry found."

if __name__ == "__main__":
    changelog = extract_latest_changelog()
    print(changelog)

    with open("CHANGELOG_LAST.md", "w") as f:
        f.write(changelog)
