import fnmatch
import pathlib
import tomllib
import typing

from ..domain.diagnostic import Severity
from ..domain.rules import RuleSet, RuleSettings


CONFIG_NAME = 'housestyle.toml'
DEFAULT_WIDTH = 120

SEVERITIES = {severity.name.lower(): severity for severity in Severity}


class TomlConfigSource:
    def __init__(self, available: tuple[str, ...]) -> None:
        self._available = available

    def resolve(self, path: str) -> RuleSet:
        found = self._locate(pathlib.Path(path))
        if found is None:
            return self.defaults()
        return self._parse(tomllib.loads(found.read_text(encoding='utf-8')))

    def excludes(self, path: str) -> tuple[str, ...]:
        found = self._locate(pathlib.Path(path))
        if found is None:
            return ()
        raw = tomllib.loads(found.read_text(encoding='utf-8')).get('housestyle')
        patterns = raw.get('exclude') if isinstance(raw, dict) else None
        if not isinstance(patterns, list):
            return ()
        return tuple(str(item) for item in patterns if isinstance(item, str))

    def is_excluded(self, target: pathlib.Path, root: pathlib.Path, patterns: tuple[str, ...]) -> bool:
        try:
            relative = target.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            relative = target.resolve().as_posix()
        return any(fnmatch.fnmatch(relative, pattern) for pattern in patterns)

    def root_for(self, path: str) -> pathlib.Path:
        found = self._locate(pathlib.Path(path))
        return found.parent if found else pathlib.Path.cwd()

    def defaults(self) -> RuleSet:
        return RuleSet(enabled=frozenset(self._available), line_width=DEFAULT_WIDTH)

    def _locate(self, start: pathlib.Path) -> pathlib.Path | None:
        base = start if start.is_dir() else start.parent
        for candidate in (base.resolve(), *base.resolve().parents):
            found = candidate / CONFIG_NAME
            if found.is_file():
                return found
        return None

    def _parse(self, raw: typing.Mapping[str, object]) -> RuleSet:
        root = raw.get('housestyle')
        width = DEFAULT_WIDTH
        if isinstance(root, dict):
            candidate = root.get('line-width')
            if isinstance(candidate, int) and not isinstance(candidate, bool):
                width = candidate

        section = raw.get('rules')
        rules = section if isinstance(section, dict) else {}
        enabled: set[str] = set(self._available)
        settings: dict[str, RuleSettings] = {}

        for rule_id, value in rules.items():
            if rule_id not in self._available:
                continue
            if value is False or value == 'off':
                enabled.discard(rule_id)
                continue
            if isinstance(value, str):
                settings[rule_id] = RuleSettings(severity=SEVERITIES.get(value))
            elif isinstance(value, dict):
                severity = value.get('severity')
                options = {key: item for key, item in value.items() if key != 'severity'}
                settings[rule_id] = RuleSettings(
                    severity=SEVERITIES.get(severity) if isinstance(severity, str) else None,
                    options=options,
                )
        return RuleSet(enabled=frozenset(enabled), settings=settings, line_width=width)
