import abc

from ..models.comment import CommentGroup
from ..models.document import Document


class SourceParser(abc.ABC):
    @abc.abstractmethod
    def supports(self, language_id: str) -> bool: ...

    @abc.abstractmethod
    def parse(self, document: Document) -> tuple[CommentGroup, ...]: ...
