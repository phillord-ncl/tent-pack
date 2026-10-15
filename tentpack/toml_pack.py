"""Load a pack.toml into a Pack.

Validation is strict about the shape of format 1 files, but the format
number is checked first: a file from a newer format is refused with an
upgrade message before anything else is judged against format 1's rules.
"""

import tomllib

from . import checks
from .errors import PackError
from .pack import Pack, check_format

TOP_KEYS = {"format", "name", "output", "excludes", "exclude", "check"}


def _str(v):
    return isinstance(v, str)


def _str_list(v):
    return isinstance(v, list) and all(isinstance(x, str) for x in v)


def _bool(v):
    return isinstance(v, bool)


def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0


def _size(v):
    return (isinstance(v, int) and not isinstance(v, bool)) or isinstance(v, str)


def _str_or_list(v):
    return _str(v) or _str_list(v)


_COMMON = {
    "type": (_str, "a string"),
    "severity": (lambda v: v in checks.SEVERITIES, "'error' or 'warn'"),
    "name": (_str, "a string"),
}
_RUNNER = {
    "args": (_str_list, "a list of strings"),
    "stdin": (_str, "a string"),
    "timeout": (_number, "a positive number"),
}

# type -> (class, {key: (validator, expectation)}, required keys)
CHECK_TYPES = {
    "file-exists": (checks.FileExists, {"path": (_str, "a string")}, {"path"}),
    "max-size": (
        checks.MaxSize,
        {
            "limit": (_size, "a number of bytes or a string like '5MB'"),
            "path": (_str, "a string"),
            "total": (_bool, "true or false"),
        },
        {"limit"},
    ),
    "run-python": (
        checks.RunPython,
        {"script": (_str, "a string"), **_RUNNER},
        {"script"},
    ),
    "run-java": (
        checks.RunJava,
        {
            "main": (_str, "a string"),
            "sources": (_str_or_list, "a string or list of strings"),
            **_RUNNER,
        },
        {"main"},
    ),
    "run": (
        checks.RunCommand,
        {"command": (_str_list, "a list of strings"), **_RUNNER},
        {"command"},
    ),
}


def _build_check(index, table):
    where = "check #{}".format(index)
    ctype = table.get("type")
    if ctype is None:
        raise PackError("{} has no 'type'".format(where))
    if ctype not in CHECK_TYPES:
        raise PackError(
            "{}: unknown type {!r}; known types: {}".format(
                where, ctype, ", ".join(sorted(CHECK_TYPES))
            )
        )
    cls, keys, required = CHECK_TYPES[ctype]
    where = "{} ({})".format(where, ctype)
    allowed = {**_COMMON, **keys}
    unknown = sorted(set(table) - set(allowed))
    if unknown:
        raise PackError(
            "{}: unknown key(s) {}; allowed: {}".format(
                where, ", ".join(unknown), ", ".join(sorted(allowed))
            )
        )
    missing = sorted(required - set(table))
    if missing:
        raise PackError("{}: missing {}".format(where, ", ".join(missing)))
    for key, value in table.items():
        ok, expect = allowed[key]
        if not ok(value):
            raise PackError("{}: '{}' must be {}".format(where, key, expect))
    kwargs = {k: v for k, v in table.items() if k != "type"}
    try:
        return cls(**kwargs)
    except PackError as e:
        raise PackError("{}: {}".format(where, e)) from None


def pack_from_dict(data):
    if "format" not in data:
        raise PackError("no 'format' given; start the file with: format = 1")
    check_format(data["format"])
    unknown = sorted(set(data) - TOP_KEYS)
    if unknown:
        raise PackError(
            "unknown key(s) {}; allowed: {}".format(
                ", ".join(unknown), ", ".join(sorted(TOP_KEYS))
            )
        )
    for key, ok, expect in (
        ("name", _str, "a string"),
        ("output", _str, "a string"),
        ("excludes", _str_list, "a list of strings"),
        ("exclude", _str_list, "a list of strings"),
    ):
        if key in data and not ok(data[key]):
            raise PackError("'{}' must be {}".format(key, expect))
    tables = data.get("check", [])
    if not isinstance(tables, list) or not all(isinstance(t, dict) for t in tables):
        raise PackError("checks must be written as [[check]] tables")
    pack = Pack(format=data["format"], name=data.get("name"), output=data.get("output"))
    pack.exclude_set(*data.get("excludes", []))
    pack.exclude(*data.get("exclude", []))
    for i, table in enumerate(tables, 1):
        pack.add(_build_check(i, table))
    return pack


def load_toml(path):
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise PackError("{} is not valid TOML: {}".format(path, e)) from None
    except OSError as e:
        raise PackError("cannot read {}: {}".format(path, e)) from None
    return pack_from_dict(data)
