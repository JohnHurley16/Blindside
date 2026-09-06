"""Pick a vispy backend. Windows needs an explicit one."""
from __future__ import annotations

import vispy

CANDIDATES: tuple[str, ...] = ("pyqt6", "glfw", "pyqt5", "pyside6")


def pick_backend() -> str:
    for name in CANDIDATES:
        try:
            vispy.use(app=name)
            return name
        except Exception:      # noqa: BLE001 - any import or init failure
            continue
    raise RuntimeError("no vispy backend available: pip install PyQt6 (or glfw)")
