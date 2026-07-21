#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: generate_user_guide.py
# Purpose: Generate docs/USER_GUIDE.pdf
#
# Description:
# Builds the end-user PDF guide covering every CLI switch, usage
# recipes, project structure, version management, and the git
# workflow. Re-run after CLI or workflow changes:
#
#   python scripts/generate_user_guide.py
#
# Requires: pip install reportlab
#
# Author: Tim Canady
# Created: 2026-07-20
#
# Version: 1.0.0
###################################################################

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable, PageBreak, Paragraph, Preformatted, SimpleDocTemplate,
    Spacer, Table, TableStyle,
)

OUTPUT = Path(__file__).parent.parent / "docs" / "USER_GUIDE.pdf"

NAVY = colors.HexColor("#1a3a5c")
STEEL = colors.HexColor("#2e6da4")
CODE_BG = colors.HexColor("#f4f4f4")
CODE_BORDER = colors.HexColor("#d0d0d0")

styles = getSampleStyleSheet()

title_style = ParagraphStyle("DocTitle", parent=styles["Title"], fontSize=30,
                             leading=36, textColor=NAVY, spaceAfter=14)
subtitle_style = ParagraphStyle("DocSubtitle", parent=styles["Normal"], fontSize=14,
                                textColor=STEEL, alignment=1, spaceAfter=20)
h1 = ParagraphStyle("H1x", parent=styles["Heading1"], fontSize=18, textColor=NAVY,
                    spaceBefore=18, spaceAfter=8)
h2 = ParagraphStyle("H2x", parent=styles["Heading2"], fontSize=14, textColor=STEEL,
                    spaceBefore=12, spaceAfter=6)
body = ParagraphStyle("Bodyx", parent=styles["Normal"], fontSize=10.5, leading=15,
                      spaceAfter=8)
flag_style = ParagraphStyle("Flag", parent=body, fontName="Helvetica-Bold",
                            fontSize=11, textColor=NAVY, spaceBefore=10, spaceAfter=2)
code_style = ParagraphStyle("Code", parent=styles["Code"], fontSize=8.5, leading=11,
                            backColor=CODE_BG, borderColor=CODE_BORDER,
                            borderWidth=0.5, borderPadding=6, leftIndent=4,
                            spaceBefore=4, spaceAfter=8)
toc_style = ParagraphStyle("TOC", parent=body, fontSize=11, leading=20)


def code(text):
    return Preformatted(text.strip("\n"), code_style)


def para(text, style=body):
    return Paragraph(text, style)


def flag(name, meta, description, example=None):
    out = [para(f"{name}  <font face='Courier' size='9' color='#555555'>{meta}</font>",
                flag_style),
           para(description)]
    if example:
        out.append(code(example))
    return out


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawString(0.9 * inch, 0.55 * inch,
                      "File_Deduplification User Guide")
    canvas.drawRightString(letter[0] - 0.9 * inch, 0.55 * inch,
                           f"Page {doc.page}")
    canvas.restoreState()


story = []

# ------------------------------------------------------------------ cover
story.append(Spacer(1, 2.2 * inch))
story.append(para("File_Deduplification", title_style))
story.append(para("User Guide", subtitle_style))
story.append(HRFlowable(width="60%", thickness=1, color=STEEL, hAlign="CENTER"))
story.append(Spacer(1, 0.3 * inch))
story.append(para(
    "AI-enhanced file deduplication and organization: recursive scanning, "
    "SHA256 duplicate detection, 250+ file-type classification, local-LLM "
    "fallback classification, semantic tagging, and safe dry-run previews.",
    ParagraphStyle("CoverBlurb", parent=body, alignment=1, fontSize=11,
                   leading=16)))
story.append(Spacer(1, 2.0 * inch))
story.append(para("Version 0.4.11 &nbsp;&bull;&nbsp; July 2026 &nbsp;&bull;&nbsp; Tim Canady",
                  ParagraphStyle("CoverMeta", parent=body, alignment=1,
                                 textColor=colors.grey)))
story.append(PageBreak())

