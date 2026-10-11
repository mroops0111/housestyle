import dataclasses
import typing

from .diagnostic import RuleMetadata, Severity


@dataclasses.dataclass(frozen=True, slots=True)
class RuleSettings:
    severity: Severity | None = None
    options: typing.Mapping[str, object] = dataclasses.field(default_factory=dict)

    def integer(self, name: str, fallback: int) -> int:
        option = self.options.get(name, fallback)
        return option if isinstance(option, int) and not isinstance(option, bool) else fallback


@dataclasses.dataclass(frozen=True, slots=True)
class RuleSet:
    enabled_rule_ids: frozenset[str]
    settings: typing.Mapping[str, RuleSettings] = dataclasses.field(default_factory=dict)
    line_width: int = 120

    def is_enabled(self, rule_id: str) -> bool:
        return rule_id in self.enabled_rule_ids

    def settings_for(self, rule_id: str) -> RuleSettings:
        return self.settings.get(rule_id, RuleSettings())

    def severity_for(self, metadata: RuleMetadata) -> Severity:
        return self.settings_for(metadata.rule_id).severity or metadata.default_severity
