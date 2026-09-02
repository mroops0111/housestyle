import dataclasses
import json
import pathlib
import sys
import typing

from ..application import FixDocument, LintDocument, RuleEngine
from ..domain.document import Document
from ..infrastructure import ALL_RULES, DEFAULT_CONFIG, DEFAULT_PARSER, PYTHON
from . import report as reporters


BLOCK_EXIT = 2
EDIT_TOOLS = frozenset({'Edit', 'Write', 'MultiEdit', 'NotebookEdit'})


@dataclasses.dataclass(frozen=True, slots=True)
class HookOutcome:
    exit_code: int
    stderr: str = ''
    repaired: tuple[str, ...] = ()

    @property
    def blocks(self) -> bool:
        return self.exit_code == BLOCK_EXIT


def targets(payload: typing.Mapping[str, object]) -> tuple[pathlib.Path, ...]:
    tool = payload.get('tool_name')
    if isinstance(tool, str) and tool not in EDIT_TOOLS:
        return ()
    tool_input = payload.get('tool_input')
    fields = tool_input if isinstance(tool_input, dict) else {}
    paths: list[pathlib.Path] = []
    for key in ('file_path', 'notebook_path'):
        candidate = fields.get(key)
        if isinstance(candidate, str) and candidate:
            paths.append(pathlib.Path(candidate))
    return tuple(path for path in paths if path.suffix in PYTHON.extensions and path.is_file())


def run(payload: typing.Mapping[str, object], *, write: bool = True) -> HookOutcome:
    paths = targets(payload)
    if not paths:
        return HookOutcome(exit_code=0)

    fixer = FixDocument(LintDocument(DEFAULT_PARSER, RuleEngine(ALL_RULES)))
    messages: list[str] = []
    repaired: list[str] = []

    for path in paths:
        try:
            text = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        document = Document(uri=path.resolve().as_uri(), text=text, language_id=PYTHON.language_id)
        outcome = fixer.run(document, DEFAULT_CONFIG.resolve(str(path)))
        if outcome.changed and write:
            path.write_text(outcome.document.text, encoding='utf-8')
            repaired.append(str(path))
        rendered_report = reporters.brief(outcome.document, outcome.report)
        if rendered_report:
            messages.append(rendered_report)

    if not messages:
        return HookOutcome(exit_code=0, repaired=tuple(repaired))
    return HookOutcome(exit_code=BLOCK_EXIT, stderr='\n\n'.join(messages), repaired=tuple(repaired))


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if not isinstance(payload, dict):
        return 0
    outcome = run(payload)
    if outcome.stderr:
        sys.stderr.write(outcome.stderr + '\n')
    return outcome.exit_code


if __name__ == '__main__':
    sys.exit(main())
