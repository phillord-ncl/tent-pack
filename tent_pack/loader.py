"""Find and load the pack file: pack.toml or pack.py in the project dir."""

import importlib.util
import pathlib

from .errors import PackError
from .pack import Pack
from .toml_pack import load_toml


def find_pack_file(root, explicit=None):
    if explicit:
        path = pathlib.Path(explicit)
        if not path.is_absolute():
            path = pathlib.Path.cwd() / path
        if not path.is_file():
            raise PackError("pack file {} not found".format(explicit))
        return path
    found = [root / n for n in ("pack.toml", "pack.py") if (root / n).is_file()]
    if not found:
        raise PackError(
            "no pack.toml or pack.py in {}; run tent-pack in the coursework "
            "folder".format(root)
        )
    if len(found) > 1:
        raise PackError(
            "both pack.toml and pack.py exist in {}; choose one with --file".format(root)
        )
    return found[0]


def load_py(path):
    spec = importlib.util.spec_from_file_location("tent_pack_packfile", path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except PackError:
        raise
    except Exception as e:
        raise PackError("{} failed to load: {}: {}".format(path.name, type(e).__name__, e)) from e
    build = getattr(module, "build", None)
    if not callable(build):
        raise PackError("{} must define a build() function returning a Pack".format(path.name))
    try:
        pack = build()
    except PackError:
        raise
    except Exception as e:
        raise PackError("{} build() failed: {}: {}".format(path.name, type(e).__name__, e)) from e
    if not isinstance(pack, Pack):
        raise PackError("{} build() must return a tent_pack.Pack".format(path.name))
    return pack


def load_pack(path):
    path = pathlib.Path(path)
    if path.suffix == ".toml":
        return load_toml(path)
    if path.suffix == ".py":
        return load_py(path)
    raise PackError("pack file must end in .toml or .py, got {}".format(path.name))