# ------------------------------------------------------------------ TOC
story.append(para("Contents", h1))
for num, item in enumerate([
    "Introduction",
    "Installation and Setup",
    "Running the Application",
    "Execution Modes",
    "Command-Line Reference",
    "Common Recipes",
    "Project Structure",
    "Version Management and Releases",
    "Git Workflow: Committing and Pushing",
    "Tests and Utility Scripts",
    "Troubleshooting",
], start=1):
    story.append(para(f"{num}.&nbsp;&nbsp;{item}", toc_style))
story.append(PageBreak())

# ------------------------------------------------------------------ 1
story.append(para("1. Introduction", h1))
story.append(para(
    "File_Deduplification scans a directory tree, detects duplicate files by "
    "SHA256 hash, classifies every file into one of 18+ categories, and plans "
    "(then optionally executes) a clean, organized folder structure. All "
    "potentially destructive operations are gated behind an explicit "
    "<b>--execute</b> flag with a confirmation prompt; the default mode is "
    "always a safe dry-run preview."))
story.append(para("Key capabilities:", body))
for cap in [
    "<b>Atomic package detection</b> — macOS bundles (.app, .pkg, .dmg) are treated "
    "as single units instead of thousands of internal files (18–60x faster).",
    "<b>Parallel, resumable hashing</b> — SHA256 hashing runs on a thread pool "
    "(--workers), every hash commits to MySQL immediately, and interrupted runs "
    "resume from the cache: unchanged files are never hashed twice.",
    "<b>Rule-based classification</b> — MIME types, extensions, filenames, and "
    "directory patterns place files into categories such as document, financial, "
    "code, or education.",
    "<b>Local LLM fallback</b> — files no rule can place are classified by a local "
    "Ollama model from filename, path, and content. Nothing leaves your machine.",
    "<b>Semantic tagging</b> — path context and (optionally) CLIP image analysis "
    "generate searchable tags stored in the database.",
    "<b>Intelligent size handling</b> — very large files can be processed "
    "metadata-only, skipping expensive hashing.",
]:
    story.append(para(f"&bull;&nbsp;&nbsp;{cap}"))
story.append(PageBreak())

# ------------------------------------------------------------------ 2
story.append(para("2. Installation and Setup", h1))
story.append(para("2.1 Requirements", h2))
for req in [
    "Python 3.9 or newer",
    "MySQL 8.x (only when using <b>--use-db</b> and related features)",
    "Ollama with a pulled model (only for <b>--llm-classify</b>)",
    "Slack webhook URL (only for <b>--notify slack</b>)",
]:
    story.append(para(f"&bull;&nbsp;&nbsp;{req}"))

story.append(para("2.2 Installing Dependencies", h2))
story.append(code("""
# Core install (light — no ML libraries)
pip install -r requirements.txt

# Optional: CLIP-based image content analysis (~2GB of ML deps)
pip install -r requirements-ai.txt

# Optional: install as a package, giving you the `dedupe` command
pip install .          # add [ai] for the CLIP extras: pip install .[ai]
"""))
story.append(para(
    "The application degrades gracefully: without the AI extras, image content "
    "tagging is simply skipped; without a reachable Ollama server, LLM "
    "classification is skipped."))

story.append(para("2.3 The .env File", h2))
story.append(para(
    "Create a <font face='Courier'>.env</font> file in the project root "
    "(never commit it — it is gitignored):"))
story.append(code("""
# MySQL connection (used by core/db.py when --use-db is passed)
DB_HOST=localhost
DB_PORT=3306
DB_NAME=File_Deduplification
DB_USER=your-db-user
DB_PASSWORD=your-db-password

# Optional: Slack notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Optional: local LLM classification fallback (--llm-classify)
OLLAMA_HOST=http://localhost:11434
LLM_MODEL=llama3.1:8b
"""))
story.append(para(
    "Database bootstrap: run the scripts in "
    "<font face='Courier'>database/schema/</font> first (table creation), then "
    "any needed <font face='Courier'>database/migrations/</font> in order."))
story.append(PageBreak())

# ------------------------------------------------------------------ 3
story.append(para("3. Running the Application", h1))
story.append(para(
    "Three equivalent ways to invoke the same command-line interface:"))
story.append(code("""
python main.py SOURCE --base-dir DEST        # root wrapper script
python -m core.main SOURCE --base-dir DEST   # module form
dedupe SOURCE --base-dir DEST                # console script (after pip install .)
"""))
story.append(para(
    "<b>SOURCE</b> is the directory tree to scan. <b>--base-dir DEST</b> is where "
    "the organized structure will be created. Both are required."))
