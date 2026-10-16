"""The `Pack` builder: what pack.toml is translated into and what pack.py
builds directly."""

import dataclasses
import os
import tempfile
import zipfile

from .checks import (
    Check,
    Custom,
    FileExists,
    MaxSize,
    Outcome,
    RunCommand,
    RunJava,
    RunPython,
)
from .context import Context
from .errors import PackError
from .excludes import Excluder, standard_set

# Highest pack-file format this tent-pack understands. Old formats keep
# working; a bump means a new format, never a change to an old one.
FORMAT_VERSION = 1
UPGRADE_HINT = "pip install --upgrade tent-pack"


def check_format(fmt):
    if isinstance(fmt, bool) or not isinstance(fmt, int) or fmt < 1:
        raise PackError("format must be a whole number, 1 or more, got {!r}".format(fmt))
    if fmt > FORMAT_VERSION:
        raise PackError(
            "this pack file uses format {} but this tent-pack only understands "
            "up to format {}; upgrade with: {}".format(fmt, FORMAT_VERSION, UPGRADE_HINT)
        )
    return fmt


@dataclasses.dataclass
class Result:
    name: str
    status: str  # "pass", "warn" or "fail"
    message: str = ""
    detail: str = ""


class Pack:
    def __init__(self, format, name=None, output=None):
        self.format = check_format(format)
        self.name = name
        if output is not None and (
            not isinstance(output, str) or not output or "/" in output or "\\" in output
        ):
            raise PackError("output must be a plain file name like 'cw1.zip'")
        self.output = output
        self.excludes = []
        self.checks = []

    def exclude(self, *patterns):
        self.excludes.extend(patterns)
        return self

    def exclude_set(self, *names):
        for n in names:
            self.excludes.extend(standard_set(n))
        return self

    def add(self, check):
        if not isinstance(check, Check):
            raise PackError("not a check: {!r}".format(check))
        self.checks.append(check)
        return self

    def require(self, path, **kw):
        return self.add(FileExists(path, **kw))

    def max_size(self, limit, path="*", total=False, **kw):
        return self.add(MaxSize(limit, path=path, total=total, **kw))

    def run_python(self, script, **kw):
        return self.add(RunPython(script, **kw))

    def run_java(self, main, **kw):
        return self.add(RunJava(main, **kw))

    def run(self, command, **kw):
        return self.add(RunCommand(command, **kw))

    def check(self, fn, **kw):
        return self.add(Custom(fn, **kw))

    def context(self, root):
        patterns = list(self.excludes)
        if self.output:
            patterns.append("/" + self.output)
        return Context(root, Excluder(patterns))

    def run_checks(self, ctx):
        results = []
        for check in self.checks:
            try:
                outcome = check.run(ctx)
            except Exception as e:  # a broken check must not hide the others
                outcome = Outcome(False, "{}: {}".format(type(e).__name__, e))
            if outcome.ok:
                status = "pass"
            else:
                status = "fail" if check.severity == "error" else "warn"
            results.append(Result(check.name, status, outcome.message, outcome.detail))
        return results

    def pack(self, ctx):
        """Write the zip into the project root; returns (path, file count)."""
        if not self.output:
            raise PackError("this pack file does not name an output zip")
        files = ctx.files()
        target = ctx.root / self.output
        fd, tmp = tempfile.mkstemp(suffix=".zip", dir=str(ctx.root))
        os.close(fd)
        try:
            with zipfile.ZipFile(
                tmp, "w", zipfile.ZIP_DEFLATED, strict_timestamps=False
            ) as z:
                for f in files:
                    z.write(ctx.path(f), f)
            os.replace(tmp, target)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
        return target, len(files)
