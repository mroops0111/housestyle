import fnmatch
import pathlib
import tomllib

from ..domain.rules import RuleSet, RuleSettings
from .schema import ConfigFile, RuleTable


CONFIG_NAME = 'housestyle.toml'
DEFAULT_WIDTH = 120


class TomlConfigSource:
    def __init__(self, available: tuple[str, ...]) -> None:
        self._available = available

    def resolve(self, path: str) -> RuleSet:
        config_file = self._read(path)
        if config_file is None:
            return self.defaults()
        return self._to_rule_set(config_file)

    def defaults(self) -> RuleSet:
        return RuleSet(enabled=frozenset(self._available), line_width=DEFAULT_WIDTH)

    def excludes(self, path: str) -> tuple[str, ...]:
        config_file = self._read(path)
        return config_file.housestyle.exclude if config_file else ()

    def is_excluded(self, target: pathlib.Path, root: pathlib.Path, patterns: tuple[str, ...]) -> bool:
        try:
            relative = target.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            relative = target.resolve().as_posix()
        return any(fnmatch.fnmatch(relative, pattern) for pattern in patterns)

    def root_for(self, path: str) -> pathlib.Path:
        config_path = self._locate(pathlib.Path(path))
        return config_path.parent if config_path else pathlib.Path.cwd()

    def _read(self, path: str) -> ConfigFile | None:
        config_path = self._locate(pathlib.Path(path))
        if config_path is None:
            return None
        try:
            raw_table = tomllib.loads(config_path.read_text(encoding='utf-8'))
        except (OSError, tomllib.TOMLDecodeError):
            return None
        return ConfigFile.parse(raw_table)

    def _locate(self, start: pathlib.Path) -> pathlib.Path | None:
        base = start if start.is_dir() else start.parent
        for candidate in (base.resolve(), *base.resolve().parents):
            config_path = candidate / CONFIG_NAME
            if config_path.is_file():
                return config_path
        return None

    def _to_rule_set(self, config_file: ConfigFile) -> RuleSet:
        enabled = set(self._available)
        settings: dict[str, RuleSettings] = {}

        for rule_id, entry in config_file.rules.items():
            if rule_id not in self._available:
                continue
            if entry is False or entry == 'off':
                enabled.discard(rule_id)
            elif isinstance(entry, RuleTable):
                settings[rule_id] = RuleSettings(severity=entry.resolved_severity, options=entry.options)
            elif isinstance(entry, str):
                settings[rule_id] = RuleSettings(severity=RuleTable(severity=entry).resolved_severity)

        return RuleSet(
            enabled=frozenset(enabled),
            settings=settings,
            line_width=config_file.housestyle.line_width,
        )