story.append(para("3.1 Pipeline Stages", h2))
story.append(para(
    "Every run flows through the same stages, in order:"))
for i, (stage, desc) in enumerate([
    ("Scan", "recursively collect files, honoring --filter, --file-types, "
             "--max-files, and .dedupignore patterns; atomic packages are "
             "collapsed into single units. On walks longer than 10 seconds a "
             "progress heartbeat logs files matched, directories visited, and "
             "the current location."),
    ("Hash", "SHA256 each file on a thread pool (--workers, default 4), or "
             "record metadata only above the --metadata-only-size threshold. "
             "With --use-db every hash commits immediately and files unchanged "
             "since a previous run are skipped via the cache."),
    ("Deduplicate", "group files by hash; mark duplicates and optionally "
                    "report or drop them."),
    ("Classify", "rule-based category assignment, with optional local-LLM "
                 "fallback for unclassifiable files (--llm-classify)."),
    ("Tag / Analyze", "with --use-db: semantic path tags; optionally image "
                      "metadata (--analyze-images) and CLIP content tags "
                      "(--ai-tagging)."),
    ("Plan", "compute the target folder structure (year / type / owner "
             "grouping, structure-preserving categories)."),
    ("Preview / Execute", "print the plan (and optionally log, notify, or "
                          "show a GUI); move files only with --execute after "
                          "a y/N confirmation."),
], start=1):
    story.append(para(f"<b>{i}. {stage}</b> — {desc}"))
story.append(PageBreak())

# ------------------------------------------------------------------ 4
story.append(para("4. Execution Modes", h1))
story.append(para("4.1 Dry Run (default)", h2))
story.append(para(
    "With no mode flags, the tool scans, hashes, classifies, and prints the "
    "proposed folder tree without touching a single file. Always start here."))
story.append(code("python main.py /Volumes/home --base-dir /organized"))
story.append(para("4.2 Logged Dry Run", h2))
story.append(para(
    "Add <b>--dry-run-log</b> to write the plan to a timestamped "
    "<font face='Courier'>dry_run_preview_*.json</font> (or .txt with "
    "<b>--log-format txt</b>) for later review or diffing between runs."))
story.append(code("python main.py /Volumes/home --base-dir /organized --dry-run-log --log-format json"))
story.append(para("4.3 GUI Preview", h2))
story.append(para(
    "Add <b>--gui</b> to review the plan in a PySimpleGUI window instead of "
    "reading terminal output."))
story.append(para("4.4 Execute", h2))
story.append(para(
    "Add <b>--execute</b> to apply the plan. The preview is still shown first, "
    "and you must confirm with <b>y</b> at the prompt before any file moves."))
story.append(code("python main.py /Volumes/home --base-dir /organized --use-db --execute"))
story.append(para("4.5 Interrupting and Resuming", h2))
story.append(para(
    "With <b>--use-db</b>, long runs are safe to interrupt. Every completed "
    "hash is committed to MySQL immediately, so pressing Ctrl+C during the "
    "hashing stage loses at most the handful of files in flight. The run "
    "exits cleanly with a message confirming how much work was persisted. "
    "To resume, simply re-run the same command: files whose path and "
    "modification time match a cached entry are skipped without reading a "
    "byte (marked \"(cached)\" in the log), and the run picks up where it "
    "left off. Without --use-db, interrupted work is not persisted."))
story.append(PageBreak())

# ------------------------------------------------------------------ 5
story.append(para("5. Command-Line Reference", h1))

story.append(para("5.1 Required Arguments", h2))
story.extend(flag("source", "(positional)",
    "Root directory to scan. Must exist and be readable.",
    "python main.py /Volumes/home --base-dir /organized"))
story.extend(flag("--base-dir", "PATH (required)",
    "Base output directory where the organized folder structure is planned "
    "and (with --execute) created. Created automatically if the parent "
    "directory exists and is writable."))

story.append(para("5.2 Scan Control", h2))
story.extend(flag("--filter", "PATTERN [PATTERN ...]",
    "Only include top-level directories whose names match one of the given "
    "patterns. Useful for picking specific user folders out of a large volume.",
    "python main.py /Volumes/home --base-dir /organized --filter canadytw canamac"))
