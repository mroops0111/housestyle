import typing

from ..models.comment import CommentGroup
from ..models.diagnostic import Diagnostic, Fix, FixKind, RuleMetadata
from ..ports.rule import Rule, RuleContext
from .rewrite import stub_floor


MID_CLAUSE_BREAK = RuleMetadata(
    rule_id='mid-clause-break',
    summary='A comment block must be laid out one sentence per line, splitting only at commas.',
    fix_kind=FixKind.REFLOW,
)

LINE_TOO_LONG = RuleMetadata(
    rule_id='line-too-long',
    summary='A physical comment line must fit the configured width, counting indent and delimiter.',
    fix_kind=FixKind.REFLOW,
)


class MidClauseBreakRule(Rule):
    metadata = MID_CLAUSE_BREAK

    def check(self, group: CommentGroup, context: RuleContext) -> typing.Iterable[Diagnostic]:
        reflowed = group.reflow(context.line_width, stub_floor(context))
        if reflowed.render() == group.render():
            return
        yield Diagnostic(
            rule_id=self.metadata.rule_id,
            range=group.range,
            message=(
                'Comment layout differs from one sentence per line. '
                'Break only at a period or a comma, never mid clause.'
            ),
            fix=Fix.reflow(reflowed.as_edit()),
        )


class LineTooLongRule(Rule):
    metadata = LINE_TOO_LONG

    def check(self, group: CommentGroup, context: RuleContext) -> typing.Iterable[Diagnostic]:
        width = context.line_width
        if group.longest_line <= width:
            return
        reflowed = group.reflow(width, stub_floor(context))
        if reflowed.longest_line > width:
            return
        yield Diagnostic(
            rule_id=self.metadata.rule_id,
            range=group.range,
            message=(
                f'A comment line runs to {group.longest_line} characters against a limit of {width}, '
                'counting indent and delimiter.'
            ),
            fix=Fix.reflow(reflowed.as_edit()),
        )
