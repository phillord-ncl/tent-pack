# Tent-Pack: Check and Pack Student Coursework

Check student coursework and, optionally, pack it into a zip for upload.
A lecturer ships a `pack.toml` (or `pack.py`) with the coursework; the
student runs `tent-pack` in the coursework folder.

    $ tent-pack
    tent-pack: Coursework 1 (pack.toml, format 1)
    [ OK ] file exists: report.pdf
    [FAIL] python main.py runs
           exited with status 1
    ...

Exit status: 0 all fine (warnings allowed), 1 a check failed, 2 the pack
file or command line is wrong. `tent-pack --verify` runs the checks without
writing the zip (students can dry-run; markers can reuse it). `-C DIR` and
`-f FILE` choose the folder and pack file.

tent-pack is part of the tent-tools suite. See also:

- [tent-pole](https://github.com/phillord-ncl/tent-pole) -- manage Canvas
  course content as markdown and push it to Canvas
- [tent-peg](https://github.com/phillord-ncl/tent-peg) -- download the
  submissions you are marking from Canvas, and push marks back
- [arbiter](https://github.com/phillord-ncl/arbiter) -- mark programming
  assignments

## pack.toml

```toml
format = 1                    # required; see "Compatibility"
name = "Coursework 1"
output = "cw1.zip"            # omit to run checks only
excludes = ["python", "os"]   # standard sets: python java os vcs
exclude = ["*.log", "/scratch"]

[[check]]
type = "file-exists"          # path may be a glob or a directory
path = "report.pdf"

[[check]]
type = "max-size"             # each matching file; total = true for the sum
limit = "5MB"                 # bytes, or KB/MB/GB (1 KB = 1024 bytes)
path = "*"
severity = "warn"             # default "error" blocks packing; "warn" doesn't

[[check]]
type = "run-python"           # exit status 0 within the timeout
script = "main.py"
args = []
stdin = "input text"
timeout = 30

[[check]]
type = "run-java"             # compiled to a temp dir, nothing left behind
main = "Main"
sources = "*.java"

[[check]]
type = "run"                  # any command on the PATH
command = ["jupyter", "nbconvert", "--execute", "work.ipynb"]
```

Every check also takes `name` (display text) and `severity`.
Python, `javac` and `java` are taken from the `PATH`. The output zip is
never included in itself, and files excluded from the zip are also
invisible to the checks.

## pack.py

Same model in code. Define `build()` returning a `Pack`:

```python
from tent_pack import Pack

def build():
    pack = Pack(format=1, output="cw1.zip").exclude_set("python", "os")
    pack.require("report.pdf")
    pack.max_size("5MB", severity="warn")
    pack.run_python("main.py", timeout=10)
    pack.check(lambda ctx: "no TODOs" if "TODO" in ctx.path("main.py").read_text() else None,
               name="no TODO left in main.py")
    return pack
```

A custom check takes the `Context` (`ctx.root`, `ctx.files()`, `ctx.path(rel)`)
and returns `None`/`True` to pass, or `False` / a message to fail.

## Compatibility

The pack file and tent-pack are distributed separately. `format` is the
pack-file format version. Old formats keep working on newer tent-pack; a
file from a newer format is refused with an upgrade message. A new
feature that changes meaning gets a new format number. Frozen example pack
files for each format live in `tests/fixtures/formatN/` and must not be
edited (keep them for at least one academic year).
