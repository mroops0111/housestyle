import dataclasses
import typing

from .comment import CommentBlock
from .diagnostic import Diagnostic, RuleMeta, Severity
from .document import Document


@dataclasses.dataclass(frozen=True, slots=True)
class RuleSettings:
    severity: Severity | None = None
    options: typing.Mapping[str, object] = dataclasses.field(default_factory=dict)

    def integer(self, name: str, fallback: int) -> int:
        value = self.options.get(name, fallback)
        return value if isinstance(value, int) and not isinstance(value, bool) else fallback


@dataclasses.dataclass(frozen=True, slots=True)
class RuleSet:
    enabled: frozenset[str]
    settings: typing.Mapping[str, RuleSettings] = dataclasses.field(default_factory=dict)
    line_width: int = 120

    def is_enabled(self, rule_id: str) -> bool:
        return rule_id in self.enabled

    def settings_for(self, rule_id: str) -> RuleSettings:
        return self.settings.get(rule_id, RuleSettings())

    def severity_for(self, meta: RuleMeta) -> Severity:
        return self.settings_for(meta.rule_id).severity or meta.default_severity


@dataclasses.dataclass(frozen=True, slots=True)
class RuleContext:
    document: Document
    rules: RuleSet

    @property
    def line_width(self) -> int:
        return self.rules.line_width

    def settings(self, rule_id: str) -> RuleSettings:
        return self.rules.settings_for(rule_id)


class Rule(typing.Protocol):
    @property
    def meta(self) -> RuleMeta: ...

    def check(self, block: CommentBlock, context: RuleContext) -> typing.Iterable[Diagnostic]: ...


class ConfigSource(typing.Protocol):
    def resolve(self, path: str) -> RuleSet: ...
