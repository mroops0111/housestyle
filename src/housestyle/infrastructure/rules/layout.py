import typing

from ...domain.comment import CommentBlock
from ...domain.diagnostic import Diagnostic, Fix, FixKind, RuleMeta
from ...domain.rules import RuleContext


WRAP_POINT = RuleMeta(
    rule_id='wrap-point',
    summary='A comment block must be laid out one sentence per line, splitting only at commas.',
    fix_kind=FixKind.REFLOW,
)

LINE_WIDTH = RuleMeta(
    rule_id='line-width',
    summary='A physical comment line must fit the configured width, counting indent and marker.',
    fix_kind=FixKind.REFLOW,
)


class WrapPointRule:
    meta = WRAP_POINT

    def check(self, block: CommentBlock, context: RuleContext) -> typing.Iterable[Diagnostic]:
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


class LineWidthRule:
    meta = LINE_WIDTH

    def check(self, block: CommentBlock, context: RuleContext) -> typing.Iterable[Diagnostic]:
        width = context.line_width
        if block.widest_line <= width:
            return
        reflowed = block.reflow(width)
        if reflowed.widest_line > width:
            return
        yield Diagnostic(
            rule_id=self.meta.rule_id,
            range=block.range,
            message=(
                f'A comment line runs to {block.widest_line} characters against a limit of {width}, '
                'counting indent and marker.'
            ),
            fix=Fix.reflow(reflowed.as_edit()),
        )
