import shutil
import sys

import pytest

from tent_pack import FileExists, MaxSize, Pack, RunCommand, RunJava, RunPython
from tent_pack.checks import Custom
from tent_pack.errors import PackError


def ctx_for(root, *patterns):
    return Pack(format=1).exclude(*patterns).context(root)


def test_file_exists(cw):
    ctx = ctx_for(cw)
    assert FileExists("report.txt").run(ctx).ok
    assert FileExists("sub").run(ctx).ok
    assert FileExists("*.csv").run(ctx).ok
    out = FileExists("missing.txt").run(ctx)
    assert not out.ok and "not found" in out.message


def test_file_exists_but_excluded(cw):
    out = FileExists("debug.log").run(ctx_for(cw, "*.log"))
    assert not out.ok and "left out of the zip" in out.message


def test_max_size_each(cw):
    (cw / "big.bin").write_bytes(b"x" * 2000)
    ctx = ctx_for(cw)
    assert MaxSize(5000).run(ctx).ok
    out = MaxSize(1000).run(ctx)
    assert not out.ok and "big.bin" in out.detail


def test_max_size_total_and_glob(cw):
    (cw / "a.bin").write_bytes(b"x" * 600)
    (cw / "b.bin").write_bytes(b"x" * 600)
    ctx = ctx_for(cw)
    assert not MaxSize(1000, path="*.bin", total=True).run(ctx).ok
    assert MaxSize(1000, path="*.bin").run(ctx).ok


def test_max_size_ignores_excluded(cw):
    (cw / "big.log").write_bytes(b"x" * 5000)
    assert MaxSize(1000, path="*.log").run(ctx_for(cw, "*.log")).ok


def test_run_python_pass_and_fail(cw):
    ctx = ctx_for(cw)
    assert RunPython("main.py").run(ctx).ok
    (cw / "bad.py").write_text("import sys\nprint('boom')\nsys.exit(3)\n")
    out = RunPython("bad.py").run(ctx)
    assert not out.ok and "status 3" in out.message and "boom" in out.detail


def test_run_python_missing_script(cw):
    out = RunPython("nope.py").run(ctx_for(cw))
    assert not out.ok and "not found" in out.message


def test_run_python_timeout_and_stdin(cw):
    (cw / "slow.py").write_text("import time\ntime.sleep(30)\n")
    out = RunPython("slow.py", timeout=0.5).run(ctx_for(cw))
    assert not out.ok and "timed out" in out.message
    (cw / "echo.py").write_text("import sys\nassert input() == 'hi'\n")
    assert RunPython("echo.py", stdin="hi\n").run(ctx_for(cw)).ok
    assert not RunPython("echo.py").run(ctx_for(cw)).ok  # stdin closed


def test_run_python_does_not_leave_pycache(cw):
    (cw / "helper.py").write_text("x = 1\n")
    (cw / "uses.py").write_text("import helper\n")
    RunPython("uses.py").run(ctx_for(cw))
    assert not (cw / "__pycache__" / "helper.cpython-314.pyc").exists()


def test_run_command(cw):
    ctx = ctx_for(cw)
    assert RunCommand([sys.executable, "-c", "pass"]).run(ctx).ok
    assert not RunCommand([sys.executable, "-c", "raise SystemExit(1)"]).run(ctx).ok
    assert not RunCommand(["no-such-tool-xyz"]).run(ctx).ok


@pytest.mark.skipif(not (shutil.which("javac") and shutil.which("java")), reason="no JDK")
def test_run_java(tmp_path):
    (tmp_path / "Main.java").write_text(
        "public class Main { public static void main(String[] a) { System.out.println(1); } }\n"
    )
    ctx = ctx_for(tmp_path)
    assert RunJava("Main").run(ctx).ok
    (tmp_path / "Main.java").write_text("public class Main { oops }\n")
    out = RunJava("Main").run(ctx)
    assert not out.ok and "compilation failed" in out.message
    assert not list(tmp_path.glob("*.class"))


def test_custom_check(cw):
    ctx = ctx_for(cw)
    assert Custom(lambda c: None).run(ctx).ok
    assert not Custom(lambda c: False).run(ctx).ok
    assert Custom(lambda c: "bad thing").run(ctx).message == "bad thing"


def test_bad_severity():
    with pytest.raises(PackError):
        FileExists("x", severity="loud")
