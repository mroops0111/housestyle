import pathlib
import re
import shutil
import subprocess

from ...domain.diagnostic import Diagnostic, Fix, Severity
from ...domain.document import Document
from ...domain.position import Position, SourceRange
from ...domain.text import TextEdit


LOCATION = re.compile(r'^(?P<path>.+?):(?P<line>\d+):(?P<column>\d+)$')
TIMEOUT_SECONDS = 30
RULE_ID = 'autocorrect/spacing'


class AutoCorrectAdapter:
    name = 'autocorrect'

    def __init__(self, executable: str = 'autocorrect') -> None:
        self._executable = executable

    def is_available(self) -> bool:
        return shutil.which(self._executable) is not None

    def run(self, document: Document) -> tuple[Diagnostic, ...]:
        path = pathlib.Path(document.uri.removeprefix('file://'))
        if not self.is_available() or not path.is_file():
            return ()
        corrected = self._corrected(path)
        if corrected is None or corrected == document.text:
            return ()
        return self._diff(document, corrected)

    def _corrected(self, path: pathlib.Path) -> str | None:
        try:
            result = subprocess.run(  # noqa: S603
                [self._executable, '--stdin', str(path)],
                capture_output=True,
                text=True,
                check=False,
                timeout=TIMEOUT_SECONDS,
                input=path.read_text(encoding='utf-8'),
            )
        except (OSError, UnicodeDecodeError, subprocess.TimeoutExpired):
            return None
        return result.stdout if result.stdout else None

    def _diff(self, document: Document, corrected: str) -> tuple[Diagnostic, ...]:
        before = document.text.splitlines(keepends=True)
        after = corrected.splitlines(keepends=True)
        if len(before) != len(after):
            return ()
        found: list[Diagnostic] = []
        for index, (original, fixed) in enumerate(zip(before, after, strict=True)):
            if original == fixed:
                continue
            start = document.positions.to_offset(Position(index, 0))
            end = start + len(original.rstrip('\n').encode('utf-8'))
            found.append(
                Diagnostic(
                    rule_id=RULE_ID,
                    range=SourceRange(start, end),
                    message='Spacing or punctuation between CJK and Latin text needs correcting.',
                    severity=Severity.ERROR,
                    fix=Fix.targeted(TextEdit(SourceRange(start, end), fixed.rstrip('\n'))),
                    source=self.name,
                )
            )
        return tuple(found)
