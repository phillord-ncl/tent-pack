import zipfile

from tentpack.cli import main

TOML = """\
format = 1
output = "cw1.zip"
excludes = ["python", "os"]
exclude = ["*.log"]

[[check]]
type = "file-exists"
path = "report.txt"

[[check]]
type = "run-python"
script = "main.py"
"""


def run(cw, capsys, *args):
    code = main(["-C", str(cw), "--no-color", *args])
    cap = capsys.readouterr()
    return code, cap.out, cap.err


def test_pass_and_pack(cw, capsys):
    (cw / "pack.toml").write_text(TOML)
    code, out, _ = run(cw, capsys)
    assert code == 0
    assert "[ OK ] file exists: report.txt" in out
    assert "2 passed, 0 warning(s), 0 failed" in out
    assert "Packed" in out
    with zipfile.ZipFile(cw / "cw1.zip") as z:
        assert "report.txt" in z.namelist()
        assert "debug.log" not in z.namelist()


def test_failure_blocks_pack(cw, capsys):
    (cw / "pack.toml").write_text(TOML)
    (cw / "report.txt").unlink()
    code, out, _ = run(cw, capsys)
    assert code == 1
    assert "[FAIL] file exists: report.txt" in out
    assert "report.txt not found" in out
    assert "Not packing" in out
    assert not (cw / "cw1.zip").exists()


def test_warning_does_not_block(cw, capsys):
    (cw / "pack.toml").write_text(
        TOML + '\n[[check]]\ntype = "file-exists"\npath = "nope"\nseverity = "warn"\n'
    )
    code, out, _ = run(cw, capsys)
    assert code == 0
    assert "[WARN]" in out
    assert (cw / "cw1.zip").exists()


def test_verify_does_not_pack(cw, capsys):
    (cw / "pack.toml").write_text(TOML)
    code, out, _ = run(cw, capsys, "--verify")
    assert code == 0
    assert "nothing was packed" in out
    assert not (cw / "cw1.zip").exists()


def test_checks_only_pack(cw, capsys):
    (cw / "pack.toml").write_text('format = 1\n[[check]]\ntype = "file-exists"\npath = "main.py"\n')
    code, out, _ = run(cw, capsys)
    assert code == 0 and "All checks passed" in out


def test_pack_py(cw, capsys):
    (cw / "pack.py").write_text(
        "from tentpack import Pack\n"
        "def build():\n"
        "    return Pack(format=1, output='x.zip').require('main.py')\n"
    )
    code, out, _ = run(cw, capsys)
    assert code == 0
    assert (cw / "x.zip").exists()


def test_no_pack_file(cw, capsys):
    code, _, err = run(cw, capsys)
    assert code == 2 and "no pack.toml or pack.py" in err


def test_both_pack_files(cw, capsys):
    (cw / "pack.toml").write_text("format = 1\n")
    (cw / "pack.py").write_text("")
    code, _, err = run(cw, capsys)
    assert code == 2 and "both" in err


def test_explicit_file(cw, capsys):
    (cw / "pack.toml").write_text("format = 1\n")
    (cw / "pack.py").write_text("")
    code, _, _ = run(cw, capsys, "--file", str(cw / "pack.toml"))
    assert code == 0


def test_newer_format_message(cw, capsys):
    (cw / "pack.toml").write_text("format = 7\nfuture = true\n")
    code, _, err = run(cw, capsys)
    assert code == 2 and "upgrade" in err


def test_pack_py_errors(cw, capsys):
    (cw / "pack.py").write_text("def build():\n    return 5\n")
    code, _, err = run(cw, capsys)
    assert code == 2 and "must return a tentpack.Pack" in err
    (cw / "pack.py").write_text("raise RuntimeError('x')\n")
    code, _, err = run(cw, capsys)
    assert code == 2 and "failed to load" in err