story.extend(flag("--file-types", "GROUPS",
    "Restrict the scan to file-type groups (comma-separated). Hierarchical "
    "groups are supported: 'media' expands to images, videos, and audio.",
    "python main.py /photos --base-dir /organized --file-types images,videos"))
story.extend(flag("--list-file-types", "",
    "Print all available file-type groups and their extensions, then exit. "
    "No other arguments are required.",
    "python main.py --list-file-types"))
story.extend(flag("--max-files", "N",
    "Stop after processing N files. Ideal for a quick trial run on a very "
    "large volume before committing to a full scan.",
    "python main.py /Volumes/home --base-dir /tmp/preview --max-files 500"))
story.extend(flag("--ignore-errors", "",
    "Skip files that cannot be read (permissions, broken links) instead of "
    "aborting the run."))

story.append(para("5.3 Hashing and Duplicates", h2))
story.extend(flag("--metadata-only-size", "SIZE",
    "Files larger than SIZE are recorded metadata-only — no hashing, no "
    "duplicate detection. Accepts B, KB, MB, GB, TB. Use this to keep runs "
    "fast on volumes full of video files or disk images.",
    "python main.py /Videos --base-dir /organized --metadata-only-size 1GB"))
story.extend(flag("--workers", "N (default: 4)",
    "Number of parallel hashing threads. Hashing is I/O-bound, so multiple "
    "threads significantly speed up network volumes; try 8 for a fast NAS.",
    "python main.py /Volumes/home --base-dir /organized --use-db --workers 8"))
story.extend(flag("--batch-size", "N (default: 500)",
    "Files per hashing batch. Every completed file is committed to the "
    "database immediately (with --use-db), so an interrupted run (Ctrl+C) "
    "loses at most the files in flight; batches add periodic checkpoint "
    "summaries to the log. Re-running the same command after an interruption "
    "resumes from the cache — unchanged files are skipped without re-reading."))
story.extend(flag("--skip-duplicates", "",
    "Drop duplicate files from the plan entirely; only unique files are "
    "organized. Without this flag, duplicates are kept and marked."))
story.extend(flag("--duplicate-report", "FILE",
    "Write a report of all detected duplicate groups to FILE.",
    "python main.py /Volumes/home --base-dir /organized --duplicate-report dupes.txt"))

story.append(para("5.4 Database and AI Features", h2))
story.extend(flag("--use-db", "",
    "Enable MySQL persistence: hash caching across runs, saved "
    "classifications with confidence scores, and the unified file_tags "
    "table. Requires the DB_* variables in .env. Semantic path tagging "
    "runs automatically when this flag is present."))
story.extend(flag("--llm-classify", "",
    "Local LLM fallback: files that land in the 'other' category after "
    "every rule-based tier are classified by a local Ollama model using "
    "filename, path, and a 1KB content snippet for text-like files. "
    "Results are cached per content hash (duplicates cost one call). "
    "Skipped gracefully if the server is unreachable. Configure via "
    "OLLAMA_HOST and LLM_MODEL in .env.",
    "python main.py /Volumes/home --base-dir /organized --use-db --llm-classify"))
story.extend(flag("--analyze-images", "(requires --use-db)",
    "Extract EXIF, IPTC, and GPS metadata from images into the database.",
    "python main.py /photos --base-dir /organized --use-db --analyze-images"))
story.extend(flag("--ai-tagging", "(requires --use-db and requirements-ai.txt)",
    "CLIP-based image content tagging: objects, scenes, and people are "
    "identified and stored as keywords and file tags. Run --analyze-images "
    "first (or in the same invocation) so base metadata exists.",
    "python main.py /photos --base-dir /organized --use-db --analyze-images --ai-tagging"))

story.append(para("5.5 Output, Notification, and Execution", h2))
story.extend(flag("--dry-run-log", "",
    "Write the preview plan to a timestamped dry_run_preview_* file."))
story.extend(flag("--log-format", "json | txt (default: json)",
    "Format for the dry-run log file."))
story.extend(flag("--gui", "",
    "Show the plan in a PySimpleGUI preview window."))
story.extend(flag("--notify", "slack | email",
    "Send a completion notification. Slack requires SLACK_WEBHOOK_URL in .env.",
    "python main.py /Volumes/home --base-dir /organized --notify slack"))
