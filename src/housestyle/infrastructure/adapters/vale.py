import pathlib
import shutil
import subprocess

from ...domain.diagnostic import Diagnostic, Fix
from ...domain.document import Document
from ...domain.position import Position, SourceRange
from ..schema import ValeAlert, ValeReport


TIMEOUT_SECONDS = 30


class ValeAdapter:
    name = 'vale'

    def __init__(self, executable: str = 'vale') -> None:
        self._executable = executable

    def is_available(self) -> bool:
        return shutil.which(self._executable) is not None

    def run(self, document: Document) -> tuple[Diagnostic, ...]:
        path = pathlib.Path(document.uri.removeprefix('file://'))
        if not self.is_available() or not path.is_file():
            return ()
        try:
            completed = subprocess.run(  # noqa: S603
                [self._executable, '--no-exit', '--output=JSON', str(path)],
                capture_output=True,
                text=True,
                check=False,
                timeout=TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired):
            return ()
        return self._decode(document, completed.stdout)

    def _decode(self, document: Document, payload: str) -> tuple[Diagnostic, ...]:
        diagnostics: list[Diagnostic] = []
        for alert in ValeReport.parse(payload):
            diagnostic = self._one(document, alert)
            if diagnostic is not None:
                diagnostics.append(diagnostic)
        return tuple(diagnostics)

    def _one(self, document: Document, alert: ValeAlert) -> Diagnostic | None:
        start_column, end_column = alert.span
        try:
            start = document.positions.to_offset(Position(alert.line - 1, start_column - 1))
            end = document.positions.to_offset(Position(alert.line - 1, end_column))
        except ValueError:
            return None
        return Diagnostic(
            rule_id=alert.check,
            range=SourceRange(start, max(start, end)),
            message=alert.message,
            severity=alert.resolved_severity,
            fix=Fix.rewrite(),
            source=self.name,
        )
