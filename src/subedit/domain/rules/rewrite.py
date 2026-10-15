import typing

from ..models.comment import CommentGroup
from ..models.diagnostic import Diagnostic, Fix, FixKind, RuleMetadata, Severity
from ..models.prose import Prose, reflow_sentence
from ..ports.rule import Rule, RuleContext


STUB_FRAGMENT = RuleMetadata(
    rule_id='stub-fragment',
    summary='A sentence forced to break must not leave a stub of a line behind.',
    fix_kind=FixKind.REWRITE,
    default_severity=Severity.WARNING,
)

UNBREAKABLE_SENTENCE = RuleMetadata(
    rule_id='unbreakable-sentence',
    summary='A sentence over the width must carry a clause comma wherever it has to break.',
    fix_kind=FixKind.REWRITE,
)


DEFAULT_MINIMUM_CHARACTERS = 24
BRACKET_NOTE = 'A comma inside brackets or a code span separates items, so it is no place to break. '


def prose_sentences(group: CommentGroup) -> tuple[str, ...]:
    return tuple(
        sentence.text
        for segment in group.prose().segments()
        if not segment.is_literal
        for sentence in Prose(segment.text).sentences()
    )


def budgeted_sentences(group: CommentGroup, context: RuleContext) -> tuple[tuple[str, int], ...]:
    """Pair each sentence with the budget reflow lays it out in, so no rule judges a layout reflow would not make."""
    return tuple(
        (sentence, group.text_budget(context.line_width, first_line=index == 0))
        for index, sentence in enumerate(prose_sentences(group))
    )


def stub_floor(context: RuleContext) -> int:
    """Reflow reads the same floor, so a fix never lays out a stub that this rule then rejects."""
    if not context.rule_set.is_enabled(STUB_FRAGMENT.rule_id):
        return 0
    return context.settings(STUB_FRAGMENT.rule_id).integer('minimum_characters', DEFAULT_MINIMUM_CHARACTERS)


class StubFragmentRule(Rule):
    metadata = STUB_FRAGMENT

    def check(self, group: CommentGroup, context: RuleContext) -> typing.Iterable[Diagnostic]:
        minimum_length = stub_floor(context)
        for sentence, budget in budgeted_sentences(group, context):
            split_pieces = reflow_sentence(sentence, budget, minimum_length)
            if len(split_pieces) < 2:
                continue
            shortest_piece = min(split_pieces, key=len)
            if len(shortest_piece) >= minimum_length:
                continue
            yield Diagnostic(
                rule_id=self.metadata.rule_id,
                range=group.range,
                message=(
                    f'Breaking this sentence leaves a line of {len(shortest_piece)} characters, below the minimum of '
                    f'{minimum_length}, so the layout reads as a stub rather than a clause. '
                    f'Rewrite it to fit one line, or split it into two complete sentences. '
                    f'The fragment is "{shortest_piece.strip()}".'
                ),
                fix=Fix.rewrite(),
            )


class UnbreakableSentenceRule(Rule):
    metadata = UNBREAKABLE_SENTENCE

    def check(self, group: CommentGroup, context: RuleContext) -> typing.Iterable[Diagnostic]:
        for sentence, budget in budgeted_sentences(group, context):
            longest_line = max(reflow_sentence(sentence, budget), key=len)
            if len(longest_line) <= budget:
                continue
            if longest_line == sentence:
                cause = 'contains no comma that ends a clause, so there is no legal place to break it'
            else:
                cause = f'still leaves a line of {len(longest_line)} characters when broken at every clause comma'
            yield Diagnostic(
                rule_id=self.metadata.rule_id,
                range=group.range,
                message=(
                    f'This sentence runs to {len(sentence)} characters against a budget of {budget} characters '
                    f'and {cause}. '
                    f'{BRACKET_NOTE if "," in sentence else ""}'
                    'Add a comma at a clause boundary, or split it into two sentences. '
                    f'The part that does not fit is "{longest_line}".'
                ),
                fix=Fix.rewrite(),
            )
