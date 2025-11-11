
from pathlib import Path
import logging
from types import SimpleNamespace

def plan_organization(file_info_list, base_dir):
    planned_operations = []
    for entry in file_info_list:
        # Convert to SimpleNamespace for dot access
        file_info = SimpleNamespace(**entry) if isinstance(entry, dict) else entry

        try:
            category = file_info.category or "Uncategorized"
            year = str(file_info.year) if getattr(file_info, "year", None) else "UnknownYear"
            target_path = Path(base_dir) / category / year / file_info.path.name
            planned_operations.append((file_info.path, target_path))
        except Exception as e:
            logging.warning(f"⚠️ Failed to plan for {entry}: {e}")
            continue
    return planned_operations
