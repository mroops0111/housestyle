import dataclasses

from ..domain.diagnostic import Diagnostic, FixKind, Report
from ..domain.document import Document
from ..domain.rules import RuleSet
from ..domain.text import TextEdit, apply_edits
from .linting import LintDocument


MAX_ROUNDS = 10


@dataclasses.dataclass(frozen=True, slots=True)
class FixResult:
    document: Document
    report: Report
    round_count: int
    applied_edit_count: int

    @property
    def has_changes(self) -> bool:
        return self.applied_edit_count > 0

    @property
    def unresolved_findings(self) -> tuple[Diagnostic, ...]:
        return self.report.needing_author


class FixDocument:
    def __init__(self, lint: LintDocument, max_rounds: int = MAX_ROUNDS) -> None:
        self._lint = lint
        self._max_rounds = max_rounds

    def run(self, document: Document, rules: RuleSet) -> FixResult:
        working_document = document
        applied_edit_count = 0
        round_count = 0
        report = self._lint.run(working_document, rules)

        while round_count < self._max_rounds:
            edits = self._next_edits(report)
            if not edits:
                break
            working_document = working_document.with_text(apply_edits(working_document.text, edits))
            applied_edit_count += len(edits)
            round_count += 1
            report = self._lint.run(working_document, rules)

        return FixResult(
            document=working_document, report=report, round_count=round_count, applied_edit_count=applied_edit_count
        )

    def _next_edits(self, report: Report) -> tuple[TextEdit, ...]:
        for mechanical_kind in (FixKind.TARGETED, FixKind.REFLOW):
            edits = self._without_overlaps(report.by_fix_kind(mechanical_kind))
            if edits:
                return edits
        return ()

    def _without_overlaps(self, diagnostics: tuple[Diagnostic, ...]) -> tuple[TextEdit, ...]:
        candidate_edits = [edit for diagnostic in diagnostics if diagnostic.fix for edit in diagnostic.fix.edits]
        candidate_edits.sort(key=lambda edit: (edit.range.start, edit.range.end))
        accepted_edits: list[TextEdit] = []
        for edit in candidate_edits:
            if accepted_edits and accepted_edits[-1].range.overlaps(edit.range):
                continue
            accepted_edits.append(edit)
        return tuple(accepted_edits)
