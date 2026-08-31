import re

from ...domain.comment import CommentForm, SymbolKind, Visibility
from .base import DelimiterSplit, NodeRole


_DOC_DELIMITER = re.compile(r'^([rRbBuUfF]{0,2})("""|\'\'\')')
_HASH_DELIMITER = re.compile(r'^(#+\s?)')

QUERY = """
(comment) @comment
(module . (string) @docstring)
(function_definition body: (block . (string) @docstring))
(class_definition body: (block . (string) @docstring))
"""


class PythonProfile:
    language_id = 'python'
    extensions = frozenset({'.py', '.pyi'})
    doc_delimiter = '"""'
    signature_tags = ('Args:', 'Returns:', 'Raises:', 'Yields:', ':param', ':return', ':rtype')
    _ROLES = {
        'module': NodeRole.ROOT,
        'comment': NodeRole.COMMENT,
        'function_definition': NodeRole.DEFINITION,
        'class_definition': NodeRole.DEFINITION,
        'decorated_definition': NodeRole.DEFINITION,
    }

    def query(self) -> str:
        return QUERY

    def role_of(self, node_type: str) -> NodeRole:
        return self._ROLES.get(node_type, NodeRole.OTHER)

    def symbol_kind(self, node_type: str) -> SymbolKind:
        return SymbolKind.CLASS if node_type == 'class_definition' else SymbolKind.FUNCTION

    def visibility_of(self, name: str) -> Visibility:
        return Visibility.INTERNAL if name.startswith('_') else Visibility.PUBLIC

    def split_delimiter(self, line: str, form: CommentForm) -> DelimiterSplit:
        indent = line[: len(line) - len(line.lstrip())]
        rest = line[len(indent) :]
        if form is CommentForm.DOC:
            delimiter, text, suffix = self._split_doc(rest)
            return DelimiterSplit(indent=indent, delimiter=delimiter, text=text, suffix=suffix)
        match = _HASH_DELIMITER.match(rest)
        if match is None:
            return DelimiterSplit(indent=indent, delimiter='', text=rest.rstrip())
        return DelimiterSplit(indent=indent, delimiter=match.group(1), text=rest[match.end() :].rstrip())

    def _split_doc(self, rest: str) -> tuple[str, str, str]:
        opening = _DOC_DELIMITER.match(rest)
        delimiter = opening.group(0) if opening else ''
        body = rest[len(delimiter) :]
        delimiter = opening.group(2) if opening else ''
        suffix = ''
        for candidate in (delimiter, '"""', "'''"):
            if candidate and body.endswith(candidate):
                suffix = candidate
                body = body[: -len(candidate)]
                break
        return delimiter, body.rstrip(), suffix


PYTHON = PythonProfile()
