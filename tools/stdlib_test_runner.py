from __future__ import annotations

import importlib.util
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Callable, List, Tuple


@dataclass
class TestFailure:
    file: str
    test_name: str
    error: str


def _load_module_from_path(path: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load module from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _iter_test_functions(mod: ModuleType) -> List[Tuple[str, Callable[[], object]]]:
    tests: List[Tuple[str, Callable[[], object]]] = []
    for name, value in vars(mod).items():
        if name.startswith("test_") and callable(value):
            # Only support 0-arg tests (keeps it stdlib-only).
            try:
                if value.__code__.co_argcount == 0:  # type: ignore[attr-defined]
                    tests.append((name, value))
            except Exception:
                # If we can't introspect, just skip.
                pass
    return tests


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]

    # Ensure repo root is importable (so `import freecad_gitpdm` works)
    sys.path.insert(0, str(repo_root))

    candidates = []
    for folder in [repo_root, repo_root / "tests"]:
        if folder.is_dir():
            candidates.extend(sorted(folder.glob("test_*.py")))

    failures: List[TestFailure] = []
    ran = 0

    for test_file in candidates:
        module_name = f"_gitpdm_test_{test_file.stem}_{abs(hash(str(test_file))) }"
        try:
            mod = _load_module_from_path(test_file, module_name)
        except Exception:
            failures.append(
                TestFailure(
                    file=str(test_file.relative_to(repo_root)),
                    test_name="<import>",
                    error=traceback.format_exc(),
                )
            )
            continue

        for test_name, fn in _iter_test_functions(mod):
            ran += 1
            try:
                fn()
            except Exception:
                failures.append(
                    TestFailure(
                        file=str(test_file.relative_to(repo_root)),
                        test_name=test_name,
                        error=traceback.format_exc(),
                    )
                )

    print(f"Ran {ran} stdlib tests across {len(candidates)} files")

    if failures:
        print(f"\nFAILED: {len(failures)} test(s)\n")
        for f in failures:
            print(f"--- {f.file}::{f.test_name} ---")
            print(f.error.rstrip())
            print()
        return 1

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
