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


def test_check_reports_findings_and_exits_non_zero(tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / 'bad.py'
    target.write_text(
        'def f():\n    # cap the size so the mmap does not\n    # blow past it, an unbounded value faults.\n    pass\n',
        encoding='utf-8',
    )
    (tmp_path / 'housestyle.toml').write_text('[housestyle]\nline-width = 60\n', encoding='utf-8')

    with pytest.raises(SystemExit) as exit_info:
        app(['check', str(target)])
    assert exit_info.value.code == 1
    assert 'wrap-point' in capsys.readouterr().out


def test_check_on_clean_input_exits_zero(tmp_path: pathlib.Path) -> None:
    target = tmp_path / 'good.py'
    target.write_text('def f():\n    # short and fine.\n    pass\n', encoding='utf-8')
    with pytest.raises(SystemExit) as exit_info:
        app(['check', str(target)])
    assert exit_info.value.code == 0


def test_check_rejects_an_unknown_output_format(tmp_path: pathlib.Path) -> None:
    target = tmp_path / 'a.py'
    target.write_text('# note\n', encoding='utf-8')
    with pytest.raises(SystemExit) as exit_info:
        app(['check', str(target), '--output', 'nonsense'])
    assert exit_info.value.code == 2


def test_fix_prints_a_diff_without_write(tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / 'bad.py'
    original = (
        'def f():\n    # cap the size so the mmap does not\n    # blow past it, an unbounded value faults.\n    pass\n'
    )
    target.write_text(original, encoding='utf-8')
    (tmp_path / 'housestyle.toml').write_text('[housestyle]\nline-width = 60\n', encoding='utf-8')

    with pytest.raises(SystemExit):
        app(['fix', str(target)])
    assert '---' in capsys.readouterr().out
    assert target.read_text(encoding='utf-8') == original


def test_fix_write_applies_the_change(tmp_path: pathlib.Path) -> None:
    target = tmp_path / 'bad.py'
    original = (
        'def f():\n    # cap the size so the mmap does not\n    # blow past it, an unbounded value faults.\n    pass\n'
    )
    target.write_text(original, encoding='utf-8')
    (tmp_path / 'housestyle.toml').write_text('[housestyle]\nline-width = 60\n', encoding='utf-8')

    with pytest.raises(SystemExit):
        app(['fix', str(target), '--write'])
    assert target.read_text(encoding='utf-8') != original
    assert 'does not blow past it,' in target.read_text(encoding='utf-8')


def test_the_actionable_format_shows_only_findings_needing_an_author(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / 'a.py'
    target.write_text(
        'def f():\n    # this single sentence has no comma anywhere and runs well past the budget here.\n    pass\n',
        encoding='utf-8',
    )
    (tmp_path / 'housestyle.toml').write_text('[housestyle]\nline-width = 50\n', encoding='utf-8')

    with pytest.raises(SystemExit):
        app(['check', str(target), '--output', 'actionable'])
    output = capsys.readouterr().out
    assert 'unbreakable-sentence' in output
    assert 'do not add a suppression comment' in output


def test_the_json_format_encodes_ranges_and_fix_kind(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import json

    target = tmp_path / 'a.py'
    target.write_text(
        'def f():\n    # cap the size so the mmap does not\n    # blow past it, an unbounded value faults.\n    pass\n',
        encoding='utf-8',
    )
    (tmp_path / 'housestyle.toml').write_text('[housestyle]\nline-width = 60\n', encoding='utf-8')

    with pytest.raises(SystemExit):
        app(['check', str(target), '--output', 'json'])
    text = json.loads(capsys.readouterr().out)
    assert text['diagnostics'][0]['fixKind'] == 'reflow'
    assert text['diagnostics'][0]['mechanical'] is True


def test_the_actionable_format_says_so_when_only_mechanical_findings_exist(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / 'a.py'
    target.write_text(
        'def f():\n    # cap the size so the mmap does not\n    # blow past it, an unbounded value faults.\n    pass\n',
        encoding='utf-8',
    )
    (tmp_path / 'housestyle.toml').write_text('[housestyle]\nline-width = 60\n', encoding='utf-8')

    with pytest.raises(SystemExit):
        app(['check', str(target), '--output', 'actionable'])
    output = capsys.readouterr().out
    assert 'Nothing needs rewriting' in output
    assert 'repaired mechanically' in output


def test_the_actionable_format_says_so_when_nothing_is_wrong(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / 'a.py'
    target.write_text('def f():\n    # short and fine.\n    pass\n', encoding='utf-8')

    with pytest.raises(SystemExit):
        app(['check', str(target), '--output', 'actionable'])
    assert 'No findings' in capsys.readouterr().out
