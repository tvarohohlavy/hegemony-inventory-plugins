# SPDX-FileCopyrightText: 2025-2026 Jakub Travnik <jakub.travnik@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Install built wheels in a clean virtualenv and verify imports/entry points."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

from package_paths import ROOT

EXPECTED_MODULES = (
    "hegemony_inventory_sdk",
    "hegemony_inventory_netbox",
    "hegemony_inventory_infrahub",
    "hegemony_inventory_git",
)

EXPECTED_ENTRY_POINTS = {"netbox", "infrahub", "git"}


def _python_bin(venv_dir: Path) -> Path:
    return venv_dir / ("Scripts" if sys.platform == "win32" else "bin") / "python"


def main() -> None:
    wheels = sorted((ROOT / "dist").glob("*.whl"))
    if len(wheels) != 4:
        raise SystemExit(f"Expected 4 wheels in dist/, found {len(wheels)}")

    tmp = Path(tempfile.mkdtemp(prefix="hegemony-inventory-wheel-smoke-"))
    try:
        venv_dir = tmp / "venv"
        venv.EnvBuilder(with_pip=True).create(venv_dir)
        python = _python_bin(venv_dir)
        subprocess.run(
            ["uv", "pip", "install", "--python", str(python), *map(str, wheels)],
            cwd=ROOT,
            check=True,
        )
        code = """
from importlib import import_module
from importlib.metadata import entry_points

modules = (
    "hegemony_inventory_sdk",
    "hegemony_inventory_netbox",
    "hegemony_inventory_infrahub",
    "hegemony_inventory_git",
)
for module in modules:
    import_module(module)

entries = entry_points(group="hegemony.inventory_plugins")
names = {entry.name for entry in entries}
expected = {"netbox", "infrahub", "git"}
missing = expected - names
assert not missing, missing
"""
        subprocess.run([str(python), "-c", code], check=True)
    finally:
        shutil.rmtree(tmp)


if __name__ == "__main__":
    main()
