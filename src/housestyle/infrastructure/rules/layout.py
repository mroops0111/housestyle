import typing

from ...domain.comment import CommentGroup
from ...domain.diagnostic import Diagnostic, Fix, FixKind, RuleMeta
from ...domain.rules import RuleContext


MID_CLAUSE_BREAK = RuleMeta(
    rule_id='mid-clause-break',
    summary='A comment block must be laid out one sentence per line, splitting only at commas.',
    fix_kind=FixKind.REFLOW,
)

LINE_TOO_LONG = RuleMeta(
    rule_id='line-too-long',
    summary='A physical comment line must fit the configured width, counting indent and delimiter.',
    fix_kind=FixKind.REFLOW,
)


class MidClauseBreakRule:
    meta = MID_CLAUSE_BREAK

    def check(self, block: CommentGroup, context: RuleContext) -> typing.Iterable[Diagnostic]:
        reflowed = block.reflow(context.line_width)
        if reflowed.render() == block.render():
            return
        yield Diagnostic(
            rule_id=self.meta.rule_id,
            range=block.range,
            message=(
                'Comment layout differs from one sentence per line. '
                'Break only at a period or a comma, never mid clause.'
            ),
            fix=Fix.reflow(reflowed.as_edit()),
        )


class LineTooLongRule:
    meta = LINE_TOO_LONG

    def check(self, block: CommentGroup, context: RuleContext) -> typing.Iterable[Diagnostic]:
        width = context.line_width
        if block.longest_line <= width:
            return
        reflowed = block.reflow(width)
        if reflowed.longest_line > width:
            return
        yield Diagnostic(
            rule_id=self.meta.rule_id,
            range=block.range,
            message=(
                f'A comment line runs to {block.longest_line} characters against a limit of {width}, '
                'counting indent and delimiter.'
            ),
            fix=Fix.reflow(reflowed.as_edit()),
        )
