import pathlib

from .excludes import Excluder


class Context:
    """What a check can see: the project root and the files that would be
    packed (everything not excluded)."""

    def __init__(self, root, excluder=None):
        self.root = pathlib.Path(root)
        self.excluder = excluder or Excluder([])
        self._files = None

    def files(self):
        """Sorted relative paths (with `/`) of the non-excluded files."""
        if self._files is None:
            self._files = self.excluder.walk(self.root)
        return list(self._files)

    def path(self, rel):
        return self.root / rel
