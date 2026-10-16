"""The checks a pack can run. Each check looks at the project and returns an
`Outcome`; the pack decides what a failure means from the check's severity."""

import dataclasses
import fnmatch
import os
import shutil
import signal
import subprocess
import tempfile

from .errors import PackError
from .sizes import format_size, parse_size

SEVERITIES = ("error", "warn")
TAIL_LINES = 15
TAIL_CHARS = 2000


@dataclasses.dataclass
class Outcome:
    ok: bool
    message: str = ""
    detail: str = ""


class Check:
    """Base class. Subclasses set `type` and implement `describe` and `run`."""

    type = ""

    def __init__(self, severity="error", name=None):
        if severity not in SEVERITIES:
            raise PackError(
                "severity must be one of {}, got {!r}".format(SEVERITIES, severity)
            )
        self.severity = severity
        self._name = name

    @property
    def name(self):
        return self._name or self.describe()

    def describe(self):
        return self.type

    def run(self, ctx):
        raise NotImplementedError


class FileExists(Check):
    type = "file-exists"

    def __init__(self, path, **kw):
        super().__init__(**kw)
        self.path = path

    def describe(self):
        return "file exists: {}".format(self.path)

    def run(self, ctx):
        dirprefix = self.path.rstrip("/") + "/"
        for f in ctx.files():
            if f == self.path or f.startswith(dirprefix) or fnmatch.fnmatchcase(f, self.path):
                return Outcome(True)
        if ctx.path(self.path).exists():
            return Outcome(
                False, "{} exists but would be left out of the zip".format(self.path)
            )
        return Outcome(False, "{} not found".format(self.path))


class MaxSize(Check):
    type = "max-size"

    def __init__(self, limit, path="*", total=False, **kw):
        super().__init__(**kw)
        self.limit = parse_size(limit)
        self.path = path
        self.total = total

    def describe(self):
        what = "total size of {}".format(self.path) if self.total else "size of each {}".format(self.path)
        return "{} at most {}".format(what, format_size(self.limit))

    def run(self, ctx):
        sized = [
            (f, os.path.getsize(ctx.path(f)))
            for f in ctx.files()
            if fnmatch.fnmatchcase(f, self.path)
        ]
        if self.total:
            total = sum(s for _, s in sized)
            if total > self.limit:
                return Outcome(
                    False,
                    "{} in total, limit is {}".format(
                        format_size(total), format_size(self.limit)
                    ),
                )
            return Outcome(True)
        big = [(f, s) for f, s in sized if s > self.limit]
        if big:
            return Outcome(
                False,
                "{} file(s) over {}".format(len(big), format_size(self.limit)),
                "\n".join("{} ({})".format(f, format_size(s)) for f, s in big),
            )
        return Outcome(True)


def _tail(text):
    lines = text.strip().splitlines()[-TAIL_LINES:]
    out = "\n".join(lines)
    return out[-TAIL_CHARS:]


def _decode(data):
    if data is None:
        return ""
    return data.decode(errors="replace") if isinstance(data, bytes) else data


def _kill_tree(proc):
    """Kill the process and anything it started, so a runaway student
    program cannot outlive the check (or hold our pipes open)."""
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            os.killpg(proc.pid, signal.SIGKILL)
    except OSError:
        pass
    proc.kill()


def run_process(argv, cwd, stdin=None, timeout=30, env=None):
    """Run argv; ok if it exits 0 within the timeout."""
    full_env = dict(os.environ)
    full_env.update(env or {})
    try:
        proc = subprocess.Popen(
            argv,
            cwd=str(cwd),
            stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=full_env,
            start_new_session=os.name != "nt",
        )
    except OSError as e:
        return Outcome(False, "could not run {}: {}".format(argv[0], e))
    try:
        output, _ = proc.communicate(
            stdin.encode() if stdin is not None else None, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        _kill_tree(proc)
        try:
            output, _ = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            output = b""
        return Outcome(
            False, "timed out after {:g}s".format(timeout), _tail(_decode(output))
        )
    if proc.returncode != 0:
        return Outcome(
            False,
            "exited with status {}".format(proc.returncode),
            _tail(_decode(output)),
        )
    return Outcome(True)


def _find_python():
    for name in ("python3", "python"):
        path = shutil.which(name)
        if path:
            return [path]
    path = shutil.which("py")
    if path:
        return [path, "-3"]
    return None


class _Runner(Check):
    def __init__(self, args=(), stdin=None, timeout=30, **kw):
        super().__init__(**kw)
        if timeout <= 0:
            raise PackError("timeout must be positive")
        self.args = list(args)
        self.stdin = stdin
        self.timeout = timeout


class RunPython(_Runner):
    type = "run-python"

    def __init__(self, script, **kw):
        super().__init__(**kw)
        self.script = script

    def describe(self):
        return "python {} runs".format(self.script)

    def run(self, ctx):
        if not ctx.path(self.script).is_file():
            return Outcome(False, "{} not found".format(self.script))
        python = _find_python()
        if python is None:
            return Outcome(False, "python was not found on the PATH")
        return run_process(
            python + [self.script] + self.args,
            ctx.root,
            self.stdin,
            self.timeout,
            env={"PYTHONDONTWRITEBYTECODE": "1", "MPLBACKEND": "Agg"},
        )


class RunJava(_Runner):
    type = "run-java"

    def __init__(self, main, sources="*.java", **kw):
        super().__init__(**kw)
        self.main = main
        self.sources = [sources] if isinstance(sources, str) else list(sources)

    def describe(self):
        return "java {} compiles and runs".format(self.main)

    def run(self, ctx):
        javac, java = shutil.which("javac"), shutil.which("java")
        if javac is None or java is None:
            return Outcome(False, "javac/java were not found on the PATH")
        files = [
            f
            for f in ctx.files()
            if any(fnmatch.fnmatchcase(f, s) for s in self.sources)
        ]
        if not files:
            return Outcome(False, "no java files found")
        with tempfile.TemporaryDirectory() as out:
            compiled = run_process(
                [javac, "-encoding", "UTF-8", "-d", out] + files,
                ctx.root,
                timeout=max(self.timeout, 60),
            )
            if not compiled.ok:
                compiled.message = "compilation failed ({})".format(compiled.message)
                return compiled
            return run_process(
                [java, "-cp", out, self.main] + self.args,
                ctx.root,
                self.stdin,
                self.timeout,
            )


class RunCommand(_Runner):
    type = "run"

    def __init__(self, command, **kw):
        super().__init__(**kw)
        if not command:
            raise PackError("command must not be empty")
        self.command = list(command)

    def describe(self):
        return "command runs: {}".format(" ".join(self.command))

    def run(self, ctx):
        exe = shutil.which(self.command[0])
        if exe is None:
            return Outcome(False, "{} was not found on the PATH".format(self.command[0]))
        return run_process(
            [exe] + self.command[1:] + self.args, ctx.root, self.stdin, self.timeout
        )


class Custom(Check):
    """A check backed by a function, from pack.py. The function takes the
    Context and returns None/True to pass, False or a message string to fail
    (an exception also fails)."""

    type = "custom"

    def __init__(self, fn, **kw):
        kw.setdefault("name", getattr(fn, "__name__", "custom check"))
        super().__init__(**kw)
        self.fn = fn

    def run(self, ctx):
        result = self.fn(ctx)
        if result is None or result is True:
            return Outcome(True)
        if result is False:
            return Outcome(False, "check failed")
        if isinstance(result, Outcome):
            return result
        return Outcome(False, str(result))
