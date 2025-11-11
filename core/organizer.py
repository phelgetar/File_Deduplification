
from pathlib import Path

def plan_organization(classified_files, base_dir):
    plan = []
    for file_info in classified_files:
        # Convert to dict if not already
        file_info = vars(file_info) if hasattr(file_info, '__dict__') else file_info

        year_folder = str(file_info.get("year", "Unknown"))
        category_folder = file_info.get("category", "Uncategorized")
        original_path = file_info["path"]
        new_path = Path(base_dir) / year_folder / category_folder / original_path.name
        plan.append((original_path, new_path))
    return plan
