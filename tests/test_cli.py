import pathlib

import pytest

from housestyle.presentation.cli import app


def test_version_prints_the_package_version(capsys: pytest.CaptureFixture[str]) -> None:
    from housestyle import __version__

    with pytest.raises(SystemExit) as exit_info:
        app(['version'])
    assert exit_info.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_stats_reports_a_measured_corpus(tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / 'sample.py'
    source.write_text('def build():\n    """Public doc."""\n    # inline note\n', encoding='utf-8')

    with pytest.raises(SystemExit) as exit_info:
        app(['stats', str(source)])
    assert exit_info.value.code == 0

    output = capsys.readouterr().out
    assert '1 documents, 2 comment blocks' in output
    assert 'doc/public' in output
    assert 'line/inline-body' in output


def test_stats_exits_non_zero_when_nothing_is_readable(tmp_path: pathlib.Path) -> None:
    with pytest.raises(SystemExit) as exit_info:
        app(['stats', str(tmp_path)])
    assert exit_info.value.code == 1
