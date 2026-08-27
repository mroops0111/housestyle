import pytest

from housestyle.domain import CommentBlock, CommentForm, CommentPlacement, Document, Visibility
from housestyle.infrastructure import DEFAULT_PARSER


def parse(source: str) -> tuple[CommentBlock, ...]:
    return DEFAULT_PARSER.parse(Document(uri='file:///a.py', text=source, language_id='python'))


def prose_of(source: str) -> list[str]:
    return [block.prose().flattened for block in parse(source)]


def test_an_unsupported_language_yields_nothing() -> None:
    assert DEFAULT_PARSER.parse(Document(uri='a.rb', text='# hi', language_id='ruby')) == ()
    assert DEFAULT_PARSER.supports('python')
    assert not DEFAULT_PARSER.supports('ruby')


def test_a_hash_comment_is_extracted_without_its_marker() -> None:
    assert prose_of('# a note\n') == ['a note']


def test_a_docstring_is_extracted_even_though_it_is_not_a_comment_node() -> None:
    assert prose_of('def f():\n    """A docstring."""\n') == ['A docstring.']


def test_consecutive_hash_lines_group_into_one_block() -> None:
    blocks = parse('# first line,\n# second line.\nx = 1\n')
    assert len(blocks) == 1
    assert blocks[0].line_count == 2
    assert blocks[0].prose().flattened == 'first line, second line.'


def test_a_blank_line_separates_two_blocks() -> None:
    assert len(parse('# first\n\n# second\nx = 1\n')) == 2


def test_differing_indentation_separates_two_blocks() -> None:
    assert len(parse('def f():\n    # inner\n# outer\n    pass\n')) == 2


def test_a_hash_inside_a_string_literal_is_not_a_comment() -> None:
    assert prose_of('colour = "#ff0000 not a comment"\n') == []


def test_a_string_in_expression_position_that_is_not_first_is_not_a_docstring() -> None:
    assert prose_of('def f():\n    x = 1\n    "not a docstring"\n    return x\n') == []


def test_a_bare_string_statement_after_a_docstring_is_not_a_second_docstring() -> None:
    assert prose_of('def f():\n    """Real."""\n    "decoy"\n') == ['Real.']


def test_a_trailing_comment_excludes_the_code_before_it() -> None:
    blocks = parse('y = x  # trailing note\n')
    assert blocks[0].prose().flattened == 'trailing note'
    assert blocks[0].placement is CommentPlacement.TRAILING


def test_a_trailing_comment_counts_the_code_in_its_physical_width() -> None:
    line = parse('y = x  # trailing note\n')[0].lines[0]
    assert line.indent == 'y = x  '
    assert line.physical_width == len('y = x  # trailing note')


def test_a_trailing_comment_does_not_group_with_a_standalone_one() -> None:
    assert len(parse('y = x  # trailing\n# standalone\nz = 2\n')) == 2


@pytest.mark.parametrize(
    ('source', 'expected'),
    [
        ('"""Module level."""\n', CommentPlacement.FILE_HEADER),
        ('# header note\nimport os\n', CommentPlacement.FILE_HEADER),
        ('# leading\ndef f():\n    pass\n', CommentPlacement.LEADING_DECLARATION),
        ('def f():\n    """Doc."""\n', CommentPlacement.LEADING_DECLARATION),
        ('def f():\n    # inside\n    pass\n', CommentPlacement.INLINE_BODY),
        ('x = 1  # trailing\n', CommentPlacement.TRAILING),
    ],
)
def test_placement_classification(source: str, expected: CommentPlacement) -> None:
    assert parse(source)[0].placement is expected


def test_a_comment_after_code_at_module_level_is_not_a_file_header() -> None:
    assert parse('import os\n\n# not a header\nx = 1\n')[0].placement is CommentPlacement.INLINE_BODY


def test_a_comment_separated_from_a_definition_by_a_second_comment_still_attaches() -> None:
    blocks = parse('# one\n# two\ndef build():\n    pass\n')
    assert blocks[0].attachment is not None
    assert blocks[0].attachment.name == 'build'


def test_visibility_follows_the_leading_underscore() -> None:
    public = parse('def build():\n    """Doc."""\n')[0]
    internal = parse('def _helper():\n    """Doc."""\n')[0]

    assert public.attachment is not None
    assert internal.attachment is not None
    assert public.attachment.visibility is Visibility.PUBLIC
    assert internal.attachment.visibility is Visibility.INTERNAL
    assert public.attaches_to_public_symbol
    assert not internal.attaches_to_public_symbol


def test_a_class_docstring_attaches_to_the_class() -> None:
    block = parse('class Widget:\n    """Doc."""\n')[0]
    assert block.attachment is not None
    assert block.attachment.kind == 'class'
    assert block.attachment.name == 'Widget'


def test_form_distinguishes_docstrings_from_hash_comments() -> None:
    assert parse('def f():\n    """Doc."""\n')[0].form is CommentForm.DOC
    assert parse('# note\n')[0].form is CommentForm.LINE


def test_a_multiline_docstring_keeps_every_physical_line() -> None:
    block = parse('def f():\n    """Summary.\n\n    Detail here.\n    """\n')[0]
    assert block.line_count == 4
    assert block.prose().flattened == 'Summary. Detail here.'


def test_a_prefixed_docstring_delimiter_is_stripped() -> None:
    assert prose_of('def f():\n    r"""Raw doc."""\n') == ['Raw doc.']


def test_single_quoted_docstrings_are_handled() -> None:
    assert prose_of("def f():\n    '''Single quoted.'''\n") == ['Single quoted.']


def test_physical_width_counts_indent_and_marker() -> None:
    source = 'def a():\n    def b():\n        def c():\n            # payload\n            pass\n'
    line = parse(source)[0].lines[0]
    assert line.payload == 'payload'
    assert line.physical_width == len('            # payload')


@pytest.mark.parametrize(
    'source',
    [
        '"""Module."""\nimport os\n\n\n# lead\n# more\ndef build(x):\n    """Doc.\n\n    Detail.\n    """\n    # inner\n    return x  # trailing\n',
        'class _Thing:\n    """Doc."""\n\n    def _method(self):\n        # note\n        pass\n',
        '# only a comment\n',
    ],
)
def test_every_block_range_reproduces_its_rendering(source: str) -> None:
    data = source.encode('utf-8')
    for block in parse(source):
        assert data[block.range.start : block.range.end].decode('utf-8') == block.render()


def test_blocks_come_back_in_source_order() -> None:
    source = '"""Header."""\n# middle\ndef f():\n    """Doc."""\n'
    starts = [block.range.start for block in parse(source)]
    assert starts == sorted(starts)


def test_the_profile_satisfies_the_language_profile_port() -> None:
    from housestyle.domain import LanguageProfile, SourceParser
    from housestyle.infrastructure import PYTHON

    profile: LanguageProfile = PYTHON
    parser: SourceParser = DEFAULT_PARSER
    assert profile.language_id == 'python'
    assert '.py' in profile.extensions
    assert parser.supports('python')
