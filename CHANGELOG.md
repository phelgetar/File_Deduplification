# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### 🛡️ Safety
- 🐛 **FIX**: The review-and-commit summary blocked the request while it worked. Cold, it walks every candidate directory over SMB to spot companion files — over three minutes on this data — so the panel hung on first load after each restart, then answered in ~3s once the directory cache was warm. It now uses the same background-and-poll contract as `/status` and `/tree`: the request returns immediately with `{status: "computing"}` and the page polls. The cached answer is dropped whenever a decision is saved, unsaved, deleted or undone, so it can never show a stale total.

- 🐛 **FIX**: Zero-byte files were all grouped as one duplicate set. Every empty file hashes to `e3b0c442…` (SHA-256 of the empty string), so this project's own inventory had a single "duplicate group" of **149,296 members** — and it had been resolved, meaning one click on Review-and-trash would have moved 149,295 files to the Trash to reclaim **0 bytes**, taking `.localized`, empty `__init__.py`, `.gitkeep` and other marker files with them. Emptiness is usually the point of such a file, so byte-identity is not evidence of redundancy: zero-byte files are now excluded from duplicate grouping outright, in the detector and again in the delete path so a resolution saved earlier cannot act on them.
- ⚡ This also fixes the review-and-commit summary, which had to stat 149,785 candidate paths over SMB and never returned. It now answers in **3.0s**.

- ✨ **NEW**: **A captured folder is not a pile to be sorted.** `fred_disk` on the Desktop is somebody's Windows disk — `$RECYCLE.BIN`, `System Volume Information`, event logs, prefetch files, 5,986 files 23 levels deep — and filing it by type scattered it into `Desktop/Data/fred_disk`, `Desktop/Code/fred_disk`, `Desktop/Certs/fred_disk`, `Desktop/Backups/fred_disk`, `Desktop/Archives/fred_disk` and `Desktop/Applications/fred_disk`: six copies of a name that means one thing. A folder under a context spanning **3+ categories over 8+ files** is now treated as a captured unit and kept whole. On the real tree, 1,981 sampled files spanning **18 distinct categories** now land under exactly one destination, `Desktop/fred_disk/`.
  - Deciding this needs the whole file list — whether a folder is a captured unit or a pile is invisible from any single file inside it — so `plan_organization` makes one pass to find them before planning anything.
  - Loose files and single-purpose folders still sort by type: a Desktop PDF lands in `Desktop/Docs/PDF`, and a camera folder of nothing but JPEGs is one category, so it goes to `Desktop/Media/Images/100JVCSO/`. Volume alone is not evidence either — forty `.txt` files in one folder is still one category, and still sorts.

### 🗂️ Job history
- ✨ **NEW**: Command-line runs are recorded too, so they appear in the web UI's Jobs tab alongside runs started there — the plan stays browsable and can be executed from the UI later. Both entry points now write the same artifacts via `core/artifacts.py`; previously only the server did, and `--dry-run-log` wrote `str(tuple)` Python reprs that could not be read back. Disable with `--no-record`.
- ✨ **NEW**: The Jobs tab survives a restart. Plans, duplicate groups and results were always written to `.workbench/jobs/<id>/`, but the index of them lived only in memory, so restarting the server emptied the list and made completed work look lost. A `job.json` manifest is now written when a run starts, and the registry rebuilds itself from disk — including jobs from before manifests existed, whose source is recovered from the plan. A run interrupted by the restart is shown as interrupted rather than silently missing.
- ✨ **NEW**: `api_version` handshake. `index.html` and `app.js` are read from disk on every request, so a server left running across an update serves a new UI against old routes — the only symptom being a bare 404 ("Not Found" under a greyed-out button). The page now compares versions and says plainly that the server needs restarting.

### 🖥️ Web UI
- 🐛 **FIX**: The folder picker could not see symlinked directories, because it asked `is_dir(follow_symlinks=False)`. On macOS the boot volume is presented as a symlink at `/Volumes/Macintosh HD`, so browsing `/Volumes` with no network share mounted showed **"No subfolders"** and there was nothing to click. Following symlinks is safe here — browsing is read-only, and the forbidden-root check now runs against the resolved target rather than the link.
- ✨ **NEW**: An empty `/Volumes` says *why*. "No subfolders" reads as a broken picker when it actually means the shares dropped; the listing now names the unmounted volumes and how to get them back. This is the same failure the mount preflight exists to catch — an unmounted path looks exactly like an empty one.

### 📖 Documentation
- 📖 **README rewritten.** It described the deduplicator as it was before the three tools merged, listed 15 of the 30 CLI switches, and still advertised 18 categories and 250+ file types against the current 28 and 309. It now opens with what the tool actually is — one pipeline reached from a terminal or a browser — documents **every switch** grouped by what it decides, with defaults and failure modes, and explains the rule order that decides a destination (project roots → context → captured folders → category). New sections cover the maintenance scripts, the environment variables that are not in `.env`, and a categories table generated from `config/rules.yaml` rather than transcribed.
- 🐛 **FIX**: Five switches had no `--help` text at all — `--gui`, `--execute`, `--write-metadata`, `--log-format` and `--notify`. `--execute` is the one that copies files, so "no description" was the worst possible place for the gap.
- ✅ The README is checked against the code rather than trusted: all 30 switches it documents exist, no real switch is undocumented, all 11 `main.py` examples use only real switches, and all 48 files named in the project tree exist.

### 🖥️ Web UI
- 🐛 **FIX**: The Jobs list showed a bare time — fine for the run you started ten minutes ago, useless for the rest. The list now spans imported command-line runs from November 2025 onward, where "3:14 PM" identifies nothing. Each row now reads `2026-08-21 22:08`, written year-first so the column sorts the way it reads, with the full timestamp on hover.

- ✨ **NEW**: The Run form gains **Metadata only above** and **Hash workers**. `ScanRequest` had accepted `metadata_only_size` and `hash_workers` since the server was written, but the page never sent them — so every scan started from the browser hashed *every* file regardless of size, with no way to say otherwise, while the CLI had `--metadata-only-size` and `--workers`. The two front ends now offer the same knobs. Blank means the same as omitting the flag: no threshold, and workers sized for the machine. The form carries the warning the size threshold deserves — above it a file is recorded but not read, so identical large videos will not be found as duplicates.

- ✨ **NEW**: A command-line run's record now says what the run actually *did*, not just where it pointed. The manifest held six fields — source, destination, `use_db`, `max_files`, `file_types` — so the Jobs tab could not answer "did this one use cloud escalation?" or "was that scan hashing everything?". It now records the whole ladder (`llm_classify`, `cloud_classify`, the spend cap and model), `metadata_only_size`, `hash_workers`, `skip_duplicates`, `ai_tagging`, `analyze_images` and whether project roots were on. This matters because the two front ends do not default the same way, so the answer was not inferable from the source path alone.

### 🗂️ Project roots
  - 🐛 **FIX**: A marker now takes the **outermost** ancestor, not the nearest. Build files recur at every level of a source tree — `swift-master`, its `benchmark/` and its `benchmark/scripts/` each carry a `CMakeLists.txt`, and `ffmpeg-4.1` carries a `Makefile` in every one of its `libav*` directories — so stopping at the nearest one shattered swift-master into **185 separate "projects"** and ffmpeg into 40. On a real scan of `~/Documents`: **358 roots → 124**, and **234 roots nested inside another → 0**. The trade is a monorepo whose packages you would rather see separately; declare those as a container and the seams come back, since containers are checked first.
  - 🐛 **FIX**: Two more paths that repeated a folder name. A category folder that merely restates the context (`education` inside the Education context) gave `Education/Education/Wright-State-University`, and a category folder ending in the same name as the source folder gave `Media/Videos/SecurityCameraVideos/SecurityCameraVideos/` — 38 files. The context planner stripped the overlap against the context folder but not against the category folder; it now strips against everything already in the destination.

### 🎓 Coursework
- 🔧 **CHANGED**: **Under a school, the structure IS the organisation.** `preserve_subfolders` makes every directory below an Education context arrive verbatim — `Education/AFIT/SENG640/Week4/slides.pptx`, not `Education/AFIT/SENG640/Docs/PowerPoints/Week4/slides.pptx`. A week holds slides, a PDF reading, a spreadsheet and some code, and they are one week's work. The cohesive-unit heuristic already kept most courses whole, but only because they happened to be mixed enough; a course holding three PDFs would have been broken up. This guarantees it. Loose files at a school's own level still sort — `Education/AFIT/Docs/PDF/Academic Integrity.pdf`.
- 🐛 **FIX**: **1,906 coursework files were being pulled out of Education.** A `www` folder that is an AFIT SENG610 assignment went to top-level `Websites/` (1,559 files), and `.xcodeproj`/`.sln` markers buried in assignments lifted them into `Projects/` (347). Education contexts now set `beats_project_roots`, so a project marker inside coursework is understood as part of the course. Scoped to Education — elsewhere a project really is the unit. Verified on the real tree: **0 files escape** where 1,906 did, and **10,074 of 10,074** files in a school subdirectory land at exactly `Education/<original relative path>`.
- 🐛 **FIX**: `C++Monitoring` was split in half — `main.cpp` under one project root and `project.pbxproj` under another. An `.xcodeproj` bundle contains a `project.xcworkspace`, which tripped the marker suffix check and made the bundle its own root nested inside the real project. A bundle is a marker, not a directory holding one.

