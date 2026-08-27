import pytest

from housestyle.domain import (
    CommentBlock,
    CommentForm,
    CommentLine,
    CommentPlacement,
    SourceRange,
    SymbolKind,
    SymbolRef,
    Visibility,
)


def line(payload: str, indent: str = '  ', marker: str = '// ', start: int = 0) -> CommentLine:
    return CommentLine(SourceRange(start, start + 1), indent, marker, payload)


def block(*payloads: str, **kwargs: object) -> CommentBlock:
    defaults: dict[str, object] = {
        'range': SourceRange(0, 10),
        'lines': tuple(line(payload) for payload in payloads),
        'form': CommentForm.LINE,
        'placement': CommentPlacement.INLINE_BODY,
    }
    defaults.update(kwargs)
    return CommentBlock(**defaults)  # pyright: ignore[reportArgumentType]


def test_a_block_needs_at_least_one_line() -> None:
    with pytest.raises(ValueError, match='at least one line'):
        CommentBlock(
            range=SourceRange(0, 1),
            lines=(),
            form=CommentForm.LINE,
            placement=CommentPlacement.INLINE_BODY,
        )


def test_physical_width_counts_indent_and_marker_not_just_payload() -> None:
    subject = line('payload', indent=' ' * 40, marker='// ')
    assert len(subject.payload) == 7
    assert subject.physical_width == 50
    assert subject.prefix_width == 43


def test_widest_line_is_measured_across_the_block() -> None:
    subject = block('short', 'a much longer payload here')
    assert subject.widest_line == len('  // ') + len('a much longer payload here')


def test_multiline_detection() -> None:
    assert not block('only').is_multiline
    assert block('first', 'second').is_multiline
    assert block('first', 'second').line_count == 2


def test_prose_strips_markers_and_joins_lines() -> None:
    subject = block('cap the size to the limit,', 'an unbounded value faults')
    assert subject.prose().physical_lines == ('cap the size to the limit,', 'an unbounded value faults')
    assert subject.prose().flattened == 'cap the size to the limit, an unbounded value faults'


def test_rendering_round_trips_the_prefix() -> None:
    assert block('alpha', 'beta').render() == '  // alpha\n  // beta'


def test_an_empty_payload_renders_without_trailing_space() -> None:
    assert block('').render() == '  //'


def test_with_payloads_returns_a_new_block_and_leaves_the_original_alone() -> None:
    original = block('one', 'two')
    rewrapped = original.with_payloads(('single line now',))

    assert rewrapped is not original
    assert original.line_count == 2
    assert rewrapped.line_count == 1
    assert rewrapped.render() == '  // single line now'


def test_with_payloads_can_grow_the_block_using_the_first_line_prefix() -> None:
    grown = block('one').with_payloads(('one', 'two', 'three'))
    assert grown.render() == '  // one\n  // two\n  // three'


def test_with_payloads_rejects_an_empty_result() -> None:
    with pytest.raises(ValueError, match='at least one line'):
        block('one').with_payloads(())


def test_public_attachment_is_reported() -> None:
    public = block('doc', attachment=SymbolRef('buildProposal', SymbolKind.FUNCTION, Visibility.PUBLIC))
    internal = block('doc', attachment=SymbolRef('_helper', SymbolKind.FUNCTION, Visibility.INTERNAL))

    assert public.attaches_to_public_symbol
    assert not internal.attaches_to_public_symbol
    assert not block('doc').attaches_to_public_symbol


def test_as_edit_targets_the_block_range() -> None:
    subject = block('alpha', range=SourceRange(4, 40))
    edit = subject.as_edit()
    assert edit.range == SourceRange(4, 40)
    assert edit.new_text == '  // alpha'


def test_prose_preserves_indentation_relative_to_the_block() -> None:
    lines = (
        CommentLine(SourceRange(0, 1), '    ', '', 'Summary.'),
        CommentLine(SourceRange(1, 2), '', '', ''),
        CommentLine(SourceRange(2, 3), '        ', '', 'indented_code()'),
        CommentLine(SourceRange(3, 4), '    ', '', 'Trailing.'),
    )
    block = CommentBlock(
        range=SourceRange(0, 4),
        lines=lines,
        form=CommentForm.DOC,
        placement=CommentPlacement.LEADING_DECLARATION,
    )
    assert block.prose().physical_lines == ('Summary.', '', '    indented_code()', 'Trailing.')
    assert block.prose().flattened == 'Summary. Trailing.'


def test_prose_keeps_uniformly_indented_lines_flush() -> None:
    lines = tuple(CommentLine(SourceRange(i, i + 1), '        ', '# ', text) for i, text in enumerate(('one', 'two')))
    block = CommentBlock(
        range=SourceRange(0, 2),
        lines=lines,
        form=CommentForm.LINE,
        placement=CommentPlacement.INLINE_BODY,
    )
    assert block.prose().physical_lines == ('one', 'two')
