import json

from ..domain.diagnostic import Diagnostic, Report
from ..domain.document import Document


def full(document: Document, report: Report) -> str:
    if report.is_clean:
        return ''
    lines: list[str] = []
    for diagnostic in report.diagnostics:
        position = document.positions.to_position(diagnostic.range.start)
        location = f'{_path(document)}:{position.line + 1}:{position.character + 1}'
        lines.append(f'{location}  {diagnostic.severity.name.lower()}  {diagnostic.rule_id}  {diagnostic.message}')
    return '\n'.join(lines)


def brief(document: Document, report: Report) -> str:
    if not report.needing_author:
        return ''
    return _rewrite_brief(document, report)


def actionable(document: Document, report: Report) -> str:
    if report.needing_author:
        return _rewrite_brief(document, report)
    if report.mechanical:
        count = len(report.mechanical)
        return (
            f'Nothing needs rewriting in {_path(document)}. '
            f'{count} finding{"s" if count != 1 else ""} can be repaired mechanically, '
            'so run fix --write rather than editing by hand.'
        )
    return f'No findings in {_path(document)}.'


def _rewrite_brief(document: Document, report: Report) -> str:
    lines = [
        f'{len(report.needing_author)} comment findings need rewriting in {_path(document)}.',
        'Each states the fix. Apply it in place, do not add a suppression comment.',
        '',
    ]
    for diagnostic in report.needing_author:
        position = document.positions.to_position(diagnostic.range.start)
        lines.append(f'line {position.line + 1}  [{diagnostic.rule_id}]')
        lines.append(f'  {diagnostic.message}')
    return '\n'.join(lines)


def as_json(document: Document, report: Report) -> str:
    return json.dumps(
        {
            'uri': document.uri,
            'diagnostics': [_encode(document, diagnostic) for diagnostic in report.diagnostics],
            'unavailable_sources': list(report.unavailable_sources),
        },
        indent=2,
    )


def _encode(document: Document, diagnostic: Diagnostic) -> dict[str, object]:
    start = document.positions.to_position(diagnostic.range.start)
    end = document.positions.to_position(diagnostic.range.end)
    return {
        'rule': diagnostic.rule_id,
        'severity': diagnostic.severity.name.lower(),
        'message': diagnostic.message,
        'fixKind': diagnostic.fix.kind.value if diagnostic.fix else None,
        'mechanical': diagnostic.is_mechanical,
        'range': {
            'start': {'line': start.line, 'character': start.character},
            'end': {'line': end.line, 'character': end.character},
        },
    }


def _path(document: Document) -> str:
    return document.uri.removeprefix('file://')
