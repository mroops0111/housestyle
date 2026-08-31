import pytest

from housestyle.application import LintDocument, RuleEngine
from housestyle.domain import Document, FixKind, RuleSet, RuleSettings
from housestyle.infrastructure import ALL_RULES, DEFAULT_PARSER


REWRITE_IDS = frozenset({'stub-fragment', 'unbreakable-sentence'})


def lint(source: str, width: int = 50, enabled: frozenset[str] = REWRITE_IDS, **settings: RuleSettings):
    document = Document(uri='file:///a.py', text=source, language_id='python')
    return LintDocument(DEFAULT_PARSER, RuleEngine(ALL_RULES)).run(
        document, RuleSet(enabled=enabled, line_width=width, settings=settings)
    )


def ids(source: str, **kwargs) -> list[str]:
    return [item.rule_id for item in lint(source, **kwargs).diagnostics]


def comment(text: str) -> str:
    return f'def f():\n    # {text}\n    pass\n'


def test_a_short_standalone_sentence_is_not_a_stub() -> None:
    assert ids(comment('brief.')) == []


def test_a_sentence_that_fits_is_never_flagged() -> None:
    assert ids(comment('this one fits inside the budget fine.')) == []


def test_a_forced_break_leaving_a_stub_is_reported() -> None:
    assert 'stub-fragment' in ids(comment('cap the size to the shared runner ceiling limit that we set here, ok.'))


def test_a_balanced_split_is_not_a_stub() -> None:
    assert 'stub-fragment' not in ids(comment('cap the size to the runner limit, an unbounded value faults it.'))


def test_the_stub_floor_is_configurable() -> None:
    source = comment('cap the size to the runner limit, an unbounded value faults it.')
    assert 'stub-fragment' in ids(source, **{'stub-fragment': RuleSettings(options={'minimum_characters': 40})})


def test_a_long_sentence_with_no_comma_is_unbreakable() -> None:
    assert 'unbreakable-sentence' in ids(comment('this single sentence has no comma anywhere and runs well past it.'))


def test_a_long_sentence_with_a_comma_is_breakable() -> None:
    assert 'unbreakable-sentence' not in ids(comment('this sentence is long, but it carries a comma to break at.'))


def test_a_short_sentence_without_a_comma_is_fine() -> None:
    assert 'unbreakable-sentence' not in ids(comment('no comma here.'))


def test_rewrite_diagnostics_carry_no_edits_and_reach_the_author() -> None:
    report = lint(comment('this single sentence has no comma anywhere and runs well past it.'))
    for item in report.needing_author:
        assert item.fix is not None
        assert item.fix.kind is FixKind.REWRITE
        assert item.fix.edits == ()
        assert not item.is_mechanical


def test_the_message_states_the_concrete_fix() -> None:
    report = lint(comment('this single sentence has no comma anywhere and runs well past it.'))
    message = report.needing_author[0].message
    assert 'no comma' in message
    assert 'Add a comma' in message or 'split it into two sentences' in message


def test_the_stub_message_quotes_the_offending_fragment() -> None:
    report = lint(comment('cap the size to the shared runner ceiling limit that we set here, ok.'))
    stub = next(item for item in report.needing_author if item.rule_id == 'stub-fragment')
    assert '"ok."' in stub.message


def test_a_literal_block_is_never_flagged() -> None:
    source = 'def f():\n    """Summary.\n\n        a_very_long_literal_line_with_no_comma_at_all_here_indeed(1234567890)\n    """\n'
    assert ids(source) == []


def test_the_budget_shrinks_with_indentation() -> None:
    text = 'this sentence has no comma and sits at some depth in the file.'
    shallow = f'def a():\n    # {text}\n    pass\n'
    deep = f'def a():\n    def b():\n        def c():\n            # {text}\n            pass\n'
    width = len(f'    # {text}') + 1

    assert 'unbreakable-sentence' not in ids(shallow, width=width)
    assert 'unbreakable-sentence' in ids(deep, width=width)


@pytest.mark.parametrize('rule_id', sorted(REWRITE_IDS))
def test_each_rule_can_be_disabled_independently(rule_id: str) -> None:
    source = comment('cap the size to the shared runner ceiling limit that we set here, ok.')
    assert rule_id not in ids(source, enabled=REWRITE_IDS - {rule_id})
