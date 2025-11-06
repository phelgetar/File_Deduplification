# utils/cache.py

import json
from pathlib import Path

def load_cache(cache_path: Path) -> dict:
    if cache_path.exists():
        with cache_path.open('r') as f:
            return json.load(f)
    return {}

def save_cache(cache_path: Path, data: dict):
    with cache_path.open('w') as f:
        json.dump(data, f, indent=2)
