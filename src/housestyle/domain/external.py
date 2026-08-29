import typing

from .diagnostic import Diagnostic
from .document import Document


class ExternalLinter(typing.Protocol):
    @property
    def name(self) -> str: ...

    def is_available(self) -> bool: ...

    def run(self, document: Document) -> tuple[Diagnostic, ...]: ...
