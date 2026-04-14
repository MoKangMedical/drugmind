"""
Media storage helpers.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Optional


class MediaStore:
    """Persist generated media to disk and return relative URLs."""

    def __init__(self, base_dir: Optional[str] = None):
        default_dir = Path(__file__).resolve().parent.parent / "drugmind_data" / "media"
        self.base_dir = Path(
            base_dir
            or os.getenv("DRUGMIND_MEDIA_DIR", "").strip()
            or default_dir
        )
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, content: bytes, *, suffix: str, subdir: str) -> dict:
        safe_subdir = subdir.strip("/").replace("..", "")
        target_dir = self.base_dir / safe_subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid.uuid4().hex}{suffix}"
        file_path = target_dir / filename
        file_path.write_bytes(content)
        rel_path = f"{safe_subdir}/{filename}"
        return {
            "path": str(file_path),
            "relative_path": rel_path,
            "url": f"/media/generated/{rel_path}",
            "bytes": len(content),
        }
