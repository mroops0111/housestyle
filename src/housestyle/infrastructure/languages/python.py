import re

from ...domain.comment import CommentForm, Visibility
from .base import MarkerSplit


_DOC_DELIMITER = re.compile(r'^([rRbBuUfF]{0,2})("""|\'\'\')')
_HASH_MARKER = re.compile(r'^(#+\s?)')

QUERY = """
(comment) @comment
(module . (string) @docstring)
(function_definition body: (block . (string) @docstring))
(class_definition body: (block . (string) @docstring))
"""


class PythonProfile:
    language_id = 'python'
    extensions = frozenset({'.py', '.pyi'})
    doc_form_marker = '"""'
    signature_tags = ('Args:', 'Returns:', 'Raises:', 'Yields:', ':param', ':return', ':rtype')
    comment_node = 'comment'
    root_nodes = frozenset({'module'})
    definition_nodes = frozenset({'function_definition', 'class_definition', 'decorated_definition'})

    def query(self) -> str:
        return QUERY

    def symbol_kind(self, node_type: str) -> str:
        return 'class' if node_type == 'class_definition' else 'function'

    def visibility_of(self, name: str) -> Visibility:
        return Visibility.INTERNAL if name.startswith('_') else Visibility.PUBLIC

    def split_marker(self, line: str, form: CommentForm) -> MarkerSplit:
        indent = line[: len(line) - len(line.lstrip())]
        rest = line[len(indent) :]
        if form is CommentForm.DOC:
            marker, payload, suffix = self._split_doc(rest)
            return MarkerSplit(indent=indent, marker=marker, payload=payload, suffix=suffix)
        match = _HASH_MARKER.match(rest)
        if match is None:
            return MarkerSplit(indent=indent, marker='', payload=rest.rstrip())
        return MarkerSplit(indent=indent, marker=match.group(1), payload=rest[match.end() :].rstrip())

    def _split_doc(self, rest: str) -> tuple[str, str, str]:
        opening = _DOC_DELIMITER.match(rest)
        marker = opening.group(0) if opening else ''
        body = rest[len(marker) :]
        delimiter = opening.group(2) if opening else ''
        suffix = ''
        for candidate in (delimiter, '"""', "'''"):
            if candidate and body.endswith(candidate):
                suffix = candidate
                body = body[: -len(candidate)]
                break
        return marker, body.rstrip(), suffix


PYTHON = PythonProfile()
