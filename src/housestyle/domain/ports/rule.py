import abc
import dataclasses
import typing

from ..models.comment import CommentGroup
from ..models.diagnostic import Diagnostic, RuleMetadata
from ..models.document import Document
from ..models.rule_set import RuleSet, RuleSettings


@dataclasses.dataclass(frozen=True, slots=True)
class RuleContext:
    document: Document
    rule_set: RuleSet

    @property
    def line_width(self) -> int:
        return self.rule_set.line_width

    def settings(self, rule_id: str) -> RuleSettings:
        return self.rule_set.settings_for(rule_id)


class Rule(abc.ABC):
    metadata: RuleMetadata

    @abc.abstractmethod
    def check(self, group: CommentGroup, context: RuleContext) -> typing.Iterable[Diagnostic]: ...
