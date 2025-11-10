import hashlib
import logging
from utils.cache import save_cache

def generate_hashes(file_paths, use_db=False):
    hashed_files = []
    for path in file_paths:
        try:
            with open(path, "rb") as f:
                file_bytes = f.read()
                sha256 = hashlib.sha256(file_bytes).hexdigest()
                hashed_files.append((path, sha256))
                if use_db:
                    save_cache_if_enabled(path, sha256)
        except Exception as e:
            logging.warning(f"⚠️ Skipping {path}: {e}")
    return [path for path, _ in hashed_files]