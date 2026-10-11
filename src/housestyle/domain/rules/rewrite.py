import typing

from ..models.comment import CommentGroup
from ..models.diagnostic import Diagnostic, Fix, FixKind, RuleMetadata
from ..models.prose import Prose, reflow_sentence
from ..ports.rule import Rule, RuleContext


STUB_FRAGMENT = RuleMetadata(
    rule_id='stub-fragment',
    summary='A sentence forced to break must not leave a stub of a line behind.',
    fix_kind=FixKind.REWRITE,
)

UNBREAKABLE_SENTENCE = RuleMetadata(
    rule_id='unbreakable-sentence',
    summary='A sentence over the width must carry a comma so it has somewhere legal to break.',
    fix_kind=FixKind.REWRITE,
)


DEFAULT_MINIMUM_CHARACTERS = 24


def prose_sentences(group: CommentGroup) -> tuple[str, ...]:
    return tuple(
        sentence.text
        for segment in group.prose().segments()
        if not segment.is_literal
        for sentence in Prose(segment.text).sentences()
    )


def sentence_budget(group: CommentGroup, context: RuleContext) -> int:
    return max(20, context.line_width - group.lines[0].prefix_width)


class StubFragmentRule(Rule):
    metadata = STUB_FRAGMENT

    def check(self, group: CommentGroup, context: RuleContext) -> typing.Iterable[Diagnostic]:
        budget = sentence_budget(group, context)
        minimum_length = context.settings(self.metadata.rule_id).integer(
            'minimum_characters', DEFAULT_MINIMUM_CHARACTERS
        )
        for sentence in prose_sentences(group):
            split_pieces = reflow_sentence(sentence, budget)
            if len(split_pieces) < 2:
                continue
            shortest_piece = min(split_pieces, key=len)
            if len(shortest_piece) >= minimum_length:
                continue
            yield Diagnostic(
                rule_id=self.metadata.rule_id,
                range=group.range,
                message=(
                    f'Breaking this sentence leaves a {len(shortest_piece)} character line, below the '
                    f'{minimum_length} character minimum, so the layout reads as a stub rather than a clause. '
                    f'Rewrite it to fit one line, or split it into two complete sentences. '
                    f'The fragment is "{shortest_piece.strip()}".'
                ),
                fix=Fix.rewrite(),
            )


class UnbreakableSentenceRule(Rule):
    metadata = UNBREAKABLE_SENTENCE

    def check(self, group: CommentGroup, context: RuleContext) -> typing.Iterable[Diagnostic]:
        budget = max(20, context.line_width - group.lines[0].prefix_width)
        for sentence in prose_sentences(group):
            if len(sentence) <= budget or ',' in sentence:
                continue
            yield Diagnostic(
                rule_id=self.metadata.rule_id,
                range=group.range,
                message=(
                    f'This sentence runs to {len(sentence)} characters against a {budget} character budget '
                    'and contains no comma, so there is no legal place to break it. '
                    'Add a comma at a clause boundary, or split it into two sentences.'
                ),
                fix=Fix.rewrite(),
            )
