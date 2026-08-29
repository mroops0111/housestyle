from ..domain.diagnostic import Report
from ..domain.document import Document
from ..domain.external import ExternalLinter
from ..domain.rules import RuleSet
from .linting import LintDocument


class Aggregator:
    def __init__(self, lint: LintDocument, linters: tuple[ExternalLinter, ...] = ()) -> None:
        self._lint = lint
        self._linters = linters

    def run(self, document: Document, rules: RuleSet) -> Report:
        report = self._lint.run(document, rules)
        unavailable: list[str] = []
        for linter in self._linters:
            if not linter.is_available():
                unavailable.append(linter.name)
                continue
            report = report.merged_with(Report(linter.run(document)))
        if unavailable:
            report = report.merged_with(Report(unavailable_sources=tuple(unavailable)))
        return report
