import re

from housestyle.domain import CommentForm, CommentPlacement, Document, Visibility
from housestyle.infrastructure import TreeSitterParser
from housestyle.infrastructure.languages import LanguageProfile, MarkerSplit


_TS_MARKER = re.compile(r'^(/\*\*|/\*|//+)\s?')

TYPESCRIPT_QUERY = '(comment) @comment'


class TypeScriptProfile:
    language_id = 'typescript'
    extensions = frozenset({'.ts', '.tsx'})
    doc_form_marker = '/**'
    signature_tags = ('@param', '@returns', '@type')
    comment_node = 'comment'
    root_nodes = frozenset({'program'})
    definition_nodes = frozenset({'function_declaration', 'class_declaration', 'method_definition', 'export_statement'})

    def query(self) -> str:
        return TYPESCRIPT_QUERY

    def symbol_kind(self, node_type: str) -> str:
        return 'class' if node_type == 'class_declaration' else 'function'

    def visibility_of(self, name: str) -> Visibility:
        return Visibility.INTERNAL if name.startswith('_') else Visibility.PUBLIC

    def split_marker(self, line: str, form: CommentForm) -> MarkerSplit:
        indent = line[: len(line) - len(line.lstrip())]
        rest = line[len(indent) :]
        match = _TS_MARKER.match(rest)
        if match is None:
            return MarkerSplit(indent=indent, marker='', payload=rest.rstrip())
        payload = rest[match.end() :].rstrip()
        suffix = ''
        if payload.endswith('*/'):
            payload, suffix = payload[:-2].rstrip(), '*/'
        return MarkerSplit(indent=indent, marker=match.group(1) + ' ', payload=payload, suffix=suffix)


def test_a_second_grammar_needs_no_parser_change() -> None:
    profile: LanguageProfile = TypeScriptProfile()
    parser = TreeSitterParser((profile,))
    source = '// a leading note\nexport function build(x: string) {\n  // an inner note\n  return x\n}\n'
    blocks = parser.parse(Document(uri='file:///a.ts', text=source, language_id='typescript'))

    assert [block.prose().flattened for block in blocks] == ['a leading note', 'an inner note']
    assert blocks[0].placement is CommentPlacement.LEADING_DECLARATION
    assert blocks[1].placement is CommentPlacement.INLINE_BODY


def test_a_typescript_file_header_is_recognised_through_the_profile_root_node() -> None:
    parser = TreeSitterParser((TypeScriptProfile(),))
    source = '// a header note\nconst x = 1\n'
    blocks = parser.parse(Document(uri='file:///a.ts', text=source, language_id='typescript'))
    assert blocks[0].placement is CommentPlacement.FILE_HEADER


def test_a_typescript_doc_comment_attaches_to_its_class() -> None:
    parser = TreeSitterParser((TypeScriptProfile(),))
    source = '// documents the widget\nclass Widget {}\n'
    blocks = parser.parse(Document(uri='file:///a.ts', text=source, language_id='typescript'))

    assert blocks[0].attachment is not None
    assert blocks[0].attachment.name == 'Widget'
    assert blocks[0].attachment.kind == 'class'


def test_grammar_node_names_come_from_the_profile_not_the_parser() -> None:
    source = 'class Widget {\n  // note\n}\n'
    document = Document(uri='file:///a.ts', text=source, language_id='typescript')

    aware = TreeSitterParser((TypeScriptProfile(),)).parse(document)
    assert aware[0].placement is CommentPlacement.INLINE_BODY

    class BlindProfile(TypeScriptProfile):
        definition_nodes = frozenset()
        root_nodes = frozenset()

    blind = TreeSitterParser((BlindProfile(),)).parse(document)
    assert blind[0].placement is CommentPlacement.INLINE_BODY
    assert blind[0].attachment is None


def test_consecutive_lines_group_under_a_different_grammar() -> None:
    parser = TreeSitterParser((TypeScriptProfile(),))
    source = '// first line,\n// second line.\nconst x = 1\n'
    blocks = parser.parse(Document(uri='file:///a.ts', text=source, language_id='typescript'))

    assert len(blocks) == 1
    assert blocks[0].line_count == 2
    assert blocks[0].prose().flattened == 'first line, second line.'
