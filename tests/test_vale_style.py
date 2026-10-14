import pathlib
import shutil
import subprocess

import pytest


REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG = REPOSITORY_ROOT / '.vale.ini'
FIXTURES = REPOSITORY_ROOT / 'tests' / 'fixtures' / 'vale'

EXPECTED_RULES = [
    'SignatureTag',
    'EmDash',
    'EditHistory',
    'ExternalRef',
    'MidSentenceColon',
    'Semicolon',
    'Ellipsis',
    'DateRef',
]

pytestmark = pytest.mark.skipif(shutil.which('vale') is None, reason='vale is not installed')


def run_vale(*targets: str) -> str:
    result = subprocess.run(
        ['vale', '--no-exit', '--output=line', f'--config={CONFIG}', *targets],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def test_every_rule_fires_on_the_violation_fixture(tmp_path: pathlib.Path) -> None:
    staged = tmp_path / 'violations.py'
    staged.write_text((FIXTURES / 'violations.py').read_text(encoding='utf-8'), encoding='utf-8')
    output = run_vale(str(staged))
    missing = [rule for rule in EXPECTED_RULES if rule not in output]
    assert not missing, f'rules that failed to fire: {missing}'


def test_allowed_constructs_stay_silent(tmp_path: pathlib.Path) -> None:
    """Staged outside the repository, whose config switches the fixtures off."""
    staged = tmp_path / 'clean.md'
    staged.write_text((FIXTURES / 'clean.md').read_text(encoding='utf-8'), encoding='utf-8')
    assert run_vale(str(staged)).strip() == ''


def test_a_date_warns_rather_than_fails(tmp_path: pathlib.Path) -> None:
    staged = tmp_path / 'dated.py'
    staged.write_text('def f():\n    # the MCP 2025-11-25 spec forbids it.\n    pass\n', encoding='utf-8')
    result = subprocess.run(
        ['vale', '--output=line', f'--config={CONFIG}', str(staged)],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert 'subedit.DateRef' in result.stdout
    assert result.returncode == 0, 'a warning alone must not fail the run'


def test_subedit_lints_itself_clean() -> None:
    assert run_vale('src', 'tests', 'README.md').strip() == ''
