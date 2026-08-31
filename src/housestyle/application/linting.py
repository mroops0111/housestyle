import dataclasses

from ..domain.comment import CommentGroup
from ..domain.diagnostic import Diagnostic, Report
from ..domain.document import Document
from ..domain.ports import SourceParser
from ..domain.rules import Rule, RuleContext, RuleSet


class RuleEngine:
    def __init__(self, rules: tuple[Rule, ...]) -> None:
        duplicates = self._duplicate_ids(rules)
        if duplicates:
            raise ValueError(f'Duplicate rule ids registered: {sorted(duplicates)}')
        self._rules = rules

    @property
    def rule_ids(self) -> tuple[str, ...]:
        return tuple(rule.meta.rule_id for rule in self._rules)

    def run(self, document: Document, blocks: tuple[CommentGroup, ...], rules: RuleSet) -> tuple[Diagnostic, ...]:
        context = RuleContext(document=document, rules=rules)
        active = [rule for rule in self._rules if rules.is_enabled(rule.meta.rule_id)]
        found: list[Diagnostic] = []
        for block in blocks:
            for rule in active:
                for diagnostic in rule.check(block, context):
                    found.append(self._with_severity(diagnostic, rule, rules))
        return tuple(found)

    def _with_severity(self, diagnostic: Diagnostic, rule: Rule, rules: RuleSet) -> Diagnostic:
        severity = rules.severity_for(rule.meta)
        if diagnostic.severity is severity:
            return diagnostic
        return dataclasses.replace(diagnostic, severity=severity)

    def _duplicate_ids(self, rules: tuple[Rule, ...]) -> set[str]:
        seen: set[str] = set()
        duplicates: set[str] = set()
        for rule in rules:
            if rule.meta.rule_id in seen:
                duplicates.add(rule.meta.rule_id)
            seen.add(rule.meta.rule_id)
        return duplicates


class LintDocument:
    def __init__(self, parser: SourceParser, engine: RuleEngine) -> None:
        self._parser = parser
        self._engine = engine

    def run(self, document: Document, rules: RuleSet) -> Report:
        if not self._parser.supports(document.language_id):
            return Report()
        blocks = self._parser.parse(document)
        diagnostics = self._engine.run(document, blocks, rules)
        ordered = sorted(diagnostics, key=lambda item: (item.range.start, item.rule_id))
        return Report(tuple(ordered))
