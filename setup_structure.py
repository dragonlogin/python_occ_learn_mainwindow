"""
Run this script ONCE from the project root to create the correct folder structure.
Place this file next to main.py, then run:  python setup_structure.py
"""

import os
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))

# ── Directory layout: {destination: source_filename} ─────────────────────────
MOVES = {
    "core/shape_item.py":        "shape_item.py",
    "core/importer.py":          "importer.py",
    "core/analysis.py":          "analysis.py",
    "viewer/occ_viewer.py":      "occ_viewer.py",
    "panels/shapes_panel.py":    "shapes_panel.py",
    "panels/distance_panel.py":  "distance_panel.py",
    "panels/collision_panel.py": "collision_panel.py",
    "panels/measure_panel.py":   "measure_panel.py",
    "ui/main_window.py":         "main_window.py",
    "ui/styles.py":              "styles.py",
    "utils/helpers.py":          "helpers.py",
}

# Packages that need an __init__.py
PACKAGES = ["core", "viewer", "panels", "ui", "utils"]


def main():
    # 1. Create package directories + __init__.py
    for pkg in PACKAGES:
        pkg_dir = os.path.join(BASE, pkg)
        os.makedirs(pkg_dir, exist_ok=True)
        init_path = os.path.join(pkg_dir, "__init__.py")
        if not os.path.exists(init_path):
            open(init_path, "w").close()
            print(f"  created  {pkg}/__init__.py")

    # 2. Move files into their packages
    for dest_rel, src_name in MOVES.items():
        src  = os.path.join(BASE, src_name)
        dest = os.path.join(BASE, dest_rel)
        if not os.path.exists(src):
            print(f"  SKIP     {src_name}  (not found in root)")
            continue
        if os.path.exists(dest):
            print(f"  EXISTS   {dest_rel}  (skipped)")
            continue
        shutil.move(src, dest)
        print(f"  moved    {src_name}  →  {dest_rel}")

    print("\n✓ Done!  Now run:  python main.py")


if __name__ == "__main__":
    main()
