import typing

from ...domain.comment import CommentBlock
from ...domain.diagnostic import Diagnostic, Fix, FixKind, RuleMeta
from ...domain.prose import Prose, reflow_sentence
from ...domain.rules import RuleContext


STUB_FRAGMENT = RuleMeta(
    rule_id='stub-fragment',
    summary='A sentence forced to break must not leave a stub of a line behind.',
    fix_kind=FixKind.REWRITE,
)

UNBREAKABLE_SENTENCE = RuleMeta(
    rule_id='unbreakable-sentence',
    summary='A sentence over the width must carry a comma so it has somewhere legal to break.',
    fix_kind=FixKind.REWRITE,
)

DEFAULT_MINIMUM_CHARACTERS = 24


def prose_sentences(block: CommentBlock) -> tuple[str, ...]:
    return tuple(
        sentence.text
        for segment in block.prose().segments()
        if not segment.is_literal
        for sentence in Prose(segment.text).sentences()
    )


def sentence_budget(block: CommentBlock, context: RuleContext) -> int:
    return max(20, context.line_width - block.lines[0].prefix_width)


class StubFragmentRule:
    meta = STUB_FRAGMENT

    def check(self, block: CommentBlock, context: RuleContext) -> typing.Iterable[Diagnostic]:
        budget = sentence_budget(block, context)
        floor = context.settings(self.meta.rule_id).integer('minimum_characters', DEFAULT_MINIMUM_CHARACTERS)
        for sentence in prose_sentences(block):
            pieces = reflow_sentence(sentence, budget)
            if len(pieces) < 2:
                continue
            shortest = min(pieces, key=len)
            if len(shortest) >= floor:
                continue
            yield Diagnostic(
                rule_id=self.meta.rule_id,
                range=block.range,
                message=(
                    f'Breaking this sentence leaves a {len(shortest)} character line, below the '
                    f'{floor} character floor, so the layout reads as a stub rather than a clause. '
                    f'Rewrite it to fit one line, or split it into two complete sentences. '
                    f'The fragment is "{shortest.strip()}".'
                ),
                fix=Fix.rewrite(),
            )


class UnbreakableSentenceRule:
    meta = UNBREAKABLE_SENTENCE

    def check(self, block: CommentBlock, context: RuleContext) -> typing.Iterable[Diagnostic]:
        budget = max(20, context.line_width - block.lines[0].prefix_width)
        for sentence in prose_sentences(block):
            if len(sentence) <= budget or ',' in sentence:
                continue
            yield Diagnostic(
                rule_id=self.meta.rule_id,
                range=block.range,
                message=(
                    f'This sentence runs to {len(sentence)} characters against a {budget} character budget '
                    'and contains no comma, so there is no legal place to break it. '
                    'Add a comma at a clause boundary, or split it into two sentences.'
                ),
                fix=Fix.rewrite(),
            )
