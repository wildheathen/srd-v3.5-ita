#!/usr/bin/env python3
"""Add source field to all data JSON files."""

import json
import os
import sys

CATEGORIES = ["spells", "feats", "races", "equipment", "classes", "monsters", "rules"]
DEFAULT_SOURCE = "SRD"


def main():
    source = DEFAULT_SOURCE
    if len(sys.argv) > 1 and sys.argv[1] == "--source":
        source = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_SOURCE

    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(os.path.dirname(script_dir), "data")

    for cat in CATEGORIES:
        path = os.path.join(data_dir, f"{cat}.json")
        if not os.path.exists(path):
            print(f"  Skip {cat}: file not found")
            continue

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        changed = 0
        for entry in data:
            if "source" not in entry:
                entry["source"] = source
                changed += 1

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")

        print(f"  {cat}: {changed} entries tagged with '{source}'")


if __name__ == "__main__":
    main()
