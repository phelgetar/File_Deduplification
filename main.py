#!/usr/bin/env python3
# ... header and imports remain unchanged ...

def main():
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="Root source directory")
    parser.add_argument("--base-dir", required=True, help="Base output directory")
    parser.add_argument("--filter", nargs="*", help="Root-level directory name patterns to include")
    parser.add_argument("--dry-run-log", action="store_true", help="Log preview to file")
    parser.add_argument("--log-format", choices=["json", "txt"], default="json")
    parser.add_argument("--notify", choices=["email", "slack"])
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--write-metadata", action="store_true")
    parser.add_argument("--ignore-errors", action="store_true")
    parser.add_argument("--max-files", type=int, help="Maximum number of files to process (for testing)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    print("🔍 Scanning files...")
    files = scan_directory(args.source, filter_names=args.filter, max_files=args.max_files)
    print(f"🔎 Matched root folders: {set(p.parent for p in files)}")
    print(f"🧮 Files matched: {len(files)}")

    # ... remainder of main unchanged ...
