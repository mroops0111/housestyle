import pytest

from housestyle.domain.prose import BreakStrength, Prose


def texts(prose: Prose) -> list[str]:
    return [sentence.text for sentence in prose.sentences()]


def test_empty_prose_has_no_sentences() -> None:
    assert Prose('').sentences() == ()
    assert Prose('   \n  ').sentences() == ()


def test_a_single_sentence_stays_whole() -> None:
    assert texts(Prose('cap the size to the CI limit.')) == ['cap the size to the CI limit.']


def test_sentences_split_on_terminators() -> None:
    prose = Prose('first one. second one! third one? fourth')
    assert texts(prose) == ['first one.', 'second one!', 'third one?', 'fourth']


def test_physical_lines_are_flattened_before_segmentation() -> None:
    prose = Prose('cap the size to the CI mmap limit,\nan unbounded value faults the runner.')
    assert texts(prose) == ['cap the size to the CI mmap limit, an unbounded value faults the runner.']


@pytest.mark.parametrize(
    'text',
    [
        'use a helper, e.g. the clock, before this runs',
        'the port, i.e. the interface, lives in domain',
        'compare vs. the previous value here',
        'see Smith et al. for the derivation',
    ],
)
def test_abbreviations_do_not_end_a_sentence(text: str) -> None:
    assert len(Prose(text).sentences()) == 1


@pytest.mark.parametrize(
    'text',
    [
        'the cap is 3.14 percent of the budget',
        'requires version 3.11 or newer to build',
        'the ratio 0.5 holds across every run',
    ],
)
def test_decimals_do_not_end_a_sentence(text: str) -> None:
    assert len(Prose(text).sentences()) == 1


@pytest.mark.parametrize(
    'text',
    [
        'see https://vale.sh/docs/formats/code for the details',
        'mirrored at www.example.com/a.b.c today',
    ],
)
def test_urls_do_not_end_a_sentence(text: str) -> None:
    assert len(Prose(text).sentences()) == 1


def test_code_spans_do_not_end_a_sentence() -> None:
    assert len(Prose('call `obj.method.chain` before the flush').sentences()) == 1


def test_an_initial_does_not_end_a_sentence() -> None:
    assert len(Prose('named after J. Smith originally').sentences()) == 1


def test_a_terminator_needs_whitespace_after_it() -> None:
    assert len(Prose('the file a.ts holds it').sentences()) == 1


def test_a_closing_quote_after_a_terminator_still_ends_the_sentence() -> None:
    assert len(Prose('he said "stop." then left the room.').sentences()) == 2


def test_break_candidates_rank_sentence_ends_above_commas() -> None:
    prose = Prose('cap the size, then flush. retry later')
    strengths = [point.strength for point in prose.break_candidates()]
    assert BreakStrength.COMMA in strengths
    assert BreakStrength.SENTENCE in strengths
    assert BreakStrength.SENTENCE > BreakStrength.COMMA


def test_break_candidates_land_after_the_punctuation() -> None:
    prose = Prose('alpha, beta')
    assert [point.offset for point in prose.break_candidates()] == [len('alpha,')]


def test_a_sentence_without_a_comma_offers_no_internal_break() -> None:
    prose = Prose('this sentence runs on without any internal punctuation at all')
    assert prose.break_candidates() == ()


def test_break_legality_is_exact() -> None:
    prose = Prose('alpha, beta')
    assert prose.is_break_legal(len('alpha,'))
    assert not prose.is_break_legal(len('alpha'))
    assert not prose.is_break_legal(3)


def test_urls_offer_no_break_candidates_inside_themselves() -> None:
    prose = Prose('see https://example.com/a,b,c now')
    assert prose.break_candidates() == ()


def test_sentence_offsets_address_the_flattened_text() -> None:
    prose = Prose('first one. second one.')
    first, second = prose.sentences()
    assert prose.flattened[first.offset : first.end] == 'first one.'
    assert prose.flattened[second.offset : second.end] == 'second one.'


def test_physical_lines_are_preserved_separately() -> None:
    prose = Prose('one\ntwo\nthree')
    assert prose.physical_lines == ('one', 'two', 'three')
    assert prose.flattened == 'one two three'


def test_a_backslash_b_block_is_literal_and_excluded_from_prose() -> None:
    prose = Prose('Run it.\n\n\\b example --flag value\n\\b example --other value\n\nDone.')
    literal = [segment for segment in prose.segments() if segment.is_literal]

    assert len(literal) == 1
    assert literal[0].lines == ('\\b example --flag value', '\\b example --other value')
    assert prose.flattened == 'Run it. Done.'


def test_an_indented_block_is_literal() -> None:
    prose = Prose('Summary.\n\n    code_line(1)\n    code_line(2)\n\nTrailing text.')
    assert prose.flattened == 'Summary. Trailing text.'


def test_a_fenced_block_is_literal_including_its_fences() -> None:
    prose = Prose('Before.\n```\ncode here\n```\nAfter.')
    assert prose.flattened == 'Before. After.'


def test_literal_lines_stay_available_for_rendering() -> None:
    prose = Prose('Before.\n    indented code\nAfter.')
    assert [segment.lines for segment in prose.segments()] == [
        ('Before.',),
        ('    indented code',),
        ('After.',),
    ]


def test_a_literal_block_produces_no_sentences() -> None:
    assert Prose('\\b just --an example\n').sentences() == ()


def test_a_literal_block_produces_no_break_candidates() -> None:
    assert Prose('\\b example --a, --b, --c\n').break_candidates() == ()


def test_prose_without_literal_blocks_is_unchanged() -> None:
    prose = Prose('cap the size to the limit,\nan unbounded value faults')
    assert [segment.is_literal for segment in prose.segments()] == [False]
    assert prose.flattened == 'cap the size to the limit, an unbounded value faults'
