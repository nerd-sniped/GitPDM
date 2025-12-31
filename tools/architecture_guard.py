from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any


@dataclass
class GuardItem:
    rel_path: str
    max_lines: int


def _count_lines(path: Path) -> int:
    # Count lines in a memory-safe way.
    count = 0
    with path.open("rb") as f:
        for _ in f:
            count += 1
    return count


def main(argv: list[str]) -> int:
    repo_root = Path(__file__).resolve().parents[1]
    baseline_path = repo_root / "tools" / "architecture_baseline.json"

    try:
        baseline: Dict[str, Any] = json.loads(baseline_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"architecture_guard: missing baseline: {baseline_path}")
        return 2
    except Exception as e:
        print(f"architecture_guard: failed to read baseline: {e}")
        return 2

    items: list[GuardItem] = []
    for rel, cfg in (baseline.get("files") or {}).items():
        try:
            items.append(GuardItem(rel_path=rel, max_lines=int(cfg["max_lines"])))
        except Exception:
            print(f"architecture_guard: invalid baseline entry for {rel}")
            return 2

    failures: list[tuple[str, int, int]] = []

    for item in items:
        file_path = repo_root / item.rel_path
        if not file_path.is_file():
            failures.append((item.rel_path, -1, item.max_lines))
            continue

        actual = _count_lines(file_path)
        if actual > item.max_lines:
            failures.append((item.rel_path, actual, item.max_lines))

    if failures:
        print("Architecture guard failed (file grew beyond limit):")
        for rel, actual, limit in failures:
            if actual < 0:
                print(f"- {rel}: missing (limit {limit})")
            else:
                print(f"- {rel}: {actual} lines (limit {limit})")
        print(
            "\nIf this growth is intentional, bump limits in tools/architecture_baseline.json as part of the same PR."
        )
        return 1

    print("Architecture guard OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
