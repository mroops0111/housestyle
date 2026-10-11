import typing

from ..models.comment import CommentGroup
from ..models.document import Document


class SourceParser(typing.Protocol):
    def supports(self, language_id: str) -> bool: ...

    def parse(self, document: Document) -> tuple[CommentGroup, ...]: ...