### 🗂️ Where files land
- 🔧 **CHANGED**: **The semantic context now comes before the category folder.** A WSU lecture deck planned to `Docs/PowerPoints/Education/WSU/FALL18-EGR3350/…`, its syllabus to `Docs/PDF/Education/WSU/…` and its lab photos to `Media/Images/Education/WSU/…` — one course split across three trees, which is the same complaint that project roots exist to answer. It now plans to `Education/WSU/Docs/PowerPoints/FALL18-EGR3350/…`: one subject, subdivided by type. Finding *every* presentation is a database question, not a directory question. Record-set contexts (`Personal - Disability/VA`, `Personal/Family`) are unaffected — they set `group_by_category: false` and never had a category folder. Set `category_position: before_context`, globally or per context, to keep the old layout.
- ✨ **NEW**: **Schools are their own contexts** at priority 92, above the generic Education rule: WSU (also matching `wright-state`), AFIT, Coursera, MIT-Sloan, Park, DAU and NPS. Without them every school shared one `Education/` folder and the institution survived only as a directory further down the path. A school is a real division of the work, not an accident of foldering.

### 🗂️ Job history
- ✨ **NEW**: **`scripts/import_cli_runs.py`** brings historical command-line runs into the Jobs tab. Runs have recorded proper artifacts since `core/artifacts.py` landed, but everything before that left only a `dry_run_preview_*.json` — a JSON array whose every element is the `repr()` of a `(FileInfo, PosixPath)` tuple, unreadable to the web UI and awkward even to grep. All **36** non-empty previews here convert, including three older ones that are bare text rather than JSON. Parsed through the AST rather than `eval()` — the files are ours, but a 5.5 GB file is not something to hand to the interpreter — and streamed line by line throughout, since `json.load()` on the largest (6,992,105 rows) would want tens of gigabytes.
- ⚠️ An imported plan is a **historical record, not a proposal**: it says what the rules decided on the day it ran. Previews older than the newest rule file are flagged `ruleset: historical`, because the oldest of these still plan files into `Desktop/Desktop/Desktop/`. `--dry-run`, `--max-size-mb` and `--only` are there so the multi-gigabyte ones can be left for a deliberate run.

### 🧰 CLI
- 🐛 **FIX**: Every CLI run opened with unrelated third-party noise — eight lines of PySimpleGUI pip instructions, a tkinter version warning, and a urllib3 LibreSSL warning — before printing anything of its own. Two module-scope imports caused it: `utils/gui.py` imported PySimpleGUI (which prints an install banner and pulls in tkinter) and `utils/notifications.py` imported `requests` (which pulls in urllib3). Neither is needed unless you pass `--gui` or a Slack webhook is configured, so both are now imported at the point of use. `--show-mounts`, `--show-parallelism` and `--show-project-roots` print only their own output, and CLI startup drops from **0.19s to 0.12s**.

  - 🐛 **FIX — would have destroyed data.** Matching a container name *wherever it appears*, which is what catches the NAS mirrors, also matched every dated backup snapshot. A real scan of `/Volumes/home` found **85 daily copies** of `PycharmProjects/SENG593` under `Backups/appdata/Teufelshunde_<timestamp>/`, and all 85 planned into one `Projects/SENG593/`. Executing that keeps whichever snapshot arrives first and **silently drops the other 84**, because the executor skips a destination that already exists. In total **3,324,641 of 3,327,969** `Projects/` files came from a project fed by more than one source. A directory with a backup-ish ancestor (`Backups`, `Restore`, `iMac_Backup`, anything containing "backup") is no longer a project root; it keeps its own structure and snapshot identity under the backup category. Only *ancestors* are examined, so `XCode-42739/Backup` — an Xcode project literally named Backup — stays a project.
  - 🐛 **FIX**: Two project roots sharing a leaf name merged into one destination. `Unit6` existed under two Park University courses, and generic leaves (`test`, `configs`, `cmake-build-debug`) collided several ways. Colliding names are now qualified by the shallowest run of ancestors that tells them apart — `Projects/2020-U1A-CS225/CLionProjects/Unit6` beside `Projects/CS225/CLionProjects/Unit6` — while unique names stay flat.
  - 🐛 **FIX**: The four structure-preserving planners did not strip the overlap between the category folder and the path they preserve, so a file under `/private/var/mobile/Applications/` planned into `Applications/Applications/…` — 4,269 of them. They now share one overlap strip, the same one the context planner already had.
  - ✅ Re-planned against the real 4,021,473-row plan: colliding source directories **369 → 10 → 0**, planner-introduced doubled path segments **334 → 0**. The 29,373 remaining doubled segments are faithful — `fred_disk/FRED_3.0/FRED_3.0` genuinely exists on disk.

  - ✨ **NEW**: **`roots`** — a third way to name a project, and the one that needs no cleverness. A container says "my children are projects"; a marker says "any folder holding this is a project". Neither fits an Eclipse install holding `cpp-oxygen` and `java-oxygen`: that is one thing, not two projects and not a folder of them. A declared root is just *this folder, whole*, and is checked before the other two because it is the most specific thing anyone can say.
  - Added `eclipse-workspace` as a container. Its own top level carries `.git` and `.metadata`, which would otherwise promote the entire workspace to one project through the marker rule and swallow every project inside it.

### 🧹 One rule table
- 🔧 **CHANGED**: **Four files held slices of the same knowledge; now one does.** The classifier's hardcoded extension lists, `CATEGORY_FOLDER_MAP`, the `--file-types` groups and `project_roots.yaml` each knew part of "what is this file and where does it go", and nothing made them agree — so they had drifted apart on **27 extensions**. `config/rules.yaml` now owns the table, each extension appearing exactly once, and `core/rules.py` is the only reader; everything else asks it. Config files for the rule set go from **six to three**, each answering one question: `rules.yaml` (what a file *is*), `semantic_paths.yaml` (where it *came from*), `image_ai_categories.yaml` (what a photograph *depicts*). `core/classifier.py` loses 86 lines of hardcoded lists and `config/folder_mapping.py` 35.
- 🐛 **FIX**: **43,701 source files were classified as documents.** `mimetypes` calls `.py` `text/x-python`, the `startswith("text")` branch claimed it as prose, and the specific `text/x-python` branch further down could never be reached — so `.py`, `.java`, `.c`, `.h`, `.js`, `.html`, `.htm` and `.css` all became `document`. The extension table now runs **before** MIME and is authoritative; MIME is the fallback for extensions the table does not know. `.html`/`.htm`/`.css`/`.js` classify as `web`, the rest as `code`.
- 🐛 **FIX**: `.rw2` — a Panasonic raw photograph — was classified **financial**, because the "financial" rule substring-matched `"w2"` against the whole filename. The same rule matched `"ira"` in any path through a folder named *Miranda* and `"tax"` in `syntax.txt`, and the education rule's `startswith("mat")` matched `matthew-wedding.jpg`. Both now match on word boundaries, and the course-prefix rule requires a digit after the prefix. In practice only files no other rule claimed were affected, but the outcome was still wrong.
- 🐛 **FIX**: `.arw` and `.orf` (raw photos) were `other`; `.docm`, `.xlsm` and `.pptm` (macro-enabled Office) were `other` while their plain forms classified correctly; `.wpd` was `other`; `.dmg` was an archive rather than an installer; `.tsv` was a document rather than a spreadsheet; `.cdr` (CorelDRAW) was an archive. All corrected. `.ts` stays **video** (MPEG transport stream) rather than TypeScript — a genuinely ambiguous extension, and loose `.ts` files on a NAS are far more often video; TypeScript inside a project keeps its place regardless, via the project-root rule above.
- ✅ Verified by snapshotting the category of all **309 known extensions** before and after: **32 changed, 0 of them unintended.** `tests/test_rules.py` adds 43 tests, including a drift guard that re-derives every extension end to end and fails if the classifier and the table ever disagree again, and a check that no `--file-types` group can select an extension outside the categories it names.
- ⚠️ **Files already in the database keep their stored category on re-runs.** Run `scripts/reclassify_files.py` to re-derive them — the source-code rows are the large ones.
- 🔧 **REMOVED**: `config/file_type_groups.yaml` and `config/project_roots.yaml`, both folded into `config/rules.yaml`. A custom groups file is still honoured if passed explicitly to `FileTypeFilter`.

