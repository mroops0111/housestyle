import dataclasses

from ..domain.diagnostic import Diagnostic, FixKind, Report
from ..domain.document import Document
from ..domain.rules import RuleSet
from ..domain.text import TextEdit, apply_edits
from .linting import LintDocument


MAX_ROUNDS = 10


@dataclasses.dataclass(frozen=True, slots=True)
class FixOutcome:
    document: Document
    report: Report
    rounds: int
    applied: int

    @property
    def changed(self) -> bool:
        return self.applied > 0

    @property
    def unresolved(self) -> tuple[Diagnostic, ...]:
        return self.report.needing_author


class FixDocument:
    def __init__(self, lint: LintDocument, max_rounds: int = MAX_ROUNDS) -> None:
        self._lint = lint
        self._max_rounds = max_rounds

    def run(self, document: Document, rules: RuleSet) -> FixOutcome:
        document_now = document
        applied = 0
        rounds = 0
        report = self._lint.run(document_now, rules)

        while rounds < self._max_rounds:
            edits = self._next_edits(report)
            if not edits:
                break
            document_now = document_now.with_text(apply_edits(document_now.text, edits))
            applied += len(edits)
            rounds += 1
            report = self._lint.run(document_now, rules)

        return FixOutcome(document=document_now, report=report, rounds=rounds, applied=applied)

    def _next_edits(self, report: Report) -> tuple[TextEdit, ...]:
        for kind in (FixKind.TARGETED, FixKind.REFLOW):
            edits = self._compatible(report.by_kind(kind))
            if edits:
                return edits
        return ()

    def _compatible(self, diagnostics: tuple[Diagnostic, ...]) -> tuple[TextEdit, ...]:
        candidates = [edit for diagnostic in diagnostics if diagnostic.fix for edit in diagnostic.fix.edits]
        candidates.sort(key=lambda edit: (edit.range.start, edit.range.end))
        accepted_edits: list[TextEdit] = []
        for edit in candidates:
            if accepted_edits and accepted_edits[-1].range.overlaps(edit.range):
                continue
            accepted_edits.append(edit)
        return tuple(accepted_edits)
