import pathlib

import pytest

from housestyle.application import LintDocument, RuleEngine
from housestyle.domain import Document, RuleSet
from housestyle.infrastructure import ALL_RULES, DEFAULT_CONFIG, DEFAULT_PARSER, PYTHON


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE_ROOT = REPO_ROOT / 'src'


def lint_text(text: str, rules: RuleSet | None = None):
    document = Document(uri='file:///probe.py', text=text, language_id=PYTHON.language_id)
    engine = RuleEngine(ALL_RULES)
    return LintDocument(DEFAULT_PARSER, engine).run(document, rules or DEFAULT_CONFIG.resolve(str(SOURCE_ROOT)))


def source_files() -> list[pathlib.Path]:
    return sorted(SOURCE_ROOT.rglob('*.py'))


def test_the_corpus_is_not_empty() -> None:
    assert len(source_files()) > 10


def test_the_project_carries_comments_worth_checking() -> None:
    blocks = 0
    for path in source_files():
        document = Document(
            uri=path.resolve().as_uri(),
            text=path.read_text(encoding='utf-8'),
            language_id=PYTHON.language_id,
        )
        blocks += len(DEFAULT_PARSER.parse(document))
    assert blocks > 0, 'a clean self-hosting run means nothing if there is nothing to check'


def test_housestyle_lints_itself_clean() -> None:
    rules = DEFAULT_CONFIG.resolve(str(SOURCE_ROOT))
    engine = RuleEngine(ALL_RULES)
    lint = LintDocument(DEFAULT_PARSER, engine)

    findings: list[str] = []
    for path in source_files():
        document = Document(
            uri=path.resolve().as_uri(),
            text=path.read_text(encoding='utf-8'),
            language_id=PYTHON.language_id,
        )
        for item in lint.run(document, rules).diagnostics:
            findings.append(f'{path.relative_to(REPO_ROOT)}: {item.rule_id} {item.message[:80]}')
    assert not findings, f'{len(findings)} self-hosting findings: {findings[:5]}'


@pytest.mark.parametrize(
    ('probe', 'expected'),
    [
        (
            'def f():\n    # cap the size so the mmap does not\n    # blow past it, an unbounded value faults.\n    pass\n',
            'wrap-point',
        ),
        (
            'def f():\n    # this single sentence carries no comma at all and runs a very long way past any '
            'sensible budget that a reader would tolerate on one line.\n    pass\n',
            'unbreakable-sentence',
        ),
    ],
)
def test_the_self_hosting_check_has_teeth(probe: str, expected: str) -> None:
    rules = RuleSet(enabled=frozenset(rule.meta.rule_id for rule in ALL_RULES), line_width=60)
    assert expected in [item.rule_id for item in lint_text(probe, rules).diagnostics]


def test_the_project_config_is_readable_and_enables_every_rule() -> None:
    rules = DEFAULT_CONFIG.resolve(str(SOURCE_ROOT))
    assert rules.enabled == frozenset(rule.meta.rule_id for rule in ALL_RULES)
    assert rules.line_width == 120
