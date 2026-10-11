from ..domain.models.diagnostic import Report
from ..domain.models.document import Document
from ..domain.models.rule_set import RuleSet
from ..domain.ports.external_linter import ExternalLinter
from .linter import Linter


class ReportAggregator:
    def __init__(self, linter: Linter, linters: tuple[ExternalLinter, ...] = ()) -> None:
        self._linter = linter
        self._linters = linters

    def run(self, document: Document, rule_set: RuleSet) -> Report:
        report = self._linter.run(document, rule_set)
        missing_sources: list[str] = []
        for linter in self._linters:
            if not linter.is_available():
                missing_sources.append(linter.name)
                continue
            report = report.merged_with(Report(linter.run(document)))
        if missing_sources:
            report = report.merged_with(Report(unavailable_sources=tuple(missing_sources)))
        return report
