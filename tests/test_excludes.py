import pytest

from tent_pack.errors import PackError
from tent_pack.excludes import Excluder, standard_set


def test_name_pattern_matches_any_depth():
    e = Excluder(["__pycache__"])
    assert e.is_excluded("__pycache__/x.pyc")
    assert e.is_excluded("a/b/__pycache__/x.pyc")
    assert not e.is_excluded("a/pycache.py")


def test_glob_pattern():
    e = Excluder(["*.log"])
    assert e.is_excluded("a/debug.log")
    assert not e.is_excluded("debug.txt")


def test_anchored_pattern_only_matches_top_level():
    e = Excluder(["/build"])
    assert e.is_excluded("build/x")
    assert not e.is_excluded("src/build/x")


def test_slash_pattern_matches_below_directory():
    e = Excluder(["docs/drafts"])
    assert e.is_excluded("docs/drafts/a.txt")
    assert not e.is_excluded("other/docs/drafts/a.txt")


def test_walk_prunes_and_sorts(cw):
    files = Excluder(standard_set("python") + ["*.log", ".DS_Store"]).walk(cw)
    assert files == ["main.py", "report.txt", "sub/data.csv"]


def test_unknown_standard_set():
    with pytest.raises(PackError, match="unknown exclude set"):
        standard_set("nope")
