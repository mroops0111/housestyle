import json
import pathlib
import subprocess
import typing

import pytest

from housestyle.presentation.harnesses.claude_code import EDIT_TOOLS


ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / '.claude-plugin' / 'plugin.json'
MARKETPLACE = ROOT / '.claude-plugin' / 'marketplace.json'
HOOKS = ROOT / 'hooks' / 'hooks.json'
WRAPPER = ROOT / 'hooks' / 'run-housestyle-hook.sh'


def load(path: pathlib.Path) -> typing.Any:
    return json.loads(path.read_text(encoding='utf-8'))


@pytest.mark.parametrize('path', [MANIFEST, MARKETPLACE, HOOKS])
def test_every_plugin_file_is_valid_json(path: pathlib.Path) -> None:
    assert isinstance(load(path), dict)


def test_the_manifest_names_the_plugin() -> None:
    assert load(MANIFEST)['name'] == 'housestyle'


def test_the_manifest_version_matches_the_package() -> None:
    pyproject = (ROOT / 'pyproject.toml').read_text(encoding='utf-8')
    declared = next(line for line in pyproject.splitlines() if line.startswith('version'))

    assert load(MANIFEST)['version'] in declared, 'a plugin claiming a different version misleads whoever installs it'


def test_the_hook_matcher_covers_every_tool_the_harness_recognises() -> None:
    entries = load(HOOKS)['hooks']['PostToolUse']
    matched = set(entries[0]['matcher'].split('|'))

    assert matched == EDIT_TOOLS, 'a tool the harness reads but the matcher omits never reaches the hook'


def test_the_hook_runs_the_wrapper_from_the_plugin_directory() -> None:
    command = load(HOOKS)['hooks']['PostToolUse'][0]['hooks'][0]['command']

    assert '${CLAUDE_PLUGIN_ROOT}' in command, 'a bare path breaks once the plugin is installed elsewhere'
    assert command.endswith(WRAPPER.name)


def test_the_wrapper_is_executable() -> None:
    assert WRAPPER.stat().st_mode & 0o111, 'a wrapper without the execute bit fails only once installed'


def test_the_wrapper_is_valid_shell() -> None:
    subprocess.run(['bash', '-n', str(WRAPPER)], check=True, capture_output=True)


def test_the_wrapper_says_what_to_install_when_nothing_is_found() -> None:
    completed = subprocess.run(
        ['bash', str(WRAPPER)],
        check=False,
        capture_output=True,
        text=True,
        env={'PATH': '/usr/bin:/bin'},
        input='',
    )

    assert completed.returncode == 1
    assert 'uv tool install' in completed.stderr, 'a missing command must say how to get it'


def test_the_marketplace_points_at_this_repository() -> None:
    listed = load(MARKETPLACE)['plugins']

    assert [plugin['name'] for plugin in listed] == ['housestyle']
    assert listed[0]['source']['repo'] == 'mroops0111/housestyle'
