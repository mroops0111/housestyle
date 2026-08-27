import pathlib

from housestyle.domain import Severity
from housestyle.infrastructure import CONFIG_NAME, TomlConfigSource


AVAILABLE = ('wrap-point', 'line-width', 'stub-fragment')


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
    target = write(tmp_path, '[rules]\nwrap-point = false\n')
    rules = source().resolve(str(target))
    assert not rules.is_enabled('wrap-point')
    assert rules.is_enabled('line-width')


def test_a_severity_string_is_honoured(tmp_path: pathlib.Path) -> None:
    target = write(tmp_path, '[rules]\nwrap-point = "warning"\n')
    rules = source().resolve(str(target))
    assert rules.settings_for('wrap-point').severity is Severity.WARNING


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
