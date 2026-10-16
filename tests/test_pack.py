import zipfile

import pytest

from tent_pack import FileExists, Pack
from tent_pack.errors import PackError


def test_severity_and_exceptions(cw):
    pack = Pack(format=1)
    pack.require("missing", severity="warn")
    pack.require("also-missing")
    pack.require("report.txt")
    pack.check(lambda ctx: 1 / 0, name="explodes")
    results = pack.run_checks(pack.context(cw))
    assert [r.status for r in results] == ["warn", "fail", "pass", "fail"]
    assert "ZeroDivisionError" in results[3].message


def test_pack_zip_contents(cw):
    pack = Pack(format=1, output="cw1.zip").exclude_set("python", "os").exclude("*.log")
    target, count = pack.pack(pack.context(cw))
    assert count == 3
    with zipfile.ZipFile(target) as z:
        assert sorted(z.namelist()) == ["main.py", "report.txt", "sub/data.csv"]


def test_repack_does_not_include_old_zip(cw):
    pack = Pack(format=1, output="cw1.zip")
    pack.pack(pack.context(cw))
    target, _ = pack.pack(pack.context(cw))
    with zipfile.ZipFile(target) as z:
        assert "cw1.zip" not in z.namelist()


def test_pack_without_output(cw):
    pack = Pack(format=1)
    with pytest.raises(PackError):
        pack.pack(pack.context(cw))


@pytest.mark.parametrize("bad", ["a/b.zip", "..\\x.zip", ""])
def test_bad_output(bad):
    with pytest.raises(PackError):
        Pack(format=1, output=bad)


def test_format_checks():
    with pytest.raises(PackError, match="upgrade"):
        Pack(format=99)
    for bad in (0, "1", None, True):
        with pytest.raises(PackError):
            Pack(format=bad)


def test_add_rejects_non_check():
    with pytest.raises(PackError):
        Pack(format=1).add("nope")
