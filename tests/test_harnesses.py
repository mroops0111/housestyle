import pathlib
import typing

import pytest

from housestyle.presentation.harnesses import (
    ALL_HARNESSES,
    ClaudeCodeHarness,
    CodexHarness,
    ExplicitPathsHarness,
    harness_for,
)


@pytest.fixture
def source(tmp_path: pathlib.Path) -> pathlib.Path:
    target = tmp_path / 'module.py'
    target.write_text('# a note\n', encoding='utf-8')
    return target


def test_claude_code_reads_the_named_file(source: pathlib.Path) -> None:
    payload = {'tool_name': 'Edit', 'tool_input': {'file_path': str(source)}}

    assert name_of(payload) == 'claude-code'
    assert targets_of(payload) == (source,)


def test_claude_code_also_reads_a_notebook_path(tmp_path: pathlib.Path) -> None:
    notebook = tmp_path / 'a.ipynb'
    notebook.write_text('{}', encoding='utf-8')
    payload = {'tool_name': 'NotebookEdit', 'tool_input': {'notebook_path': str(notebook)}}

    assert name_of(payload) == 'claude-code'


@pytest.mark.parametrize(
    'patch',
    [
        '*** Update File: {path}\n@@\n-old\n+new\n',
        '--- a/{path}\n+++ b/{path}\n@@\n',
        '--- {path}\n+++ {path}\n',
    ],
)
def test_codex_recovers_the_path_from_the_patch_body(source: pathlib.Path, patch: str) -> None:
    payload = {'tool_name': 'apply_patch', 'tool_input': {'command': patch.format(path=source)}}

    assert name_of(payload) == 'codex'
    assert targets_of(payload) == (source,)


def test_codex_ignores_the_dev_null_side_of_an_addition(source: pathlib.Path) -> None:
    patch = f'--- /dev/null\n+++ {source}\n'
    payload = {'tool_name': 'apply_patch', 'tool_input': {'command': patch}}

    assert targets_of(payload) == (source,)


def test_explicit_paths_serve_a_caller_with_no_harness(source: pathlib.Path) -> None:
    payload = {'paths': [str(source)]}

    assert name_of(payload) == 'explicit'
    assert targets_of(payload) == (source,)


def test_a_payload_no_harness_claims_selects_nothing() -> None:
    assert harness_for({'tool_name': 'Bash', 'tool_input': {'command': 'ls'}}) is None
    assert harness_for({}) is None


def test_a_read_only_tool_is_not_claimed(source: pathlib.Path) -> None:
    assert harness_for({'tool_name': 'Read', 'tool_input': {'file_path': str(source)}}) is None


def test_a_missing_file_is_dropped(tmp_path: pathlib.Path) -> None:
    payload = {'paths': [str(tmp_path / 'gone.py')]}
    assert targets_of(payload) == ()


def test_a_file_of_another_language_is_dropped(tmp_path: pathlib.Path) -> None:
    other = tmp_path / 'notes.md'
    other.write_text('# heading\n', encoding='utf-8')
    assert targets_of({'paths': [str(other)]}) == ()


def test_the_same_path_named_twice_is_visited_once(source: pathlib.Path) -> None:
    patch = f'--- {source}\n+++ {source}\n'
    payload = {'tool_name': 'apply_patch', 'tool_input': {'command': patch}}
    assert targets_of(payload) == (source,)


def test_the_fallback_comes_last_so_it_never_shadows_a_real_harness() -> None:
    assert isinstance(ALL_HARNESSES[-1], ExplicitPathsHarness)
    assert isinstance(ALL_HARNESSES[0], ClaudeCodeHarness)
    assert isinstance(ALL_HARNESSES[1], CodexHarness)


def targets_of(payload: typing.Mapping[str, object]) -> tuple[pathlib.Path, ...]:
    harness = harness_for(payload)
    return harness.targets(payload) if harness else ()


def name_of(payload: typing.Mapping[str, object]) -> str:
    harness = harness_for(payload)
    assert harness is not None, 'no harness claimed the payload'
    return harness.name
