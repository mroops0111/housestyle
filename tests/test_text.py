import pytest

from housestyle.domain import Document, SourceRange, TextEdit, apply_edits


def edit(start: int, end: int, new_text: str) -> TextEdit:
    return TextEdit(SourceRange(start, end), new_text)


def test_no_edits_returns_the_original() -> None:
    assert apply_edits('unchanged', ()) == 'unchanged'


def test_edits_apply_back_to_front_so_offsets_stay_valid() -> None:
    text = 'alpha beta gamma'
    result = apply_edits(text, (edit(0, 5, 'FIRST'), edit(11, 16, 'LAST')))
    assert result == 'FIRST beta LAST'


def test_edits_are_order_independent() -> None:
    text = 'alpha beta gamma'
    forward = apply_edits(text, (edit(0, 5, 'X'), edit(11, 16, 'Y')))
    backward = apply_edits(text, (edit(11, 16, 'Y'), edit(0, 5, 'X')))
    assert forward == backward == 'X beta Y'


def test_insertion_and_deletion() -> None:
    assert apply_edits('ac', (edit(1, 1, 'b'),)) == 'abc'
    assert apply_edits('abc', (edit(1, 2, ''),)) == 'ac'


def test_edits_respect_byte_offsets_on_multibyte_text() -> None:
    text = '使用 MCP 協定'
    start = len('使用 '.encode())
    end = start + len(b'MCP')
    assert apply_edits(text, (edit(start, end, 'HTTP'),)) == '使用 HTTP 協定'


def test_overlapping_edits_are_rejected() -> None:
    with pytest.raises(ValueError, match='Overlapping edits'):
        apply_edits('alpha beta', (edit(0, 5, 'X'), edit(3, 8, 'Y')))


def test_adjacent_edits_are_allowed() -> None:
    assert apply_edits('abcd', (edit(0, 2, 'X'), edit(2, 4, 'Y'))) == 'XY'


def test_edit_classification() -> None:
    assert edit(3, 3, 'new').is_insertion
    assert edit(0, 4, '').is_deletion
    assert not edit(0, 4, 'text').is_deletion


def test_document_maps_positions_and_bumps_version_on_change() -> None:
    document = Document(uri='file:///a.ts', text='const x = 1\n', language_id='typescript')
    assert document.positions.line_count == 2
    assert document.version == 0

    updated = document.with_text('const x = 2\n')
    assert updated.version == 1
    assert updated.positions.line_text(0) == 'const x = 2'
    assert document.text == 'const x = 1\n'


def test_document_accepts_an_explicit_version() -> None:
    document = Document(uri='file:///a.ts', text='a', language_id='typescript')
    assert document.with_text('b', version=42).version == 42
