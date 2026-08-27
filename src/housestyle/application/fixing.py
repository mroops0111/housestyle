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
    def remaining(self) -> tuple[Diagnostic, ...]:
        return self.report.needing_author


class FixDocument:
    def __init__(self, lint: LintDocument, max_rounds: int = MAX_ROUNDS) -> None:
        self._lint = lint
        self._max_rounds = max_rounds

    def run(self, document: Document, rules: RuleSet) -> FixOutcome:
        current = document
        applied = 0
        rounds = 0
        report = self._lint.run(current, rules)

        while rounds < self._max_rounds:
            edits = self._next_edits(report)
            if not edits:
                break
            current = current.with_text(apply_edits(current.text, edits))
            applied += len(edits)
            rounds += 1
            report = self._lint.run(current, rules)

        return FixOutcome(document=current, report=report, rounds=rounds, applied=applied)

    def _next_edits(self, report: Report) -> tuple[TextEdit, ...]:
        for kind in (FixKind.TARGETED, FixKind.REFLOW):
            edits = self._compatible(report.by_kind(kind))
            if edits:
                return edits
        return ()

    def _compatible(self, diagnostics: tuple[Diagnostic, ...]) -> tuple[TextEdit, ...]:
        candidates = [edit for item in diagnostics if item.fix for edit in item.fix.edits]
        candidates.sort(key=lambda edit: (edit.range.start, edit.range.end))
        chosen: list[TextEdit] = []
        for edit in candidates:
            if chosen and chosen[-1].range.overlaps(edit.range):
                continue
            chosen.append(edit)
        return tuple(chosen)