### 🗂️ Organizer rules
- ✨ **NEW**: **Project trees stay whole.** A project is not a category. `/Users/canadytw/PycharmProjects/Foo` holds source, a README, design PDFs, a Word spec and screenshots, and each of those only means something in place — but the organizer filed them by type, scattering one working thing across `Code/`, `Docs/PDF/`, `Docs/Word/` and `Media/Images/`, with nothing able to reassemble it. A new highest-priority rule (`core/projects.py`, above semantic contexts) copies the whole subtree verbatim to `<dest>/Projects/<project name>/<original relative path>`, whatever it contains. Verified against the real tree: 400 sampled files spanning code, images, text, audio, web and data all landed at their original relative positions, 400/400.
  - Roots are found two ways, configured in the `project_roots` section of **`config/rules.yaml`**. A **container** is a directory whose immediate children are each one project (`/Users/canadytw/PycharmProjects` ships enabled) — add your web root or `~/Developer` the same way. A **marker** is `.git`, `package.json`, `pyproject.toml`, `.xcodeproj` and 18 others, making any directory that holds one a root wherever it lives. Containers are checked first and win, so a vendored repository inside a project does not carve out a smaller root than you intended.
  - **More project shapes, found by surveying the actual disks.** Xcode (`~/Documents/XCode`, `XCode-42739` — note that `XCode-42739/Backup` and `/Backups` are Xcode projects *named* Backup, and reaching them before the `/backup/` path rule is exactly why project roots run first), MATLAB Drive (`.MATLABDriveTag`, dropped into every synced folder), Xilinx ISE (`.xise`, `.gise`, `.prj` under `Documents - 2996KD/fpga`), Eclipse workspaces (`.project`, `.classpath`), plus `.sln`, `.vcxproj`, `.cbp`, `.Rproj`, `.iml` and `.mlproj`. Markers go from 22 to 34.
  - ✨ **NEW**: **`container_names`** — containers matched by directory name, wherever they appear. Absolute paths do not survive contact with this data: `PycharmProjects` exists in the home directory, again under `/Volumes/home/Data/Restore/`, again under `/Volumes/homes/canadytw/Data/Restore/` (the same share seen from its parent), and a third time under `iMac_Backup`. Name matching catches every copy for a string comparison rather than a stat. Ships with the IDE workspaces (`PycharmProjects`, `CLionProjects`, `NetBeansProjects`, `IdeaProjects`, `workspace`), `XCode`, `MATLAB-Drive`, `fpga`, `allegro-projects`, and `Sites`/`www`/`public_html` → `Websites`. The **outermost** match wins, so an inner folder of the same name is part of the project rather than a seam that splits it.
  - 🐛 **FIX**: A file sitting loose at the top of a container became its own project, planning to `Projects/notes.docx/notes.docx`. A project needs at least one directory level.
  - 🐛 **FIX**: A container could be promoted to a project by the marker rule. `MATLAB-Drive` carries a `.MATLABDriveTag` at its own top as well as in each synced folder, so the whole drive became one "project" — sweeping in loose files that only happen to live there, including a 1Password emergency-kit PDF. A container holds projects; it is not one.
  - ✅ Verified against 17 real paths spanning Xcode, MATLAB Drive, Xilinx, Eclipse, both NAS mirrors and the backup copy: **17/17**, with loose files correctly falling through to normal filing (`Example3_help.m` → code, the 1Password PDF → `Docs/PDF`).
  - `index.html` is deliberately **not** a marker, and a scope guard rejects `/`, `/Users`, a home directory, `/Volumes` and a bare share root plus anything in `never_roots`. Otherwise one stray `Makefile` at the top of a scan would make every file below it a single "project" and copy the entire volume under one folder.
  - Inspect with `--show-project-roots`; disable for one run with `--no-project-roots`, or permanently with `WORKBENCH_NO_PROJECT_ROOTS=1`.
- 🐛 **FIX**: `--show-mounts`, `--show-parallelism` and `--show-project-roots` errored out with "the following arguments are required: source, --base-dir" when run on their own — which is the only way anyone runs a flag that prints something and exits. `source` and `--base-dir` are now validated after the informational flags have had their chance to exit, and still required for a real run.
- 🐛 **FIX**: `--list-file-types` was declared but never handled, so it silently started a normal run with whatever other arguments were present. It now prints the groups and exits.

- 🛡️ **NEW**: `scripts/reclassify_files.py` no longer trades a specific category for an unclassified one. A dry run over the 93,163 `document` rows here wanted to move **3,624** of them to `other` — extensionless files like `AUTHORS` and `COPYING`, plus legacy `.wpd`, `.wk4` and `.123` formats that today's extension checks do not recognise. Those were classified under an older ruleset and reclassifying them is a loss, not an improvement, so a move into `other`/`unknown` is now skipped and reported. `--allow-downgrade` opts back in.
- 🐛 **FIX**: A folder named `src`, `bin`, `lib`, `out` or `build` classified everything inside it as code, before any extension was looked at — a photo album under `src/` became `Code/`. Extensions whose meaning does not depend on location (images, video, audio, PDF, Office) are now immune to the path rules. `.txt`, `.md`, `.json` and friends deliberately still follow the project, since they really are part of one when they live in it. The organizer additionally now requires a real project marker nearby (`.git`, `package.json`, `pyproject.toml`, …) before preserving a code-project structure.
- 🐛 **FIX**: `document` split into `document_word`, `document_pdf` and `document_text`, mapping to `Docs/Word`, `Docs/PDF` and `Docs/Text`. The single category mapped to `Docs/Word`, which filed every PDF and `.txt` under Word. The generic `document` fallback now maps to plain `Docs`. **Files already classified in the database keep their stored `document` category on re-runs** — use `scripts/reclassify_files.py` to re-derive them.
- 🐛 **FIX**: The special video collections matched a filename substring, so any file with `clip` in its name — `vacation-clip.mov` — was filed as a wolf video. They now match a directory name (`WolfVids/`, `SecurityCameraVideos/`), which is a deliberate act of organisation rather than a coincidence.
- 🐛 **FIX**: The web, backup and application planners each hardcoded their own folder name, disagreeing with `CATEGORY_FOLDER_MAP` — a `.pkg` landed in `application/` while a `.app` landed in `Installers/`. All four now resolve the folder through the one mapping that owns it.
- ✨ **NEW**: `group_by_category` per semantic context in `config/semantic_paths.yaml`. Contexts previously overrode file type outright, so a photo on the Desktop was planned as `Desktop/100JVCSO/PIC_0065.JPG` and its category existed only in the database. Location-style contexts (Desktop, Work, Education, Personal, Hobbies) now file by category first — `Media/Images/Desktop/100JVCSO/PIC_0065.JPG`, `Docs/Word/Desktop/canadytw_12192006.doc` — while record sets (`Personal - Disability/VA`, `Personal/Family`) keep `group_by_category: false` so a DICOM series and its cover letter are not split across `Media/Images` and `Docs`. Set per context; the flag defaults to true.

- 🐛 **FIX**: Context-based destinations repeated their own folder name, up to three times. `/Volumes/home/canamac/Desktop/BitPim.app` planned as `Desktop/Desktop/Desktop/BitPim.app`. Three causes, all now fixed: the semantic patterns carry surrounding slashes (`/desktop/`), so `Path(...).parts` began with `"/"` and the slice meant to skip the matched directory skipped the root separator instead; `root_folder` was added even when it duplicated the context destination; and a destination could already spell out folders the preserved tail repeated (`Personal/Disability/VA` + a tail starting `VA/`). Verified against 200 real files from the NAS.
- 🐛 **FIX**: The general planning branch discarded each file's directory structure and kept only the filename, so every file of a category resolved into one folder. Same-named files then collided and the executor skipped all but the first — a controlled test put 9 photos from 3 albums in and got 3 files out. It now preserves the path under the category folder, matching what the backup/web/code/application branches already did. This branch handles **1,849,594** classified files, including 1,086,984 in `data` and 275,287 in `image`.
- 🐛 **FIX**: `/personal/` was a pattern of both the priority-100 "Personal - Disability/VA" context and the priority-80 "Personal" context. Contexts are sorted by priority and the first match returns, so the priority-80 rule was unreachable and every personal file — tax returns, family photos — was filed as medical. Also dropped `/va/`: two letters between slashes matches far more than VA records.
- 🔧 **REMOVED**: `config/folder_mappings.yaml`. It read like configuration but was never loaded — `folder_mapping.py` contains no YAML parser, and the live mapping is a hardcoded dict. Its 229 lines of glob patterns (security-camera clips, movies, TV shows) had never matched anything, and it disagreed with the dict that does run.
### 🐛 Fixes
- 🐛 **FIX**: Re-running a scan with `--use-db` planned every already-classified file as **unclassified**. The resume path used a bulk query to skip files that already had a classification, but only asked *whether* one existed — it never read the category back onto the `FileInfo`. The per-file `classify_file(use_db=True)` it replaced did (`file_info.type = existing[0]`), so the bulk rewrite silently dropped every cached category. On a re-scan of an already-indexed folder this meant 100 of 100 planned rows had no type. `get_classified_paths()` is now `get_classified_categories()` and returns `{path: category}`.

