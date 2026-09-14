import dataclasses
import json
import pathlib
import sys

from ..application import FixDocument, LintDocument, RuleEngine
from ..domain.document import Document
from ..infrastructure import ALL_RULES, DEFAULT_CONFIG, DEFAULT_PARSER, PYTHON
from . import report as reporters
from .harnesses import ALL_HARNESSES, BLOCK_EXIT, Payload, resolve


@dataclasses.dataclass(frozen=True, slots=True)
class HookResult:
    exit_code: int
    stderr: str = ''
    repaired: tuple[str, ...] = ()
    harness: str = ''

    @property
    def is_blocking(self) -> bool:
        return self.exit_code == BLOCK_EXIT


def edited_files(payload: Payload) -> tuple[pathlib.Path, ...]:
    resolved = resolve(payload)
    return resolved[1] if resolved else ()


def run(payload: Payload, *, write: bool = True) -> HookResult:
    resolved = resolve(payload)
    if resolved is None:
        return HookResult(exit_code=0)
    chosen, paths = resolved
    if not paths:
        return HookResult(exit_code=0, harness=chosen.meta.name)

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
        return HookResult(exit_code=0, repaired=tuple(repaired), harness=chosen.meta.name)
    return HookResult(
        exit_code=BLOCK_EXIT,
        stderr='\n\n'.join(messages),
        repaired=tuple(repaired),
        harness=chosen.meta.name,
    )


def describe_harnesses() -> str:
    """Say which payload shapes reach this hook, so a caller can check its own.

    Unrecognised payloads exit quietly, since an agent sends many that are none of our business,
    and that silence is why the shapes have to be askable for.
    """
    lines = ['housestyle-hook reads one agent payload on stdin.', '']
    for harness in ALL_HARNESSES:
        meta = harness.meta
        lines.extend([meta.name, f'  {meta.summary}', f'  {json.dumps(meta.example)}', ''])
    lines.extend(
        [
            'A payload no harness claims exits 0 and changes nothing.',
            'Outside an agent, use housestyle fix --write and housestyle check instead.',
        ]
    )
    return '\n'.join(lines)


def main() -> int:
    if {'--help', '-h', '--harnesses'} & set(sys.argv[1:]):
        sys.stdout.write(describe_harnesses() + '\n')
        return 0
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
