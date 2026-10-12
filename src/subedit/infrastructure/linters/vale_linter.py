import shutil
import subprocess

import pydantic

from ...domain.models.diagnostic import SEVERITY_BY_NAME, Diagnostic, Fix, Severity
from ...domain.models.document import Document
from ...domain.models.position import Position, SourceRange
from ...domain.ports.external_linter import ExternalLinter


TIMEOUT_SECONDS = 30


class ValeAlert(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(frozen=True, extra='ignore')

    check: str = pydantic.Field(alias='Check')
    message: str = pydantic.Field(alias='Message')
    line: int = pydantic.Field(alias='Line', ge=1)
    span: tuple[int, int] = pydantic.Field(default=(1, 1), alias='Span')
    severity: str = pydantic.Field(default='error', alias='Severity')

    @property
    def resolved_severity(self) -> Severity:
        return SEVERITY_BY_NAME.get(self.severity, Severity.ERROR)


class ValeReport(pydantic.RootModel[dict[str, list[ValeAlert]]]):
    @classmethod
    def parse(cls, payload: str) -> tuple[ValeAlert, ...]:
        try:
            report = cls.model_validate_json(payload or '{}')
        except pydantic.ValidationError:
            return ()
        return tuple(alert for alerts in report.root.values() for alert in alerts)


class ValeLinter(ExternalLinter):
    name = 'vale'

    def __init__(self, executable: str = 'vale') -> None:
        self._executable = executable

    def is_available(self) -> bool:
        return shutil.which(self._executable) is not None

    def run(self, document: Document) -> tuple[Diagnostic, ...]:
        if not self.is_available():
            return ()
        # The text goes in on stdin, because during a fix it is ahead of what the file on disk holds.
        # The path still selects the config sections, and Vale matches them exactly as for a file.
        source_path = document.uri.removeprefix('file://')
        try:
            process = subprocess.run(  # noqa: S603
                [self._executable, '--no-exit', '--output=JSON', f'--path={source_path}'],
                input=document.text,
                capture_output=True,
                text=True,
                check=False,
                timeout=TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired):
            return ()
        return self._decode(document, process.stdout)

    def _decode(self, document: Document, payload: str) -> tuple[Diagnostic, ...]:
        diagnostics: list[Diagnostic] = []
        for alert in ValeReport.parse(payload):
            diagnostic = self._to_diagnostic(document, alert)
            if diagnostic is not None:
                diagnostics.append(diagnostic)
        return tuple(diagnostics)

    def _to_diagnostic(self, document: Document, alert: ValeAlert) -> Diagnostic | None:
        start_column, end_column = alert.span
        try:
            start_offset = document.positions.to_offset(Position(alert.line - 1, start_column - 1))
            end_offset = document.positions.to_offset(Position(alert.line - 1, end_column))
        except ValueError:
            return None
        return Diagnostic(
            rule_id=alert.check,
            range=SourceRange(start_offset, max(start_offset, end_offset)),
            message=alert.message,
            severity=alert.resolved_severity,
            fix=Fix.rewrite(),
            source=self.name,
        )