- 🐛 **FIX**: Atomic packages (`.app`, `.framework`, bundle-style `.pkg`) never arrived at the destination. The scanner correctly hands them over whole — it does not descend into them — but `execute_plan()` called `shutil.copy2` unconditionally, which raises `IsADirectoryError` on a directory. The bundle was counted as an error and skipped while the run still reported success. Bundles now copy with `shutil.copytree(..., symlinks=True)`; preserving symlinks matters because a `.framework`'s `Versions/Current` is a link, and resolving it both duplicates the payload and produces a bundle that no longer matches the original.
### 🗑️ Duplicate deletion, undo, and companion protection
- ✨ **NEW**: Duplicates can now be deleted from the Duplicates tab — by **moving them to the Trash**, never unlinking. The Trash used is the one on the file's *own* volume (`/Volumes/<vol>/.Trashes/<uid>/`), so removing a 40 GB video from the NAS is a rename rather than a copy across the network onto the boot disk.
- ✨ **NEW**: **Put back last batch** restores the most recent deletion to its original paths, driven by the `operations` log. Restore refuses rather than overwrites if something already occupies the original path.
- ✨ **NEW**: A **review-and-commit step**. Saving a duplicate decision has never deleted anything and still doesn't; deletion happens once, from a summary showing exactly how many files and how many bytes, behind a typed `TRASH THEM` confirmation. Deletion is refused outright when the database is down, since an unlogged deletion cannot be undone.
- ✨ **NEW**: `utils/protected.py` — companion files are never offered for deletion even when byte-identical. This covers files inside a media-named directory (`lecture.mp4/…`) and, the case that actually occurs in this data, browser *Save Page Complete* asset folders: `SENG520_Wk4_1 of 4.mp4_files/odsp.knockout.lib-*.js`. Those scripts are identical across every saved page, so they look like perfect duplicates while each copy is what makes its own page work. On the 148 groups already resolved here, this excludes **136 of 467 files** that would otherwise have been trashed.
- 🐛 **FIX**: The confirmation endpoint issued one `WHERE hash = ?` per resolved group. `files.hash` is unindexed, so each was a full scan of ~7.7M rows — at 148 groups the endpoint never returned. Now a single batched query: **5.5s** instead of exceeding two minutes.
- ✨ **NEW**: `database/migrations/004_add_files_hash_index.sql` — indexes `files.hash`, **applied 2026-08-19**. Grouping and filtering by hash is the core access pattern of the whole duplicate feature, including `detect_duplicates()` on every `--use-db` run, and `EXPLAIN` previously reported a full scan. Built online in 17s with `ALGORITHM=INPLACE, LOCK=NONE` (explicit, so MySQL refuses rather than silently locking the table); index size 2.17 → 2.84 GB. A hash lookup went from scanning ~7.4M rows to `cost=4.4 rows=4` — 0.3 ms — and the confirmation endpoint from never returning, to 5.5s batched, to **0.31s**.
- 🔧 **REMOVED**: `config/folder_mappings.yaml` — actually removed this time. The previous commit claimed it but the deletion was reverted by an intervening stash.

### 🔌 Mount preflight
- ✨ **NEW**: `utils/mounts.py` — the CLI now verifies `/Volumes/home` and `/Volumes/homes` are mounted before a run, and mounts them from `smb://canome/...` if they are not. Mounting goes through `osascript ... mount volume`, so it uses the login Keychain: no credential is read, stored, or logged by this project, and no `sudo` is required.
- ✨ **NEW**: A path under `/Volumes` that is *not* a mount point now aborts the run, from the CLI and the web UI alike. This is the failure worth guarding: an unmounted `/Volumes/home` is an ordinary empty directory, so a scan "succeeds" over nothing and — with `--use-db` — records a volume that appears to have lost every file. With `--execute` it is worse, because the destination also resolves locally and files are copied onto the boot disk. The check is `os.path.ismount()`, not `path.exists()`.
- ✨ **NEW**: `--show-mounts` prints the state of each required volume; `--no-auto-mount` checks without mounting; `WORKBENCH_MOUNT_HOST`, `WORKBENCH_MOUNT_SCHEME` and `WORKBENCH_NO_AUTOMOUNT` override the defaults without editing code.
- 🔧 Mount failures are reported with the OSStatus code translated into what to check — `-5016` (server unreachable or wrong share name) and `-128` (no saved Keychain credentials) being the two that actually occur.

## [v0.11.0] – 2026-08-17

### 🚀 Major Features

#### **File Workbench — one application over three**
`doc-classifier` and `File_Classifier` are absorbed into this project. All three
used to walk the same files with their own scanner, storage, and interface.
- ✨ **NEW**: Web front end (`server/`, `web/`) — Run, Duplicates, Dup Trees, Plan, and Jobs screens. Start it with `./.venv/bin/python -m server.app`; it binds to localhost only and picks the first free port from 8000
- ✨ **NEW**: `core/pipeline.py` — the pipeline as a callable library. `core/main.py` is now argument parsing and terminal output only, so the CLI and the browser drive identical code and cannot drift apart. Organization plans are byte-identical to v0.10.0
- ✨ **NEW**: `classify/` — text extraction, image captioning/OCR, and the classification ladder, ported from `doc-classifier` and `File_Classifier`
- ✨ **NEW**: `search/` — RAG index and user metadata, ported from `doc-classifier`
- ✨ **NEW**: Jobs run in spawned child processes with progress over a queue, cooperative cancellation, and a reconnect-safe event stream. Plans are written to `.workbench/jobs/<id>/` rather than held in the API process, so a multi-million-row plan can be paged and executed later
- 📘 **NEW**: `WORKBENCH.md` — the application's own guide

#### **Interactive duplicate review**
- ✨ **NEW**: Tick which copies of a duplicate group to keep (one or more) and save. The group is settled, leaves the review list, and **future runs apply the decision automatically** — `core/deduplicator.py` consults `duplicate_resolutions` before marking anything
- ✨ **NEW**: `duplicate_resolutions` table (`hash`, `kept_paths`, `resolved_at`)

#### **Dup Trees explorer**
- ✨ **NEW**: The whole database's duplicates as a navigable directory tree — drill into any folder for duplicate ratios, sizes, and which other trees hold the originals
- ✨ **NEW**: Aggregations run on a worker thread and cache for 15 minutes; the endpoint returns `{status: "computing"}` and the client polls, so the request never blocks
- ✨ **NEW**: Folder picker (`/api/fs/dirs`) for choosing scan and destination directories in the UI

### ⚡ Performance

#### **Stage-aware parallelism**
- ✨ **NEW**: `core/parallel.py` — one policy table sizing each stage to what actually limits it. Classification, tagging, and image metadata previously ran **one file at a time**; they now use worker processes sized to the machine's performance cores
- ✨ **NEW**: A process pool is only built when it pays. A short serial sample measures the real per-item cost first — forcing a pool over trivial work is *slower* (measured: 8,000 small files, 0.12s serial vs 0.27s pooled), while genuinely expensive work sees ~8x. A stage reported as serial is doing the right thing
- ✨ **NEW**: `--show-parallelism` prints the per-stage sizing; `WORKBENCH_<STAGE>_WORKERS` overrides any of it
- 🔧 `--workers` now applies to hashing only, and its default is derived from the machine rather than fixed at 4
- ✨ **NEW**: Bulk database helpers (`get_file_ids`, `get_classified_paths`, `save_classifications_bulk`, `save_file_tags_bulk`). The per-file pattern issued one query per file — and one more per tag — which dominated the wall clock at this inventory's scale once the CPU stages were parallel

#### **Whole-database duplicate totals**
- 🐛 **FIX**: The Dup Trees banner aggregated over every row in `files` synchronously, hanging the request for minutes on a large database. It now uses the same background-and-poll path as the tree itself
- ✨ **NEW**: `database/migrations/003_add_files_duplicate_index.sql` — a covering `(is_duplicate, size)` index so that aggregate is an index-only scan instead of a walk of the clustered index. Safe to apply while a run is in progress (MySQL 8 online DDL)

### 🤖 Classification Ladder
- ✨ **NEW**: Three tiers, cheapest first, each seeing only what the tier below could not place: rules → local Ollama (`--llm-classify`) → Claude (`--cloud-classify`)
- ✨ **NEW**: The cloud tier is bounded, not open-ended — `--cloud-cost-limit` (default $1.00) is checked against a pre-flight estimate *and* enforced against real token usage as the run proceeds. Without `ANTHROPIC_API_KEY` the tier disables itself and the run continues on the free tiers
- ✨ **NEW**: `--cloud-model` (default `claude-opus-5`, also honours `CLOUD_MODEL`)

