from ..domain.models.diagnostic import Report
from ..domain.models.document import Document
from ..domain.models.rule_set import RuleSet
from ..domain.ports.external_linter import ExternalLinter
from .linter import Linter


class ReportAggregator:
    def __init__(self, linter: Linter, external_linters: tuple[ExternalLinter, ...] = ()) -> None:
        self._linter = linter
        self._external_linters = external_linters

    def run(self, document: Document, rule_set: RuleSet) -> Report:
        report = self._linter.run(document, rule_set)
        missing_sources: list[str] = []
        for external_linter in self._external_linters:
            if not external_linter.is_available():
                missing_sources.append(external_linter.name)
                continue
            report = report.merged_with(Report(external_linter.run(document)))
        if missing_sources:
            report = report.merged_with(Report(unavailable_sources=tuple(missing_sources)))
        return report
