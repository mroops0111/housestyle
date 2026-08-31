import typing

from .comment import CommentGroup
from .document import Document


class SourceParser(typing.Protocol):
    def supports(self, language_id: str) -> bool: ...

    def parse(self, document: Document) -> tuple[CommentGroup, ...]: ...
