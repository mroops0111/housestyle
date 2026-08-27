import pytest

from housestyle.application import LintDocument, RuleEngine
from housestyle.domain import Document, FixKind, RuleSet, apply_edits
from housestyle.infrastructure import DEFAULT_PARSER, LAYOUT_RULES


ALL_LAYOUT = frozenset({'wrap-point', 'line-width'})


def lint(source: str, width: int = 60, enabled: frozenset[str] = ALL_LAYOUT):
    document = Document(uri='file:///a.py', text=source, language_id='python')
    return LintDocument(DEFAULT_PARSER, RuleEngine(LAYOUT_RULES)).run(
        document, RuleSet(enabled=enabled, line_width=width)
    )


def fixed(source: str, width: int = 60) -> str:
    report = lint(source, width)
    edits = tuple(edit for item in report.mechanical if item.fix for edit in item.fix.edits)
    return apply_edits(source, edits[:1]) if edits else source


def test_already_correct_layout_is_clean() -> None:
    assert lint('def f():\n    # one sentence here.\n    pass\n').is_clean


def test_a_mid_clause_break_is_reported_and_reflowed() -> None:
    source = 'def f():\n    # cap the size to the limit so the mmap does not\n    # blow past it, an unbounded value faults.\n    pass\n'
    report = lint(source)
    assert 'wrap-point' in [item.rule_id for item in report.diagnostics]
    assert '# cap the size to the limit so the mmap does not blow past it,\n' in fixed(source)


def test_reflow_splits_one_sentence_per_line() -> None:
    source = 'def f():\n    # first one. second one. third one.\n    pass\n'
    result = fixed(source)
    assert result.count('    # ') == 3


def test_a_long_sentence_splits_at_commas_only() -> None:
    source = 'def f():\n    # this is long indeed, it carries clauses, and it ends here.\n    pass\n'
    for line in fixed(source, width=40).splitlines():
        if line.strip().startswith('#'):
            assert line.rstrip().endswith((',', '.')) or line.strip() == '#'


def test_a_sentence_with_no_comma_is_left_alone_by_reflow() -> None:
    source = 'def f():\n    # this single sentence has no comma at all and cannot be split anywhere.\n    pass\n'
    assert fixed(source, width=40) == source


def test_line_width_counts_indent_and_marker() -> None:
    payload = 'a padded payload here, and a tail clause that follows.'
    shallow = f'def a():\n    # {payload}\n    pass\n'
    deep = f'def a():\n    def b():\n        def c():\n            # {payload}\n            pass\n'

    width = len(f'    # {payload}') + 1
    assert 'line-width' not in [item.rule_id for item in lint(shallow, width=width).diagnostics]
    assert 'line-width' in [item.rule_id for item in lint(deep, width=width).diagnostics]


def test_line_width_stays_silent_when_the_block_already_fits() -> None:
    source = 'def f():\n    # short.\n    pass\n'
    assert 'line-width' not in [item.rule_id for item in lint(source, width=80).diagnostics]


def test_line_width_stays_silent_when_reflow_cannot_help() -> None:
    long_word = 'a' * 90
    source = f'def f():\n    # {long_word}.\n    pass\n'
    assert 'line-width' not in [item.rule_id for item in lint(source, width=40).diagnostics]


def test_layout_fixes_are_reflow_kind() -> None:
    source = 'def f():\n    # one. two.\n    pass\n'
    for item in lint(source).diagnostics:
        assert item.fix is not None
        assert item.fix.kind is FixKind.REFLOW
        assert item.is_mechanical


def test_reflow_is_idempotent_on_its_own_output() -> None:
    source = 'def f():\n    # cap the size to the limit so the mmap does not\n    # blow past it, an unbounded value faults.\n    pass\n'
    once = fixed(source)
    assert fixed(once) == once


def test_a_docstring_keeps_its_delimiters_through_reflow() -> None:
    source = 'def f():\n    """Summary here, with a clause that runs on and on and needs a split.\n    """\n'
    result = fixed(source, width=40)
    assert result.count('"""') == 2
    assert result.rstrip().endswith('"""')


def test_a_single_line_docstring_stays_on_one_line() -> None:
    source = 'def f():\n    """Short."""\n'
    assert fixed(source, width=80) == source


def test_a_literal_block_survives_reflow_untouched() -> None:
    source = 'def f():\n    """Summary.\n\n        literal_code(1)\n\n    Tail prose, with a comma.\n    """\n'
    assert '        literal_code(1)' in fixed(source, width=40)


@pytest.mark.parametrize('rule_id', sorted(ALL_LAYOUT))
def test_each_rule_can_be_disabled_independently(rule_id: str) -> None:
    source = 'def f():\n    # cap the size to the limit so the mmap does not\n    # blow past it, an unbounded value faults.\n    pass\n'
    ids = [item.rule_id for item in lint(source, enabled=ALL_LAYOUT - {rule_id}).diagnostics]
    assert rule_id not in ids
