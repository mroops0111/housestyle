import json

from ..domain.diagnostic import Diagnostic, Report
from ..domain.document import Document


def human(document: Document, report: Report) -> str:
    if report.is_clean:
        return ''
    lines: list[str] = []
    for item in report.diagnostics:
        position = document.positions.to_position(item.range.start)
        location = f'{_path(document)}:{position.line + 1}:{position.character + 1}'
        lines.append(f'{location}  {item.severity.name.lower()}  {item.rule_id}  {item.message}')
    return '\n'.join(lines)


def agent(document: Document, report: Report) -> str:
    if not report.needing_author:
        return ''
    return _rewrite_brief(document, report)


def agent_verbose(document: Document, report: Report) -> str:
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
    for item in report.needing_author:
        position = document.positions.to_position(item.range.start)
        lines.append(f'line {position.line + 1}  [{item.rule_id}]')
        lines.append(f'  {item.message}')
    return '\n'.join(lines)


def as_json(document: Document, report: Report) -> str:
    return json.dumps(
        {
            'uri': document.uri,
            'diagnostics': [_encode(document, item) for item in report.diagnostics],
            'unavailable_sources': list(report.unavailable_sources),
        },
        indent=2,
    )


def _encode(document: Document, item: Diagnostic) -> dict[str, object]:
    start = document.positions.to_position(item.range.start)
    end = document.positions.to_position(item.range.end)
    return {
        'rule': item.rule_id,
        'severity': item.severity.name.lower(),
        'message': item.message,
        'fixKind': item.fix.kind.value if item.fix else None,
        'mechanical': item.is_mechanical,
        'range': {
            'start': {'line': start.line, 'character': start.character},
            'end': {'line': end.line, 'character': end.character},
        },
    }


def _path(document: Document) -> str:
    return document.uri.removeprefix('file://')