story.extend(flag("--execute", "",
    "Apply the planned file operations after an interactive y/N "
    "confirmation. Without this flag every run is a dry run."))
story.extend(flag("--write-metadata", "",
    "During execution, write extracted metadata alongside the organized files."))
story.append(PageBreak())

# ------------------------------------------------------------------ 6
story.append(para("6. Common Recipes", h1))
story.append(para("<b>First look at a messy volume</b> — cheap, safe, fast:"))
story.append(code("python main.py /Volumes/home --base-dir /tmp/preview --max-files 500"))
story.append(para("<b>Full-featured dry run on a NAS</b> — database caching, LLM "
                  "fallback, large-file handling, 8 parallel hashing threads, "
                  "saved log. Safe to Ctrl+C and re-run to resume:"))
story.append(code("""
python main.py /Volumes/home --base-dir /organized \\
  --use-db --llm-classify --metadata-only-size 100MB --workers 8 --dry-run-log
"""))
story.append(para("<b>Photo library pass</b> — images only, with metadata and "
                  "AI content tags:"))
story.append(code("""
python main.py /Volumes/photos --base-dir /organized_photos \\
  --use-db --file-types images --analyze-images --ai-tagging
"""))
story.append(para("<b>Deduplicate only</b> — report duplicates, organize just "
                  "the unique files:"))
story.append(code("""
python main.py /Volumes/home --base-dir /organized \\
  --use-db --skip-duplicates --duplicate-report duplicates.txt
"""))
story.append(para("<b>The real thing</b> — after reviewing a dry run:"))
story.append(code("""
python main.py /Volumes/home --base-dir /organized \\
  --use-db --llm-classify --execute --notify slack
"""))
story.append(PageBreak())

# ------------------------------------------------------------------ 7
story.append(para("7. Project Structure", h1))
story.append(code("""
File_Deduplification/
+-- main.py                  # CLI entry point (delegates to core/main.py)
+-- setup.py                 # Packaging (console script: dedupe, extra: [ai])
+-- requirements.txt         # Core dependencies
+-- requirements-ai.txt      # Optional CLIP/torch stack
+-- Makefile                 # bump / changelog / release automation
+-- README.md
+-- CHANGELOG.md
+-- config/                  # YAML config + folder mapping rules
|   +-- file_type_groups.yaml
|   +-- folder_mapping.py
|   +-- folder_mappings.yaml
|   +-- image_ai_categories.yaml
|   +-- semantic_paths.yaml
+-- core/                    # Application library code
|   +-- main.py              # CLI implementation and pipeline orchestration
|   +-- scanner.py           # Recursive scan + atomic package detection
|   +-- hasher.py            # SHA256 hashing with DB cache
|   +-- deduplicator.py      # Duplicate detection and filtering
|   +-- classifier.py        # Rule-based classification (18+ categories)
|   +-- llm_client.py        # Local Ollama classification fallback
|   +-- organizer.py         # Folder structure planning
|   +-- previewer.py         # Dry-run previews and tree rendering
|   +-- executor.py          # Executes planned file operations
|   +-- context_detector.py  # Semantic context detection (Work/Personal/...)
|   +-- ai_tagger.py         # Path-based semantic tagging
|   +-- image_analyzer.py    # EXIF/IPTC/GPS metadata extraction
|   +-- image_content_analyzer.py  # CLIP-based image content analysis
|   +-- image_db.py          # Image metadata persistence
|   +-- metadata_writer.py   # Metadata output during execution
|   +-- db.py                # MySQL connection and persistence helpers
+-- database/
|   +-- schema/              # Table creation scripts (run first)
|   +-- migrations/          # Incremental schema changes (run in order)
|   +-- queries/             # Ad-hoc analysis queries
+-- docs/                    # All guides, this document, historical notes
+-- models/
|   +-- file_info.py         # FileInfo dataclass shared by the pipeline
+-- scripts/                 # Automation: versioning, changelog, env setup,
|                            #   reclassification, debug tools
+-- tests/                   # Test suite (script-style + pytest-style)
+-- utils/                   # Cache, GUI, notifications, path metadata,
                             #   file type filtering
"""))
story.append(para(
    "The flow of a file through the code: <font face='Courier'>scanner.py</font> "
    "&rarr; <font face='Courier'>hasher.py</font> &rarr; "
    "<font face='Courier'>deduplicator.py</font> &rarr; "
    "<font face='Courier'>classifier.py</font> (with "
    "<font face='Courier'>llm_client.py</font> as fallback) &rarr; "
    "<font face='Courier'>organizer.py</font> &rarr; "
    "<font face='Courier'>previewer.py</font> &rarr; "
    "<font face='Courier'>executor.py</font>. The "
    "<font face='Courier'>FileInfo</font> dataclass in "
    "<font face='Courier'>models/file_info.py</font> is the shared record "
    "passed between every stage."))
