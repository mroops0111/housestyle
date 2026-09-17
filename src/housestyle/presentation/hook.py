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
    repaired_paths: tuple[str, ...] = ()
    harness_name: str = ''

    @property
    def is_blocking(self) -> bool:
        return self.exit_code == BLOCK_EXIT


def edited_files(payload: Payload) -> tuple[pathlib.Path, ...]:
    recognition = resolve(payload)
    if recognition is None:
        return ()
    _, edited_paths = recognition
    return edited_paths


def run(payload: Payload, *, write: bool = True) -> HookResult:
    recognition = resolve(payload)
    if recognition is None:
        return HookResult(exit_code=0)
    harness, edited_paths = recognition
    if not edited_paths:
        return HookResult(exit_code=0, harness_name=harness.meta.name)

    fix_document = FixDocument(LintDocument(DEFAULT_PARSER, RuleEngine(ALL_RULES)))
    author_messages: list[str] = []
    repaired_paths: list[str] = []

    for source_path in edited_paths:
        try:
            source_text = source_path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        document = Document(uri=source_path.resolve().as_uri(), text=source_text, language_id=PYTHON.language_id)
        fix_result = fix_document.run(document, DEFAULT_CONFIG.resolve(str(source_path)))
        if fix_result.has_changes and write:
            source_path.write_text(fix_result.document.text, encoding='utf-8')
            repaired_paths.append(str(source_path))
        brief_report = reporters.brief(fix_result.document, fix_result.report)
        if brief_report:
            author_messages.append(brief_report)

    if not author_messages:
        return HookResult(exit_code=0, repaired_paths=tuple(repaired_paths), harness_name=harness.meta.name)
    return HookResult(
        exit_code=BLOCK_EXIT,
        stderr='\n\n'.join(author_messages),
        repaired_paths=tuple(repaired_paths),
        harness_name=harness.meta.name,
    )


def describe_harnesses() -> str:
    """Say which payload shapes reach this hook, so a caller can check its own.

    Unrecognised payloads exit quietly, since an agent sends many that are none of our business.
    That silence is why the shapes have to be askable for.
    """
    help_lines = ['housestyle-hook reads one agent payload on stdin.', '']
    for harness in ALL_HARNESSES:
        meta = harness.meta
        help_lines.extend([meta.name, f'  {meta.summary}', f'  {json.dumps(meta.example)}', ''])
    help_lines.extend(
        [
            'A payload no harness recognises exits 0 and changes nothing.',
            'Outside an agent, use housestyle fix --write and housestyle check instead.',
        ]
    )
    return '\n'.join(help_lines)


HELP_FLAGS = frozenset({'--help', '-h', '--harnesses'})


def main() -> int:
    if HELP_FLAGS & set(sys.argv[1:]):
        sys.stdout.write(describe_harnesses() + '\n')
        return 0
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if not isinstance(payload, dict):
        return 0
    hook_result = run(payload)
    if hook_result.stderr:
        sys.stderr.write(hook_result.stderr + '\n')
    return hook_result.exit_code


if __name__ == '__main__':
    sys.exit(main())
