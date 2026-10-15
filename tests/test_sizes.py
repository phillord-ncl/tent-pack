import pytest

from tentpack.errors import PackError
from tentpack.sizes import format_size, parse_size


def test_parse():
    assert parse_size(10) == 10
    assert parse_size("10") == 10
    assert parse_size("5MB") == 5 * 1024**2
    assert parse_size("200 kb") == 200 * 1024
    assert parse_size("1.5KB") == 1536


@pytest.mark.parametrize("bad", ["x", "5 parsecs", -1, True, None, 1.5])
def test_parse_bad(bad):
    with pytest.raises(PackError):
        parse_size(bad)


def test_format():
    assert format_size(10) == "10 B"
    assert format_size(2048) == "2.0 KB"
