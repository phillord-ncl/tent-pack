"""Backwards compatibility: every fixture under fixtures/formatN/ is a pack
file as it was written for that format. They are frozen -- never edit one;
a change in behaviour needs a new format number and new fixtures. Keep them
for at least one academic year."""

import pathlib

import pytest

from tentpack.toml_pack import load_toml

FIXTURES = sorted(pathlib.Path(__file__).parent.joinpath("fixtures").glob("format*/*.toml"))


def test_fixtures_exist():
    assert FIXTURES


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: "{}/{}".format(p.parent.name, p.name))
def test_old_pack_files_still_load(path):
    pack = load_toml(path)
    assert pack.format == int(path.parent.name.removeprefix("format"))
