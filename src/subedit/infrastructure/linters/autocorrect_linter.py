import re
import shutil
import subprocess

from ...domain.models.diagnostic import Diagnostic, Fix, Severity
from ...domain.models.document import Document
from ...domain.models.position import Position, SourceRange
from ...domain.models.text import TextEdit
from ...domain.ports.external_linter import ExternalLinter


LOCATION = re.compile(r'^(?P<source_path>.+?):(?P<line>\d+):(?P<column>\d+)$')
TIMEOUT_SECONDS = 30
RULE_ID = 'autocorrect/spacing'


class AutoCorrectLinter(ExternalLinter):
    name = 'autocorrect'

    def __init__(self, executable: str = 'autocorrect') -> None:
        self._executable = executable

    def is_available(self) -> bool:
        return shutil.which(self._executable) is not None

    def run(self, document: Document) -> tuple[Diagnostic, ...]:
        if not self.is_available():
            return ()
        corrected_text = self._run_autocorrect(document)
        if corrected_text is None or corrected_text == document.text:
            return ()
        return self._diff_lines(document, corrected_text)

    # The path only tells AutoCorrect which file type to parse, so it need not exist on disk.
    def _run_autocorrect(self, document: Document) -> str | None:
        try:
            process = subprocess.run(  # noqa: S603
                [self._executable, '--stdin', document.uri.removeprefix('file://')],
                capture_output=True,
                text=True,
                check=False,
                timeout=TIMEOUT_SECONDS,
                input=document.text,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        return process.stdout if process.stdout else None

    def _diff_lines(self, document: Document, corrected_text: str) -> tuple[Diagnostic, ...]:
        original_lines = document.text.splitlines(keepends=True)
        corrected_lines = corrected_text.splitlines(keepends=True)
        if len(original_lines) != len(corrected_lines):
            return ()
        diagnostics: list[Diagnostic] = []
        for index, (original, fixed) in enumerate(zip(original_lines, corrected_lines, strict=True)):
            if original == fixed:
                continue
            start_offset = document.positions.to_offset(Position(index, 0))
            end_offset = start_offset + len(original.rstrip('\n').encode('utf-8'))
            diagnostics.append(
                Diagnostic(
                    rule_id=RULE_ID,
                    range=SourceRange(start_offset, end_offset),
                    message='Spacing or punctuation between CJK and Latin text needs correcting.',
                    severity=Severity.ERROR,
                    fix=Fix.targeted(TextEdit(SourceRange(start_offset, end_offset), fixed.rstrip('\n'))),
                    source=self.name,
                )
            )
        return tuple(diagnostics)
