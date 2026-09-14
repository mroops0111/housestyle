import dataclasses
import json
import pathlib
import sys

from ..application import FixDocument, LintDocument, RuleEngine
from ..domain.document import Document
from ..infrastructure import ALL_RULES, DEFAULT_CONFIG, DEFAULT_PARSER, PYTHON
from . import report as reporters
from .harnesses import BLOCK_EXIT, AgentHarness, Payload, harness_for


@dataclasses.dataclass(frozen=True, slots=True)
class HookResult:
    exit_code: int
    stderr: str = ''
    repaired: tuple[str, ...] = ()
    harness: str = ''

    @property
    def is_blocking(self) -> bool:
        return self.exit_code == BLOCK_EXIT


def targets(payload: Payload) -> tuple[pathlib.Path, ...]:
    harness = harness_for(payload)
    return harness.targets(payload) if harness else ()


def run(payload: Payload, *, write: bool = True, harness: AgentHarness | None = None) -> HookResult:
    chosen = harness or harness_for(payload)
    if chosen is None:
        return HookResult(exit_code=0)
    paths = chosen.targets(payload)
    if not paths:
        return HookResult(exit_code=0, harness=chosen.name)

    fixer = FixDocument(LintDocument(DEFAULT_PARSER, RuleEngine(ALL_RULES)))
    messages: list[str] = []
    repaired: list[str] = []

    for path in paths:
        try:
            source = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        document = Document(uri=path.resolve().as_uri(), text=source, language_id=PYTHON.language_id)
        outcome = fixer.run(document, DEFAULT_CONFIG.resolve(str(path)))
        if outcome.has_changes and write:
            path.write_text(outcome.document.text, encoding='utf-8')
            repaired.append(str(path))
        rendered_report = reporters.brief(outcome.document, outcome.report)
        if rendered_report:
            messages.append(rendered_report)

    if not messages:
        return HookResult(exit_code=0, repaired=tuple(repaired), harness=chosen.name)
    return HookResult(
        exit_code=BLOCK_EXIT,
        stderr='\n\n'.join(messages),
        repaired=tuple(repaired),
        harness=chosen.name,
    )


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
