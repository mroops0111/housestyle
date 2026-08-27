import pathlib
import shutil
import subprocess

import pytest


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG = REPO_ROOT / '.vale.ini'
FIXTURES = REPO_ROOT / 'tests' / 'fixtures' / 'vale'

EXPECTED_RULES = [
    'SignatureTag',
    'EmDash',
    'EditHistory',
    'ExternalRef',
    'MidSentenceColon',
    'Semicolon',
    'Ellipsis',
]

pytestmark = pytest.mark.skipif(shutil.which('vale') is None, reason='vale is not installed')


def run_vale(*targets: str) -> str:
    result = subprocess.run(
        ['vale', '--no-exit', '--output=line', f'--config={CONFIG}', *targets],
        cwd=REPO_ROOT,
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


def test_allowed_constructs_stay_silent() -> None:
    assert run_vale('tests/fixtures/vale/clean.md').strip() == ''


def test_housestyle_lints_itself_clean() -> None:
    assert run_vale('src', 'tests', 'README.md').strip() == ''
