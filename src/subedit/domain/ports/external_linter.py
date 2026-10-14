import abc

from ..models.diagnostic import Diagnostic
from ..models.document import Document


class ExternalLinter(abc.ABC):
    name: str

    @abc.abstractmethod
    def is_available(self) -> bool: ...

    @abc.abstractmethod
    def run(self, document: Document) -> tuple[Diagnostic, ...]: ...

    def prepare(self) -> None:  # noqa: B027, an optional hook rather than a required one
        """Fetch what the tool needs, for a caller that can afford to wait. Most tools need nothing."""
