import abc

from ..models.diagnostic import Diagnostic
from ..models.document import Document


class ExternalLinter(abc.ABC):
    name: str

    @abc.abstractmethod
    def is_available(self) -> bool: ...

    @abc.abstractmethod
    def run(self, document: Document) -> tuple[Diagnostic, ...]: ...
