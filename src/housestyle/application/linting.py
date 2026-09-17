import dataclasses

from ..domain.comment import CommentGroup
from ..domain.diagnostic import Diagnostic, Report
from ..domain.document import Document
from ..domain.ports import SourceParser
from ..domain.rules import Rule, RuleContext, RuleSet


class RuleEngine:
    def __init__(self, rules: tuple[Rule, ...]) -> None:
        duplicate_ids = self._find_duplicate_ids(rules)
        if duplicate_ids:
            raise ValueError(f'Duplicate rule ids registered: {sorted(duplicate_ids)}')
        self._rules = rules

    def run(self, document: Document, groups: tuple[CommentGroup, ...], rules: RuleSet) -> tuple[Diagnostic, ...]:
        context = RuleContext(document=document, rules=rules)
        enabled_rules = [rule for rule in self._rules if rules.is_enabled(rule.meta.rule_id)]
        diagnostics: list[Diagnostic] = []
        for group in groups:
            for rule in enabled_rules:
                for diagnostic in rule.check(group, context):
                    diagnostics.append(self._with_severity(diagnostic, rule, rules))
        return tuple(diagnostics)

    def _with_severity(self, diagnostic: Diagnostic, rule: Rule, rules: RuleSet) -> Diagnostic:
        severity = rules.severity_for(rule.meta)
        if diagnostic.severity is severity:
            return diagnostic
        return dataclasses.replace(diagnostic, severity=severity)

    def _find_duplicate_ids(self, rules: tuple[Rule, ...]) -> set[str]:
        seen_ids: set[str] = set()
        duplicate_ids: set[str] = set()
        for rule in rules:
            if rule.meta.rule_id in seen_ids:
                duplicate_ids.add(rule.meta.rule_id)
            seen_ids.add(rule.meta.rule_id)
        return duplicate_ids


class LintDocument:
    def __init__(self, parser: SourceParser, engine: RuleEngine) -> None:
        self._parser = parser
        self._engine = engine

    def run(self, document: Document, rules: RuleSet) -> Report:
        if not self._parser.supports(document.language_id):
            return Report()
        groups = self._parser.parse(document)
        diagnostics = self._engine.run(document, groups, rules)
        sorted_diagnostics = sorted(diagnostics, key=lambda item: (item.range.start, item.rule_id))
        return Report(tuple(sorted_diagnostics))