story.append(PageBreak())

# ------------------------------------------------------------------ 8
story.append(para("8. Version Management and Releases", h1))
story.append(para(
    "The project version lives in <font face='Courier'>scripts/version.yaml</font> "
    "and is read by <font face='Courier'>scripts/read_version.py</font>. "
    "<font face='Courier'>setup.py</font> carries the same version for packaging."))
story.append(para("8.1 Bumping the Version", h2))
story.append(code("""
make bump                 # bump the patch version (0.4.11 -> 0.4.12),
                          #   commit, and push

# What it runs under the hood:
python scripts/bump_version.py patch
git add scripts/version.yaml
git commit -m "Bump patch version"
git push origin main
"""))
story.append(para("8.2 Updating the Changelog", h2))
story.append(code("""
make changelog            # regenerate from commit history:
                          #   scripts/gen_changelog.py > docs/CHANGELOG_LAST.md
                          #   scripts/gen_changelog.py >> CHANGELOG.md
                          #   then commits and pushes
"""))
story.append(para("8.3 Cutting a Release", h2))
story.append(code("""
make release              # 1. verifies no staged file exceeds 100MB
                          # 2. commits with the current version number
                          # 3. pushes to origin/main
                          # 4. creates a GitHub release via `gh release create`
                          #    using docs/CHANGELOG_LAST.md as the notes
"""))
story.append(para(
    "Typical release sequence: <b>make bump</b> &rarr; <b>make changelog</b> "
    "&rarr; <b>make release</b>. The GitHub CLI (<font face='Courier'>gh</font>) "
    "must be installed and authenticated for the release step."))
story.append(PageBreak())

# ------------------------------------------------------------------ 9
story.append(para("9. Git Workflow: Committing and Pushing", h1))
story.append(para(
    "The repository is hosted on <b>GitHub</b> at "
    "<font face='Courier'>github.com/phelgetar/File_Deduplification</font>, "
    "with <font face='Courier'>main</font> as the working branch."))
story.append(para("9.1 Day-to-Day Commits", h2))
story.append(code("""
git status                          # review what changed
git add <files>                     # stage specific files (or -A for all)
git commit -m "feat(scope): short description"
git push origin main
"""))
story.append(para(
    "Commit messages follow the conventional-commits style used throughout "
    "the history: a type prefix (<font face='Courier'>feat</font>, "
    "<font face='Courier'>fix</font>, <font face='Courier'>docs</font>, "
    "<font face='Courier'>chore</font>, <font face='Courier'>refactor</font>), "
    "an optional scope in parentheses, and a concise imperative summary."))
story.append(para("9.2 The Pre-Commit Size Guard", h2))
story.append(para(
    "A pre-commit hook (symlinked to "
    "<font face='Courier'>scripts/validate_large_files.sh</font>) blocks any "
    "commit containing a staged file over 100MB — GitHub's hard limit. If a "
    "commit is rejected, remove the offending file from staging; generated "
    "artifacts belong in <font face='Courier'>output/</font>, which is "
    "gitignored."))
story.append(para("9.3 What Never Gets Committed", h2))
for item in [
    "<font face='Courier'>.env</font> — contains database credentials",
    "<font face='Courier'>output/</font> — dry-run previews and reports",
    "<font face='Courier'>.venv*/</font> — virtual environments",
    "<font face='Courier'>.file_dedup_cache.json</font> — local hash cache",
    "<font face='Courier'>__pycache__/</font>, <font face='Courier'>.DS_Store</font>, "
    "IDE folders",
]:
    story.append(para(f"&bull;&nbsp;&nbsp;{item}"))
story.append(para(
    "All of these are covered by <font face='Courier'>.gitignore</font>; if "
    "git ever shows them as untracked changes, do not force-add them."))
