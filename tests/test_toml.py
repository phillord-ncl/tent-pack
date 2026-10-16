import pytest

from tent_pack.errors import PackError
from tent_pack.toml_pack import load_toml, pack_from_dict


def bad(data, match):
    with pytest.raises(PackError, match=match):
        pack_from_dict(data)


def test_missing_format():
    bad({}, "no 'format'")


def test_newer_format_is_refused_before_other_validation():
    bad({"format": 99, "some-new-key": 1}, "upgrade")


def test_unknown_top_level_key():
    bad({"format": 1, "colour": "red"}, "unknown key")


def test_unknown_check_type_and_key():
    bad({"format": 1, "check": [{"type": "magic"}]}, "unknown type")
    bad({"format": 1, "check": [{"type": "file-exists", "path": "a", "x": 1}]}, "unknown key")


def test_missing_and_mistyped_check_keys():
    bad({"format": 1, "check": [{"type": "file-exists"}]}, "missing path")
    bad({"format": 1, "check": [{"type": "file-exists", "path": 3}]}, "'path' must be")
    bad({"format": 1, "check": [{"type": "run-python", "script": "a", "timeout": 0}]}, "timeout")
    bad({"format": 1, "check": [{"type": "file-exists", "path": "a", "severity": "x"}]}, "severity")
    bad({"format": 1, "check": [{"type": "max-size", "limit": "lots"}]}, "size")


def test_check_without_type():
    bad({"format": 1, "check": [{"path": "a"}]}, "no 'type'")


def test_bad_exclude_set():
    bad({"format": 1, "excludes": ["nope"]}, "unknown exclude set")


def test_invalid_toml(tmp_path):
    p = tmp_path / "pack.toml"
    p.write_text("format = = 1")
    with pytest.raises(PackError, match="not valid TOML"):
        load_toml(p)


def test_loads_full_example(tmp_path):
    p = tmp_path / "pack.toml"
    p.write_text(
        'format = 1\noutput = "x.zip"\nexcludes = ["python"]\n'
        '[[check]]\ntype = "file-exists"\npath = "a"\nseverity = "warn"\n'
    )
    pack = load_toml(p)
    assert pack.output == "x.zip"
    assert pack.checks[0].severity == "warn"
    assert "__pycache__" in pack.excludes
