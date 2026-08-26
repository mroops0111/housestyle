import pytest

from housestyle import __version__
from housestyle.presentation.cli import main


def test_main_succeeds(capsys: pytest.CaptureFixture[str]) -> None:
    assert main() == 0
    assert __version__ in capsys.readouterr().out
