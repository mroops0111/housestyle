import pathlib

from housestyle.domain import Severity
from housestyle.infrastructure import CONFIG_NAME, TomlConfigSource


AVAILABLE = ('mid-clause-break', 'line-too-long', 'stub-fragment')


def source() -> TomlConfigSource:
    return TomlConfigSource(AVAILABLE)


def write(directory: pathlib.Path, body: str) -> pathlib.Path:
    (directory / CONFIG_NAME).write_text(body, encoding='utf-8')
    target = directory / 'module.py'
    target.write_text('# note\n', encoding='utf-8')
    return target


def test_defaults_enable_every_available_rule(tmp_path: pathlib.Path) -> None:
    rules = source().resolve(str(tmp_path))
    assert rules.enabled == frozenset(AVAILABLE)
    assert rules.line_width == 120


def test_configuration_is_found_by_walking_upward(tmp_path: pathlib.Path) -> None:
    nested = tmp_path / 'a' / 'b'
    nested.mkdir(parents=True)
    write(tmp_path, '[housestyle]\nline-width = 88\n')
    assert source().resolve(str(nested / 'module.py')).line_width == 88


def test_a_rule_can_be_switched_off(tmp_path: pathlib.Path) -> None:
    target = write(tmp_path, '[rules]\nmid-clause-break = false\n')
    rules = source().resolve(str(target))
    assert not rules.is_enabled('mid-clause-break')
    assert rules.is_enabled('line-too-long')


def test_a_severity_string_is_honoured(tmp_path: pathlib.Path) -> None:
    target = write(tmp_path, '[rules]\nmid-clause-break = "warning"\n')
    rules = source().resolve(str(target))
    assert rules.settings_for('mid-clause-break').severity is Severity.WARNING


def test_a_table_carries_severity_and_options(tmp_path: pathlib.Path) -> None:
    target = write(tmp_path, '[rules]\nstub-fragment = { severity = "warning", minimum_characters = 30 }\n')
    settings = source().resolve(str(target)).settings_for('stub-fragment')
    assert settings.severity is Severity.WARNING
    assert settings.integer('minimum_characters', 24) == 30


def test_an_unknown_rule_is_ignored(tmp_path: pathlib.Path) -> None:
    target = write(tmp_path, '[rules]\nnot-a-rule = false\n')
    assert source().resolve(str(target)).enabled == frozenset(AVAILABLE)


def test_a_nonsense_width_falls_back_to_the_default(tmp_path: pathlib.Path) -> None:
    target = write(tmp_path, '[housestyle]\nline-width = "wide"\n')
    assert source().resolve(str(target)).line_width == 120


PYPROJECT = 'pyproject.toml'


def write_pyproject(directory: pathlib.Path, body: str) -> pathlib.Path:
    (directory / PYPROJECT).write_text(body, encoding='utf-8')
    target = directory / 'module.py'
    target.write_text('# note\n', encoding='utf-8')
    return target


def test_settings_are_read_from_pyproject(tmp_path: pathlib.Path) -> None:
    target = write_pyproject(tmp_path, '[project]\nname = "x"\n\n[tool.housestyle]\nline-width = 96\n')
    assert source().resolve(str(target)).line_width == 96


def test_rules_nest_under_the_tool_table_in_pyproject(tmp_path: pathlib.Path) -> None:
    body = '[tool.housestyle]\nline-width = 96\n\n[tool.housestyle.rules]\nmid-clause-break = false\n'
    rules = source().resolve(str(write_pyproject(tmp_path, body)))

    assert not rules.is_enabled('mid-clause-break')
    assert rules.is_enabled('line-too-long')


def test_excludes_are_read_from_pyproject(tmp_path: pathlib.Path) -> None:
    body = '[tool.housestyle]\nexclude = ["build/**"]\n'
    assert source().excludes(str(write_pyproject(tmp_path, body))) == ('build/**',)


def test_a_pyproject_without_our_table_is_ignored(tmp_path: pathlib.Path) -> None:
    target = write_pyproject(tmp_path, '[project]\nname = "x"\n\n[tool.ruff]\nline-length = 88\n')
    assert source().resolve(str(target)).line_width == 120


def test_a_dedicated_file_wins_over_pyproject(tmp_path: pathlib.Path) -> None:
    (tmp_path / PYPROJECT).write_text('[tool.housestyle]\nline-width = 96\n', encoding='utf-8')
    target = write(tmp_path, '[housestyle]\nline-width = 70\n')
    assert source().resolve(str(target)).line_width == 70
