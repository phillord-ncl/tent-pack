"""tent-pack -- check student coursework and pack it into a zip for upload.

A lecturer distributes a pack.toml (declarative) or pack.py (code) with the
coursework; the student runs `tent-pack`. Both build the same `Pack`.
"""

from .checks import (
    Check,
    FileExists,
    MaxSize,
    Outcome,
    RunCommand,
    RunJava,
    RunPython,
)
from .errors import PackError
from .pack import FORMAT_VERSION, Pack

__all__ = [
    "Check",
    "FORMAT_VERSION",
    "FileExists",
    "MaxSize",
    "Outcome",
    "Pack",
    "PackError",
    "RunCommand",
    "RunJava",
    "RunPython",
]
