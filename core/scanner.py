from pathlib import Path

def scan_directory(root, filter_names=None, max_files=None):
    results = []
    root_path = Path(root)

    for p in root_path.rglob("*"):
        if p.is_file():
            if filter_names and not any(fn in str(p) for fn in filter_names):
                continue
            results.append(p)
            if max_files and len(results) >= max_files:
                break
    return results