story.append(PageBreak())

# ------------------------------------------------------------------ 10
story.append(para("10. Tests and Utility Scripts", h1))
story.append(para("10.1 Script-Style Tests (run directly)", h2))
story.append(code("""
python tests/test_llm_classifier.py     # LLM fallback (skips if Ollama is down)
python tests/test_atomic_packages.py    # atomic .app/.pkg detection
python tests/test_db_connection.py      # MySQL connectivity + .env sanity
python tests/test_context_detection.py  # semantic context rules
python tests/test_folder_mapping.py     # custom folder mapping rules
python tests/test_image_metadata.py     # image metadata extraction
"""))
story.append(para("10.2 Pytest-Style Tests", h2))
story.append(code("""
pip install pytest
pytest tests/test_scanner.py tests/test_hasher.py \\
       tests/test_classifier.py tests/test_organizer.py tests/test_executor.py
"""))
story.append(para("10.3 Utility Scripts", h2))
story.append(code("""
python scripts/reclassify_files.py      # re-classify files already in the DB
                                        #   (after classifier rule changes)
python scripts/debug_classification.py  # inspect why a file classifies as it does
./scripts/setup_env.sh                  # bootstrap a starter .env file
python scripts/generate_user_guide.py   # regenerate this PDF
"""))
story.append(PageBreak())

# ------------------------------------------------------------------ 11
story.append(para("11. Troubleshooting", h1))
rows = [
    ["Symptom", "Likely Cause and Fix"],
    ["Database initialization fails at startup",
     "Missing or wrong DB_* values in .env. Verify with: "
     "python tests/test_db_connection.py"],
    ["'Ollama server not reachable' warning",
     "Start the server with `ollama serve` and confirm the model exists "
     "(ollama list). Override host/model via OLLAMA_HOST / LLM_MODEL."],
    ["'AI tagging requires additional libraries'",
     "Install the optional stack: pip install -r requirements-ai.txt"],
    ["PySimpleGUI install or import errors",
     "PySimpleGUI moved to a private index in 2024. Install with: pip install "
     "--extra-index-url https://PySimpleGUI.net/install PySimpleGUI"],
    ["Commit rejected: file exceeds 100MB",
     "The pre-commit size guard fired. Unstage the file; large artifacts "
     "belong in output/ (gitignored)."],
    ["Run is slow on huge video collections",
     "Use --metadata-only-size (e.g. 1GB) to skip hashing large files, "
     "--workers 8 to parallelize network reads, and --use-db so hashes are "
     "cached across runs."],
    ["Scan phase seems silent or hung",
     "The walk logs a heartbeat every 10 seconds (files matched, directories "
     "visited, current location). If heartbeats stop advancing, check the "
     "directory named in the last one — likely a dead mount or permission "
     "stall."],
    ["Run was interrupted (Ctrl+C, crash, reboot)",
     "With --use-db, completed work is already saved. Re-run the same "
     "command; unchanged files show '(cached)' and are skipped instantly."],
    ["Everything classifies as 'code' or 'application'",
     "The path contains a structure-preserving directory name (src, scripts, "
     "software, adobe, ...). This is by design: those trees are preserved "
     "as-is."],
]
tbl = Table([[Paragraph(c, ParagraphStyle("Cell", parent=body, fontSize=9,
                                          leading=12, spaceAfter=0))
              for c in row] for row in rows],
            colWidths=[2.2 * inch, 4.4 * inch])
tbl.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("GRID", (0, 0), (-1, -1), 0.5, CODE_BORDER),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CODE_BG]),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
]))
story.append(tbl)
story.append(Spacer(1, 0.3 * inch))
story.append(para(
    "For deeper dives, see the topic guides in <font face='Courier'>docs/</font>: "
    "duplicate detection, atomic packages, image analysis, path metadata, "
    "reclassification, database troubleshooting, and more."))


def build():
    OUTPUT.parent.mkdir(exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT), pagesize=letter,
        leftMargin=0.9 * inch, rightMargin=0.9 * inch,
        topMargin=0.8 * inch, bottomMargin=0.9 * inch,
        title="File_Deduplification User Guide",
        author="Tim Canady",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(f"✅ Wrote {OUTPUT}")


if __name__ == "__main__":
    build()
