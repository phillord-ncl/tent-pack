"""Exclusion patterns: standard sets plus lecturer-supplied globs.

Patterns are gitignore-like but deliberately simple. A pattern without a
slash matches any file or directory name at any depth; one with a slash (or
a leading slash) is matched against the path from the project root, and
matches everything below a matching directory.
"""

import fnmatch
import os

from .errors import PackError

STANDARD_EXCLUDES = {
    "python": [
        "__pycache__",
        "*.pyc",
        "venv",
        ".venv",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "*.egg-info",
        ".ipynb_checkpoints",
    ],
    "java": [
        "*.class",
        ".gradle",
        "build",
        "target",
        "out",
        ".idea",
    ],
    "os": [
        ".DS_Store",
        "Thumbs.db",
        "desktop.ini",
        "__MACOSX",
    ],
    "vcs": [
        ".git",
        ".svn",
        ".hg",
    ],
}


def standard_set(name):
    try:
        return list(STANDARD_EXCLUDES[name])
    except KeyError:
        raise PackError(
            "unknown exclude set {!r}; known sets: {}".format(
                name, ", ".join(sorted(STANDARD_EXCLUDES))
            )
        ) from None


def _match(pattern, rel):
    anchored = pattern.startswith("/")
    pattern = pattern.strip("/")
    if not pattern:
        return False
    parts = rel.split("/")
    if "/" in pattern:
        return any(
            fnmatch.fnmatchcase("/".join(parts[:i]), pattern)
            for i in range(1, len(parts) + 1)
        )
    if anchored:
        return fnmatch.fnmatchcase(parts[0], pattern)
    return any(fnmatch.fnmatchcase(part, pattern) for part in parts)


class Excluder:
    def __init__(self, patterns):
        self.patterns = list(patterns)

    def is_excluded(self, rel):
        """rel is a path relative to the project root, with `/` separators."""
        return any(_match(p, rel) for p in self.patterns)

    def walk(self, root):
        """Sorted relative paths (with `/`) of every non-excluded file."""
        found = []
        root = str(root)
        for dirpath, dirnames, filenames in os.walk(root):
            reldir = os.path.relpath(dirpath, root)
            prefix = "" if reldir == "." else reldir.replace(os.sep, "/") + "/"
            dirnames[:] = sorted(
                d for d in dirnames if not self.is_excluded(prefix + d)
            )
            for name in filenames:
                rel = prefix + name
                if not self.is_excluded(rel):
                    found.append(rel)
        return sorted(found)
