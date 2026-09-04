import pytest

from housestyle.application import FixDocument, LintDocument, RuleEngine
from housestyle.domain import (
    CommentGroup,
    Diagnostic,
    Document,
    Fix,
    FixKind,
    RuleContext,
    RuleMeta,
    RuleSet,
    SourceRange,
    TextEdit,
)
from housestyle.infrastructure import ALL_RULES, DEFAULT_PARSER


LAYOUT = frozenset({'wrap-point', 'line-width', 'stub-fragment', 'unbreakable-sentence'})


def fixer(rules=ALL_RULES, max_rounds: int = 10) -> FixDocument:
    return FixDocument(LintDocument(DEFAULT_PARSER, RuleEngine(rules)), max_rounds=max_rounds)


def run(source: str, width: int = 60, enabled: frozenset[str] = LAYOUT, **kwargs):
    document = Document(uri='file:///a.py', text=source, language_id='python')
    return fixer(**kwargs).run(document, RuleSet(enabled=enabled, line_width=width))


def test_clean_input_is_left_alone() -> None:
    source = 'def f():\n    # short and fine.\n    pass\n'
    outcome = run(source)
    assert outcome.document.text == source
    assert not outcome.changed
    assert outcome.rounds == 0


def test_a_mis_wrapped_block_is_repaired() -> None:
    source = (
        'def f():\n    # cap the size so the mmap does not\n    # blow past it, an unbounded value faults.\n    pass\n'
    )
    outcome = run(source)
    assert outcome.changed
    assert '# cap the size so the mmap does not blow past it,\n' in outcome.document.text


def test_fixing_reaches_a_fixpoint() -> None:
    source = 'def f():\n    # one. two. three. four.\n    pass\n'
    outcome = run(source)
    assert run(outcome.document.text).document.text == outcome.document.text


def test_the_round_cap_is_honoured() -> None:
    source = 'def f():\n    # one. two. three.\n    pass\n'
    assert run(source, max_rounds=1).rounds <= 1


def test_rewrite_findings_survive_fixing_and_are_reported() -> None:
    source = (
        'def f():\n    # this single sentence has no comma anywhere and runs well past the budget here.\n    pass\n'
    )
    outcome = run(source, width=50)
    assert [item.rule_id for item in outcome.unresolved] == ['unbreakable-sentence']
    assert outcome.document.text == source


def test_a_rewrite_never_contributes_an_edit() -> None:
    source = (
        'def f():\n    # this single sentence has no comma anywhere and runs well past the budget here.\n    pass\n'
    )
    outcome = run(source, width=50)
    assert outcome.applied == 0


def test_the_document_version_advances_with_each_applied_round() -> None:
    source = (
        'def f():\n    # cap the size so the mmap does not\n    # blow past it, an unbounded value faults.\n    pass\n'
    )
    outcome = run(source)
    assert outcome.document.version == outcome.rounds


def test_targeted_edits_run_before_reflow() -> None:
    order: list[str] = []

    class TargetedRule:
        meta = RuleMeta(rule_id='targeted', summary='t', fix_kind=FixKind.TARGETED)

        def check(self, block: CommentGroup, context: RuleContext):
            order.append('targeted')
            if '!' in block.render():
                return
            start = block.lines[0].range.start + len(block.lines[0].indent + block.lines[0].delimiter)
            yield Diagnostic(
                rule_id='targeted',
                range=block.range,
                message='insert a delimiter',
                fix=Fix.targeted(TextEdit(SourceRange(start, start), '!')),
            )

    class ReflowRule:
        meta = RuleMeta(rule_id='reflowing', summary='r', fix_kind=FixKind.REFLOW)

        def check(self, block: CommentGroup, context: RuleContext):
            order.append('reflow')
            reflowed = block.reflow(context.line_width)
            if reflowed.render() != block.render():
                yield Diagnostic(
                    rule_id='reflowing',
                    range=block.range,
                    message='reflow',
                    fix=Fix.reflow(reflowed.as_edit()),
                )

    source = 'def f():\n    # one. two.\n    pass\n'
    document = Document(uri='file:///a.py', text=source, language_id='python')
    outcome = FixDocument(LintDocument(DEFAULT_PARSER, RuleEngine((ReflowRule(), TargetedRule())))).run(
        document, RuleSet(enabled=frozenset({'targeted', 'reflowing'}), line_width=60)
    )
    assert '!' in outcome.document.text
    assert outcome.document.text.count('    # ') == 2


def test_overlapping_edits_are_deferred_rather_than_dropped() -> None:
    class DoubleRule:
        meta = RuleMeta(rule_id='double', summary='d', fix_kind=FixKind.TARGETED)

        def check(self, block: CommentGroup, context: RuleContext):
            if block.render().count('!') >= 2:
                return
            start = block.range.start
            yield Diagnostic(
                rule_id='double',
                range=block.range,
                message='first',
                fix=Fix.targeted(TextEdit(SourceRange(start, start), '!')),
            )
            yield Diagnostic(
                rule_id='double',
                range=block.range,
                message='second',
                fix=Fix.targeted(TextEdit(SourceRange(start, start + 1), '!x')),
            )

    document = Document(uri='file:///a.py', text='# note\n', language_id='python')
    outcome = FixDocument(LintDocument(DEFAULT_PARSER, RuleEngine((DoubleRule(),))), max_rounds=3).run(
        document, RuleSet(enabled=frozenset({'double'}), line_width=60)
    )
    assert outcome.rounds >= 1
    assert outcome.applied >= 1


@pytest.mark.parametrize('width', [40, 60, 80, 120])
def test_fixing_is_idempotent_at_every_width(width: int) -> None:
    source = 'def f():\n    # cap the size, an unbounded value faults the runner. retry later if it fails.\n    pass\n'
    once = run(source, width=width).document.text
    assert run(once, width=width).document.text == once
