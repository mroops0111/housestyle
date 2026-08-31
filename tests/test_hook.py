import json
import pathlib
import subprocess
import sys

import pytest

from housestyle.presentation import hook


CONFIG = '[housestyle]\nline-width = 74\n'
MIS_WRAPPED = (
    'def f():\n'
    '    # cap the size to the shared limit so the mmap does not\n'
    '    # blow past it, an unbounded value faults the runner.\n'
    '    pass\n'
)
UNBREAKABLE = (
    'def f():\n    # this one carries no comma at all and runs a very long way past the budget here.\n    pass\n'
)


def payload(path: pathlib.Path, tool: str = 'Edit') -> dict[str, object]:
    return {'tool_name': tool, 'tool_input': {'file_path': str(path)}}


def seed(tmp_path: pathlib.Path, body: str, name: str = 'probe.py') -> pathlib.Path:
    (tmp_path / 'housestyle.toml').write_text(CONFIG, encoding='utf-8')
    target = tmp_path / name
    target.write_text(body, encoding='utf-8')
    return target


def test_a_non_edit_tool_is_ignored(tmp_path: pathlib.Path) -> None:
    target = seed(tmp_path, MIS_WRAPPED)
    assert hook.run(payload(target, tool='Read')).exit_code == 0


def test_a_non_python_file_is_ignored(tmp_path: pathlib.Path) -> None:
    target = tmp_path / 'notes.md'
    target.write_text('# heading\n', encoding='utf-8')
    assert hook.targets(payload(target)) == ()


def test_a_missing_file_is_ignored(tmp_path: pathlib.Path) -> None:
    assert hook.targets(payload(tmp_path / 'gone.py')) == ()


def test_a_payload_without_a_path_is_ignored() -> None:
    assert hook.run({'tool_name': 'Edit', 'tool_input': {}}).exit_code == 0


def test_mechanical_findings_are_repaired_silently(tmp_path: pathlib.Path) -> None:
    target = seed(tmp_path, MIS_WRAPPED)
    outcome = hook.run(payload(target))

    assert outcome.exit_code == 0
    assert not outcome.blocks
    assert outcome.stderr == ''
    assert str(target) in outcome.repaired
    assert 'does not blow past it,\n' in target.read_text(encoding='utf-8')


def test_a_rewrite_finding_blocks_with_exit_two(tmp_path: pathlib.Path) -> None:
    target = seed(tmp_path, UNBREAKABLE)
    outcome = hook.run(payload(target))

    assert outcome.exit_code == 2
    assert outcome.blocks
    assert 'unbreakable-sentence' in outcome.stderr
    assert 'Add a comma' in outcome.stderr


def test_a_clean_file_neither_writes_nor_blocks(tmp_path: pathlib.Path) -> None:
    target = seed(tmp_path, 'def f():\n    # short and fine.\n    pass\n')
    original = target.read_text(encoding='utf-8')
    outcome = hook.run(payload(target))

    assert outcome.exit_code == 0
    assert outcome.repaired == ()
    assert target.read_text(encoding='utf-8') == original


def test_a_fixable_neighbour_is_repaired_even_when_the_run_blocks(tmp_path: pathlib.Path) -> None:
    extra = '    # this trailing one carries no comma at all and runs a very long way past the budget here.\n'
    body = MIS_WRAPPED.replace('    pass\n', extra + '    pass\n')
    target = seed(tmp_path, body)
    outcome = hook.run(payload(target))

    assert outcome.blocks
    assert 'does not blow past it,\n' in target.read_text(encoding='utf-8')


def test_write_can_be_suppressed(tmp_path: pathlib.Path) -> None:
    target = seed(tmp_path, MIS_WRAPPED)
    original = target.read_text(encoding='utf-8')
    hook.run(payload(target), write=False)
    assert target.read_text(encoding='utf-8') == original


@pytest.mark.parametrize('body', ['not json at all', '[]', '"a string"'])
def test_malformed_input_never_blocks(body: str) -> None:
    result = subprocess.run(
        [sys.executable, '-m', 'housestyle.presentation.hook'],
        input=body,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0


def test_the_entry_point_blocks_on_a_rewrite_finding(tmp_path: pathlib.Path) -> None:
    target = seed(tmp_path, UNBREAKABLE)
    result = subprocess.run(
        [sys.executable, '-m', 'housestyle.presentation.hook'],
        input=json.dumps(payload(target)),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert 'unbreakable-sentence' in result.stderr


def test_the_hook_stays_silent_on_mechanical_findings_even_now(tmp_path: pathlib.Path) -> None:
    target = seed(tmp_path, MIS_WRAPPED)
    outcome = hook.run(payload(target))
    assert outcome.stderr == '', 'the hook must never narrate a repair it made silently'
    assert outcome.exit_code == 0
