#!/usr/bin/env python3
"""CLI wrapper for STR Property Information semantic/usefulness gates."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from property_note_semantic_quality import main

if __name__ == "__main__":
    raise SystemExit(main())
