import pathlib
import re
import shutil
import subprocess

from ...domain.diagnostic import Diagnostic, Fix, Severity
from ...domain.document import Document
from ...domain.position import Position, SourceRange
from ...domain.text import TextEdit


LOCATION = re.compile(r'^(?P<source_path>.+?):(?P<line>\d+):(?P<column>\d+)$')
TIMEOUT_SECONDS = 30
RULE_ID = 'autocorrect/spacing'


class AutoCorrectAdapter:
    name = 'autocorrect'

    def __init__(self, executable: str = 'autocorrect') -> None:
        self._executable = executable

    def is_available(self) -> bool:
        return shutil.which(self._executable) is not None

    def run(self, document: Document) -> tuple[Diagnostic, ...]:
        source_path = pathlib.Path(document.uri.removeprefix('file://'))
        if not self.is_available() or not source_path.is_file():
            return ()
        corrected_text = self._run_autocorrect(source_path)
        if corrected_text is None or corrected_text == document.text:
            return ()
        return self._diff_lines(document, corrected_text)

    def _run_autocorrect(self, source_path: pathlib.Path) -> str | None:
        try:
            process = subprocess.run(  # noqa: S603
                [self._executable, '--stdin', str(source_path)],
                capture_output=True,
                text=True,
                check=False,
                timeout=TIMEOUT_SECONDS,
                input=source_path.read_text(encoding='utf-8'),
            )
        except (OSError, UnicodeDecodeError, subprocess.TimeoutExpired):
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
