# File: scripts/gen_changelog.py

import subprocess
from datetime import datetime
from pathlib import Path

import changelog

from read_version import read_version

changelog_file = Path("CHANGELOG.md")

def generate_changelog():
    version = read_version()
    date_str = datetime.now().strftime("%Y-%m-%d")
    title = f"## [v{version}] - {date_str}\n"

    log = subprocess.run(
        ["git", "log", "--pretty=format:* %s", "--no-merges", "HEAD~10..HEAD"],
        capture_output=True,
        text=True,
        check=True
    ).stdout

    changelog_entry = f"\n{title}\n{log}\n"

    if changelog_file.exists():
        original = changelog_file.read_text()
        changelog_file.write_text(changelog_entry + original)
    else:
        changelog_file.write_text(changelog_entry)

    print(f"\U0001F4DD Changelog updated for v{version}")

if __name__ == "__main__":
    generate_changelog()

with open("CHANGELOG_LAST.md", "w") as f:
    f.write(changelog)
