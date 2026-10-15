import pytest


@pytest.fixture
def cw(tmp_path):
    """A small coursework directory."""
    (tmp_path / "main.py").write_text("print('hello')\n")
    (tmp_path / "report.txt").write_text("my report\n")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "main.cpython.pyc").write_bytes(b"x")
    (tmp_path / "debug.log").write_text("noise\n")
    (tmp_path / ".DS_Store").write_bytes(b"x")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "data.csv").write_text("1,2\n")
    return tmp_path