### 🛡️ Safety
- 🔧 Execution **copies**; sources are never removed, so a run is undone by deleting the destination. The UI requires a typed confirmation phrase, and existing destination files are skipped rather than overwritten
- ✨ **NEW**: Deny-by-default path guards — system directories are refused as scan roots, and file preview is restricted to files present in that job's own plan
- 🐛 **FIX**: `safe_output_dir()` let `PermissionError` escape from `mkdir`, so a denied destination surfaced as a 500 instead of a readable message

### 📘 Documentation
- ✨ **NEW**: User guide section 5 "The Web Interface (File Workbench)" and 4.2 "How the Work Is Parallelised" (17 → 21+ pages)
- ✨ **NEW**: `WORKBENCH.md`; README lists the new packages in its structure tree

### ♻️ Classification Resume + Email Rules
- ✨ **NEW**: Classification resumes across runs — files that already have a classification row are skipped (no rule re-work and, critically, no repeat LLM calls). Force a redo with `scripts/reclassify_files.py`.
- ✨ **NEW**: Email/message archive extensions (`.emlx`, `.olk14Message`, `.olk15Message`, `.olk15MsgSource`, `.ichat`) now classify by rule as "data" — previously each fell through to the LLM at ~0.4s per message (observed: ~2 days of GPU time on one 7.5M-file run's mail stores).

### ⚡ Performance

#### **Fixed O(n²) classification slowdown (missing index)**
- 🐛 **FIX**: `classifications.file_id` had no index, so `save_classification()` full-table-scanned the classifications table for every file — throughput on a 7.5M-file run decayed from ~417k files/day to ~128k/day
- ✨ **NEW**: `database/migrations/002_add_classifications_file_id_index.sql` (safe to apply while a run is in progress — MySQL 8 online DDL)
- 🔧 `Classification.file_id` model column now declares `index=True` for fresh deployments

### 🛡️ Resilience

#### **Database Circuit Breaker + Fail-Fast Execution**
- ✨ **NEW**: After 3 consecutive DB failures mid-run, a circuit breaker trips — one clear error, then all DB helpers become instant no-ops (no per-file timeout stalls); dry runs still complete
- ✨ **NEW**: `--execute` is refused after a trip; an in-progress execution stops cleanly before its next file move (operations are never performed unlogged)
- 🔧 DB connection attempts bounded to 5 seconds (`connect_timeout`)

### 📘 Documentation
- ✨ **NEW**: User guide section 2 "Before You Run: Pitfalls and Red Alerts" — execution copies (not moves), base-dir placement, duplicate-detection blind spots, hidden-file skips, resume requirements, operational cautions
- 🔧 README: "Before You Run" warning summary; fixed the basic example, which placed `--base-dir` inside the scanned tree

## [v0.10.0] – 2026-07-20

### 🚀 Major Features

#### **Local LLM Classification Fallback**
- ✨ **NEW**: `--llm-classify` flag — files that fall through every rule-based tier are classified by a local Ollama model (default `llama3.1:8b`)
  - Uses filename, path context, and a 1KB content snippet for text-like files; binary content detected and skipped
  - Structured output constrained to the known category enum — the model cannot invent categories
  - Per-run cache keyed by content hash: duplicates cost one LLM call
  - LLM confidence persisted to the database instead of the fixed 0.8
  - Degrades gracefully when the Ollama server is unreachable
  - Configure via `OLLAMA_HOST` / `LLM_MODEL` in `.env`

#### **Parallel, Resumable Hashing**
- ✨ **NEW**: `--workers N` (default 4) — SHA256 hashing runs on a thread pool; large speedup on network volumes
- ✨ **NEW**: `--batch-size N` (default 500) — periodic checkpoint summaries during hashing
- ✨ **NEW**: Resume from the database cache — unchanged files (path + mtime match) are skipped without reading a byte, logged as `(cached)`
- 🐛 **FIX**: `get_cached_hash()` existed but was never called — restarts re-hashed everything
- 🐛 **FIX**: mtimes are normalized to whole seconds; MySQL DATETIME truncation silently defeated the cache equality check
- ✨ **NEW**: Graceful Ctrl+C — interrupted runs exit cleanly, report persisted progress, and resume on re-run

#### **Scan Progress Heartbeat**
- ✨ **NEW**: Long directory walks log progress every 10 seconds (files matched, directories visited, current directory)
- ✨ **NEW**: Completion summary with totals and elapsed time

#### **Documentation & Repository**
- ✨ **NEW**: `docs/USER_GUIDE.pdf` — full user guide (every switch with examples, project structure, versioning, git workflow); regenerate with `python scripts/generate_user_guide.py`
- 🔧 Repository restructure: docs into `docs/`, SQL into `database/{schema,migrations,queries}`, tests into `tests/`, requirements split (`requirements-ai.txt` for the CLIP stack)
- 🔧 Activated the 100MB pre-commit size guard (hook was never executable)
- 🔧 Version streams unified: `version.yaml`/`setup.py` (0.4.11) and CHANGELOG/`main.py` (0.9.0) now both track v0.10.0

## [v0.9.0] – 2025-11-21

### 🚀 Major Features

#### **AI Tagging for ALL File Types**
- ✨ **NEW**: `AITagger` class generates intelligent tags for all files (not just images)
  - Semantic context detection (Personal/Disability/VA, Work, Education)
  - Path structure analysis (directory names, parent folders)
  - Filename analysis (extracts meaningful keywords)
  - File metadata tags (dates, categories, owners)
  - Temporal tags (years, decades)
- ✨ **NEW**: `file_tags` database table for unified tag storage
  - Tracks tag source: `ai_tagger`, `image_content`, `semantic_context`, `manual`
  - Confidence scoring for each tag
  - Database views for tag statistics and file queries
- ✨ **NEW**: Tags automatically generated during file classification
  - Example: `/Work/Projects/Python/web_scraper.py` → tags: "Work", "Projects", "Python", "Scraper", "Code"

#### **File Type Filtering System**
- ✨ **NEW**: `--file-types` CLI parameter for selective scanning
  - Filter by file type groups: `images`, `videos`, `audio`, `docs`, `word_docs`, `presentations`, etc.
  - 20+ predefined groups in `config/file_type_groups.yaml`
  - Hierarchical support: `media` includes `images`, `videos`, `audio`
  - Comma-separated multiple types: `--file-types images,videos`
- ✨ **NEW**: `--list-file-types` flag to display all available groups
- ✨ **NEW**: `FileTypeFilter` utility class for group management
  - Recursive group resolution
  - Extension aggregation
  - Group descriptions and examples

#### **Enhanced Image Content Analysis**
- ✨ **IMPROVED**: Image AI tags now saved to unified `file_tags` table
  - Tags from CLIP model stored with source = `image_content`
  - Combined with path-based semantic tags for comprehensive tagging
  - Confidence scoring (0.85 for image content, 0.9 for semantic tags)

### 🐛 Critical Bug Fixes

#### **Directory Structure Organization**
- 🔧 **FIXED**: Root folder double-nesting bug
  - Before: `/organized/Documents - 42739/Documents - 42739/Media/Images/...`
  - After: `/organized/Documents - 42739/Media/Images/...`
  - Added `_should_add_root_folder()` helper to prevent duplication
  - Checks if base_dir already contains the root folder name
- 🔧 **FIXED**: Path metadata extraction priority
  - Now prioritizes backup-style folders ("Documents - 42739") over standalone ("Documents")
  - Two-pass search: first for patterns with dashes, then for standalone folders
- 🔧 **FIXED**: Semantic context pattern conflict
  - Disabled "Archives/Documents" semantic context that was overriding file-type classification
  - Files from backup machines now organized by file type instead of being forced to Archives/
  - Pattern `/documents - 42739/` was matching and sending all files to Archives/

### 📝 New Files Created

**Core Modules:**
- `core/ai_tagger.py`: AI-powered semantic tagger for all file types
- `core/ai_tagger.py`: Generates tags from multiple sources (context, path, metadata, filename)

**Database:**
- `database/migrations/add_file_tags_table.sql`: Schema for unified tag storage
- `database/migrations/cleanup_wrong_classifications.sql`: Removes incorrect archive classifications
- `database/migrations/reset_all_classifications.sql`: Complete classification reset script

**Configuration:**
- `config/file_type_groups.yaml`: Defines 20+ file type groups with hierarchical support

**Utilities:**
- `utils/file_type_filter.py`: Utility for loading and parsing file type groups

**Debug Tools:**
- `debug_classification.py`: Debug script for testing file classification

### 🔄 Modified Files

**Core Modules:**
- `main.py` v0.9.0
  - Added AI tagging workflow for all files (after classification)
  - Added `--file-types` and `--list-file-types` CLI parameters
  - Integrated `FileTypeFilter` for extension filtering
  - Image content tags now saved to `file_tags` table
- `core/organizer.py` v0.9.0
  - Added `_should_add_root_folder()` helper function
  - Updated all planning functions to use helper (prevents double-nesting)
  - Applied fix to: regular files, web projects, backups, code, applications, contexts, video subcategories
- `core/scanner.py` v0.7.0
  - Added `allowed_extensions` parameter to `scan_directory()`
  - Extension filtering applied during scan (more efficient)
  - Logs filtered file type groups and extension counts
- `core/db.py` v0.6.0
  - Added `FileTag` ORM model
  - Added `save_file_tags()` function for bulk tag insertion
  - Added `get_file_tags()` function for tag retrieval
  - Handles duplicate tags and confidence updates

**Utility Modules:**
- `utils/path_metadata.py` v0.2.0
  - Fixed `extract_path_metadata()` to prioritize backup-style folders
  - Two-pass search algorithm (with dash first, then without)

**Configuration:**
- `config/semantic_paths.yaml`
  - Disabled "Archives/Documents" semantic context (commented out)
  - Added explanation of why it was disabled
  - Preserved for future reference if needed

### 📊 Performance & Impact

**Tag Generation:**
- All files receive intelligent semantic tags
- Tags searchable via database queries
- Average 3-7 tags per file

**Organization Accuracy:**
- 100% fix rate for directory structure bugs
- Files now correctly organized by file type
- No more unwanted Archives/ classification

**Filtering Performance:**
- Scanning only desired file types significantly faster
- Example: `--file-types images` on mixed directory = 5x faster

### 🧪 Testing Performed

✅ Path metadata extraction (prioritizes "Documents - 42739" over "Documents")
✅ Root folder helper prevents double-nesting
✅ File type filtering with multiple groups
✅ AI tagger generates tags from all sources
✅ Database tag storage and retrieval
✅ Image content tags saved to file_tags table
✅ Semantic context pattern disabled correctly
✅ Files organized to correct directories (Media/Images, Docs/Word, etc.)

### 🎓 Migration Instructions

1. **Add file_tags table** (required for tag storage):
```bash
mysql -u your_user -p < database/migrations/add_file_tags_table.sql
```

2. **Clean up stale classifications** (optional but recommended):
```bash
# Remove wrong "archive" classifications from previous buggy runs
mysql -u your_user -p < database/migrations/reset_all_classifications.sql
```

3. **Remove incorrectly organized files** (if they exist):
```bash
rm -rf "/organized/Documents/Documents - 42739/Archives"
```

### 💡 Usage Examples

**Scan only images with AI tagging:**
```bash
python main.py /source --base-dir /organized \
  --use-db --analyze-images --ai-tagging \
  --file-types images --execute
```

**List available file type groups:**
```bash
python main.py --list-file-types
```

**Scan multiple file types:**
```bash
python main.py /source --base-dir /organized \
  --use-db --file-types images,videos,docs --execute
```

**Query tags in database:**
```sql
-- View all tags for a file
SELECT f.path, ft.tag, ft.tag_source, ft.confidence
FROM files f
JOIN file_tags ft ON f.id = ft.file_id
WHERE f.path LIKE '%example.jpg%';

-- Tag statistics
SELECT * FROM tag_statistics
ORDER BY usage_count DESC LIMIT 20;
```

### 📈 Statistics

**Lines Changed:**
- main.py: ~40 lines added
- core/organizer.py: ~50 lines modified
- core/scanner.py: ~15 lines modified
- core/db.py: ~80 lines added
- utils/path_metadata.py: ~20 lines modified
- config/semantic_paths.yaml: ~20 lines commented

**New Files:**
- core/ai_tagger.py: 300 lines
- database/migrations/*: 3 new SQL files
- config/file_type_groups.yaml: 313 lines
- utils/file_type_filter.py: 162 lines

**Total Impact:**
- ~980 lines added/modified
- 7 new files created
- 6 existing files modified
- 100% backwards compatible
- 3 critical bugs fixed

---

## [v0.8.0] – 2025-11-14

### 🚀 Major Performance Enhancement

#### **Atomic Package Detection**
- ✨ **NEW**: Automatic detection and handling of macOS packages as single units
  - Treats `.app`, `.pkg`, and `.dmg` files as atomic packages
  - Stops scanning at package boundary instead of recursing into thousands of internal files
  - Hashes entire package directory as single unit for consistent duplicate detection
  - Delivers **18-60x performance improvement** when scanning directories with applications

#### **Smart Directory Hashing**
- ✨ **NEW**: `hash_directory()` function for consistent package hashing
  - Recursively hashes all files within a directory in deterministic order
  - Includes relative file paths in hash for structural integrity
  - Produces consistent SHA256 hash regardless of scan order
  - Same package always generates identical hash for reliable duplicate detection

#### **Enhanced Scanner**
- ✨ **NEW**: `is_atomic_package()` detection function
  - Automatically identifies .app, .pkg, and .dmg extensions
  - Tracks processed paths to prevent duplicate scanning
  - Logs atomic packages found during scan
  - Example: `HP Easy Start.app` with 2,500 internal files scanned as 1 unit

### 📊 Performance Impact

**Real-world example:**
```
HP Easy Start.app (250MB, 2,500 files)
- Without atomic detection: ~5 minutes
- With atomic detection: ~5 seconds
- Speedup: 60x faster!

/Applications directory (100 apps)
- Before: 45 minutes (45,000+ files)
- After: 2.5 minutes (150 items)
- Improvement: 18x faster!
```

### 🧪 Testing

- ✨ **NEW**: Comprehensive test suite (`test_atomic_packages.py`)
  - Test 1: Atomic package detection (.app, .pkg, .dmg)
  - Test 2: Scanner skips internal files
  - Test 3: Directory hashing consistency
  - Test 4: End-to-end pipeline verification

### 📝 Documentation

- ✨ **NEW**: [ATOMIC_PACKAGES_GUIDE.md](ATOMIC_PACKAGES_GUIDE.md) - Complete guide to atomic package handling
  - How atomic packages work
  - Performance comparisons
  - Usage examples
  - Troubleshooting guide
  - Technical implementation details

### 🔧 Code Changes

- **core/scanner.py v0.6.0**
  - Added `is_atomic_package()` function
  - Modified `scan_directory()` to detect and skip atomic package internals
  - Added tracking for processed paths to avoid duplicates
  - Enhanced logging for atomic packages

- **core/hasher.py v0.6.0**
  - Added `hash_directory()` function for directory hashing
  - Modified `generate_hashes()` to detect directories vs files
  - Added support for hashing entire packages as single units
  - Calculates total package size for metadata-only threshold

---

## [v0.7.0] – 2025-11-13

### 🎯 Major Features Added

#### **Intelligent File Size Management**
- ✨ **NEW**: `--metadata-only-size` CLI parameter for handling large files efficiently
  - Accepts human-readable sizes: `75MB`, `1GB`, `500KB`, etc.
  - Files above threshold are tracked with metadata only (no hashing)
  - Files below threshold are fully hashed for deduplication
  - Configurable per-scan for maximum flexibility

#### **Database Schema Enhancement**
- ✨ **NEW**: Added `metadata_only` boolean column to `files` table
  - Tracks which files were processed metadata-only vs. fully hashed
  - Includes database migration script: `migrations/001_add_metadata_only_column.sql`
  - Backwards compatible with existing databases

#### **Massive File Classification Improvements**
- ✨ **NEW**: Expanded from **10 to 18 categories** (+80% increase)
- ✨ **NEW**: Support for **250+ file types** (+400% increase)
- ✨ **NEW**: 8 additional file categories:
  - `font`: Typography files (.ttf, .otf, .woff, .woff2, etc.)
  - `installer`: Executables and packages (.exe, .dmg, .pkg, .apk, .msu, etc.)
  - `certificate`: Security certificates (.p7b, .cer, .pem, .key, etc.)
  - `shortcut`: Links and shortcuts (.lnk, .webloc, .rdp, etc.)
  - `scientific`: Research data (.mat, .hdf5, .npy, .fits, etc.)
  - `backup`: Backup files (.bak, .old, .swp, etc.)
  - `temporary`: Temp/download files (.tmp, .crdownload, .cache, etc.)
  - `system`: Config and macOS files (.plist, .strings, Makefile, etc.)

### 📈 Enhanced Existing Categories

#### **Code Category** (+40 new languages)
- Added: Rust, Swift, Kotlin, Scala, PowerShell, TypeScript, Dart
- Added: Lisp family (.lisp, .cl, .scm, .el, .clj)
- Added: Functional languages (Haskell, OCaml, Erlang, Elixir)
- Added: Scientific languages (R, MATLAB, Julia, Fortran)
- Added: Shell scripts (.bash, .zsh, .bat, .cmd, .ps1)

#### **Archive Category** (+10 new formats)
- Added: Disk images (.iso, .dmg, .img)
- Added: Virtual machine formats (.vhd, .vmdk, .ova, .ovf, .qcow2)
- Added: Additional compression (.xz, .lzma, .sitx, .ace, .arj)

#### **Image Category** (+10 new formats)
- Added: RAW camera formats (.cr2, .nef, .dng, .raw)
- Added: Design files (.psd, .ai, .eps, .indd)
- Added: Modern formats (.heic, .heif, .webp)

#### **Video Category** (+7 new formats)
- Added: Broadcast formats (.ts, .mts, .m2ts, .vob)
- Added: Mobile and streaming (.3gp, .ogv, .m4v)

#### **Audio Category** (+5 new formats)
- Added: Lossless formats (.opus, .ape, .alac, .aiff)
- Added: MIDI music files (.mid, .midi)

#### **Document Category** (+5 new formats)
- Added: Academic papers (.tex for LaTeX)
- Added: E-books (.epub, .mobi, .azw, .djvu)
- Added: Apple Pages documents (.pages)

#### **Spreadsheet Category** (+2 new formats)
- Added: Apple Numbers (.numbers)
- Added: Tab-separated values (.tsv)

#### **Presentation Category** (+1 new format)
- Added: Apple Keynote (.key)

#### **Data Category** (+8 new formats)
- Added: Configuration files (.toml, .ini, .conf, .cfg)
- Added: Database files (.sqlite, .db, .mdb, .accdb)
- Added: SQLite temp files (.sqlite-wal, .sqlite-shm)
- Added: Generic data files (.dat, .data)

### 🐛 Bug Fixes

#### **macOS File Type Recognition**
- 🔧 Fixed: Unknown MIME type warnings for macOS `.strings` files
- 🔧 Fixed: Unrecognized `.plist`, `.nib`, `.xib`, `.storyboard` files
- 🔧 Fixed: macOS app bundle files (CodeResources, Info.plist, etc.)
- 🔧 Fixed: Files inside `/Contents/MacOS/`, `/Contents/PlugIns/`, `/Contents/Resources/`
- 🔧 Fixed: macOS alias files now properly classified as shortcuts

#### **GUI Error Handling**
- 🔧 Fixed: PySimpleGUI crash when `theme()` method unavailable
- 🔧 Added: Graceful fallback when PySimpleGUI not installed
- 🔧 Added: Comprehensive error handling with helpful installation instructions
- 🔧 Added: Compatibility with both old and new PySimpleGUI API versions

### 📝 Documentation

- 📄 **NEW**: `CLASSIFICATION_IMPROVEMENTS.md` - Comprehensive guide to all 250+ file types
- 📄 Updated: `README.md` with new features and CLI options
- 📄 Updated: `CHANGELOG.md` cleaned up and reorganized
- 📄 **NEW**: `migrations/001_add_metadata_only_column.sql` - Database migration script

### 🧪 Testing

- ✅ Tested: Metadata-only size filtering with 75MB threshold
- ✅ Tested: Files above/below threshold processed correctly
- ✅ Tested: Database migration on existing database
- ✅ Verified: Classification improvements reduce "other" category by ~90%

### 🔄 Changed Files

**Core Modules:**
- `main.py`: Added `--metadata-only-size` parameter and `parse_size()` function
- `core/hasher.py`: Added `metadata_only_size` parameter and size checking logic
- `core/db.py`: Added `metadata_only` column and updated `cache_file_entry()`
- `core/classifier.py`: Complete rewrite with 250+ file type support

**Utility Modules:**
- `utils/gui.py`: Enhanced error handling and updated statistics display

**Database:**
- `migrations/001_add_metadata_only_column.sql`: New migration script

**Documentation:**
- `CLASSIFICATION_IMPROVEMENTS.md`: New comprehensive classification guide
- `README.md`: Updated with new features
- `CHANGELOG.md`: Cleaned and updated

### 💡 Performance Improvements

- ⚡ Files larger than threshold skip expensive hashing operation
- ⚡ Significantly reduced processing time for large file collections
- ⚡ Reduced "unknown type" warnings by ~90%
- ⚡ More accurate file organization with expanded categories

### 🎓 Migration Notes

If you have an existing database, run the migration:

```bash
cd migrations
mysql -u your_user -p your_database < 001_add_metadata_only_column.sql
```

Or let SQLAlchemy auto-create the column on next run with `--use-db`.

### 📊 Impact

**Before v0.7.0:**
- 10 categories
- ~50 file types supported
- High "other" classification rate

**After v0.7.0:**
- 18 categories (+80%)
- 250+ file types supported (+400%)
- ~90% reduction in "other" classifications
- Intelligent large file handling

---

## [v0.4.6] – 2025-11-06

### Added
- 🔖 Automated release versioning

---

## [v0.4.5] – 2025-11-06

### Added
- ✅ Added all `utils` modules:
  - `utils/cache.py`
  - `utils/notifications.py`
  - `utils/versioning.py`
  - `utils/gui.py`
  - `utils/__init__.py`
- ✅ Restored `core/organizer.py` with planning logic

### Fixed
- 🐛 Resolved missing imports and broken features due to incomplete files

### Changed
- 🔧 Code cleanup and structure compliance

---

## [v0.4.3] – 2025-11-06

### Added
- 🗑️ Removed `.scan_cache.json` from Git history
- 🧹 Added cleanup scripts:
  - `force_clean_push.sh`
  - `validate_large_files.sh`
- Both assist in cleaning up git push and restricting large files

---

## [v0.4.2] – 2025-11-06

### Added
- 🗑️ Removed `.scan_cache.json` from Git history
- 🧹 Cleaned up repo and added `.gitignore` for cache files
- ✅ Completed version/release workflow integration

---

## [v0.4.0] – 2025-11-04

### Added
- `scripts/update_core.sh`: Now validates extracted Python file syntax after unzip
- `scripts/rollback_core.sh`: Allows restoring the most recent core/ backup
- JSON log support and dry-run change preview from CLI
- Optional directory filtering via `--filter` using multiple values and regex

### Changed
- `core/hasher.py`: Checks and stores hashes using MySQL caching layer
- `core/scanner.py`: Skips rescanning files whose size & mtime match cache
- `core/executor.py`: Logs file move/delete operations to MySQL

### Fixed
- ZIP generation now correctly flattens core files for proper extraction
- Updated `update_core.sh` to prevent `core/core/` nesting errors

### Security
- `.env` now securely stores OpenAI API key and MySQL credentials

### Core System Update
- Integrated MySQL-based deduplication cache and operation logging
- Enhanced ZIP packaging to flatten files correctly during deploy
- Added syntax-checking to core update script for safe merges
- Introduced directory-level filtering using regex in main.py
- `rollback_core.sh` script added to enable easy restoration of last known good state
- `CHANGELOG.md` created for versioned tracking of features and patches

---

## [v0.3.0] – 2025-11-04

### Added
- Initial release with core deduplication features
- File scanning and hashing
- Basic file classification
- Database integration
- Slack notifications

---

[Unreleased]: https://github.com/yourusername/File_Deduplification/compare/v0.7.0...HEAD
[v0.7.0]: https://github.com/yourusername/File_Deduplification/compare/v0.4.6...v0.7.0
[v0.4.6]: https://github.com/yourusername/File_Deduplification/compare/v0.4.5...v0.4.6
[v0.4.5]: https://github.com/yourusername/File_Deduplification/compare/v0.4.3...v0.4.5
[v0.4.3]: https://github.com/yourusername/File_Deduplification/compare/v0.4.2...v0.4.3
[v0.4.2]: https://github.com/yourusername/File_Deduplification/compare/v0.4.0...v0.4.2
[v0.4.0]: https://github.com/yourusername/File_Deduplification/compare/v0.3.0...v0.4.0
[v0.3.0]: https://github.com/yourusername/File_Deduplification/releases/tag/v0.3.0
## [v0.7.0]
– 2025-11-13

### 🎯 Major Features Added

#### **Intelligent File Size Management**
- ✨ **NEW**: `--metadata-only-size` CLI parameter for handling large files efficiently
  - Accepts human-readable sizes: `75MB`, `1GB`, `500KB`, etc.
  - Files above threshold are tracked with metadata only (no hashing)
  - Files below threshold are fully hashed for deduplication
  - Configurable per-scan for maximum flexibility

#### **Database Schema Enhancement**
- ✨ **NEW**: Added `metadata_only` boolean column to `files` table
  - Tracks which files were processed metadata-only vs. fully hashed
  - Includes database migration script: `migrations/001_add_metadata_only_column.sql`
  - Backwards compatible with existing databases

#### **Massive File Classification Improvements**
- ✨ **NEW**: Expanded from **10 to 18 categories** (+80% increase)
- ✨ **NEW**: Support for **250+ file types** (+400% increase)
- ✨ **NEW**: 8 additional file categories:
  - `font`: Typography files (.ttf, .otf, .woff, .woff2, etc.)
  - `installer`: Executables and packages (.exe, .dmg, .pkg, .apk, .msu, etc.)
  - `certificate`: Security certificates (.p7b, .cer, .pem, .key, etc.)
  - `shortcut`: Links and shortcuts (.lnk, .webloc, .rdp, etc.)
  - `scientific`: Research data (.mat, .hdf5, .npy, .fits, etc.)
  - `backup`: Backup files (.bak, .old, .swp, etc.)
  - `temporary`: Temp/download files (.tmp, .crdownload, .cache, etc.)
  - `system`: Config and macOS files (.plist, .strings, Makefile, etc.)

### 📈 Enhanced Existing Categories

#### **Code Category** (+40 new languages)
- Added: Rust, Swift, Kotlin, Scala, PowerShell, TypeScript, Dart
- Added: Lisp family (.lisp, .cl, .scm, .el, .clj)
- Added: Functional languages (Haskell, OCaml, Erlang, Elixir)
- Added: Scientific languages (R, MATLAB, Julia, Fortran)
- Added: Shell scripts (.bash, .zsh, .bat, .cmd, .ps1)

#### **Archive Category** (+10 new formats)
- Added: Disk images (.iso, .dmg, .img)
- Added: Virtual machine formats (.vhd, .vmdk, .ova, .ovf, .qcow2)
- Added: Additional compression (.xz, .lzma, .sitx, .ace, .arj)

#### **Image Category** (+10 new formats)
- Added: RAW camera formats (.cr2, .nef, .dng, .raw)
- Added: Design files (.psd, .ai, .eps, .indd)
- Added: Modern formats (.heic, .heif, .webp)

#### **Video Category** (+7 new formats)
- Added: Broadcast formats (.ts, .mts, .m2ts, .vob)
- Added: Mobile and streaming (.3gp, .ogv, .m4v)

#### **Audio Category** (+5 new formats)
- Added: Lossless formats (.opus, .ape, .alac, .aiff)
- Added: MIDI music files (.mid, .midi)

#### **Document Category** (+5 new formats)
- Added: Academic papers (.tex for LaTeX)
- Added: E-books (.epub, .mobi, .azw, .djvu)
- Added: Apple Pages documents (.pages)

#### **Spreadsheet Category** (+2 new formats)
- Added: Apple Numbers (.numbers)
- Added: Tab-separated values (.tsv)

#### **Presentation Category** (+1 new format)
- Added: Apple Keynote (.key)

#### **Data Category** (+8 new formats)
- Added: Configuration files (.toml, .ini, .conf, .cfg)
- Added: Database files (.sqlite, .db, .mdb, .accdb)
- Added: SQLite temp files (.sqlite-wal, .sqlite-shm)
- Added: Generic data files (.dat, .data)

### 🐛 Bug Fixes

#### **macOS File Type Recognition**
- 🔧 Fixed: Unknown MIME type warnings for macOS `.strings` files
- 🔧 Fixed: Unrecognized `.plist`, `.nib`, `.xib`, `.storyboard` files
- 🔧 Fixed: macOS app bundle files (CodeResources, Info.plist, etc.)
- 🔧 Fixed: Files inside `/Contents/MacOS/`, `/Contents/PlugIns/`, `/Contents/Resources/`
- 🔧 Fixed: macOS alias files now properly classified as shortcuts

#### **GUI Error Handling**
- 🔧 Fixed: PySimpleGUI crash when `theme()` method unavailable
- 🔧 Added: Graceful fallback when PySimpleGUI not installed
- 🔧 Added: Comprehensive error handling with helpful installation instructions
- 🔧 Added: Compatibility with both old and new PySimpleGUI API versions

### 📝 Documentation

- 📄 **NEW**: `CLASSIFICATION_IMPROVEMENTS.md` - Comprehensive guide to all 250+ file types
- 📄 Updated: `README.md` with new features and CLI options
- 📄 Updated: `CHANGELOG.md` cleaned up and reorganized
- 📄 **NEW**: `migrations/001_add_metadata_only_column.sql` - Database migration script

### 🧪 Testing

- ✅ Tested: Metadata-only size filtering with 75MB threshold
- ✅ Tested: Files above/below threshold processed correctly
- ✅ Tested: Database migration on existing database
- ✅ Verified: Classification improvements reduce "other" category by ~90%

### 🔄 Changed Files

**Core Modules:**
- `main.py`: Added `--metadata-only-size` parameter and `parse_size()` function
- `core/hasher.py`: Added `metadata_only_size` parameter and size checking logic
- `core/db.py`: Added `metadata_only` column and updated `cache_file_entry()`
- `core/classifier.py`: Complete rewrite with 250+ file type support

**Utility Modules:**
- `utils/gui.py`: Enhanced error handling and updated statistics display

**Database:**
- `migrations/001_add_metadata_only_column.sql`: New migration script

**Documentation:**
- `CLASSIFICATION_IMPROVEMENTS.md`: New comprehensive classification guide
- `README.md`: Updated with new features
- `CHANGELOG.md`: Cleaned and updated

### 💡 Performance Improvements

- ⚡ Files larger than threshold skip expensive hashing operation
- ⚡ Significantly reduced processing time for large file collections
- ⚡ Reduced "unknown type" warnings by ~90%
- ⚡ More accurate file organization with expanded categories

### 🎓 Migration Notes

If you have an existing database, run the migration:

```bash
cd migrations
mysql -u your_user -p your_database < 001_add_metadata_only_column.sql
```

Or let SQLAlchemy auto-create the column on next run with `--use-db`.

### 📊 Impact

**Before v0.7.0:**
- 10 categories
- ~50 file types supported
- High "other" classification rate

**After v0.7.0:**
- 18 categories (+80%)
- 250+ file types supported (+400%)
- ~90% reduction in "other" classifications
- Intelligent large file handling

---
## [v0.8.0]
– 2025-11-14

### 🚀 Major Performance Enhancement

#### **Atomic Package Detection**
- ✨ **NEW**: Automatic detection and handling of macOS packages as single units
  - Treats `.app`, `.pkg`, and `.dmg` files as atomic packages
  - Stops scanning at package boundary instead of recursing into thousands of internal files
  - Hashes entire package directory as single unit for consistent duplicate detection
  - Delivers **18-60x performance improvement** when scanning directories with applications

#### **Smart Directory Hashing**
- ✨ **NEW**: `hash_directory()` function for consistent package hashing
  - Recursively hashes all files within a directory in deterministic order
  - Includes relative file paths in hash for structural integrity
  - Produces consistent SHA256 hash regardless of scan order
  - Same package always generates identical hash for reliable duplicate detection

#### **Enhanced Scanner**
- ✨ **NEW**: `is_atomic_package()` detection function
  - Automatically identifies .app, .pkg, and .dmg extensions
  - Tracks processed paths to prevent duplicate scanning
  - Logs atomic packages found during scan
  - Example: `HP Easy Start.app` with 2,500 internal files scanned as 1 unit

### 📊 Performance Impact

**Real-world example:**
```
HP Easy Start.app (250MB, 2,500 files)
- Without atomic detection: ~5 minutes
- With atomic detection: ~5 seconds
- Speedup: 60x faster!

/Applications directory (100 apps)
- Before: 45 minutes (45,000+ files)
- After: 2.5 minutes (150 items)
- Improvement: 18x faster!
```

### 🧪 Testing

- ✨ **NEW**: Comprehensive test suite (`test_atomic_packages.py`)
  - Test 1: Atomic package detection (.app, .pkg, .dmg)
  - Test 2: Scanner skips internal files
  - Test 3: Directory hashing consistency
  - Test 4: End-to-end pipeline verification

### 📝 Documentation

- ✨ **NEW**: [ATOMIC_PACKAGES_GUIDE.md](ATOMIC_PACKAGES_GUIDE.md) - Complete guide to atomic package handling
  - How atomic packages work
  - Performance comparisons
  - Usage examples
  - Troubleshooting guide
  - Technical implementation details

### 🔧 Code Changes

- **core/scanner.py v0.6.0**
  - Added `is_atomic_package()` function
  - Modified `scan_directory()` to detect and skip atomic package internals
  - Added tracking for processed paths to avoid duplicates
  - Enhanced logging for atomic packages

- **core/hasher.py v0.6.0**
  - Added `hash_directory()` function for directory hashing
  - Modified `generate_hashes()` to detect directories vs files
  - Added support for hashing entire packages as single units
  - Calculates total package size for metadata-only threshold

---
