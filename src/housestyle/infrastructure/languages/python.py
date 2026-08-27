import re

from ...domain.comment import CommentForm, Visibility


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
    line_width = 120
    signature_tags = ('Args:', 'Returns:', 'Raises:', 'Yields:', ':param', ':return', ':rtype')

    def query(self) -> str:
        return QUERY

    def visibility_of(self, name: str) -> Visibility:
        return Visibility.INTERNAL if name.startswith('_') else Visibility.PUBLIC

    def split_marker(self, line: str, form: CommentForm) -> tuple[str, str, str, str]:
        indent = line[: len(line) - len(line.lstrip())]
        rest = line[len(indent) :]
        if form is CommentForm.DOC:
            return (indent, *self._split_doc(rest))
        match = _HASH_MARKER.match(rest)
        if match is None:
            return indent, '', rest.rstrip(), ''
        return indent, match.group(1), rest[match.end() :].rstrip(), ''

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
