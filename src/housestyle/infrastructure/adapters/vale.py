import json
import pathlib
import shutil
import subprocess

from ...domain.diagnostic import Diagnostic, Fix, Severity
from ...domain.document import Document
from ...domain.position import Position, SourceRange


SEVERITIES = {'error': Severity.ERROR, 'warning': Severity.WARNING, 'suggestion': Severity.SUGGESTION}
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
            result = subprocess.run(  # noqa: S603
                [self._executable, '--no-exit', '--output=JSON', str(path)],
                capture_output=True,
                text=True,
                check=False,
                timeout=TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired):
            return ()
        return self._decode(document, result.stdout)

    def _decode(self, document: Document, text: str) -> tuple[Diagnostic, ...]:
        try:
            parsed = json.loads(text or '{}')
        except json.JSONDecodeError:
            return ()
        if not isinstance(parsed, dict):
            return ()
        found: list[Diagnostic] = []
        for alerts in parsed.values():
            if not isinstance(alerts, list):
                continue
            for alert in alerts:
                if isinstance(alert, dict):
                    diagnostic = self._one(document, alert)
                    if diagnostic is not None:
                        found.append(diagnostic)
        return tuple(found)

    def _one(self, document: Document, alert: dict[str, object]) -> Diagnostic | None:
        line = alert.get('Line')
        span = alert.get('Span')
        check = alert.get('Check')
        message = alert.get('Message')
        if not isinstance(line, int) or not isinstance(check, str) or not isinstance(message, str):
            return None
        start_column, end_column = self._span(span)
        try:
            start = document.positions.to_offset(Position(line - 1, start_column - 1))
            end = document.positions.to_offset(Position(line - 1, end_column))
        except ValueError:
            return None
        severity = alert.get('Severity')
        return Diagnostic(
            rule_id=check,
            range=SourceRange(start, max(start, end)),
            message=message,
            severity=SEVERITIES.get(severity, Severity.ERROR) if isinstance(severity, str) else Severity.ERROR,
            fix=Fix.rewrite(),
            source=self.name,
        )

    def _span(self, span: object) -> tuple[int, int]:
        if isinstance(span, list) and len(span) == 2 and all(isinstance(item, int) for item in span):
            return int(span[0]), int(span[1])
        return 1, 1
